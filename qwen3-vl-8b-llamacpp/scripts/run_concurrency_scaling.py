#!/usr/bin/env python3
"""Benchmark 1/2/4 concurrent multimodal requests with exact response routing checks."""

from __future__ import annotations

import base64
import json
import os
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"
SERVER_BIN = PROJECT_DIR / "worktrees/llama.cpp/build-release-metal/bin/llama-server"
IMAGE_PATH = PROJECT_DIR / "tests/fixtures/reasoning/29-release-operations-dashboard.png"
MODEL_CACHE = os.environ.get(
    "LLAMA_CACHE", str(Path.home() / "Documents/AI-Models/huggingface")
)
PORT = int(os.environ.get("CONCURRENCY_TEST_PORT", "8095"))
BASE_URL = f"http://127.0.0.1:{PORT}"
LEVELS = (1, 2, 4)


def health_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=0.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def wait_for_server(process: subprocess.Popen[bytes]) -> float:
    started = time.perf_counter()
    for _ in range(180):
        if health_ready():
            return time.perf_counter() - started
        if process.poll() is not None:
            raise RuntimeError("llama-server exited before becoming ready")
        time.sleep(0.25)
    raise RuntimeError("llama-server did not become ready within 45 seconds")


def parse_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    text = content.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[len("```json") : -len("```")].strip()
    return json.loads(text)


def rss_kib(pid: int) -> int | None:
    result = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


