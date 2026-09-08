#!/usr/bin/env python3
"""Reproduce VAD segment timestamps that can precede their source audio."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


SRT_TIME_RE = re.compile(
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}),(?P<millisecond>\d{3})"
)
VAD_SEGMENT_RE = re.compile(
    r"Speech segment \d+: start = (?P<start>[0-9.]+), end = (?P<end>[0-9.]+)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--whisper-cli",
        default=os.environ.get("WHISPER_CLI", "./build/bin/whisper-cli"),
    )
    parser.add_argument(
        "--vad-cli",
        default=os.environ.get(
            "WHISPER_VAD_CLI", "./build/bin/whisper-vad-speech-segments"
        ),
    )
    parser.add_argument("--model", default=os.environ.get("WHISPER_MODEL"))
    parser.add_argument("--vad-model", default=os.environ.get("WHISPER_VAD_MODEL"))
    parser.add_argument("--sample", default="./samples/jfk.wav")
    parser.add_argument("--output-dir", default="./vad-timestamp-repro")
    parser.add_argument("--gap-seconds", type=float, default=2.0)
    parser.add_argument("--threads", type=int, default=8)
    return parser.parse_args()


def require_file(value: str | None, label: str, executable: bool = False) -> Path:
    if not value:
        raise RuntimeError(f"{label} is required")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"{label} not found: {path}")
    if executable and not os.access(path, os.X_OK):
        raise RuntimeError(f"{label} is not executable: {path}")
    return path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        detail = (process.stdout + process.stderr).strip()
        raise RuntimeError(
            f"command failed with exit code {process.returncode}: {' '.join(command)}\n{detail}"
        )
    return process


def duration_seconds(path: Path) -> float:
    process = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(process.stdout.strip())


def srt_seconds(value: str) -> float:
    match = SRT_TIME_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value}")
    return (
        int(match.group("hour")) * 3600
        + int(match.group("minute")) * 60
        + int(match.group("second"))
        + int(match.group("millisecond")) / 1000
    )


def parse_srt(path: Path) -> list[dict[str, Any]]:
    timestamp_re = re.compile(
        r"(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> "
        r"(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
    )
    cues: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = block.splitlines()
        if len(lines) < 2:
            continue
        match = timestamp_re.fullmatch(lines[1].strip())
        if not match:
            continue
        cues.append(
            {
                "start_seconds": srt_seconds(match.group("start")),
                "end_seconds": srt_seconds(match.group("end")),
                "text": " ".join(line.strip() for line in lines[2:]),
            }
        )
    return cues


def transcribe(
    whisper_cli: Path,
    model: Path,
    vad_model: Path,
    audio: Path,
    output_base: Path,
    threads: int,
    vad_enabled: bool,
) -> tuple[list[dict[str, Any]], str]:
    for suffix in (".srt", ".txt", ".json"):
        candidate = Path(str(output_base) + suffix)
        if candidate.exists():
            candidate.unlink()
    command = [
        str(whisper_cli),
        "--model",
        str(model),
        "--file",
        str(audio),
        "--language",
        "en",
        "--threads",
        str(threads),
        "--output-srt",
        "--output-txt",
        "--output-json",
        "--output-file",
        str(output_base),
    ]
    if vad_enabled:
        command.extend(["--vad", "--vad-model", str(vad_model)])
    process = run(command)
    log = process.stdout + process.stderr
    Path(str(output_base) + ".log").write_text(log, encoding="utf-8")
    srt_path = Path(str(output_base) + ".srt")
    if not srt_path.is_file():
        raise RuntimeError(f"expected SRT was not created: {srt_path}")
    return parse_srt(srt_path), log


def main() -> int:
    args = parse_args()
    whisper_cli = require_file(args.whisper_cli, "whisper-cli", executable=True)
    vad_cli = require_file(args.vad_cli, "whisper-vad-speech-segments", executable=True)
    model = require_file(args.model, "Whisper model")
    vad_model = require_file(args.vad_model, "VAD model")
    sample = require_file(args.sample, "sample audio")
    if args.gap_seconds <= 0:
        raise RuntimeError("--gap-seconds must be greater than zero")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    silence = output_dir / "silence.wav"
    composite = output_dir / "jfk-three-segments.wav"

    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            str(args.gap_seconds),
            "-c:a",
            "pcm_s16le",
            str(silence),
        ]
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(sample),
            "-i",
            str(silence),
            "-i",
            str(sample),
            "-i",
            str(silence),
            "-i",
            str(sample),
            "-filter_complex",
            "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[out]",
            "-map",
            "[out]",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(composite),
        ]
    )

    sample_duration = duration_seconds(sample)
    copy_starts = [
        0.0,
        sample_duration + args.gap_seconds,
        2 * (sample_duration + args.gap_seconds),
    ]
    vad_process = run(
        [
            str(vad_cli),
            "--file",
            str(composite),
            "--vad-model",
            str(vad_model),
            "--threads",
            str(args.threads),
            "--no-prints",
        ]
    )
    vad_log = vad_process.stdout + vad_process.stderr
    (output_dir / "vad-segments.log").write_text(vad_log, encoding="utf-8")
    vad_segments = [
        {
            "start_seconds": float(match.group("start")) / 100,
            "end_seconds": float(match.group("end")) / 100,
        }
        for match in VAD_SEGMENT_RE.finditer(vad_log)
    ]
    first_vad_starts = [
        next(
            (
                segment["start_seconds"]
                for segment in vad_segments
                if segment["start_seconds"] >= copy_start
            ),
            None,
        )
        for copy_start in copy_starts
    ]

    off_cues, _ = transcribe(
        whisper_cli,
        model,
        vad_model,
        composite,
        output_dir / "vad-off",
        args.threads,
        False,
    )
    on_cues, _ = transcribe(
        whisper_cli,
        model,
        vad_model,
        composite,
        output_dir / "vad-on",
        args.threads,
        True,
    )
    off_starts = [cue["start_seconds"] for cue in off_cues]
    on_starts = [cue["start_seconds"] for cue in on_cues]
    comparisons = []
    for index, copy_start in enumerate(copy_starts):
        vad_start = first_vad_starts[index]
        off_start = off_starts[index] if index < len(off_starts) else None
        on_start = on_starts[index] if index < len(on_starts) else None
        comparisons.append(
            {
                "copy": index + 1,
                "copy_start_seconds": copy_start,
                "first_vad_start_seconds": vad_start,
                "vad_off_cue_start_seconds": off_start,
                "vad_on_cue_start_seconds": on_start,
                "vad_on_minus_copy_start_seconds": (
                    on_start - copy_start if on_start is not None else None
                ),
                "vad_on_starts_before_copy": (
                    index > 0
                    and on_start is not None
                    and on_start < copy_start - 0.5
                ),
                "vad_on_inside_preceding_gap": (
                    index > 0
                    and on_start is not None
                    and copy_start - args.gap_seconds < on_start < copy_start
                ),
            }
        )

    bug_reproduced = any(
        item["vad_on_starts_before_copy"] for item in comparisons
    )
    summary = {
        "model": str(model),
        "vad_model": str(vad_model),
        "sample": str(sample),
        "sample_duration_seconds": sample_duration,
        "gap_seconds": args.gap_seconds,
        "composite_duration_seconds": duration_seconds(composite),
        "copy_starts_seconds": copy_starts,
        "vad_segments": vad_segments,
        "vad_off_cues": off_cues,
        "vad_on_cues": on_cues,
        "comparisons": comparisons,
        "bug_reproduced": bug_reproduced,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("copy  audio_start  first_vad  srt_without_vad  srt_with_vad  delta")
    for item in comparisons:
        values = [
            item["copy"],
            item["copy_start_seconds"],
            item["first_vad_start_seconds"],
            item["vad_off_cue_start_seconds"],
            item["vad_on_cue_start_seconds"],
            item["vad_on_minus_copy_start_seconds"],
        ]
        print(
            f"{values[0]:>4}  {values[1]:>11.3f}  "
            f"{values[2] if values[2] is not None else float('nan'):>9.3f}  "
            f"{values[3] if values[3] is not None else float('nan'):>15.3f}  "
            f"{values[4] if values[4] is not None else float('nan'):>12.3f}  "
            f"{values[5] if values[5] is not None else float('nan'):>+6.3f}"
        )
    print(f"bug_reproduced={'yes' if bug_reproduced else 'no'}")
    print(f"summary={output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}")
        raise SystemExit(2) from error
