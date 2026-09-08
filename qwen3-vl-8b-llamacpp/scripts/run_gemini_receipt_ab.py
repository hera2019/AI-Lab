#!/usr/bin/env python3

import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
IMAGE_PATH = PROJECT_DIR / "tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg"
OCR_PATH = PROJECT_DIR / "results/apple-vision-receipt-ocr.json"
BUILDER_PATH = PROJECT_DIR / "scripts/build_hybrid_receipt_request.py"
VALIDATOR_PATH = PROJECT_DIR / "scripts/validate_hybrid_receipt_responses.py"
RESULTS_DIR = PROJECT_DIR / "results"
DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


class GeminiHTTPError(RuntimeError):
    def __init__(self, code: int, body: str) -> None:
        super().__init__(f"Gemini HTTP {code}: {body}")
        self.code = code
        self.body = body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Gemini receipt extraction with the local Qwen result."
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", "gemini-3.7-flash"),
        help="Gemini model ID (default: gemini-3.7-flash)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        choices=(1, 2, 3),
        help="Number of paid/free-tier API requests (default: 1)",
    )
    parser.add_argument(
        "--thinking-level",
        choices=("low", "medium", "high"),
        default="low",
        help="Gemini thinking level (default: low)",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=1,
        choices=(1, 2, 3, 4, 5),
        help="Attempts per run for temporary 429/5xx errors (default: 1)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5.0,
        help="Initial retry delay in seconds; doubles after each failure (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and inspect the request without reading a key or using the network.",
    )
    return parser.parse_args()


def build_local_request(output_path: Path) -> dict[str, Any]:
    subprocess.run(
        [
            sys.executable,
            str(BUILDER_PATH),
            "--image",
            str(IMAGE_PATH),
            "--ocr",
            str(OCR_PATH),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def build_gemini_request(
    local_request: dict[str, Any], model: str, thinking_level: str
) -> dict[str, Any]:
    user_content = local_request["messages"][1]["content"]
    image_url = user_content[0]["image_url"]["url"]
    header, image_data = image_url.split(",", 1)
    mime_type = header.removeprefix("data:").split(";", 1)[0]
    schema = local_request["response_format"]["json_schema"]["schema"]

    return {
        "model": model,
        "system_instruction": local_request["messages"][0]["content"],
        "input": [
            {"type": "text", "text": user_content[1]["text"]},
            {
                "type": "image",
                "data": image_data,
                "mime_type": mime_type,
            },
        ],
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
        "generation_config": {
            "thinking_level": thinking_level,
            "max_output_tokens": 2048,
        },
        "store": False,
    }


def read_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        return api_key
    if sys.stdin.isatty():
        api_key = getpass.getpass("Gemini API key (hidden, not saved): ").strip()
        if api_key:
            return api_key
    raise RuntimeError(
        "GEMINI_API_KEY is not configured. Run this script in Terminal to enter it "
        "at the hidden prompt, or export GEMINI_API_KEY for this shell session."
    )


def request_gemini(
    endpoint: str, api_key: str, payload: bytes, timeout: float
) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "qwen3-vl-receipt-ab/1.0",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise GeminiHTTPError(error.code, body) from error
    elapsed = time.perf_counter() - started
    return json.loads(body), elapsed


def extract_output_text(response: dict[str, Any]) -> str:
    for step in reversed(response.get("steps", [])):
        if step.get("type") != "model_output":
            continue
        parts = [
            block.get("text", "")
            for block in step.get("content", [])
            if block.get("type") == "text"
        ]
        if parts:
            return "".join(parts)
    raise ValueError("Gemini response has no text model_output step")


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    endpoint = os.environ.get("GEMINI_INTERACTIONS_URL", DEFAULT_ENDPOINT)

    with tempfile.TemporaryDirectory(prefix="gemini-receipt-ab.") as temp_dir:
        local_request = build_local_request(Path(temp_dir) / "local-request.json")
        request_body = build_gemini_request(
            local_request, args.model, args.thinking_level
        )
        payload = json.dumps(
            request_body, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    print(f"model={args.model}")
    print(f"thinking_level={args.thinking_level}")
    print(f"request_bytes={len(payload)}")
    print(f"runs={args.runs}")
    print(f"max_attempts={args.max_attempts}")
    if args.dry_run:
        print("dry_run=yes")
        print("network_request_sent=no")
        return 0

    api_key = read_api_key()
    response_paths: list[Path] = []
    timing_lines: list[str] = []
    for run_number in range(1, args.runs + 1):
        run_started = time.perf_counter()
        raw_response: dict[str, Any] | None = None
        request_elapsed = 0.0
        attempts_used = 0
        for attempt in range(1, args.max_attempts + 1):
            attempts_used = attempt
            try:
                raw_response, request_elapsed = request_gemini(
                    endpoint, api_key, payload, args.timeout
                )
                break
            except GeminiHTTPError as error:
                if (
                    error.code not in RETRYABLE_HTTP_CODES
                    or attempt == args.max_attempts
                ):
                    raise
                delay = args.retry_delay * (2 ** (attempt - 1))
                print(
                    f"run_{run_number}_attempt_{attempt}=temporary_http_{error.code}; "
                    f"retry_in_seconds={delay:g}",
                    flush=True,
                )
                time.sleep(delay)
        if raw_response is None:
            raise RuntimeError("Gemini request ended without a response")
        elapsed = time.perf_counter() - run_started
        raw_path = RESULTS_DIR / f"gemini-receipt-raw-{run_number}.json"
        response_path = RESULTS_DIR / f"gemini-receipt-response-{run_number}.json"
        write_json(raw_path, raw_response)

        content = extract_output_text(raw_response)
        compatible_response = {
            "provider": "google-gemini-interactions",
            "provider_response_id": raw_response.get("id"),
            "model": raw_response.get("model", args.model),
            "choices": [
                {"message": {"role": "assistant", "content": content}}
            ],
            "timings": {
                "wall_seconds": round(elapsed, 6),
                "successful_request_seconds": round(request_elapsed, 6),
                "attempts": attempts_used,
            },
            "usage": raw_response.get("usage", {}),
        }
        write_json(response_path, compatible_response)
        response_paths.append(response_path)
        timing_lines.append(
            f"run_{run_number}_seconds={elapsed:.6f} attempts={attempts_used}"
        )
        print(timing_lines[-1])

    validation = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), *map(str, response_paths)],
        check=False,
        text=True,
        capture_output=True,
    )
    summary = "\n".join(
        [
            f"model={args.model}",
            f"thinking_level={args.thinking_level}",
            *timing_lines,
            "",
            validation.stdout.rstrip(),
            "",
        ]
    )
    (RESULTS_DIR / "gemini-receipt-api-latest.log").write_text(
        summary, encoding="utf-8"
    )
    print()
    print(validation.stdout, end="")
    if validation.stderr:
        print(validation.stderr, file=sys.stderr, end="")
    return validation.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
