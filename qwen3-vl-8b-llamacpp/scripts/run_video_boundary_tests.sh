#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
video_dir="$project_dir/tests/fixtures/video"
log_file="$project_dir/results/video-boundary-latest.log"

if [[ ! -x "$llama_cli" ]]; then
    echo "Missing llama-cli: worktrees/llama.cpp/build-release-metal/bin/llama-cli" >&2
    exit 1
fi

for required_file in \
    "$video_dir/22-video-a-very-short.mp4" \
    "$video_dir/23-video-abc-moov-tail.mp4" \
    "$video_dir/24-video-vfr-abc.mp4" \
    "$video_dir/25-not-a-video.mp4"; do
    if [[ ! -f "$required_file" ]]; then
        echo "Missing fixture: ${required_file#$project_dir/}" >&2
        exit 1
    fi
done

exec > >(tee "$log_file") 2>&1

run_case() {
    local case_id="$1"
    local video_file="$2"
    local video_fps="$3"
    local prompt="$4"

    echo
    echo "===== $case_id ====="
    LLAMA_CACHE="$model_cache" "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --video "$video_file" \
        --video-fps "$video_fps" \
        --video-timestamp-interval 500 \
        -p "$prompt" \
        -ngl all \
        -fa on \
        -c 8192 \
        -n 192 \
        --no-warmup \
        --temp 0 \
        --reasoning off \
        --simple-io \
        --single-turn
    local status=$?
    echo "===== $case_id exit=$status ====="
}

run_bad_case() {
    local case_id="VIDEO-BAD-001"
    local video_file="$video_dir/25-not-a-video.mp4"

    echo
    echo "===== $case_id ====="
    LLAMA_CACHE="$model_cache" perl -e 'alarm shift; exec @ARGV' 30 \
        "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --video "$video_file" \
        -p "Report whether the video loaded." \
        -ngl all \
        -c 4096 \
        -n 1 \
        --no-warmup \
        --reasoning off \
        --simple-io \
        --single-turn
    local status=$?
    echo "===== $case_id exit=$status ====="
}

run_case "VIDEO-003-VERY-SHORT" \
    "$video_dir/22-video-a-very-short.mp4" \
    10 \
    "Identify the visible letter, color, shape, and code. State whether the video changes to another scene."

sequence_prompt="Return exactly three lines, one stage per line. Format each line as: start time, letter, color, shape, code. Preserve time order and do not add explanations."

run_case "VIDEO-004A-MOOV-HEAD-CONTROL" \
    "$video_dir/20-video-abc.mp4" \
    1 \
    "$sequence_prompt"

run_case "VIDEO-004B-MOOV-TAIL" \
    "$video_dir/23-video-abc-moov-tail.mp4" \
    1 \
    "$sequence_prompt"

run_case "VIDEO-005-VFR" \
    "$video_dir/24-video-vfr-abc.mp4" \
    1 \
    "Return exactly four lines: one line for each stage in time order, then one line naming the longest stage. Include approximate start and end times, letters, colors, shapes, and codes."

run_bad_case
