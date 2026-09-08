#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
input_file="$project_dir/results/generated/phase-1-baseline/flux2-klein-4b-seed-260903.png"
result_dir="$project_dir/results/generated/phase-3-single-edit"
output_file="$result_dir/03-remove-white-cat.png"
log_file="$result_dir/03-remove-white-cat.log"
prompt_file="$result_dir/03-remove-white-cat-prompt.txt"
seed="260911"
prompt="Edit the provided image. Remove only the small white or cream-colored cat sitting on the right side of the serving counter. Replace the area it occupied with a natural continuation of the wooden counter and the shop interior behind it. Keep the small blue ceramic cat on the left side of the counter exactly unchanged. Preserve every other existing element: the red bicycle, all five paper lanterns, the storefront, rainy street, reflections, lighting, shadows, camera angle, composition, and the exact current sign text AI LLAB. Do not correct or alter the sign. Do not add any new object, animal, person, text, logo, or decoration."

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

echo "Removing the unintended white cat (seed $seed, 1024x1024, 4 steps)"

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

echo "Object removal complete: results/generated/phase-3-single-edit/03-remove-white-cat.png"
