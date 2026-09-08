#!/usr/bin/env python3
"""Run exact-scored natural-scene reliability cases against llama-server."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_DIR / "tests/fixtures/natural"
RESULTS_DIR = PROJECT_DIR / "results"
SERVER_BIN = PROJECT_DIR / "worktrees/llama.cpp/build-release-metal/bin/llama-server"
SERVER_LOG = RESULTS_DIR / "natural-scene-server.log"
SUMMARY_LOG = RESULTS_DIR / "natural-scene-latest.log"
MODEL_CACHE = os.environ.get(
    "LLAMA_CACHE", str(Path.home() / "Documents/AI-Models/huggingface")
)
PORT = int(os.environ.get("NATURAL_SCENE_PORT", "8093"))
BASE_URL = f"http://127.0.0.1:{PORT}"


CASES: list[dict[str, Any]] = [
    {
        "id": "NAT-001",
        "file": "source-bus.jpg",
        "prompt": (
            "分析街头照片中的前景行人。统计所有可见行人，包括被左右画面边缘截断的人；"
            "不要把车窗反射或车内模糊影子算作行人。分别返回完整可见与边缘截断人数，"
            "并统计公交车，判断是否出现自行车。"
        ),
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "person_count": {"type": "integer"},
                "fully_visible_people": {"type": "integer"},
                "edge_cropped_people": {"type": "integer"},
                "bus_count": {"type": "integer"},
                "bicycle_present": {"type": "boolean"},
            },
            "required": [
                "person_count",
                "fully_visible_people",
                "edge_cropped_people",
                "bus_count",
                "bicycle_present",
            ],
        },
        "expected": {
            "person_count": 4,
            "fully_visible_people": 2,
            "edge_cropped_people": 2,
            "bus_count": 1,
            "bicycle_present": False,
        },
    },
    {
        "id": "NAT-002",
        "file": "source-zidane.jpg",
        "prompt": (
            "只按画面坐标描述，不识别人名。返回可见人数、前景人物的主要动作和手指指向，"
            "以及背景人物相对前景人物位于画面左侧还是右侧。"
        ),
        "schema": {
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
                "background_person_position": {
                    "type": "string",
                    "enum": ["image_left", "image_right", "unknown"],
                },
            },
            "required": [
                "people_count",
                "foreground_action",
                "pointing_direction",
                "background_person_position",
            ],
        },
        "expected": {
            "people_count": 2,
            "foreground_action": "pointing",
            "pointing_direction": "image_right",
            "background_person_position": "image_right",
        },
    },
    {
        "id": "NAT-002-DIAGNOSTIC",
        "file": "source-zidane.jpg",
        "prompt": (
            "观察前景人物伸出的右臂和手。分别判断手臂是否向画面右侧伸出、食指是否指向右侧、"
            "双手是否彼此接触，然后根据这些可见事实选择主要动作。"
        ),
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "right_arm_extended": {"type": "boolean"},
                "index_finger_points_right": {"type": "boolean"},
                "hands_touching": {"type": "boolean"},
                "action": {
                    "type": "string",
                    "enum": ["pointing", "clapping", "waving", "unknown"],
                },
            },
            "required": [
                "right_arm_extended",
                "index_finger_points_right",
                "hands_touching",
                "action",
            ],
        },
        "expected": {
            "right_arm_extended": True,
            "index_finger_points_right": True,
            "hands_touching": False,
            "action": "pointing",
        },
    },
    {
        "id": "NAT-003",
        "file": "34-zidane-tie-occluded.png",
        "prompt": (
            "前景人物胸前有一块不透明遮挡。判断他的领带是否仍可见；"
            "如果领带被完全遮住，颜色必须返回 UNKNOWN，不要根据原图知识、服装或周围像素猜测。"
        ),
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "people_count": {"type": "integer"},
                "foreground_tie_visible": {"type": "boolean"},
                "foreground_tie_color": {
                    "type": "string",
                    "enum": ["BLACK", "BLUE", "GRAY", "GREEN", "RED", "WHITE", "UNKNOWN"],
                },
            },
            "required": ["people_count", "foreground_tie_visible", "foreground_tie_color"],
        },
        "expected": {
            "people_count": 2,
            "foreground_tie_visible": False,
            "foreground_tie_color": "UNKNOWN",
        },
    },
    {
        "id": "NAT-004",
        "file": "35-bus-route-display-occluded.png",
        "prompt": (
            "公交车前方路线显示屏被不透明区域遮住。分别判断路线显示屏文字能否读取，"
            "以及车身侧面靠近交通标志的城市品牌文字。被遮住的路线文字必须返回 UNKNOWN，"
            "不能用车身其他文字推测路线目的地。"
        ),
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "route_display_readable": {"type": "boolean"},
                "route_display_text": {"type": "string"},
                "city_branding_visible": {"type": "boolean"},
                "city_branding_text": {"type": "string"},
            },
            "required": [
                "route_display_readable",
                "route_display_text",
                "city_branding_visible",
                "city_branding_text",
            ],
        },
        "expected": {
            "route_display_readable": False,
            "route_display_text": "UNKNOWN",
            "city_branding_visible": True,
            "city_branding_text": "EMT MADRID",
        },
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
    image_path = FIXTURE_DIR / case["file"]
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = {
        "model": "qwen3-vl-8b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Use only visible evidence. Never guess obscured, cropped, blurred, or unreadable details. "
                    "Use image-relative left and right, not a person's perspective."
                ),
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
    parsed = parse_content(raw["choices"][0]["message"]["content"])
    return raw, parsed, elapsed


def main() -> int:
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
    all_passed = True
    with SERVER_LOG.open("w", encoding="utf-8") as server_log:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            emit(lines, f"server_ready_seconds={wait_for_server(process):.3f}")
            for case in CASES:
                emit(lines)
                emit(lines, f"===== {case['id']} =====")
                raw, parsed, elapsed = request_case(case)
                response_path = RESULTS_DIR / f"natural-scene-{case['id'].lower()}.json"
                response_path.write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                emit(lines, json.dumps(parsed, ensure_ascii=False, sort_keys=True))
                emit(lines, f"elapsed_seconds={elapsed:.6f}")
                timings = raw.get("timings", {})
                if timings:
                    emit(lines, "timings=" + json.dumps(timings, sort_keys=True))
                expected = case["expected"]
                passed = parsed == expected
                emit(lines, "expected=" + json.dumps(expected, ensure_ascii=False, sort_keys=True))
                emit(lines, f"result={'PASS' if passed else 'FAIL'}")
                all_passed = all_passed and passed
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    emit(lines)
    emit(lines, f"all_cases_passed={'yes' if all_passed else 'no'}")
    SUMMARY_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
