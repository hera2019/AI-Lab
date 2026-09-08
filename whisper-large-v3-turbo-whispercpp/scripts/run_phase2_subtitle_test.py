#!/usr/bin/env python3
"""Generate and validate TXT, JSON, SRT, and VTT from a timed fixture."""

from __future__ import annotations

import argparse
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
FIXTURE_DIR = PROJECT_DIR / "tests/fixtures/audio/phase2-subtitles"
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


def meaning_compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = normalized.replace("ten thirty", "10:30")
    return compact(normalized)


def parse_time(value: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    if not match:
        raise ValueError(f"invalid subtitle timestamp: {value}")
    hours, minutes, seconds, milliseconds = (int(item) for item in match.groups())
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def parse_srt(text: str) -> list[dict[str, Any]]:
    cues = []
    blocks = re.split(r"\n\s*\n", text.strip()) if text.strip() else []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start, end = lines[1].split(" --> ", 1)
        cues.append(
            {
                "index": int(lines[0]),
                "start_seconds": parse_time(start),
                "end_seconds": parse_time(end),
                "text": " ".join(lines[2:]).strip(),
            }
        )
    return cues


def parse_vtt(text: str) -> list[dict[str, Any]]:
    cues = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if " --> " not in lines[index]:
            index += 1
            continue
        start, end = lines[index].split(" --> ", 1)
        index += 1
        payload = []
        while index < len(lines) and lines[index].strip():
            payload.append(lines[index].strip())
            index += 1
        cues.append(
            {
                "start_seconds": parse_time(start),
                "end_seconds": parse_time(end),
                "text": " ".join(payload),
            }
        )
    return cues


def timeline_valid(cues: list[dict[str, Any]], duration: float) -> bool:
    if not cues:
        return False
    previous_end = 0.0
    for cue in cues:
        if not (0 <= cue["start_seconds"] < cue["end_seconds"] <= duration + 0.5):
            return False
        if cue["start_seconds"] < previous_end:
            return False
        previous_end = cue["end_seconds"]
    return True


def content_valid(cues: list[dict[str, Any]], expected_sentences: list[str]) -> bool:
    combined = meaning_compact(" ".join(cue["text"] for cue in cues))
    return all(meaning_compact(sentence) in combined for sentence in expected_sentences)


def nearest_alignment(
    cues: list[dict[str, Any]], expected: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    alignments = []
    for sentence in expected:
        expected_text = meaning_compact(sentence["text"])
        candidate = next(
            (
                cue
                for cue in cues
                if meaning_compact(cue["text"]) in expected_text
                or expected_text in meaning_compact(cue["text"])
            ),
            None,
        )
        if candidate is None:
            alignments.append({"index": sentence["index"], "matched": False})
            continue
        start_error = candidate["start_seconds"] - sentence["expected_start_seconds"]
        end_error = candidate["end_seconds"] - sentence["expected_end_seconds"]
        alignments.append(
            {
                "index": sentence["index"],
                "matched": True,
                "expected_start_seconds": sentence["expected_start_seconds"],
                "actual_start_seconds": candidate["start_seconds"],
                "start_error_seconds": start_error,
                "expected_end_seconds": sentence["expected_end_seconds"],
                "actual_end_seconds": candidate["end_seconds"],
                "end_error_seconds": end_error,
                "within_one_second": abs(start_error) <= 1.0 and abs(end_error) <= 1.0,
            }
        )
    return alignments


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--readable",
        action="store_true",
        help="limit cue length and split on word timestamps",
    )
    args = parser.parse_args()
    mode = "readable" if args.readable else "standard"
    output_base = RESULTS_DIR / f"phase2-subtitle-en-001-{mode}"

    for path in (CLI, MODEL, MANIFEST_PATH):
        if not path.is_file():
            raise RuntimeError(f"missing required file: {path}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    audio_path = PROJECT_DIR / manifest["file"]
    for suffix in (".txt", ".json", ".srt", ".vtt"):
        path = Path(str(output_base) + suffix)
        if path.exists():
            path.unlink()

    command = [
        "/usr/bin/time", "-lp", str(CLI),
        "--model", str(MODEL), "--file", str(audio_path),
        "--language", "en", "--threads", "8",
        "--output-txt", "--output-json", "--output-srt", "--output-vtt",
        "--output-file", str(output_base),
    ]
    if args.readable:
        command.extend(["--max-len", "42", "--split-on-word"])
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    (RESULTS_DIR / f"phase2-subtitle-en-001-{mode}.log").write_text(log, encoding="utf-8")

    paths = {suffix: Path(str(output_base) + suffix) for suffix in (".txt", ".json", ".srt", ".vtt")}
    files_present = {suffix.removeprefix("."): path.is_file() for suffix, path in paths.items()}
    txt = paths[".txt"].read_text(encoding="utf-8").strip() if paths[".txt"].is_file() else ""
    srt_text = paths[".srt"].read_text(encoding="utf-8") if paths[".srt"].is_file() else ""
    vtt_text = paths[".vtt"].read_text(encoding="utf-8") if paths[".vtt"].is_file() else ""
    json_data = json.loads(paths[".json"].read_text(encoding="utf-8")) if paths[".json"].is_file() else {}
    srt_cues = parse_srt(srt_text)
    vtt_cues = parse_vtt(vtt_text)
    json_segments = json_data.get("transcription", [])
    expected_sentences = [item["text"] for item in manifest["timeline"]]
    duration = float(manifest["duration_seconds"])
    alignments = nearest_alignment(srt_cues, manifest["timeline"])
    total_ms = parse_timing_ms(log, "total")

    checks = {
        "command_exit_zero": process.returncode == 0,
        "all_four_files_present": all(files_present.values()),
        "txt_contains_all_sentences": all(
            meaning_compact(sentence) in meaning_compact(txt)
            for sentence in expected_sentences
        ),
        "srt_has_valid_monotonic_timeline": timeline_valid(srt_cues, duration),
        "vtt_has_valid_monotonic_timeline": timeline_valid(vtt_cues, duration),
        "srt_contains_all_sentences": content_valid(srt_cues, expected_sentences),
        "vtt_contains_all_sentences": content_valid(vtt_cues, expected_sentences),
        "json_has_timestamped_segments": bool(json_segments) and all(
            "timestamps" in item and "offsets" in item for item in json_segments
        ),
        "all_expected_segments_within_one_second": len(alignments) == len(expected_sentences)
        and all(item.get("within_one_second", False) for item in alignments),
    }
    summary = {
        "mode": mode,
        "extra_arguments": ["--max-len", "42", "--split-on-word"] if args.readable else [],
        "audio": manifest,
        "exit_code": process.returncode,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (total_ms / 1000) / duration if total_ms else None,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_log_detected": "ggml_metal" in log.lower(),
        "files_present": files_present,
        "txt": txt,
        "srt_cues": srt_cues,
        "vtt_cues": vtt_cues,
        "json_segment_count": len(json_segments),
        "timestamp_alignment": alignments,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    pipeline_check_names = {
        "command_exit_zero",
        "all_four_files_present",
        "srt_has_valid_monotonic_timeline",
        "vtt_has_valid_monotonic_timeline",
        "json_has_timestamped_segments",
    }
    summary["pipeline_ok"] = all(checks[name] for name in pipeline_check_names)
    output_path = RESULTS_DIR / f"phase2-subtitle-{mode}-summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"exit_code={process.returncode}")
    print(f"txt={txt!r}")
    print(f"srt_cues={len(srt_cues)} vtt_cues={len(vtt_cues)} json_segments={len(json_segments)}")
    for item in alignments:
        print(f"alignment={item}")
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"summary={output_path.relative_to(PROJECT_DIR)}")
    return 0 if summary["pipeline_ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", flush=True)
        raise SystemExit(2) from error
