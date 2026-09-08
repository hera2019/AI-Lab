#!/usr/bin/env python3
"""Compare Whisper output, timing, and subtitles with VAD disabled/enabled."""

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
from run_phase2_subtitle_test import nearest_alignment, parse_srt, timeline_valid


PROJECT_DIR = Path(__file__).resolve().parent.parent
SILENCE_MANIFEST = PROJECT_DIR / "tests/fixtures/audio/phase3-silence/manifest.json"
SUBTITLE_MANIFEST = PROJECT_DIR / "tests/fixtures/audio/phase2-subtitles/manifest.json"
NOISE_SUMMARY = PROJECT_DIR / "results/phase3-noise-summary.json"
RESULTS_DIR = PROJECT_DIR / "results"
CLI = PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-cli"
MODEL = Path(
    os.environ.get(
        "WHISPER_MODEL",
        str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin"),
    )
)
VAD_MODEL = Path(
    os.environ.get(
        "WHISPER_VAD_MODEL",
        str(Path.home() / "Documents/AI-Models/whispercpp/ggml-silero-v6.2.0.bin"),
    )
)


def compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", normalized)
    normalized = normalized.replace("ten thirty", "10:30")
    return "".join(
        char
        for char in normalized
        if not unicodedata.category(char).startswith(("P", "S", "Z"))
        and not char.isspace()
    )


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
    vad_enabled: bool,
    expected_text: str,
    expects_speech: bool,
    subtitle_manifest: dict[str, Any] | None = None,
    expected_markers: list[str] | None = None,
) -> dict[str, Any]:
    mode = "vad-on" if vad_enabled else "vad-off"
    slug = f"{case_id.lower()}-{mode}"
    output_base = RESULTS_DIR / f"phase3-{slug}"
    for suffix in (".txt", ".json", ".srt"):
        path = Path(str(output_base) + suffix)
        if path.exists():
            path.unlink()
    command = [
        "/usr/bin/time", "-lp", str(CLI),
        "--model", str(MODEL), "--file", str(input_path),
        "--language", "en", "--threads", "8",
        "--output-txt", "--output-json", "--output-srt", "--output-file", str(output_base),
    ]
    if vad_enabled:
        command.extend(["--vad", "--vad-model", str(VAD_MODEL)])
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase3-{slug}.log").write_text(log, encoding="utf-8")
    text_path = Path(str(output_base) + ".txt")
    json_path = Path(str(output_base) + ".json")
    srt_path = Path(str(output_base) + ".srt")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    json_data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    srt_text = srt_path.read_text(encoding="utf-8") if srt_path.exists() else ""
    srt_cues = parse_srt(srt_text)
    duration = duration_seconds(input_path)
    total_ms = parse_timing_ms(log, "total")
    if expects_speech:
        content_pass = compact(actual) == compact(expected_text)
    else:
        content_pass = compact(actual) == ""
    marker_checks = (
        {marker: compact(marker) in compact(actual) for marker in expected_markers}
        if expected_markers
        else None
    )

    subtitle_checks = None
    if subtitle_manifest is not None:
        expected_sentences = [item["text"] for item in subtitle_manifest["timeline"]]
        subtitle_checks = {
            "contains_all_sentences": all(
                compact(sentence) in compact(actual) for sentence in expected_sentences
            ),
            "valid_monotonic_timeline": timeline_valid(srt_cues, duration),
            "alignment": nearest_alignment(srt_cues, subtitle_manifest["timeline"]),
        }

    return {
        "id": case_id,
        "vad_enabled": vad_enabled,
        "input": str(input_path.relative_to(PROJECT_DIR)),
        "duration_seconds": duration,
        "exit_code": process.returncode,
        "actual": actual,
        "content_pass": content_pass,
        "semantic_marker_checks": marker_checks,
        "semantic_markers_passed": sum(marker_checks.values()) if marker_checks else None,
        "semantic_markers_total": len(marker_checks) if marker_checks else None,
        "json_segment_count": len(json_data.get("transcription", [])),
        "srt_cues": srt_cues,
        "subtitle_checks": subtitle_checks,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
        "vad_log_detected": "vad" in log.lower(),
    }


