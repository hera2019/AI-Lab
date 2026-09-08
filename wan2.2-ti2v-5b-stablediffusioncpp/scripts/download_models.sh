#!/usr/bin/env bash

set -euo pipefail

model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"

download_one() {
    local label="$1"
    local url="$2"
    local target="$3"
    local expected_bytes="$4"
    local expected_sha256="$5"
    local part_file="$target.part"

    mkdir -p "$(dirname "$target")"

    if [[ -f "$target" ]]; then
        local existing_sha256
        existing_sha256="$(shasum -a 256 "$target" | awk '{print $1}')"
        if [[ "$existing_sha256" == "$expected_sha256" ]]; then
            echo "$label already present and verified"
            return
        fi
        echo "$label exists but its SHA-256 is wrong; refusing to overwrite: $target" >&2
        exit 3
    fi

    echo "Downloading $label"
    curl --location --fail --retry 5 --retry-delay 5 --continue-at - \
        --progress-bar --output "$part_file" "$url"

    local actual_bytes
    local actual_sha256
    actual_bytes="$(stat -f '%z' "$part_file")"
    actual_sha256="$(shasum -a 256 "$part_file" | awk '{print $1}')"

    if [[ "$actual_bytes" != "$expected_bytes" ]]; then
        echo "$label size mismatch: expected $expected_bytes, got $actual_bytes" >&2
        exit 4
    fi
    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        echo "$label SHA-256 mismatch" >&2
        exit 5
    fi

    mv "$part_file" "$target"
    echo "$label verified: $actual_bytes bytes"
}

download_one \
    "Wan2.2 TI2V 5B Q4_K_M" \
    "https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF/resolve/57437632ddd08bdcbd1508c866aa22e126ed51d2/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
    "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
    "3433116000" \
    "95b19697b7f98e65b0a543640e9ca7b4dfec32e2a6e3731e8e10708be52655e2"

download_one \
    "UMT5-XXL Q5_K_M" \
    "https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/b535255bee98c2b0a59ea7c0ae2dcd0c6657b3b7/umt5-xxl-encoder-Q5_K_M.gguf" \
    "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    "4145878880" \
    "eaea358bb438c5d211721a4feecc162000e3636e9cb96f51e216f1f44ebd12ce"

download_one \
    "Wan2.2 VAE" \
    "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/c4f60d30c55a624e35427060fdd217579a6c1d77/split_files/vae/wan2.2_vae.safetensors" \
    "$model_dir/vae/wan2.2_vae.safetensors" \
    "1409400960" \
    "e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156"

download_one \
    "Wan2.2 TI2V 5B TAEHV" \
    "https://raw.githubusercontent.com/madebyollin/taehv/011dfc2112197741c540e0bdd5b7b67bcc930771/safetensors/taew2_2.safetensors" \
    "$model_dir/tae/taew2_2.safetensors" \
    "22848048" \
    "b84609b2a133d48434bd9636bfcb44bf05168dc436e2d3cecf26256faa1f5325"

download_one \
    "Wan2.2 TI2V 5B TAEHV Super (experimental compatibility probe)" \
    "https://raw.githubusercontent.com/madebyollin/taehv/011dfc2112197741c540e0bdd5b7b67bcc930771/safetensors/taew2_2_super.safetensors" \
    "$model_dir/tae/taew2_2_super.safetensors" \
    "40986488" \
    "cf6d8bdadb77d9f9741ae28b5b4659bb74cf9b0be6d08fc4afed3cb50c39364c"

download_one \
    "FastWan2.2 TI2V 5B Q8_0" \
    "https://huggingface.co/Green-Sky/FastWan2.2-TI2V-5B-FullAttn-GGUF/resolve/3e8fe5537b1200654868aa24ea8d0f4012fb3a1e/FastWan2.2-TI2V-5B-q8_0.gguf" \
    "$model_dir/diffusion-fastwan/FastWan2.2-TI2V-5B-q8_0.gguf" \
    "5412844128" \
    "b62f50ff87c4dfa2910c6883d45015e05b709366581698b302e259e7f25c9208"

echo "All required and experimental model files are present and verified."
