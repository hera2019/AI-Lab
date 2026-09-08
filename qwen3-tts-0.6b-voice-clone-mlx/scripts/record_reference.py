#!/usr/bin/env python3

"""Record a controlled, consented voice-cloning reference from the microphone."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path


DEFAULT_TEXT = (
    "今天阳光很好，我正在测试完全本地的声音克隆。"
    "数字是一二三四五，我们希望声音自然、清楚，而且稳定。现在测试结束。"
)


def dbfs(amplitude: float) -> float:
    if amplitude <= 0:
        return float("-inf")
    return 20.0 * math.log10(amplitude)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a local voice reference")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--device", default=None)
    parser.add_argument("--consent-confirmed", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.consent_confirmed:
        raise SystemExit("Recording requires --consent-confirmed")
    if args.seconds <= 0 or args.sample_rate <= 0:
        raise SystemExit("Duration and sample rate must be positive")

    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    print("请用正常、自然的音量，逐字朗读下面这段话：\n")
    print(args.text)
    input("\n准备好后按回车；随后有 3 秒倒计时……")
    for remaining in (3, 2, 1):
        print(remaining, flush=True)
        time.sleep(1)
    print(f"开始录音（{args.seconds:.0f} 秒）……", flush=True)

    frames = round(args.seconds * args.sample_rate)
    recording = sd.rec(
        frames,
        samplerate=args.sample_rate,
        channels=1,
        dtype="float32",
        device=args.device,
    )
    sd.wait()
    audio = np.asarray(recording, dtype=np.float32).reshape(-1)
    print("录音结束。")

    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
    clipped_samples = int(np.count_nonzero(np.abs(audio) >= 0.999))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, args.sample_rate, subtype="PCM_16")

    payload = {
        "audio": str(args.output),
        "transcript": args.text,
        "language": "Chinese",
        "speaker_consent": "self",
        "duration_seconds": len(audio) / args.sample_rate,
        "sample_rate": args.sample_rate,
        "channels": 1,
        "peak_dbfs": dbfs(peak),
        "rms_dbfs": dbfs(rms),
        "clipped_samples": clipped_samples,
    }
    args.metadata.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"文件：{args.output}")
    print(f"平均音量：{dbfs(rms):.1f} dBFS")
    print(f"峰值：{dbfs(peak):.1f} dBFS")
    print(f"削波样本：{clipped_samples}")
    if rms < 10 ** (-35 / 20):
        print("提示：录音偏轻，建议靠近麦克风并用正常音量重录。")
    elif peak >= 0.999 or clipped_samples:
        print("提示：录音发生削波，建议离麦克风稍远或降低输入音量。")
    else:
        print("音量初检：正常。")


if __name__ == "__main__":
    main()
