#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lab_dir="$(cd "$project_dir/.." && pwd)"
binary="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-embedding"
model="$HOME/Documents/AI-Models/embeddings/qwen3-embedding-0.6b/Qwen3-Embedding-0.6B-Q8_0.gguf"

for required in "$binary" "$model"; do
    if [[ ! -f "$required" ]]; then
        echo "Missing required file: $required" >&2
        exit 2
    fi
done

mkdir -p "$project_dir/index" "$project_dir/results"

echo "Phase 2A: building the persistent AI-Lab index"
/usr/bin/time -l python3 "$project_dir/scripts/build_ai_lab_index.py" \
    --source-root "$lab_dir" \
    --binary "$binary" \
    --model "$model" \
    --index-output "$project_dir/index/ai-lab-index.json" \
    --manifest-output "$project_dir/index/manifest.json" \
    --max-chars 1400 \
    --prompt-batch 12 \
    2>&1 | tee "$project_dir/results/phase-2-index-build.log"

echo
echo "Phase 2B: evaluating Chinese, Japanese and English searches"
/usr/bin/time -l python3 "$project_dir/scripts/evaluate_ai_lab_index.py" \
    --index "$project_dir/index/ai-lab-index.json" \
    --queries "$project_dir/data/phase-2-queries.jsonl" \
    --binary "$binary" \
    --model "$model" \
    --json-output "$project_dir/results/phase-2-evaluation.json" \
    --markdown-output "$project_dir/results/phase-2-evaluation.md" \
    2>&1 | tee "$project_dir/results/phase-2-evaluation.log"

echo
echo "Phase 2 complete."
echo "Search interactively: scripts/search_ai_lab.sh"
