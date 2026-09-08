#!/usr/bin/env python3
"""Measure answer drift across prompt wording while image and schema stay fixed."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"
SERVER_BIN = PROJECT_DIR / "worktrees/llama.cpp/build-release-metal/bin/llama-server"
MODEL_CACHE = os.environ.get(
    "LLAMA_CACHE", str(Path.home() / "Documents/AI-Models/huggingface")
)
PORT = int(os.environ.get("PROMPT_ROBUSTNESS_PORT", "8094"))
BASE_URL = f"http://127.0.0.1:{PORT}"


CHART_IMAGE = PROJECT_DIR / "tests/fixtures/reasoning/28-quarterly-revenue-bars.png"
ACTION_IMAGE = PROJECT_DIR / "tests/fixtures/natural/source-zidane.jpg"

CHART_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "q1": {"type": "integer"},
        "q2": {"type": "integer"},
        "q3": {"type": "integer"},
        "q4": {"type": "integer"},
        "q2_to_q3_decreased": {"type": "boolean"},
    },
    "required": ["q1", "q2", "q3", "q4", "q2_to_q3_decreased"],
}
CHART_EXPECTED = {
    "q1": 12,
    "q2": 18,
    "q3": 15,
    "q4": 27,
    "q2_to_q3_decreased": True,
}

ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "people_count": {"type": "integer"},
        "foreground_action": {
            "type": "string",
            "enum": ["pointing", "clapping", "waving", "unknown"],
        },
        "pointing_direction": {
            "type": "string",
            "enum": ["image_left", "image_right", "unknown"],
        },
    },
    "required": ["people_count", "foreground_action", "pointing_direction"],
}
ACTION_EXPECTED = {
    "people_count": 2,
    "foreground_action": "pointing",
    "pointing_direction": "image_right",
}


CASES: list[dict[str, Any]] = [
    {
        "id": "PR-CHART-ZH-CONCISE",
        "task": "chart",
        "style": "zh_concise",
        "image": CHART_IMAGE,
        "prompt": "读取柱状图，返回 Q1 至 Q4 的数值，并判断从 Q2 到 Q3 是否下降。",
        "schema": CHART_SCHEMA,
        "expected": CHART_EXPECTED,
    },
    {
        "id": "PR-CHART-ZH-DEFINED",
        "task": "chart",
        "style": "zh_defined",
        "image": CHART_IMAGE,
        "prompt": (
            "读取柱状图并返回 Q1 至 Q4 的数值。这里的‘从 Q2 到 Q3 下降’严格定义为 Q3 数值小于 Q2；"
            "请按这个定义填写 q2_to_q3_decreased。"
        ),
        "schema": CHART_SCHEMA,
        "expected": CHART_EXPECTED,
    },
    {
        "id": "PR-CHART-EN-DEFINED",
        "task": "chart",
        "style": "en_defined",
        "image": CHART_IMAGE,
        "prompt": (
            "Read the Q1 through Q4 values from the bar chart. Set q2_to_q3_decreased to true "
            "exactly when the numeric Q3 value is smaller than the numeric Q2 value."
        ),
        "schema": CHART_SCHEMA,
        "expected": CHART_EXPECTED,
    },
    {
        "id": "PR-CHART-ZH-EVIDENCE",
        "task": "chart",
        "style": "zh_evidence_first",
        "image": CHART_IMAGE,
        "prompt": (
            "先逐项读取 Q1、Q2、Q3、Q4。然后比较已经读取的 Q3 与 Q2：若 Q3 < Q2，"
            "q2_to_q3_decreased 必须为 true，否则为 false。只输出所要求的结构。"
        ),
        "schema": CHART_SCHEMA,
        "expected": CHART_EXPECTED,
    },
    {
        "id": "PR-ACTION-ZH-CONCISE",
        "task": "action",
        "style": "zh_concise",
        "image": ACTION_IMAGE,
        "prompt": "返回可见人数、前景人物的主要动作，以及动作朝向的画面方向。",
        "schema": ACTION_SCHEMA,
        "expected": ACTION_EXPECTED,
    },
    {
        "id": "PR-ACTION-ZH-DEFINED",
        "task": "action",
        "style": "zh_defined",
        "image": ACTION_IMAGE,
        "prompt": (
            "返回可见人数、前景人物动作和方向。只有双手彼此接触才可标为 clapping；"
            "若手臂伸出且食指朝某侧，应标为 pointing，并使用画面左右方向。"
        ),
        "schema": ACTION_SCHEMA,
        "expected": ACTION_EXPECTED,
    },
    {
        "id": "PR-ACTION-EN-PLAIN",
        "task": "action",
        "style": "en_plain",
        "image": ACTION_IMAGE,
        "prompt": (
            "Return the visible number of people, the foreground person's main action, "
            "and the image-relative direction of that action. Do not identify either person."
        ),
        "schema": ACTION_SCHEMA,
        "expected": ACTION_EXPECTED,
    },
    {
        "id": "PR-ACTION-ZH-EVIDENCE",
        "task": "action",
        "style": "zh_evidence_first",
        "image": ACTION_IMAGE,
        "prompt": (
            "先在内部检查前景人物的手臂是否伸出、食指朝向哪里、双手是否接触；"
            "再根据这些可见证据返回人数、主要动作和画面方向。只输出所要求的结构。"
        ),
        "schema": ACTION_SCHEMA,
        "expected": ACTION_EXPECTED,
    },
]


def emit(lines: list[str], value: str = "") -> None:
    print(value, flush=True)
    lines.append(value)


def health_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=0.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def wait_for_server(process: subprocess.Popen[bytes]) -> float:
    started = time.perf_counter()
    for _ in range(120):
        if health_ready():
            return time.perf_counter() - started
        if process.poll() is not None:
            raise RuntimeError("llama-server exited before becoming ready")
        time.sleep(0.25)
    raise RuntimeError("llama-server did not become ready within 30 seconds")


def parse_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    text = content.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[len("```json") : -len("```")].strip()
    return json.loads(text)


def request_case(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], float]:
    image_path: Path = case["image"]
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = {
        "model": "qwen3-vl-8b",
        "messages": [
            {
                "role": "system",
                "content": "Use only visible evidence and use image-relative left and right.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_data}"},
                    },
                    {"type": "text", "text": case["prompt"]},
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 256,
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_effort": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": case["id"].lower().replace("-", "_"),
                "strict": True,
                "schema": case["schema"],
            },
        },
    }
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = json.loads(response.read())
    elapsed = time.perf_counter() - started
    if "error" in raw:
        raise RuntimeError(f"API error for {case['id']}: {raw['error']}")
    return raw, parse_content(raw["choices"][0]["message"]["content"]), elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", choices=("normal", "reverse"), default="normal")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = list(CASES)
    if args.order == "reverse":
        cases.reverse()
    suffix = "" if args.order == "normal" else "-reverse"
    server_log_path = RESULTS_DIR / f"prompt-robustness-server{suffix}.log"
    summary_log_path = RESULTS_DIR / f"prompt-robustness-latest{suffix}.log"

    if not SERVER_BIN.is_file() or not os.access(SERVER_BIN, os.X_OK):
        raise RuntimeError(f"missing llama-server: {SERVER_BIN}")
    if health_ready():
        raise RuntimeError(f"port {PORT} already has a healthy service")

    env = os.environ.copy()
    env["LLAMA_CACHE"] = MODEL_CACHE
    command = [
        str(SERVER_BIN),
        "-hf",
        "Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M",
        "--alias",
        "qwen3-vl-8b",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "-ngl",
        "all",
        "-fa",
        "on",
        "-c",
        "8192",
        "-np",
        "1",
        "--no-warmup",
        "--reasoning",
        "off",
    ]

    lines: list[str] = []
    passed_by_task: dict[str, int] = defaultdict(int)
    total_by_task: dict[str, int] = defaultdict(int)
    results_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_passed = True
    with server_log_path.open("w", encoding="utf-8") as server_log:
        process = subprocess.Popen(command, env=env, stdout=server_log, stderr=subprocess.STDOUT)
        try:
            emit(lines, f"server_ready_seconds={wait_for_server(process):.3f}")
            for case in cases:
                emit(lines)
                emit(lines, f"===== {case['id']} =====")
                raw, parsed, elapsed = request_case(case)
                output_path = RESULTS_DIR / f"prompt-robustness-{case['id'].lower()}{suffix}.json"
                output_path.write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                passed = parsed == case["expected"]
                total_by_task[case["task"]] += 1
                passed_by_task[case["task"]] += int(passed)
                results_by_task[case["task"]].append(parsed)
                all_passed = all_passed and passed
                emit(lines, f"style={case['style']}")
                emit(lines, json.dumps(parsed, ensure_ascii=False, sort_keys=True))
                emit(lines, f"elapsed_seconds={elapsed:.6f}")
                emit(lines, f"result={'PASS' if passed else 'FAIL'}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    emit(lines)
    for task in sorted(total_by_task):
        unique_answers = len(
            {json.dumps(value, ensure_ascii=False, sort_keys=True) for value in results_by_task[task]}
        )
        emit(
            lines,
            f"task={task} passed={passed_by_task[task]}/{total_by_task[task]} unique_answers={unique_answers}",
        )
    emit(lines, f"all_cases_passed={'yes' if all_passed else 'no'}")
    summary_log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
