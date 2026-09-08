#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_bench="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-bench"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
output_format="${1:-md}"
detail_log="$project_dir/results/benchmark-latest.log"

if [[ ! -x "$llama_bench" ]]; then
    echo "llama-bench not found: $llama_bench" >&2
    exit 1
fi

case "$output_format" in
    md|csv|json|jsonl|sql) ;;
    *)
        echo "Usage: scripts/run_benchmark.sh [md|csv|json|jsonl|sql]" >&2
        exit 2
        ;;
esac

if ! /usr/bin/time -l env LLAMA_CACHE="$model_cache" "$llama_bench" \
        --offline \
        -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
        -hff Qwen3-14B-Q4_K_M.gguf \
        -p 512 \
        -n 128 \
        -r 3 \
        -ngl -1 \
        -fa on \
        -o "$output_format" \
        2>"$detail_log"; then
    echo "Benchmark failed. Details: results/benchmark-latest.log" >&2
    exit 1
fi

echo >&2
echo "Detailed Metal and memory log: results/benchmark-latest.log" >&2
