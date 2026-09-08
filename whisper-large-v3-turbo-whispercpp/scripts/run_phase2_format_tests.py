#!/usr/bin/env python3
"""Test direct input and FFmpeg-normalized fallback for common audio containers."""

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
FIXTURE_DIR = PROJECT_DIR / "tests/fixtures/audio/phase2-formats"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
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
            value in condensed
            for value in ("todayis", "meetingstarts", "ordernumberis")
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


def transcribe(case_id: str, input_path: Path, expected: str) -> dict[str, Any]:
    slug = case_id.lower()
    output_base = RESULTS_DIR / f"phase2-{slug}"
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
    (RESULTS_DIR / f"phase2-{slug}.log").write_text(log, encoding="utf-8")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    duration = duration_seconds(input_path)
    total_ms = parse_timing_ms(log, "total")
    checks = semantic_checks(actual)
    return {
        "id": case_id,
        "input": str(input_path.relative_to(PROJECT_DIR)),
        "duration_seconds": duration,
        "exit_code": process.returncode,
        "actual": actual,
        "strict_score": score_text(expected, actual, "en"),
        "semantic_checks": checks,
        "semantic_pass": all(checks.values()),
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
    }


def normalize_with_ffmpeg(source: Path, destination: Path) -> float:
    started = time.perf_counter()
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
            "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            str(destination),
        ],
        check=True,
    )
    return time.perf_counter() - started


def main() -> int:
    for path in (CLI, MODEL, MANIFEST_PATH):
        if not path.is_file():
            raise RuntimeError(f"missing required file: {path}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest["expected_text"]

    direct = []
    for item in manifest["files"]:
        input_path = PROJECT_DIR / item["file"]
        case_id = f"FORMAT-DIRECT-{input_path.suffix.removeprefix('.').upper()}"
        print(f"\n===== {case_id} =====", flush=True)
        result = transcribe(case_id, input_path, expected)
        direct.append(result)
        print(f"exit_code={result['exit_code']} actual={result['actual']!r}", flush=True)
        print(
            f"semantic_pass={'yes' if result['semantic_pass'] else 'no'} "
            f"wall_seconds={result['wall_seconds']:.3f}", flush=True
        )

    fallback = []
    for extension in ("m4a", "mov"):
        source_item = next(
            item for item in manifest["files"] if item["file"].endswith(f".{extension}")
        )
        source = PROJECT_DIR / source_item["file"]
        normalized = RESULTS_DIR / f"phase2-normalized-from-{extension}.wav"
        conversion_seconds = normalize_with_ffmpeg(source, normalized)
        case_id = f"FORMAT-FALLBACK-{extension.upper()}-TO-WAV"
        print(f"\n===== {case_id} =====", flush=True)
        result = transcribe(case_id, normalized, expected)
        result["conversion_seconds"] = conversion_seconds
        result["pipeline_wall_seconds"] = conversion_seconds + result["wall_seconds"]
        fallback.append(result)
        print(
            f"exit_code={result['exit_code']} semantic_pass="
            f"{'yes' if result['semantic_pass'] else 'no'} "
            f"conversion_seconds={conversion_seconds:.3f}", flush=True
        )

    summary = {
        "method": "same fixed speech transcoded into common containers",
        "expected": expected,
        "direct_cases": direct,
        "ffmpeg_fallback_cases": fallback,
        "all_direct_inputs_supported": all(
            item["exit_code"] == 0 and item["semantic_pass"] for item in direct
        ),
        "all_fallbacks_passed": all(
            item["exit_code"] == 0 and item["semantic_pass"] for item in fallback
        ),
    }
    output_path = RESULTS_DIR / "phase2-format-summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nsummary={output_path.relative_to(PROJECT_DIR)}")
    return 0 if summary["all_direct_inputs_supported"] and summary["all_fallbacks_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
