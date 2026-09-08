#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_server="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-server"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
receipt_image="$project_dir/tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg"
ocr_json="$project_dir/results/apple-vision-receipt-ocr.json"
server_log="$project_dir/results/hybrid-receipt-server.log"
summary_log="$project_dir/results/hybrid-receipt-api-latest.log"
port="${HYBRID_RECEIPT_PORT:-8091}"
base_url="http://127.0.0.1:$port"
tmp_dir="$(mktemp -d -t hybrid-receipt-server.XXXXXX)"
request_file="$tmp_dir/request.json"
server_pid=""

cleanup() {
    if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
    rm -rf -- "$tmp_dir"
}
trap cleanup EXIT

if [[ ! -x "$llama_server" ]]; then
    echo "Missing llama-server: worktrees/llama.cpp/build-release-metal/bin/llama-server" >&2
    exit 1
fi

if [[ ! -f "$ocr_json" ]]; then
    echo "Missing OCR JSON; run scripts/run_apple_vision_receipt_ocr.sh first" >&2
    exit 1
fi

if curl --silent --fail "$base_url/health" >/dev/null 2>&1; then
    echo "Port $port already has a healthy HTTP service; choose HYBRID_RECEIPT_PORT" >&2
    exit 1
fi

python3 "$project_dir/scripts/build_hybrid_receipt_request.py" \
    --image "$receipt_image" \
    --ocr "$ocr_json" \
    --output "$request_file"

start_seconds="$SECONDS"
LLAMA_CACHE="$model_cache" "$llama_server" \
    -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
    --alias qwen3-vl-8b \
    --host 127.0.0.1 \
    --port "$port" \
    -ngl all \
    -fa on \
    -c 8192 \
    -np 1 \
    --no-warmup \
    --reasoning off \
    --metrics \
    >"$server_log" 2>&1 &
server_pid=$!

ready=0
for _ in {1..120}; do
    if curl --silent --fail "$base_url/health" >/dev/null 2>&1; then
        ready=1
        break
    fi
    if ! kill -0 "$server_pid" 2>/dev/null; then
        echo "llama-server exited before becoming ready" >&2
        tail -80 "$server_log" >&2
        exit 1
    fi
    sleep 0.25
done

if [[ "$ready" -ne 1 ]]; then
    echo "llama-server did not become ready within 30 seconds" >&2
    exit 1
fi

exec > >(tee "$summary_log") 2>&1
echo "server_ready_seconds=$((SECONDS - start_seconds))"

response_files=()
for run_number in 1 2 3; do
    response_file="$project_dir/results/hybrid-receipt-response-$run_number.json"
    response_files+=("$response_file")
    echo
    echo "===== API-RUN-$run_number ====="
    curl --silent --show-error \
        --output "$response_file" \
        --write-out "http_code=%{http_code} time_total=%{time_total} seconds\n" \
        --header "Content-Type: application/json" \
        --data-binary "@$request_file" \
        "$base_url/v1/chat/completions"
done

echo
python3 "$project_dir/scripts/validate_hybrid_receipt_responses.py" "${response_files[@]}"
