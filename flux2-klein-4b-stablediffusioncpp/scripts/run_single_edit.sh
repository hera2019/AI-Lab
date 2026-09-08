#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
input_file="$project_dir/results/generated/phase-2-instruction-isolation/03-position.png"
result_dir="$project_dir/results/generated/phase-3-single-edit"
output_file="$result_dir/01-blue-to-yellow.png"
log_file="$result_dir/01-blue-to-yellow.log"
prompt_file="$result_dir/01-blue-to-yellow-prompt.txt"
seed="260909"
prompt="Edit the provided image. Change only the blue glass sphere on the right to yellow glass. Preserve its transparent glass material, reflections, exact size, and exact position. Keep the red wooden cube on the left, beige background, lighting, shadows, camera angle, and composition unchanged. Do not add, remove, or move any objects. Add no text."

required_files=(
    "$sd_cli"
    "$input_file"
    "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf"
    "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf"
    "$model_dir/vae/full_encoder_small_decoder.safetensors"
)

for path in "${required_files[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "Required file not found: $path" >&2
        exit 2
    fi
done

mkdir -p "$result_dir"

if [[ -e "$output_file" ]]; then
    echo "Output already exists; refusing to overwrite: $output_file" >&2
    exit 3
fi

printf '%s\n' "$prompt" >"$prompt_file"

echo "Editing blue sphere to yellow (seed $seed, 1024x1024, 4 steps)"

/usr/bin/time -l "$sd_cli" \
    --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
    --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
    --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
    --ref-image "$input_file" \
    --ref-image-args "preset=flux2" \
    --prompt "$prompt" \
    --width 1024 \
    --height 1024 \
    --steps 4 \
    --cfg-scale 1.0 \
    --sampling-method euler \
    --seed "$seed" \
    --diffusion-fa \
    --offload-to-cpu \
    --verbose \
    --output "$output_file" 2>&1 | tee "$log_file"

if [[ ! -s "$output_file" ]]; then
    echo "No valid output image was created" >&2
    exit 4
fi

echo "Single-image edit complete: results/generated/phase-3-single-edit/01-blue-to-yellow.png"
