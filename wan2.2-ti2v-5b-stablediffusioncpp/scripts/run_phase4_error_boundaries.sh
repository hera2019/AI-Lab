#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
result_dir="$project_dir/results/phase-4-boundaries"
probe_tmp_dir="$(mktemp -d -t wan22-boundaries.XXXXXX)"
failure_count=0

cleanup() {
    rm -rf -- "$probe_tmp_dir"
}
trap cleanup EXIT

if [[ ! -x "$sd_cli" ]]; then
    echo "sd-cli not found or not executable: $sd_cli" >&2
    exit 2
fi

mkdir -p "$result_dir"
: >"$probe_tmp_dir/empty.png"
printf 'this is not an image\n' >"$probe_tmp_dir/not-an-image.jpg"

run_bad_image_case() {
    local case_id="$1"
    local input_file="$2"
    local log_file="$result_dir/$case_id.log"

    "$sd_cli" \
        --mode vid_gen \
        --diffusion-model "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
        --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
        --tae "$model_dir/tae/taew2_2.safetensors" \
        --init-img "$input_file" \
        --prompt "Boundary test" \
        --width 832 \
        --height 480 \
        --video-frames 33 \
        --steps 1 \
        --output "$probe_tmp_dir/$case_id.webm" >"$log_file" 2>&1
    local status=$?

    printf '%s exit_code=%s\n' "$case_id" "$status"
    if [[ "$status" -ne 0 ]] && grep -q "load image from .* failed" "$log_file"; then
        printf '%s PASS: invalid input rejected before generation\n' "$case_id"
    else
        printf '%s FAIL: expected non-zero image-loading failure\n' "$case_id"
        failure_count=$((failure_count + 1))
    fi
}

run_missing_model_case() {
    local case_id="MISSING-MODEL"
    local log_file="$result_dir/$case_id.log"

    "$sd_cli" \
        --mode vid_gen \
        --diffusion-model "$probe_tmp_dir/does-not-exist.gguf" \
        --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
        --tae "$model_dir/tae/taew2_2.safetensors" \
        --prompt "Boundary test" \
        --width 832 \
        --height 480 \
        --video-frames 33 \
        --steps 1 \
        --output "$probe_tmp_dir/$case_id.webm" >"$log_file" 2>&1
    local status=$?

    printf '%s exit_code=%s\n' "$case_id" "$status"
    if [[ "$status" -ne 0 ]] && grep -Eq "failed to (open|load)|new_sd_ctx_t failed" "$log_file"; then
        printf '%s PASS: missing model rejected\n' "$case_id"
    else
        printf '%s FAIL: expected non-zero model-loading failure\n' "$case_id"
        failure_count=$((failure_count + 1))
    fi
}

run_bad_image_case "MISSING-IMAGE" "$probe_tmp_dir/does-not-exist.png"
run_bad_image_case "EMPTY-IMAGE" "$probe_tmp_dir/empty.png"
run_bad_image_case "TEXT-AS-JPEG" "$probe_tmp_dir/not-an-image.jpg"
run_missing_model_case

printf 'failed_checks=%s\n' "$failure_count"
if [[ "$failure_count" -ne 0 ]]; then
    exit 1
fi