def main() -> int:
    for path in (CLI, MODEL, VAD_MODEL, SILENCE_MANIFEST, SUBTITLE_MANIFEST, NOISE_SUMMARY):
        if not path.is_file():
            raise RuntimeError(f"missing required file: {path}")
    silence_manifest = json.loads(SILENCE_MANIFEST.read_text(encoding="utf-8"))
    subtitle_manifest = json.loads(SUBTITLE_MANIFEST.read_text(encoding="utf-8"))
    noise_summary = json.loads(NOISE_SUMMARY.read_text(encoding="utf-8"))
    clean_transcript = next(
        item["actual"] for item in noise_summary["cases"] if item["id"] == "NOISE-EN-CLEAN"
    )
    silence_by_id = {item["id"]: item for item in silence_manifest["cases"]}
    specs = [
        {
            "id": "VAD-PURE-30",
            "path": PROJECT_DIR / silence_by_id["SIL-PURE-30"]["file"],
            "expected": "",
            "expects_speech": False,
            "subtitle": None,
            "markers": None,
        },
        {
            "id": "VAD-PADDED-LONG",
            "path": PROJECT_DIR / silence_by_id["SIL-PADDED-LONG"]["file"],
            "expected": clean_transcript,
            "expects_speech": True,
            "subtitle": None,
            "markers": None,
        },
        {
            "id": "VAD-SUBTITLE",
            "path": PROJECT_DIR / subtitle_manifest["file"],
            "expected": " ".join(item["text"] for item in subtitle_manifest["timeline"]),
            "expects_speech": True,
            "subtitle": subtitle_manifest,
            "markers": None,
        },
        {
            "id": "VAD-MIXED-LANGUAGE",
            "path": PROJECT_DIR / "tests/fixtures/audio/asr-mix-001.wav",
            "expected": "项目代号是海风七号。 次の会議は東京で開きます。 Please upload the final report by Friday.",
            "expects_speech": True,
            "subtitle": None,
            "markers": ["海风", "東京", "Friday"],
        },
    ]

    results = []
    for spec in specs:
        for enabled in (False, True):
            print(f"\n===== {spec['id']} {'ON' if enabled else 'OFF'} =====", flush=True)
            result = run_case(
                spec["id"], spec["path"], enabled, spec["expected"],
                spec["expects_speech"], spec["subtitle"], spec["markers"],
            )
            results.append(result)
            print(f"actual={result['actual']!r}", flush=True)
            print(
                f"exit_code={result['exit_code']} content_pass="
                f"{'yes' if result['content_pass'] else 'no'} "
                f"wall_seconds={result['wall_seconds']:.3f} "
                f"rtf={result['wall_realtime_factor']:.3f}", flush=True
            )
            if result["subtitle_checks"]:
                for item in result["subtitle_checks"]["alignment"]:
                    print(f"alignment={item}")
            if result["semantic_marker_checks"]:
                print(
                    f"semantic_markers={result['semantic_markers_passed']}/"
                    f"{result['semantic_markers_total']}"
                )

    comparisons = []
    for spec in specs:
        off = next(item for item in results if item["id"] == spec["id"] and not item["vad_enabled"])
        on = next(item for item in results if item["id"] == spec["id"] and item["vad_enabled"])
        comparisons.append(
            {
                "id": spec["id"],
                "off_wall_seconds": off["wall_seconds"],
                "on_wall_seconds": on["wall_seconds"],
                "speedup_off_over_on": off["wall_seconds"] / on["wall_seconds"],
                "off_actual": off["actual"],
                "on_actual": on["actual"],
            }
        )
    summary = {
        "vad_model": str(VAD_MODEL),
        "vad_model_size_bytes": VAD_MODEL.stat().st_size,
        "cases": results,
        "comparisons": comparisons,
        "all_commands_ok": all(item["exit_code"] == 0 for item in results),
    }
    output_path = RESULTS_DIR / "phase3-vad-comparison-summary.json"
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
