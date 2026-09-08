#!/usr/bin/env bash

set -euo pipefail

model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
minimum_margin_bytes=$((1024 * 1024 * 1024))

download_one() {
    local label="$1"
    local url="$2"
    local destination="$3"
    local expected_size="$4"
    local expected_sha256="$5"
    local partial="${destination}.part"

    mkdir -p "$(dirname "$destination")"

    if [[ -f "$destination" ]]; then
        local existing_size
        local existing_sha256
        existing_size="$(stat -f '%z' "$destination")"
        existing_sha256="$(shasum -a 256 "$destination" | awk '{print $1}')"
        if [[ "$existing_size" == "$expected_size" && "$existing_sha256" == "$expected_sha256" ]]; then
            echo "$label already present and verified"
            return
        fi
        echo "$label exists but does not match the pinned file: $destination" >&2
        exit 3
    fi

    if [[ -f "$partial" ]] && [[ "$(stat -f '%z' "$partial")" == "$expected_size" ]]; then
        if [[ "$(shasum -a 256 "$partial" | awk '{print $1}')" == "$expected_sha256" ]]; then
            mv "$partial" "$destination"
            echo "$label recovered from a verified completed partial download"
            return
        fi
    fi

    echo
    echo "Downloading $label"
    echo "Destination: $destination"
    curl --location --fail --retry 3 --retry-all-errors \
        --continue-at - --output "$partial" "$url"

    local actual_size
    local actual_sha256
    actual_size="$(stat -f '%z' "$partial")"
    actual_sha256="$(shasum -a 256 "$partial" | awk '{print $1}')"

    if [[ "$actual_size" != "$expected_size" ]]; then
        echo "$label size mismatch: expected $expected_size, got $actual_size" >&2
        exit 4
    fi
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        echo "$label SHA-256 mismatch" >&2
        echo "expected: $expected_sha256" >&2
        echo "actual:   $actual_sha256" >&2
        exit 5
    fi

    mv "$partial" "$destination"
    echo "$label verified"
}

remaining_bytes=0
files=(
    "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf:2460378560"
    "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf:2497281312"
    "$model_dir/vae/full_encoder_small_decoder.safetensors:249519092"
)

for entry in "${files[@]}"; do
    path="${entry%:*}"
    size="${entry##*:}"
    if [[ ! -f "$path" ]]; then
        remaining_bytes=$((remaining_bytes + size))
    fi
done

mkdir -p "$model_dir"
available_kib="$(df -k "$model_dir" | awk 'NR == 2 {print $4}')"
available_bytes=$((available_kib * 1024))
required_bytes=$((remaining_bytes + minimum_margin_bytes))

echo "Model directory: $model_dir"
echo "Remaining download bytes: $remaining_bytes"
echo "Available bytes: $available_bytes"

if (( available_bytes < required_bytes )); then
    echo "Not enough free space; keeping a 1 GiB safety margin requires $required_bytes bytes" >&2
    exit 6
fi

download_one \
    "FLUX.2 klein 4B diffusion Q4_0" \
    "https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/resolve/3b1f5a9dc3abb32238b053aeb3d823c30afdacbd/flux-2-klein-4b-Q4_0.gguf" \
    "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
    "2460378560" \
    "d1023499ef3f2f82ff7c50e6778495195c1b6cc34835741778868428111f9ff4"

download_one \
    "Qwen3-4B text encoder Q4_K_M" \
    "https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/22c9fc8a8c7700b76a1789366280a6a5a1ad1120/Qwen3-4B-Q4_K_M.gguf" \
    "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
    "2497281312" \
    "f6f851777709861056efcdad3af01da38b31223a3ba26e61a4f8bf3a2195813a"

download_one \
    "FLUX.2 full encoder + small decoder" \
    "https://huggingface.co/black-forest-labs/FLUX.2-small-decoder/resolve/a3efc24f613ef42d9428af62fdbd6f5fd8856c4a/full_encoder_small_decoder.safetensors" \
    "$model_dir/vae/full_encoder_small_decoder.safetensors" \
    "249519092" \
    "ea4273f02d1fafbf8e1d1c2cf6018ed8748652eb0bf34f2dd91171f16f15ab62"

echo
echo "All three model files downloaded and verified."
