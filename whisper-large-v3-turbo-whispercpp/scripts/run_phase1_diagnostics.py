#!/usr/bin/env python3
"""Measure a warm repeat and diagnose the mixed-language baseline."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from run_phase1_clean_baseline import parse_max_rss_bytes, parse_timing_ms


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
RESULTS_DIR = PROJECT_DIR / "results"
CLI = PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-cli"
MODEL = Path(
    os.environ.get(
        "WHISPER_MODEL",
        str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin"),
    )
)


CASES = [
    {
        "id": "ZH-WARM-REPEAT",
        "file": "asr-zh-001.wav",
        "language": "zh",
        "duration_seconds": 8.608,
        "purpose": "separate one-time Metal startup cost from normal transcription speed",
    },
    {
        "id": "MIX-SEG-ZH",
        "file": "mix-zh.wav",
        "language": "zh",
        "duration_seconds": 2.255063,
        "expected": "项目代号是海风七号。",
    },
    {
        "id": "MIX-SEG-JA",
        "file": "mix-ja.wav",
        "language": "ja",
        "duration_seconds": 2.649813,
        "expected": "次の会議は東京で開きます。",
    },
    {
        "id": "MIX-SEG-EN",
        "file": "mix-en.wav",
        "language": "en",
        "duration_seconds": 2.32,
        "expected": "Please upload the final report by Friday.",
    },
]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_slug = case["id"].lower()
    output_base = RESULTS_DIR / f"phase1-diagnostic-{case_slug}"
    text_path = Path(str(output_base) + ".txt")
    if text_path.exists():
        text_path.unlink()

    command = [
        "/usr/bin/time",
        "-lp",
        str(CLI),
        "--model",
        str(MODEL),
        "--file",
        str(AUDIO_DIR / case["file"]),
        "--language",
        case["language"],
        "--threads",
        "8",
        "--output-txt",
        "--output-file",
        str(output_base),
        "--no-timestamps",
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase1-diagnostic-{case_slug}.log").write_text(
        log, encoding="utf-8"
    )
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    total_ms = parse_timing_ms(log, "total")
    duration = float(case["duration_seconds"])
    return {
        **case,
        "actual": actual,
        "exit_code": process.returncode,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
    }


def main() -> int:
    if not CLI.is_file() or not os.access(CLI, os.X_OK):
        raise RuntimeError(f"missing executable: {CLI}")
    if not MODEL.is_file():
        raise RuntimeError(f"missing model: {MODEL}")

    results = []
    for case in CASES:
        print(f"\n===== {case['id']} =====", flush=True)
        result = run_case(case)
        results.append(result)
        print(f"actual={result['actual']!r}", flush=True)
        whisper_rtf = result["whisper_realtime_factor"]
        whisper_rtf_text = f"{whisper_rtf:.3f}" if whisper_rtf is not None else "unavailable"
        print(
            f"exit_code={result['exit_code']} "
            f"wall_seconds={result['wall_seconds']:.3f} "
            f"wall_rtf={result['wall_realtime_factor']:.3f} "
            f"whisper_rtf={whisper_rtf_text}",
            flush=True,
        )

    segmented = [item for item in results if item["id"].startswith("MIX-SEG-")]
    summary = {
        "model": str(MODEL),
        "cases": results,
        "segmented_mixed_transcript": " ".join(item["actual"] for item in segmented),
        "all_commands_ok": all(item["exit_code"] == 0 for item in results),
    }
    output_path = RESULTS_DIR / "phase1-diagnostics-summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nsummary={output_path.relative_to(PROJECT_DIR)}", flush=True)
    return 0 if summary["all_commands_ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
