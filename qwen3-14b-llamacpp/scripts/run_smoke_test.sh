#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"

if [[ ! -x "$llama_cli" ]]; then
    echo "llama-cli not found: $llama_cli" >&2
    exit 1
fi

env LLAMA_CACHE="$model_cache" "$llama_cli" \
    --offline \
    -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
    -hff Qwen3-14B-Q4_K_M.gguf \
    --no-mmproj \
    -ngl all \
    -fa on \
    -c 4096 \
    -n 128 \
    -st \
    --no-display-prompt \
    --reasoning off \
    --temp 0.7 \
    --top-k 20 \
    --top-p 0.8 \
    --min-p 0 \
    -p '你好。请用三句话解释什么是大型语言模型，每句话不超过30个汉字。'
