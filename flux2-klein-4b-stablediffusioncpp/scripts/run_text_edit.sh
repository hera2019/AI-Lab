#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
input_file="$project_dir/results/generated/phase-2-instruction-isolation/04-text.png"
result_dir="$project_dir/results/generated/phase-3-single-edit"
output_file="$result_dir/02-local-ai-to-local-lab.png"
log_file="$result_dir/02-local-ai-to-local-lab.log"
prompt_file="$result_dir/02-local-ai-to-local-lab-prompt.txt"
seed="260910"
prompt="Edit the provided image. Replace only the exact uppercase text LOCAL AI with the exact uppercase text LOCAL LAB. The sign must contain only LOCAL LAB, perfectly spelled, in the same large black sans-serif style and centered placement. Preserve the rectangular white sign's exact size and position, the dark wall, lighting, shadows, camera angle, and composition. Do not add any other words, letters, logos, symbols, objects, or decorations."

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

echo "Replacing LOCAL AI with LOCAL LAB (seed $seed, 1024x1024, 4 steps)"

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

echo "Text edit complete: results/generated/phase-3-single-edit/02-local-ai-to-local-lab.png"
