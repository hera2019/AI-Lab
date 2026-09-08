#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
embedding_bin="${LLAMA_EMBEDDING:-$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-embedding}"
model="${EMBEDDING_MODEL:-$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b/Qwen3-Embedding-0.6B-Q8_0.gguf}"

if [[ ! -x "$embedding_bin" ]]; then
    echo "llama-embedding not found or not executable: $embedding_bin" >&2
    exit 2
fi
if [[ ! -f "$model" ]]; then
    echo "Embedding model not found: $model" >&2
    echo "Run scripts/download_model.sh first." >&2
    exit 2
fi

mkdir -p "$project_dir/results"

{
    echo "===== Phase 1A: body only ====="
    /usr/bin/time -l python3 "$project_dir/scripts/semantic_search.py" \
        --binary "$embedding_bin" \
        --model "$model" \
        --passages "$project_dir/data/sample-passages.jsonl" \
        --queries "$project_dir/data/sample-queries.jsonl" \
        --json-output "$project_dir/results/phase-1a-body-only.json" \
        --markdown-output "$project_dir/results/phase-1a-body-only.md"

    echo
    echo "===== Phase 1B: title + body ====="
    /usr/bin/time -l python3 "$project_dir/scripts/semantic_search.py" \
        --binary "$embedding_bin" \
        --model "$model" \
        --passages "$project_dir/data/sample-passages.jsonl" \
        --queries "$project_dir/data/sample-queries.jsonl" \
        --include-title \
        --json-output "$project_dir/results/phase-1b-title-body.json" \
        --markdown-output "$project_dir/results/phase-1b-title-body.md"
} 2>&1 | tee "$project_dir/results/phase-1-semantic-search.log"
