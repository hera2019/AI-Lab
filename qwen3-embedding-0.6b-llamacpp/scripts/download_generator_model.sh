#!/usr/bin/env bash

set -euo pipefail

repo="ggml-org/Qwen3-4B-Instruct-2507-Q8_0-GGUF"
revision="e6f794d44f9395d0184a966c27b5ae99ea356fcb"
filename="qwen3-4b-instruct-2507-q8_0.gguf"
expected_bytes="4280403520"
expected_sha256="ae916ede1c010a26955ee8ae2e908bf8815a3f135ec860439ab924701c69d5f1"
model_dir="${GENERATOR_MODEL_DIR:-$HOME/Documents/AI-Models/generators/qwen3-4b-instruct-2507}"
model_path="$model_dir/$filename"
partial_path="$model_path.part"
url="https://huggingface.co/$repo/resolve/$revision/$filename"

mkdir -p "$model_dir"

verify_model() {
    local path="$1"
    local actual_bytes actual_sha256
    actual_bytes="$(stat -f '%z' "$path")"
    if [[ "$actual_bytes" != "$expected_bytes" ]]; then
        echo "Size mismatch: expected $expected_bytes, received $actual_bytes" >&2
        return 1
    fi
    actual_sha256="$(shasum -a 256 "$path" | awk '{print $1}')"
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        echo "SHA-256 mismatch: expected $expected_sha256, received $actual_sha256" >&2
        return 1
    fi
}

if [[ -f "$model_path" ]]; then
    echo "Model already exists; verifying it."
    verify_model "$model_path"
else
    echo "Downloading $repo at revision $revision"
    curl -L --fail --show-error --continue-at - --output "$partial_path" "$url"
    verify_model "$partial_path"
    mv "$partial_path" "$model_path"
fi

echo "model_path=$model_path"
echo "bytes=$expected_bytes"
echo "sha256=$expected_sha256"
echo "revision=$revision"
