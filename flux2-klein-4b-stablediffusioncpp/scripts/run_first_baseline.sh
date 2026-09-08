#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-1-baseline"
output_file="${OUTPUT_FILE:-$result_dir/flux2-klein-4b-seed-260903.png}"
log_file="${LOG_FILE:-${output_file%.*}.log}"
prompt_file="${PROMPT_FILE:-${output_file%.*}-prompt.txt}"

prompt="A cinematic realistic photograph of a tiny ramen shop on a quiet Tokyo side street at night in the rain, viewed through wet glass. Exactly three warm paper lanterns hang above the entrance. One red bicycle is parked on the left side. A small blue ceramic cat sits on the counter. Warm amber interior light contrasts with cool teal rain, detailed reflections, natural proportions, 35mm photography. A simple clean sign above the door clearly reads AI LAB."

required_files=(
    "$sd_cli"
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
mkdir -p "$(dirname "$output_file")"

if [[ -e "$output_file" && "${ALLOW_OVERWRITE:-0}" != "1" ]]; then
    echo "Output already exists; refusing to overwrite: $output_file" >&2
    exit 4
fi

printf '%s\n' "$prompt" >"$prompt_file"

echo "Output: ${output_file#"$project_dir/"}"
echo "Seed: 260903"
echo "Size: 1024x1024"
echo "Steps: 4"
echo "Starting FLUX.2 baseline generation..."

/usr/bin/time -l "$sd_cli" \
    --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
    --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
    --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
    --prompt "$prompt" \
    --width 1024 \
    --height 1024 \
    --steps 4 \
    --cfg-scale 1.0 \
    --sampling-method euler \
    --seed 260903 \
    --diffusion-fa \
    --offload-to-cpu \
    --verbose \
    --output "$output_file" 2>&1 | tee "$log_file"

if [[ ! -s "$output_file" ]]; then
    echo "Generation finished without a non-empty output image" >&2
    exit 3
fi

echo "Generation complete: $output_file"
