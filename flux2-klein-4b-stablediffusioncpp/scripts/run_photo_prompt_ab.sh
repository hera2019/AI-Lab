#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-2-photo-prompt-ab"
seed=260904

prompt_a="A realistic photograph of an adult Japanese woman sitting by a cafe window, holding a ceramic coffee cup."
prompt_b="An unretouched candid 50mm photograph of an adult Japanese woman in her early thirties sitting beside a large cafe window on an overcast afternoon, holding a simple white ceramic coffee cup with both hands. Natural relaxed expression, anatomically correct hands fully visible, realistic skin texture with subtle pores and fine facial hair, individual strands of dark hair, soft window light, gentle shadow falloff, neutral color grading, shallow depth of field, believable modern cafe background, documentary photography, no beauty retouching."

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
    local prompt="$2"
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

run_one "A-simple-prompt" "$prompt_a"
run_one "B-detailed-photo-prompt" "$prompt_b"

echo
echo "Photo prompt A/B complete: results/generated/phase-2-photo-prompt-ab"
