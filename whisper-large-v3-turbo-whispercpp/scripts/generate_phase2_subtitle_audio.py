#!/usr/bin/env python3
"""Generate three English utterances with precisely recorded silent gaps."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "tests/fixtures/audio/phase2-subtitles"
SOURCE_DIR = OUTPUT_DIR / "source"
VOICE = "Samantha"
LEADING_SILENCE = 1.0
BETWEEN_SILENCE = 2.0
TRAILING_SILENCE = 1.0
SENTENCES = [
    "Welcome to the weekly project update.",
    "The design review begins at ten thirty.",
    "Please send your comments by Friday.",
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_silence(path: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono", "-t", str(seconds),
            "-c:a", "pcm_s16le", str(path),
        ]
    )


def main() -> None:
    for program in ("say", "ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(f"missing required program: {program}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    speech_paths: list[Path] = []
    speech_durations: list[float] = []
    for index, sentence in enumerate(SENTENCES, start=1):
        aiff_path = SOURCE_DIR / f"sentence-{index}.aiff"
        wav_path = SOURCE_DIR / f"sentence-{index}.wav"
        run(["say", "-v", VOICE, "-o", str(aiff_path), sentence])
        run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff_path),
                "-af",
                "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-50dB:"
                "stop_periods=1:stop_duration=0.08:stop_threshold=-50dB",
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path),
            ]
        )
        speech_paths.append(wav_path)
        speech_durations.append(duration_seconds(wav_path))

    lead_path = SOURCE_DIR / "silence-leading.wav"
    gap_path = SOURCE_DIR / "silence-between.wav"
    trail_path = SOURCE_DIR / "silence-trailing.wav"
    make_silence(lead_path, LEADING_SILENCE)
    make_silence(gap_path, BETWEEN_SILENCE)
    make_silence(trail_path, TRAILING_SILENCE)

    output_path = OUTPUT_DIR / "subtitle-en-001.wav"
    ordered_inputs = [
        lead_path, speech_paths[0], gap_path, speech_paths[1],
        gap_path, speech_paths[2], trail_path,
    ]
    input_args: list[str] = []
    for path in ordered_inputs:
        input_args.extend(["-i", str(path)])
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", *input_args,
            "-filter_complex", "[0:a][1:a][2:a][3:a][4:a][5:a][6:a]concat=n=7:v=0:a=1[out]",
            "-map", "[out]", "-ar", "16000", "-ac", "1",
            "-c:a", "pcm_s16le", str(output_path),
        ]
    )

    timeline: list[dict[str, Any]] = []
    cursor = LEADING_SILENCE
    for index, (sentence, duration) in enumerate(zip(SENTENCES, speech_durations), start=1):
        timeline.append(
            {
                "index": index,
                "text": sentence,
                "expected_start_seconds": round(cursor, 6),
                "expected_end_seconds": round(cursor + duration, 6),
                "speech_duration_seconds": round(duration, 6),
            }
        )
        cursor += duration
        if index < len(SENTENCES):
            cursor += BETWEEN_SILENCE

    manifest = {
        "id": "SUB-EN-001",
        "purpose": "timestamp and SRT/VTT validation with known pauses",
        "generator": "macOS say + FFmpeg",
        "voice": VOICE,
        "file": str(output_path.relative_to(PROJECT_DIR)),
        "audio_format": "16000 Hz mono PCM s16le WAV",
        "duration_seconds": round(duration_seconds(output_path), 6),
        "sha256": sha256(output_path),
        "leading_silence_seconds": LEADING_SILENCE,
        "between_silence_seconds": BETWEEN_SILENCE,
        "trailing_silence_seconds": TRAILING_SILENCE,
        "timeline": timeline,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"audio={output_path.relative_to(PROJECT_DIR)}")
    print(f"duration_seconds={manifest['duration_seconds']:.3f}")
    for item in timeline:
        print(
            f"segment_{item['index']}={item['expected_start_seconds']:.3f}-"
            f"{item['expected_end_seconds']:.3f} {item['text']}"
        )
    print(f"sha256={manifest['sha256']}")
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
