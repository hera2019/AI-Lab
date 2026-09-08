#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
scene_reference="$project_dir/results/generated/phase-3-single-edit/03-remove-white-cat.png"
object_reference="$project_dir/results/generated/phase-2-instruction-isolation/02-color.png"
result_dir="$project_dir/results/generated/phase-3-multi-reference"
output_file="$result_dir/01-green-mug-in-ramen-shop.png"
log_file="$result_dir/01-green-mug-in-ramen-shop.log"
prompt_file="$result_dir/01-green-mug-in-ramen-shop-prompt.txt"
seed="260912"
prompt="Use reference image 1 as the base scene. From reference image 2, take only the solid green ceramic mug in the center, not the red mug and not the blue mug. Place exactly one green ceramic mug on the right side of the wooden serving counter in reference image 1, in the empty space to the right of the small blue ceramic cat. Match the shop's warm lighting, perspective, scale, contact shadow, and reflections so the mug sits naturally on the counter. Preserve every other part of reference image 1: the blue ceramic cat, red bicycle, all five paper lanterns, storefront, rainy street, people, lighting, composition, and the exact current sign text AI LLAB. Do not alter or correct the sign. Do not add any red or blue mug, extra cup, cat, animal, person, word, logo, symbol, or decoration."

required_files=(
    "$sd_cli"
    "$scene_reference"
    "$object_reference"
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

echo "Combining shop scene with the green mug reference (seed $seed, 1024x1024, 4 steps)"

/usr/bin/time -l "$sd_cli" \
    --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
    --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
    --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
    --ref-image "$scene_reference" \
    --ref-image "$object_reference" \
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

echo "Multi-reference edit complete: results/generated/phase-3-multi-reference/01-green-mug-in-ramen-shop.png"
