#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-4-error-handling"
summary_file="$result_dir/summary.txt"
probe_tmp_dir="$(mktemp -d -t flux2-phase4-errors.XXXXXX)"
unexpected_count=0

cleanup() {
    rm -rf -- "$probe_tmp_dir"
}
trap cleanup EXIT

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
: >"$summary_file"

run_expect_failure() {
    local case_id="$1"
    shift
    local log_file="$result_dir/$case_id.log"

    "$@" >"$log_file" 2>&1
    local status=$?

    printf '%s exit_code=%d\n' "$case_id" "$status" | tee -a "$summary_file"
    if [[ "$status" -eq 0 ]]; then
        printf '%s UNEXPECTED_SUCCESS\n' "$case_id" | tee -a "$summary_file"
        unexpected_count=$((unexpected_count + 1))
    else
        printf '%s correctly_failed=yes\n' "$case_id" | tee -a "$summary_file"
    fi
}

run_expect_failure "01-unknown-option" \
    "$sd_cli" --phase4-option-does-not-exist

run_expect_failure "02-missing-model" \
    "$sd_cli" \
        --diffusion-model "$probe_tmp_dir/does-not-exist.gguf" \
        --prompt "test" \
        --width 64 \
        --height 64 \
        --steps 1 \
        --output "$probe_tmp_dir/missing-model.png"

run_expect_failure "03-missing-reference" \
    "$sd_cli" \
        --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
        --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
        --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
        --ref-image "$probe_tmp_dir/does-not-exist.png" \
        --prompt "test" \
        --width 64 \
        --height 64 \
        --steps 1 \
        --output "$probe_tmp_dir/missing-reference.png"

# A directory with a .png suffix is deliberately used as the output target.
# Image generation should finish, saving should fail, and sd-cli should return non-zero.
mkdir "$probe_tmp_dir/cannot-write.png"
run_expect_failure "04-save-failure" \
    "$sd_cli" \
        --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
        --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
        --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
        --prompt "A plain red circle centered on a white background." \
        --width 64 \
        --height 64 \
        --steps 1 \
        --cfg-scale 1.0 \
        --sampling-method euler \
        --seed 260904 \
        --diffusion-fa \
        --offload-to-cpu \
        --output "$probe_tmp_dir/cannot-write.png"

printf 'unexpected_successes=%d\n' "$unexpected_count" | tee -a "$summary_file"
if [[ "$unexpected_count" -ne 0 ]]; then
    exit 1
fi
