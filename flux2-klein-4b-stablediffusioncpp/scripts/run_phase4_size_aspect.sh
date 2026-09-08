#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-4-size-aspect"
seed="260903"
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
printf '%s\n' "$prompt" >"$result_dir/prompt.txt"

run_case() {
    local case_id="$1"
    local width="$2"
    local height="$3"
    local output_file="$result_dir/$case_id.png"
    local log_file="$result_dir/$case_id.log"

    if [[ -e "$output_file" ]]; then
        echo "Output already exists; refusing to overwrite: $output_file" >&2
        exit 3
    fi

    echo "Running $case_id: ${width}x${height}, seed $seed, 4 steps"
    /usr/bin/time -l "$sd_cli" \
        --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
        --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
        --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
        --prompt "$prompt" \
        --width "$width" \
        --height "$height" \
        --steps 4 \
        --cfg-scale 1.0 \
        --sampling-method euler \
        --seed "$seed" \
        --diffusion-fa \
        --offload-to-cpu \
        --verbose \
        --output "$output_file" 2>&1 | tee "$log_file"

    if [[ ! -s "$output_file" ]]; then
        echo "No valid output image was created for $case_id" >&2
        exit 4
    fi
}

run_case "01-square-512" 512 512
run_case "02-square-768" 768 768
run_case "03-landscape-1024x768" 1024 768
run_case "04-portrait-768x1024" 768 1024

echo "Phase 4 size and aspect runs complete: results/generated/phase-4-size-aspect/"
