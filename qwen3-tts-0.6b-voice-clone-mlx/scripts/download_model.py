#!/usr/bin/env python3

"""Download and verify the pinned MLX Qwen3-TTS voice-cloning model."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

REPOSITORY = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16"
REVISION = "1eccf1cb2519b5a4e8a95b5f0544f3303568164f"
DEFAULT_MODEL_DIR = Path(
    str(Path.home() / "Documents/AI-Models/tts/qwen3-tts-0.6b-base-mlx")
)

# Keep every Hugging Face/Xet download artifact in the model area instead of
# silently using ~/.cache. These must be set before importing huggingface_hub.
DEFAULT_HF_HOME = DEFAULT_MODEL_DIR.parent / ".huggingface"
os.environ.setdefault("HF_HOME", str(DEFAULT_HF_HOME))
os.environ.setdefault("HF_HUB_CACHE", str(DEFAULT_HF_HOME / "hub"))
os.environ.setdefault("HF_XET_CACHE", str(DEFAULT_HF_HOME / "xet"))

from huggingface_hub import snapshot_download


EXPECTED_FILES = {
    "model.safetensors": (
        1_829_344_448,
        "d7c7ed3e3464e3e59de0f955b3755891fa8319ff061c3f0307fe2e1343bc122d",
    ),
    "speech_tokenizer/model.safetensors": (
        682_293_092,
        "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    model_dir = Path(os.environ.get("QWEN3_TTS_MODEL_DIR", DEFAULT_MODEL_DIR))
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"repository={REPOSITORY}")
    print(f"revision={REVISION}")
    print(f"model_dir={model_dir}")
    print(f"hf_home={os.environ['HF_HOME']}")

    snapshot_download(
        repo_id=REPOSITORY,
        revision=REVISION,
        local_dir=model_dir,
        max_workers=4,
    )

    for relative_path, (expected_size, expected_sha256) in EXPECTED_FILES.items():
        path = model_dir / relative_path
        actual_size = path.stat().st_size
        actual_sha256 = sha256(path)
        if actual_size != expected_size:
            raise SystemExit(
                f"size mismatch for {relative_path}: {actual_size} != {expected_size}"
            )
        if actual_sha256 != expected_sha256:
            raise SystemExit(
                f"SHA-256 mismatch for {relative_path}: "
                f"{actual_sha256} != {expected_sha256}"
            )
        print(
            f"verified={relative_path} bytes={actual_size} sha256={actual_sha256}"
        )

    print("model_verification=PASS")


if __name__ == "__main__":
    main()
