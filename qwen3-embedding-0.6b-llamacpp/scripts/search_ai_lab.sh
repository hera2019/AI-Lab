#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-embedding"
model="$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b/Qwen3-Embedding-0.6B-Q8_0.gguf"

exec python3 "$project_dir/scripts/search_ai_lab.py" \
    --index "$project_dir/index/ai-lab-index.json" \
    --binary "$binary" \
    --model "$model" \
    "$@"

