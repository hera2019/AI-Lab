#!/usr/bin/env python3
"""Create deterministic silence, room-tone, and silence-padded speech fixtures."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
OUTPUT_DIR = AUDIO_DIR / "phase3-silence"
SOURCE = AUDIO_DIR / "asr-en-001.wav"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def make_silence(path: Path, seconds: float) -> None:
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "anullsrc=r=16000:cl=mono", "-t", str(seconds),
            "-c:a", "pcm_s16le", str(path),
        ]
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    process = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=sample_rate,channels,codec_name",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(process.stdout)


def main() -> None:
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(f"missing required program: {program}")
    if not SOURCE.is_file():
        raise RuntimeError(f"missing source: {SOURCE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    silence_10 = OUTPUT_DIR / "pure-silence-10s.wav"
    silence_30 = OUTPUT_DIR / "pure-silence-30s.wav"
    pad_5 = OUTPUT_DIR / "silence-pad-5s.wav"
    pad_30 = OUTPUT_DIR / "silence-pad-30s.wav"
    room_tone = OUTPUT_DIR / "pink-room-tone-15s.wav"
    padded = OUTPUT_DIR / "english-with-5s-edge-silence.wav"
    padded_long = OUTPUT_DIR / "english-with-30s-edge-silence.wav"
    make_silence(silence_10, 10.0)
    make_silence(silence_30, 30.0)
    make_silence(pad_5, 5.0)
    make_silence(pad_30, 30.0)
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "anoisesrc=color=pink:sample_rate=16000:amplitude=0.003:duration=15:seed=731",
            "-ac", "1", "-c:a", "pcm_s16le", str(room_tone),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(pad_30), "-i", str(SOURCE), "-i", str(pad_30),
            "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
            "-map", "[out]", "-ar", "16000", "-ac", "1",
            "-c:a", "pcm_s16le", str(padded_long),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(pad_5), "-i", str(SOURCE), "-i", str(pad_5),
            "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
            "-map", "[out]", "-ar", "16000", "-ac", "1",
            "-c:a", "pcm_s16le", str(padded),
        ]
    )

    specs = [
        ("SIL-PURE-10", silence_10, "no speech; exact digital silence"),
        ("SIL-PURE-30", silence_30, "no speech; exact digital silence"),
        ("SIL-ROOM-15", room_tone, "no speech; low-level deterministic pink room tone"),
        ("SIL-PADDED-SPEECH", padded, "known speech with 5 seconds of silence before and after"),
        ("SIL-PADDED-LONG", padded_long, "known speech with 30 seconds of silence before and after"),
    ]
    records = []
    for case_id, path, purpose in specs:
        records.append(
            {
                "id": case_id,
                "file": str(path.relative_to(PROJECT_DIR)),
                "purpose": purpose,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "probe": probe(path),
            }
        )
    manifest = {
        "speech_source": str(SOURCE.relative_to(PROJECT_DIR)),
        "speech_expected": "Today is September second, twenty twenty-six. The meeting starts at three fifteen P.M. The order number is A seven three one.",
        "cases": records,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in records:
        print(f"{item['id']} {item['file']} sha256={item['sha256']}")
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
