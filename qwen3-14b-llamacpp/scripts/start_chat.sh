#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_server="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-server"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
context_size="${1:-8192}"
reasoning_mode="${2:-off}"
kv_cache="${3:-q8_0}"
host="${LLAMA_HOST:-127.0.0.1}"
port="${LLAMA_PORT:-8080}"

case "$context_size" in
    4096|8192|16384) ;;
    *)
        echo "Usage: scripts/start_chat.sh [4096|8192|16384] [off|on|auto] [q8_0|q4_0|f16]" >&2
        exit 2
        ;;
esac

case "$reasoning_mode" in
    off|on|auto) ;;
    *)
        echo "Usage: scripts/start_chat.sh [4096|8192|16384] [off|on|auto] [q8_0|q4_0|f16]" >&2
        exit 2
        ;;
esac

case "$kv_cache" in
    q8_0|q4_0|f16) ;;
    *)
        echo "Usage: scripts/start_chat.sh [4096|8192|16384] [off|on|auto] [q8_0|q4_0|f16]" >&2
        exit 2
        ;;
esac

if [[ ! -x "$llama_server" ]]; then
    echo "llama-server not found: $llama_server" >&2
    exit 1
fi

echo "Starting Qwen3-14B chat"
echo "Context: $context_size tokens"
echo "Reasoning: $reasoning_mode"
echo "KV cache: $kv_cache"
echo "Open: http://$host:$port"
echo "Press Control-C here to stop the server."
echo

exec env LLAMA_CACHE="$model_cache" "$llama_server" \
    --offline \
    -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
    -hff Qwen3-14B-Q4_K_M.gguf \
    --no-mmproj \
    -ngl all \
    -fa on \
    -c "$context_size" \
    -ctk "$kv_cache" \
    -ctv "$kv_cache" \
    -np 1 \
    --jinja \
    --reasoning "$reasoning_mode" \
    --host "$host" \
    --port "$port"
