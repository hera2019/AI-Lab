#!/usr/bin/env python3
"""Create deterministic pink-noise mixtures at measured target SNR values."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "tests/fixtures/audio"
OUTPUT_DIR = AUDIO_DIR / "phase3-noise"
SOURCE = AUDIO_DIR / "asr-en-001.wav"
TARGET_SNRS = (20, 10, 0)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def pcm_stats(path: Path) -> tuple[float, int, int]:
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise RuntimeError(f"expected mono PCM s16 WAV: {path}")
        frame_count = handle.getnframes()
        data = handle.readframes(frame_count)
    samples = struct.unpack(f"<{len(data) // 2}h", data)
    rms = math.sqrt(sum(sample * sample for sample in samples) / max(len(samples), 1))
    peak = max(abs(sample) for sample in samples)
    return rms, peak, frame_count


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

    source_rms, source_peak, frame_count = pcm_stats(SOURCE)
    duration = frame_count / 16000
    raw_noise = OUTPUT_DIR / "pink-noise-source.wav"
    run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", f"anoisesrc=color=pink:sample_rate=16000:amplitude=0.5:duration={duration}:seed=731",
            "-ac", "1", "-c:a", "pcm_s16le", str(raw_noise),
        ]
    )
    noise_rms, noise_peak, _ = pcm_stats(raw_noise)

    records = []
    for target_snr in TARGET_SNRS:
        relative_noise_gain = source_rms / (noise_rms * (10 ** (target_snr / 20)))
        common_scale = min(1.0, 0.90 * 32767 / (source_peak + noise_peak * relative_noise_gain))
        speech_weight = common_scale
        noise_weight = relative_noise_gain * common_scale
        output = OUTPUT_DIR / f"english-pink-noise-snr-{target_snr}db.wav"
        run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(SOURCE), "-i", str(raw_noise),
                "-filter_complex",
                f"[0:a][1:a]amix=inputs=2:weights='{speech_weight} {noise_weight}':normalize=0[out]",
                "-map", "[out]", "-ar", "16000", "-ac", "1",
                "-c:a", "pcm_s16le", str(output),
            ]
        )
        achieved_snr = 20 * math.log10(
            (source_rms * speech_weight) / (noise_rms * noise_weight)
        )
        records.append(
            {
                "id": f"NOISE-EN-{target_snr}DB",
                "file": str(output.relative_to(PROJECT_DIR)),
                "target_snr_db": target_snr,
                "calculated_snr_db": achieved_snr,
                "speech_weight": speech_weight,
                "noise_weight": noise_weight,
                "size_bytes": output.stat().st_size,
                "sha256": sha256(output),
                "probe": probe(output),
            }
        )

    manifest = {
        "source": str(SOURCE.relative_to(PROJECT_DIR)),
        "expected_text": "Today is September second, twenty twenty-six. The meeting starts at three fifteen P.M. The order number is A seven three one.",
        "critical_values": ["2026-09-02", "15:15", "A731"],
        "noise": "deterministic FFmpeg pink noise, seed 731",
        "snr_definition": "20*log10(weighted speech RMS / weighted noise RMS), measured over the full source duration",
        "cases": records,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in records:
        print(
            f"{item['id']} calculated_snr_db={item['calculated_snr_db']:.3f} "
            f"sha256={item['sha256']}"
        )
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
