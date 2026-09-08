#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
test_image="${1:-$project_dir/tests/fixtures/images/11-ocr-clean.png}"

if [[ ! -x "$llama_cli" ]]; then
    echo "Missing llama-cli: worktrees/llama.cpp/build-release-metal/bin/llama-cli" >&2
    exit 1
fi

if [[ ! -f "$test_image" ]]; then
    echo "Missing test image: $test_image" >&2
    exit 1
fi

LLAMA_CACHE="$model_cache" "$llama_cli" \
    -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
    --image "$test_image" \
    -p "Read every line of text in this image exactly. Return only the transcription." \
    -ngl all \
    -fa on \
    -c 4096 \
    -n 96 \
    --no-warmup \
    --temp 0 \
    --reasoning off \
    --simple-io \
    --single-turn
