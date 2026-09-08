#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundled_python="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
rag_python="${RAG_PYTHON:-$bundled_python}"
api_base="${LLAMA_API_BASE:-http://127.0.0.1:8080}"

if [[ $# -lt 1 ]]; then
    echo 'Usage: scripts/ask_documents.sh "question" [file-or-directory ...]' >&2
    exit 2
fi

if [[ ! -x "$rag_python" ]]; then
    echo "Python runtime not found: $rag_python" >&2
    exit 1
fi

question="$1"
shift
sources=()

if [[ $# -gt 0 ]]; then
    for source in "$@"; do
        sources+=("$source")
    done
else
    sources+=("$project_dir/README.md" "$project_dir/docs")
    while IFS= read -r -d '' result_file; do
        sources+=("$result_file")
    done < <(find "$project_dir/results" -maxdepth 1 -type f -name '*.md' ! -name 'rag-*.md' -print0)
fi

source_args=()
for source in "${sources[@]}"; do
    source_args+=(--source "$source")
done

exec "$rag_python" "$project_dir/scripts/local_rag.py" \
    --question "$question" \
    "${source_args[@]}" \
    --api-base "$api_base" \
    --output "$project_dir/results/rag-last-answer.md" \
    --retrieval-output "$project_dir/results/rag-last-retrieval.json"
