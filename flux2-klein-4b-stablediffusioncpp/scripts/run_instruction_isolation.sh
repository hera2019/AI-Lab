#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-2-instruction-isolation"

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

run_one() {
    local case_id="$1"
    local seed="$2"
    local prompt="$3"
    local output_file="$result_dir/$case_id.png"
    local log_file="$result_dir/$case_id.log"
    local prompt_file="$result_dir/$case_id-prompt.txt"

    if [[ -e "$output_file" ]]; then
        echo "Output already exists; refusing to overwrite: $output_file" >&2
        exit 3
    fi

    printf '%s\n' "$prompt" >"$prompt_file"
    echo
    echo "Generating $case_id (seed $seed, 1024x1024, 4 steps)"

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
        --seed "$seed" \
        --diffusion-fa \
        --offload-to-cpu \
        --verbose \
        --output "$output_file" 2>&1 | tee "$log_file"

    if [[ ! -s "$output_file" ]]; then
        echo "No valid output created for $case_id" >&2
        exit 4
    fi
}

run_one \
    "01-quantity" \
    "260905" \
    "A clean studio product photograph on a plain light gray background. Exactly three red apples, no more and no fewer, arranged in one straight horizontal row. No other objects, no text."

run_one \
    "02-color" \
    "260906" \
    "A clean studio product photograph of exactly three identical ceramic mugs in a straight horizontal row on a plain white background. The mugs are three different solid colors: red, green, and blue. No patterns, no text, no other objects."

run_one \
    "03-position" \
    "260907" \
    "A clean tabletop photograph with only two objects: a red wooden cube on the far left and a blue glass sphere on the far right, with a large empty gap between them. The cube must not be on the right. The sphere must not be on the left. Plain beige background, no text."

run_one \
    "04-text" \
    "260908" \
    "A front-facing photograph of a single rectangular white sign on a plain dark wall. The sign contains only the exact uppercase text LOCAL AI in large black sans-serif letters, centered, perfectly spelled. No other words, logos, symbols, or decorations."

echo
echo "Instruction isolation tests complete: results/generated/phase-2-instruction-isolation"
