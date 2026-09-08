#!/usr/bin/env python3
"""Run and score the clean multilingual Whisper Phase 1 baseline."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
RESULTS_DIR = PROJECT_DIR / "results"
MANIFEST_PATH = AUDIO_DIR / "manifest.json"
CLI = PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-cli"
MODEL = Path(
    os.environ.get(
        "WHISPER_MODEL",
        str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin"),
    )
)


def normalized_characters(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return [
        char
        for char in normalized
        if not unicodedata.category(char).startswith(("P", "S", "Z"))
        and not char.isspace()
    ]


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).lower())


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for row, left_item in enumerate(left, start=1):
        current = [row]
        for column, right_item in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def score_text(expected: str, actual: str, language: str) -> dict[str, Any]:
    if language == "en":
        expected_units = normalized_words(expected)
        actual_units = normalized_words(actual)
        metric = "WER"
    else:
        expected_units = normalized_characters(expected)
        actual_units = normalized_characters(actual)
        metric = "CER"
    distance = edit_distance(expected_units, actual_units)
    denominator = max(len(expected_units), 1)
    return {
        "metric": metric,
        "edit_distance": distance,
        "reference_units": len(expected_units),
        "error_rate": distance / denominator,
        "normalized_exact": expected_units == actual_units,
    }


def parse_timing_ms(log: str, label: str) -> float | None:
    pattern = rf"whisper_print_timings:\s+{re.escape(label)} time\s+=\s+([0-9.]+) ms"
    match = re.search(pattern, log)
    return float(match.group(1)) if match else None


def parse_max_rss_bytes(log: str) -> int | None:
    match = re.search(r"^\s*([0-9]+)\s+maximum resident set size\s*$", log, re.MULTILINE)
    return int(match.group(1)) if match else None


def expected_text(case: dict[str, Any]) -> str:
    if "text" in case:
        return case["text"]
    return " ".join(case["text_segments"])


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case["id"].lower()
    audio_path = AUDIO_DIR / case["file"]
    output_base = RESULTS_DIR / f"phase1-{case_id}"
    for suffix in (".txt", ".json"):
        path = Path(str(output_base) + suffix)
        if path.exists():
            path.unlink()

    language = case["language"] if case["language"] in {"zh", "ja", "en"} else "auto"
    command = [
        "/usr/bin/time",
        "-lp",
        str(CLI),
        "--model",
        str(MODEL),
        "--file",
        str(audio_path),
        "--language",
        language,
        "--threads",
        "8",
        "--output-txt",
        "--output-json",
        "--output-file",
        str(output_base),
        "--no-timestamps",
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    combined_log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase1-{case_id}.log").write_text(combined_log, encoding="utf-8")

    text_path = Path(str(output_base) + ".txt")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    reference = expected_text(case)
    score = score_text(reference, actual, case["language"])
    total_ms = parse_timing_ms(combined_log, "total")
    duration = float(case["duration_seconds"])
    max_rss = parse_max_rss_bytes(combined_log)
    return {
        "id": case["id"],
        "language_argument": language,
        "audio_file": case["file"],
        "audio_duration_seconds": duration,
        "exit_code": process.returncode,
        "expected": reference,
        "actual": actual,
        "score": score,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": max_rss,
        "metal_log_detected": "ggml_metal" in combined_log.lower(),
        "critical_values": case.get("critical_values", []),
    }


def main() -> int:
    if not CLI.is_file() or not os.access(CLI, os.X_OK):
        raise RuntimeError(f"missing executable: {CLI}")
    if not MODEL.is_file():
        raise RuntimeError(f"missing model: {MODEL}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    summary: dict[str, Any] = {
        "model": str(MODEL),
        "model_size_bytes": MODEL.stat().st_size,
        "cases": [],
    }
    all_commands_ok = True
    for case in manifest["cases"]:
        print(f"\n===== {case['id']} =====", flush=True)
        result = run_case(case)
        summary["cases"].append(result)
        all_commands_ok = all_commands_ok and result["exit_code"] == 0
        print(f"actual={result['actual']!r}", flush=True)
        print(
            f"{result['score']['metric']}={result['score']['error_rate']:.4f} "
            f"edit_distance={result['score']['edit_distance']} "
            f"normalized_exact={'yes' if result['score']['normalized_exact'] else 'no'}",
            flush=True,
        )
        print(
            f"wall_seconds={result['wall_seconds']:.3f} "
            f"wall_rtf={result['wall_realtime_factor']:.3f} "
            f"whisper_rtf={result['whisper_realtime_factor']:.3f} "
            f"metal_log={'yes' if result['metal_log_detected'] else 'no'}",
            flush=True,
        )

    summary["all_commands_ok"] = all_commands_ok
    output_path = RESULTS_DIR / "phase1-clean-baseline-summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nsummary={output_path.relative_to(PROJECT_DIR)}", flush=True)
    print(f"all_commands_ok={'yes' if all_commands_ok else 'no'}", flush=True)
    return 0 if all_commands_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
