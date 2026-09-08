#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
probe_tmp_dir="$(mktemp -d -t qwen3-vl-invalid-media.XXXXXX)"
bug_count=0

cleanup() {
    rm -rf "$probe_tmp_dir"
}
trap cleanup EXIT

run_case() {
    local case_id="$1"
    local input_file="$2"
    local output_file="$probe_tmp_dir/$case_id.log"

    LLAMA_CACHE="$model_cache" "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --image "$input_file" \
        -p "Report whether the media loaded." \
        -ngl all \
        -c 4096 \
        -n 1 \
        --no-warmup \
        --reasoning off \
        --simple-io \
        --single-turn >"$output_file" 2>&1
    local status=$?

    echo "$case_id exit_code=$status"
    if grep -q "Error: Failed to load image or audio file" "$output_file"; then
        echo "$case_id decoder_error=yes"
    else
        echo "$case_id decoder_error=no"
    fi

    if [[ "$status" -eq 0 ]] && grep -q "Error: Failed to load image or audio file" "$output_file"; then
        echo "$case_id BUG_REPRODUCED: decoder error returned success"
        bug_count=$((bug_count + 1))
    fi
}

run_missing_case() {
    local output_file="$probe_tmp_dir/BAD-MISSING.log"

    LLAMA_CACHE="$model_cache" "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --image "$probe_tmp_dir/does-not-exist.png" \
        -p "Report whether the media loaded." \
        -ngl all \
        -c 4096 \
        -n 1 \
        --no-warmup \
        --reasoning off \
        --simple-io \
        --single-turn >"$output_file" 2>&1
    local status=$?

    echo "BAD-MISSING exit_code=$status"
    if grep -q "file does not exist or cannot be opened" "$output_file"; then
        echo "BAD-MISSING staging_error=yes"
    else
        echo "BAD-MISSING staging_error=no"
    fi

    if [[ "$status" -eq 0 ]] && grep -q "file does not exist or cannot be opened" "$output_file"; then
        echo "BAD-MISSING BUG_REPRODUCED: staging error returned success"
        bug_count=$((bug_count + 1))
    fi
}

run_case "BAD-002" "$project_dir/tests/fixtures/invalid/18-not-an-image.jpg"
run_case "BAD-003" "$project_dir/tests/fixtures/invalid/19-empty.png"
run_missing_case

echo "reproduced_cases=$bug_count"
if [[ "$bug_count" -ne 0 ]]; then
    exit 1
fi