def swap_usage() -> str:
    result = subprocess.run(
        ["sysctl", "-n", "vm.swapusage"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or result.stderr.strip() or "unavailable"


class MemorySampler:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.samples: list[int] = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            value = rss_kib(self.pid)
            if value is not None:
                self.samples.append(value)
            self.stop_event.wait(0.1)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
        value = rss_kib(self.pid)
        if value is not None:
            self.samples.append(value)

    @property
    def peak_kib(self) -> int | None:
        return max(self.samples) if self.samples else None


def make_request_body(request_id: str, image_data: str) -> bytes:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "request_id": {"type": "string", "enum": [request_id]},
            "deployments": {"type": "integer"},
            "healthy": {"type": "integer"},
            "failed": {"type": "integer"},
        },
        "required": ["request_id", "deployments", "healthy", "failed"],
    }
    body = {
        "model": "qwen3-vl-8b",
        "messages": [
            {
                "role": "system",
                "content": "Read only the visible dashboard and preserve the supplied request ID.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64," + image_data},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Return request_id {request_id} and read Deployments, Healthy, and Failed."
                        ),
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_effort": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "concurrency_" + request_id.lower().replace("-", "_"),
                "strict": True,
                "schema": schema,
            },
        },
    }
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def send_request(
    request_id: str, image_data: str, barrier: threading.Barrier
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=make_request_body(request_id, image_data),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    barrier.wait(timeout=10)
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = json.loads(response.read())
    elapsed = time.perf_counter() - started
    if "error" in raw:
        raise RuntimeError(f"API error for {request_id}: {raw['error']}")
    parsed = parse_content(raw["choices"][0]["message"]["content"])
    expected = {
        "request_id": request_id,
        "deployments": 12,
        "healthy": 9,
        "failed": 1,
    }
    return {
        "request_id": request_id,
        "elapsed_seconds": elapsed,
        "passed": parsed == expected,
        "parsed": parsed,
        "expected": expected,
        "usage": raw.get("usage", {}),
        "timings": raw.get("timings", {}),
        "raw": raw,
    }


def run_level(level: int, image_data: str) -> dict[str, Any]:
    server_log_path = RESULTS_DIR / f"concurrency-c{level}-server.log"
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
        "16384",
        "-np",
        "4",
        "--no-warmup",
        "--reasoning",
        "off",
    ]

    with server_log_path.open("w", encoding="utf-8") as server_log:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            ready_seconds = wait_for_server(process)
            baseline_rss = rss_kib(process.pid)
            swap_before = swap_usage()
            sampler = MemorySampler(process.pid)
            barrier = threading.Barrier(level)
            sampler.start()
            batch_started = time.perf_counter()
            results: list[dict[str, Any]] = []
            errors: list[str] = []
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = {
                    executor.submit(
                        send_request,
                        f"C{level}-R{index}",
                        image_data,
                        barrier,
                    ): index
                    for index in range(1, level + 1)
                }
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as error:  # noqa: BLE001 - preserve all batch failures
                        errors.append(f"request_{futures[future]}: {error}")
            batch_seconds = time.perf_counter() - batch_started
            sampler.stop()
            swap_after = swap_usage()
            results.sort(key=lambda item: item["request_id"])

            for result in results:
                raw_path = RESULTS_DIR / (
                    f"concurrency-c{level}-{result['request_id'].lower()}-raw.json"
                )
                raw_path.write_text(
                    json.dumps(result.pop("raw"), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

            latencies = [result["elapsed_seconds"] for result in results]
            passed_count = sum(int(result["passed"]) for result in results)
            peak_rss = sampler.peak_kib
            return {
                "concurrency": level,
                "server_ready_seconds": ready_seconds,
                "batch_seconds": batch_seconds,
                "requests_per_second": level / batch_seconds,
                "completed": len(results),
                "passed": passed_count,
                "errors": errors,
                "latency_min_seconds": min(latencies) if latencies else None,
                "latency_mean_seconds": statistics.fmean(latencies) if latencies else None,
                "latency_max_seconds": max(latencies) if latencies else None,
                "baseline_rss_mib": baseline_rss / 1024 if baseline_rss is not None else None,
                "peak_rss_mib": peak_rss / 1024 if peak_rss is not None else None,
                "rss_growth_mib": (
                    (peak_rss - baseline_rss) / 1024
                    if peak_rss is not None and baseline_rss is not None
                    else None
                ),
                "swap_before": swap_before,
                "swap_after": swap_after,
                "requests": results,
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def format_number(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.3f}"


def main() -> int:
    if not SERVER_BIN.is_file() or not os.access(SERVER_BIN, os.X_OK):
        raise RuntimeError(f"missing llama-server: {SERVER_BIN}")
    if not IMAGE_PATH.is_file():
        raise RuntimeError(f"missing test image: {IMAGE_PATH}")
    if health_ready():
        raise RuntimeError(f"port {PORT} already has a healthy service")

    image_data = base64.b64encode(IMAGE_PATH.read_bytes()).decode("ascii")
    summary: dict[str, Any] = {
        "model": "Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M",
        "server_parallel_slots": 4,
        "server_total_context": 16384,
        "levels": [],
    }
    all_passed = True
    for level in LEVELS:
        print(f"\n===== concurrency={level} =====", flush=True)
        result = run_level(level, image_data)
        summary["levels"].append(result)
        all_passed = (
            all_passed
            and not result["errors"]
            and result["completed"] == level
            and result["passed"] == level
        )
        print(
            " ".join(
                [
                    f"completed={result['completed']}/{level}",
                    f"passed={result['passed']}/{level}",
                    f"batch_seconds={result['batch_seconds']:.3f}",
                    f"requests_per_second={result['requests_per_second']:.3f}",
                    f"latency_mean_seconds={format_number(result['latency_mean_seconds'])}",
                    f"latency_max_seconds={format_number(result['latency_max_seconds'])}",
                    f"baseline_rss_mib={format_number(result['baseline_rss_mib'])}",
                    f"peak_rss_mib={format_number(result['peak_rss_mib'])}",
                    f"rss_growth_mib={format_number(result['rss_growth_mib'])}",
                ]
            ),
            flush=True,
        )
        print(f"swap_before={result['swap_before']}", flush=True)
        print(f"swap_after={result['swap_after']}", flush=True)
        if result["errors"]:
            print("errors=" + json.dumps(result["errors"], ensure_ascii=False), flush=True)

    summary["all_passed"] = all_passed
    summary_path = RESULTS_DIR / "concurrency-scaling-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nsummary={summary_path.relative_to(PROJECT_DIR)}", flush=True)
    print(f"all_passed={'yes' if all_passed else 'no'}", flush=True)
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
