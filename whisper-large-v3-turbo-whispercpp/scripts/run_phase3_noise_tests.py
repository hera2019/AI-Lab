#!/usr/bin/env python3
"""Transcribe and score the clean source plus measured-SNR noise variants."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any

from run_phase1_clean_baseline import parse_max_rss_bytes, parse_timing_ms, score_text


PROJECT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_DIR / "tests/fixtures/audio/phase3-noise/manifest.json"
RESULTS_DIR = PROJECT_DIR / "results"
CLI = PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-cli"
MODEL = Path(
    os.environ.get(
        "WHISPER_MODEL",
        str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin"),
    )
)


def compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        char
        for char in normalized
        if not unicodedata.category(char).startswith(("P", "S", "Z"))
        and not char.isspace()
    )


def semantic_checks(text: str) -> dict[str, bool]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    condensed = compact(text)
    return {
        "date_2026_09_02": "september2" in condensed and "2026" in condensed,
        "time_15_15": re.search(r"3[.:]?15\s*p\.?m\.?(?:\b|$)", normalized) is not None,
        "order_A731": "a731" in condensed,
        "sentence_content": all(
            value in condensed for value in ("todayis", "meetingstarts", "ordernumberis")
        ),
    }


def duration_seconds(path: Path) -> float:
    process = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(process.stdout.strip())


def run_case(case_id: str, input_path: Path, expected: str, snr: int | None) -> dict[str, Any]:
    slug = case_id.lower()
    output_base = RESULTS_DIR / f"phase3-{slug}"
    text_path = Path(str(output_base) + ".txt")
    if text_path.exists():
        text_path.unlink()
    command = [
        "/usr/bin/time", "-lp", str(CLI),
        "--model", str(MODEL), "--file", str(input_path),
        "--language", "en", "--threads", "8",
        "--output-txt", "--output-file", str(output_base), "--no-timestamps",
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase3-{slug}.log").write_text(log, encoding="utf-8")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    duration = duration_seconds(input_path)
    total_ms = parse_timing_ms(log, "total")
    checks = semantic_checks(actual)
    return {
        "id": case_id,
        "snr_db": snr,
        "input": str(input_path.relative_to(PROJECT_DIR)),
        "duration_seconds": duration,
        "exit_code": process.returncode,
        "actual": actual,
        "strict_score": score_text(expected, actual, "en"),
        "semantic_checks": checks,
        "semantic_passed": sum(checks.values()),
        "semantic_total": len(checks),
        "semantic_pass": all(checks.values()),
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
    }


def main() -> int:
    for path in (CLI, MODEL, MANIFEST_PATH):
        if not path.is_file():
            raise RuntimeError(f"missing required file: {path}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cases = [
        {
            "id": "NOISE-EN-CLEAN",
            "path": PROJECT_DIR / manifest["source"],
            "snr": None,
        }
    ]
    cases.extend(
        {
            "id": item["id"],
            "path": PROJECT_DIR / item["file"],
            "snr": item["target_snr_db"],
        }
        for item in manifest["cases"]
    )

    results = []
    for case in cases:
        print(f"\n===== {case['id']} =====", flush=True)
        result = run_case(case["id"], case["path"], manifest["expected_text"], case["snr"])
        results.append(result)
        print(f"actual={result['actual']!r}", flush=True)
        print(
            f"WER={result['strict_score']['error_rate']:.4f} "
            f"semantic={result['semantic_passed']}/{result['semantic_total']} "
            f"wall_seconds={result['wall_seconds']:.3f}",
            flush=True,
        )

    summary = {
        "fixture": manifest,
        "cases": results,
        "all_commands_ok": all(item["exit_code"] == 0 for item in results),
    }
    output_path = RESULTS_DIR / "phase3-noise-summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nsummary={output_path.relative_to(PROJECT_DIR)}")
    return 0 if summary["all_commands_ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
