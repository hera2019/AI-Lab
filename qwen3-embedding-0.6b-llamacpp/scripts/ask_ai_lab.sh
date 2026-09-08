#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
embedding_binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-embedding"
generator_binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
embedding_model="$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b/Qwen3-Embedding-0.6B-Q8_0.gguf"
generator_model="$HOME/Documents/AI-Models/generators/qwen3-4b-instruct-2507/qwen3-4b-instruct-2507-q8_0.gguf"

exec python3 "$project_dir/scripts/rag_ai_lab.py" \
    --index "$project_dir/index/ai-lab-index.json" \
    --embedding-binary "$embedding_binary" \
    --embedding-model "$embedding_model" \
    --generator-binary "$generator_binary" \
    --generator-model "$generator_model" \
    --json-output "$project_dir/results/rag-last-answer.json" \
    --markdown-output "$project_dir/results/rag-last-answer.md" \
    "$@"

