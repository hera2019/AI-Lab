#!/usr/bin/env python3
"""Create mobile/common container variants from one fixed English WAV."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
OUTPUT_DIR = AUDIO_DIR / "phase2-formats"
SOURCE = AUDIO_DIR / "asr-en-001.wav"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(process.stdout)


def main() -> None:
    if not SOURCE.is_file():
        raise RuntimeError(f"missing Phase 1 source: {SOURCE}")
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(f"missing required program: {program}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = OUTPUT_DIR / "english-reference.wav"
    m4a_path = OUTPUT_DIR / "english-voice-memo.m4a"
    mp3_path = OUTPUT_DIR / "english-shared-audio.mp3"
    mov_path = OUTPUT_DIR / "english-camera-video.mov"

    shutil.copy2(SOURCE, wav_path)
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(SOURCE),
            "-c:a", "aac", "-b:a", "64k", str(m4a_path),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(SOURCE),
            "-c:a", "libmp3lame", "-b:a", "96k", str(mp3_path),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=640x360:r=1",
            "-i", str(SOURCE), "-shortest",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k", str(mov_path),
        ]
    )

    descriptions = {
        wav_path: "uncompressed reference",
        m4a_path: "iPhone Voice Memos-like AAC audio container",
        mp3_path: "common shared/downloaded audio",
        mov_path: "camera-like MOV with H.264 video and AAC audio",
    }
    files = []
    for path, purpose in descriptions.items():
        files.append(
            {
                "file": str(path.relative_to(PROJECT_DIR)),
                "purpose": purpose,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "probe": probe(path),
            }
        )
    manifest = {
        "source": str(SOURCE.relative_to(PROJECT_DIR)),
        "expected_text": "Today is September second, twenty twenty-six. The meeting starts at three fifteen P.M. The order number is A seven three one.",
        "critical_values": ["2026-09-02", "15:15", "A731"],
        "files": files,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in files:
        streams = ",".join(stream["codec_name"] for stream in item["probe"]["streams"])
        print(
            f"{item['file']} bytes={item['size_bytes']} codecs={streams} "
            f"sha256={item['sha256']}"
        )
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
