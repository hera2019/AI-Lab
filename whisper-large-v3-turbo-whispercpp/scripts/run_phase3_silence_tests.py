#!/usr/bin/env python3
"""Check hallucination behavior on silence, room tone, and padded speech."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any

from run_phase1_clean_baseline import parse_max_rss_bytes, parse_timing_ms


PROJECT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_DIR / "tests/fixtures/audio/phase3-silence/manifest.json"
NOISE_SUMMARY_PATH = PROJECT_DIR / "results/phase3-noise-summary.json"
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


def meaning_compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", normalized)
    return compact(normalized)


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


def run_case(
    case_id: str,
    input_path: Path,
    language: str,
    expects_speech: bool,
    clean_transcript: str,
) -> dict[str, Any]:
    slug = f"{case_id.lower()}-{language}"
    output_base = RESULTS_DIR / f"phase3-{slug}"
    for suffix in (".txt", ".json"):
        path = Path(str(output_base) + suffix)
        if path.exists():
            path.unlink()
    command = [
        "/usr/bin/time", "-lp", str(CLI),
        "--model", str(MODEL), "--file", str(input_path),
        "--language", language, "--threads", "8",
        "--output-txt", "--output-json", "--output-file", str(output_base),
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase3-{slug}.log").write_text(log, encoding="utf-8")
    text_path = Path(str(output_base) + ".txt")
    json_path = Path(str(output_base) + ".json")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    json_data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    duration = duration_seconds(input_path)
    total_ms = parse_timing_ms(log, "total")
    matches_clean = (
        meaning_compact(actual) == meaning_compact(clean_transcript)
        if expects_speech
        else None
    )
    raw_output_empty = actual == ""
    no_semantic_hallucination = (
        matches_clean if expects_speech else meaning_compact(actual) == ""
    )
    return {
        "id": case_id,
        "language_argument": language,
        "input": str(input_path.relative_to(PROJECT_DIR)),
        "duration_seconds": duration,
        "expects_speech": expects_speech,
        "exit_code": process.returncode,
        "actual": actual,
        "json_segment_count": len(json_data.get("transcription", [])),
        "matches_clean_transcript": matches_clean,
        "raw_output_empty": raw_output_empty,
        "no_semantic_hallucination": no_semantic_hallucination,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
    }


def main() -> int:
    for path in (CLI, MODEL, MANIFEST_PATH, NOISE_SUMMARY_PATH):
        if not path.is_file():
            raise RuntimeError(f"missing required file: {path}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    noise_summary = json.loads(NOISE_SUMMARY_PATH.read_text(encoding="utf-8"))
    clean_transcript = next(
        item["actual"] for item in noise_summary["cases"] if item["id"] == "NOISE-EN-CLEAN"
    )
    by_id = {item["id"]: item for item in manifest["cases"]}
    specs = [
        ("SIL-PURE-10", "en", False),
        ("SIL-PURE-10", "auto", False),
        ("SIL-PURE-30", "auto", False),
        ("SIL-ROOM-15", "auto", False),
        ("SIL-PADDED-SPEECH", "en", True),
    ]
    results = []
    for case_id, language, expects_speech in specs:
        print(f"\n===== {case_id} language={language} =====", flush=True)
        item = by_id[case_id]
        result = run_case(
            case_id,
            PROJECT_DIR / item["file"],
            language,
            expects_speech,
            clean_transcript,
        )
        results.append(result)
        print(f"actual={result['actual']!r}", flush=True)
        print(
            f"exit_code={result['exit_code']} segments={result['json_segment_count']} "
            f"no_semantic_hallucination="
            f"{'yes' if result['no_semantic_hallucination'] else 'no'} "
            f"wall_seconds={result['wall_seconds']:.3f}",
            flush=True,
        )

    summary = {
        "fixture": manifest,
        "clean_reference_transcript": clean_transcript,
        "cases": results,
        "all_commands_ok": all(item["exit_code"] == 0 for item in results),
        "all_no_semantic_hallucination": all(
            item["no_semantic_hallucination"] for item in results
        ),
    }
    output_path = RESULTS_DIR / "phase3-silence-summary.json"
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
