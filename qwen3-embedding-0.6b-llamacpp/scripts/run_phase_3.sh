#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
embedding_binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-embedding"
generator_binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
embedding_model="$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b/Qwen3-Embedding-0.6B-Q8_0.gguf"
generator_model="$HOME/Documents/AI-Models/generators/qwen3-4b-instruct-2507/qwen3-4b-instruct-2507-q8_0.gguf"

for required in "$embedding_binary" "$generator_binary" "$embedding_model" "$generator_model"; do
    if [[ ! -f "$required" ]]; then
        echo "Missing required file: $required" >&2
        exit 2
    fi
done

/usr/bin/time -l python3 "$project_dir/scripts/evaluate_rag.py" \
    --index "$project_dir/index/ai-lab-index.json" \
    --queries "$project_dir/data/phase-3-queries.jsonl" \
    --embedding-binary "$embedding_binary" \
    --embedding-model "$embedding_model" \
    --generator-binary "$generator_binary" \
    --generator-model "$generator_model" \
    --json-output "$project_dir/results/phase-3-rag-evaluation.json" \
    --markdown-output "$project_dir/results/phase-3-rag-evaluation.md" \
    2>&1 | tee "$project_dir/results/phase-3-rag-evaluation.log"
