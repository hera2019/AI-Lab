#!/usr/bin/env python3
"""Generate deterministic clean multilingual Phase 1 audio with macOS voices."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
SOURCE_DIR = AUDIO_DIR / "source"

CASES: list[dict[str, Any]] = [
    {
        "id": "ASR-ZH-001",
        "voice": "Tingting",
        "language": "zh",
        "text": "今天是二零二六年九月二日。会议将在下午三点十五分开始。订单编号是A七三一。",
        "file": "asr-zh-001.wav",
        "critical_values": ["2026-09-02", "15:15", "A731"],
    },
    {
        "id": "ASR-JA-001",
        "voice": "Kyoko",
        "language": "ja",
        "text": "今日は二千二十六年九月二日です。会議は午後三時十五分に始まります。注文番号はエー七三一です。",
        "file": "asr-ja-001.wav",
        "critical_values": ["2026-09-02", "15:15", "A731"],
    },
    {
        "id": "ASR-EN-001",
        "voice": "Samantha",
        "language": "en",
        "text": "Today is September second, twenty twenty-six. The meeting starts at three fifteen P.M. The order number is A seven three one.",
        "file": "asr-en-001.wav",
        "critical_values": ["2026-09-02", "15:15", "A731"],
    },
]

MIX_SEGMENTS = [
    ("Tingting", "项目代号是海风七号。", "mix-zh"),
    ("Kyoko", "次の会議は東京で開きます。", "mix-ja"),
    ("Samantha", "Please upload the final report by Friday.", "mix-en"),
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def synthesize(voice: str, text: str, stem: str) -> tuple[Path, Path]:
    aiff_path = SOURCE_DIR / f"{stem}.aiff"
    wav_path = AUDIO_DIR / f"{stem}.wav"
    run(["say", "-v", voice, "-o", str(aiff_path), text])
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(aiff_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
    )
    return aiff_path, wav_path


def main() -> None:
    if shutil.which("say") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError("macOS say and FFmpeg are required")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for case in CASES:
        stem = Path(case["file"]).stem
        _, wav_path = synthesize(case["voice"], case["text"], stem)
        records.append(
            {
                **case,
                "duration_seconds": round(duration_seconds(wav_path), 3),
                "sha256": sha256(wav_path),
                "audio_format": "16000 Hz mono PCM s16le WAV",
            }
        )

    mixed_wavs: list[Path] = []
    for voice, text, stem in MIX_SEGMENTS:
        _, wav_path = synthesize(voice, text, stem)
        mixed_wavs.append(wav_path)

    silence_path = SOURCE_DIR / "silence-600ms.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            "0.6",
            "-c:a",
            "pcm_s16le",
            str(silence_path),
        ]
    )
    mixed_path = AUDIO_DIR / "asr-mix-001.wav"
    inputs: list[str] = []
    for path in [mixed_wavs[0], silence_path, mixed_wavs[1], silence_path, mixed_wavs[2]]:
        inputs.extend(["-i", str(path)])
    run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            *inputs,
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
            str(mixed_path),
        ]
    )
    records.append(
        {
            "id": "ASR-MIX-001",
            "voices": [segment[0] for segment in MIX_SEGMENTS],
            "language": "zh+ja+en",
            "text_segments": [segment[1] for segment in MIX_SEGMENTS],
            "file": mixed_path.name,
            "critical_values": ["海风七号", "東京", "Friday"],
            "duration_seconds": round(duration_seconds(mixed_path), 3),
            "sha256": sha256(mixed_path),
            "audio_format": "16000 Hz mono PCM s16le WAV",
            "silence_between_segments_seconds": 0.6,
        }
    )

    manifest = {
        "generator": "macOS say + FFmpeg",
        "purpose": "clean synthetic baseline; not a substitute for human recordings",
        "cases": records,
    }
    manifest_path = AUDIO_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for record in records:
        print(
            f"{record['id']} {record['file']} "
            f"duration={record['duration_seconds']:.3f}s sha256={record['sha256']}"
        )
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
