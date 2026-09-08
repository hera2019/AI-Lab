#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
receipt_image="${1:-$project_dir/tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg}"
log_file="$project_dir/results/japanese-receipt-ocr-latest.log"

if [[ ! -x "$llama_cli" ]]; then
    echo "Missing llama-cli: worktrees/llama.cpp/build-release-metal/bin/llama-cli" >&2
    exit 1
fi

if [[ ! -f "$receipt_image" ]]; then
    echo "Missing receipt image: $receipt_image" >&2
    exit 1
fi

exec > >(tee "$log_file") 2>&1

echo "===== OCR-JP-RECEIPT-001 ====="
/usr/bin/time -lp env LLAMA_CACHE="$model_cache" "$llama_cli" \
    -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
    --image "$receipt_image" \
    -p "Transcribe every legible character printed on the paper receipt, from top to bottom. Preserve line order, Japanese text, numbers, punctuation, and prices. Do not correct, translate, summarize, or guess obscured text. Do not include the camera timestamp outside the receipt. Return only the transcription." \
    -ngl all \
    -fa on \
    -c 4096 \
    -n 384 \
    --no-warmup \
    --temp 0 \
    --reasoning off \
    --simple-io \
    --single-turn
