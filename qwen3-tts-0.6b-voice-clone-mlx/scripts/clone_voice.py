#!/usr/bin/env python3

"""Generate a consented local voice clone and record reproducible metrics."""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from pathlib import Path


DEFAULT_MODEL_DIR = Path(
    str(Path.home() / "Documents/AI-Models/tts/qwen3-tts-0.6b-base-mlx")
)


def standard_rtf(processing_seconds: float, audio_seconds: float) -> float:
    """Return processing seconds per generated audio second."""
    if processing_seconds < 0 or audio_seconds <= 0:
        raise ValueError("timings must be positive")
    return processing_seconds / audio_seconds


def resolve_text(direct: str | None, text_file: Path | None, label: str) -> str:
    """Resolve non-empty text supplied directly or through a UTF-8 file."""
    value = direct if direct is not None else text_file.read_text(encoding="utf-8")
    value = value.strip()
    if not value:
        raise ValueError(f"{label} must not be empty")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Qwen3-TTS voice cloning")
    parser.add_argument("--reference-audio", type=Path, required=True)
    reference_group = parser.add_mutually_exclusive_group(required=True)
    reference_group.add_argument("--reference-text")
    reference_group.add_argument("--reference-text-file", type=Path)
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--text")
    target_group.add_argument("--text-file", type=Path)
    parser.add_argument("--language", default="chinese")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--seed", type=int, default=260906)
    parser.add_argument(
        "--consent-confirmed",
        action="store_true",
        help="Confirm that the speaker is you or explicitly authorized cloning.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.consent_confirmed:
        raise SystemExit(
            "Refusing to clone without --consent-confirmed. "
            "Use only your own or explicitly authorized voice."
        )
    if not args.reference_audio.is_file():
        raise SystemExit(f"Reference audio does not exist: {args.reference_audio}")
    if not (args.model / "model.safetensors").is_file():
        raise SystemExit(f"Model is incomplete or missing: {args.model}")
    try:
        reference_text = resolve_text(
            args.reference_text, args.reference_text_file, "Reference text"
        )
        target_text = resolve_text(args.text, args.text_file, "Target text")
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    # Keep library caches with model weights rather than in ~/.cache.
    hf_home = args.model.parent / ".huggingface"
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("HF_XET_CACHE", str(hf_home / "xet"))

    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from mlx_audio.tts.utils import load_model

    reference_info = sf.info(args.reference_audio)
    mx.random.seed(args.seed)
    mx.reset_peak_memory()

    total_started = time.perf_counter()
    load_started = time.perf_counter()
    model = load_model(args.model)
    load_seconds = time.perf_counter() - load_started

    generation_started = time.perf_counter()
    generated = list(
        model.generate(
            text=target_text,
            lang_code=args.language,
            ref_audio=str(args.reference_audio),
            ref_text=reference_text,
            temperature=0.9,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.5,
            stream=False,
            verbose=False,
        )
    )
    generation_seconds = time.perf_counter() - generation_started
    if not generated:
        raise RuntimeError("The model returned no audio")

    sample_rates = {int(item.sample_rate) for item in generated}
    if len(sample_rates) != 1:
        raise RuntimeError(f"Generated segments have mixed sample rates: {sample_rates}")
    sample_rate = sample_rates.pop()
    audio_parts = [np.asarray(item.audio, dtype=np.float32).reshape(-1) for item in generated]
    audio = np.concatenate(audio_parts)
    audio_seconds = len(audio) / sample_rate
    if not np.isfinite(audio).all() or audio_seconds <= 0:
        raise RuntimeError("Generated audio is empty or contains non-finite samples")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, sample_rate, subtype="PCM_16")

    total_seconds = time.perf_counter() - total_started
    rtf = standard_rtf(generation_seconds, audio_seconds)
    payload = {
        "synthetic_audio": True,
        "consent": "self_or_explicitly_authorized",
        "model": str(args.model),
        "reference_audio": str(args.reference_audio),
        "reference_text": reference_text,
        "reference_audio_seconds": reference_info.duration,
        "target_text": target_text,
        "language": args.language,
        "seed": args.seed,
        "output": str(args.output),
        "sample_rate": sample_rate,
        "samples": len(audio),
        "audio_seconds": audio_seconds,
        "load_seconds": load_seconds,
        "generation_seconds": generation_seconds,
        "total_seconds": total_seconds,
        "standard_rtf_processing_per_audio": rtf,
        "realtime_speedup": 1.0 / rtf if rtf > 0 else None,
        "mlx_peak_memory_bytes": int(mx.get_peak_memory()),
        "process_max_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }
    args.metadata.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"output={args.output}")
    print(f"metadata={args.metadata}")
    print(f"reference_audio_seconds={reference_info.duration:.3f}")
    print(f"generated_audio_seconds={audio_seconds:.3f}")
    print(f"model_load_seconds={load_seconds:.3f}")
    print(f"generation_seconds={generation_seconds:.3f}")
    print(f"standard_rtf={rtf:.3f}")
    print(f"realtime_speedup={1.0 / rtf:.3f}x")
    print(f"mlx_peak_memory_bytes={int(mx.get_peak_memory())}")
    print("synthetic_audio=yes")


if __name__ == "__main__":
    main()
