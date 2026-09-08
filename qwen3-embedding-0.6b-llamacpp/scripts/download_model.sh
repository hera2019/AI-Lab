#!/usr/bin/env bash

set -euo pipefail

model_dir="${EMBEDDING_MODEL_DIR:-$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b}"
target="$model_dir/Qwen3-Embedding-0.6B-Q8_0.gguf"
part_file="$target.part"
expected_bytes="639150592"
expected_sha256="06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
revision="370f27d7550e0def9b39c1f16d3fbaa13aa67728"
url="https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/$revision/Qwen3-Embedding-0.6B-Q8_0.gguf"

mkdir -p "$model_dir"

if [[ -f "$target" ]]; then
    actual_bytes="$(stat -f '%z' "$target")"
    actual_sha256="$(shasum -a 256 "$target" | awk '{print $1}')"
    if [[ "$actual_bytes" == "$expected_bytes" && "$actual_sha256" == "$expected_sha256" ]]; then
        echo "Model already present and verified: $target"
        exit 0
    fi
    echo "Existing model does not match the pinned file; refusing to overwrite: $target" >&2
    exit 3
fi

echo "Downloading Qwen3-Embedding-0.6B Q8_0 (639,150,592 bytes)..."
curl --location --fail --retry 5 --retry-delay 5 --continue-at - \
    --progress-bar --output "$part_file" "$url"

actual_bytes="$(stat -f '%z' "$part_file")"
actual_sha256="$(shasum -a 256 "$part_file" | awk '{print $1}')"

if [[ "$actual_bytes" != "$expected_bytes" ]]; then
    echo "Size mismatch: expected $expected_bytes, got $actual_bytes" >&2
    exit 4
fi
if [[ "$actual_sha256" != "$expected_sha256" ]]; then
    echo "SHA-256 mismatch" >&2
    exit 5
fi

mv "$part_file" "$target"
echo "Model downloaded and verified: $target"
