#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
video_dir="$project_dir/tests/fixtures/video"
log_file="$project_dir/results/video-baseline-latest.log"

if [[ ! -x "$llama_cli" ]]; then
    echo "Missing llama-cli: worktrees/llama.cpp/build-release-metal/bin/llama-cli" >&2
    exit 1
fi

if [[ ! -f "$video_dir/20-video-abc.mp4" || ! -f "$video_dir/21-video-cba-猫-東京-🧪.mp4" ]]; then
    echo "Missing video fixtures; run scripts/generate_video_fixtures.sh first" >&2
    exit 1
fi

exec > >(tee "$log_file") 2>&1

run_case() {
    local case_id="$1"
    local video_file="$2"

    echo
    echo "===== $case_id ====="
    LLAMA_CACHE="$model_cache" "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --video "$video_file" \
        --video-fps 1 \
        --video-timestamp-interval 1000 \
        -p "Watch the complete video. Report the three stages from beginning to end. For each stage, give its position, letter, color, shape, and code. Do not sort by letter." \
        -ngl all \
        -fa on \
        -c 8192 \
        -n 160 \
        --no-warmup \
        --temp 0 \
        --reasoning off \
        --simple-io \
        --single-turn
    local status=$?
    echo "===== $case_id exit=$status ====="
}

run_case "VIDEO-001-ABC" "$video_dir/20-video-abc.mp4"
run_case "VIDEO-002-CBA-UNICODE" "$video_dir/21-video-cba-猫-東京-🧪.mp4"
