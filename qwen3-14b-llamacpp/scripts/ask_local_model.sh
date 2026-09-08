#!/usr/bin/env bash

set -euo pipefail

api_base="${LLAMA_API_BASE:-http://127.0.0.1:8080}"
prompt="${*:-请用一句中文解释什么是本地大模型 API。}"

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required." >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required." >&2
    exit 1
fi

if ! curl --fail --silent --max-time 2 "$api_base/health" >/dev/null; then
    echo "The local model server is not running." >&2
    echo "Start it first with: scripts/start_chat.sh" >&2
    exit 1
fi

request_json="$(jq -n \
    --arg model "Qwen3-14B-Q4_K_M.gguf" \
    --arg system "你是一个运行在 Mac Studio 上的本地中文助手。回答准确、简洁；不确定时明确说明。" \
    --arg prompt "$prompt" \
    '{
        model: $model,
        messages: [
            {role: "system", content: $system},
            {role: "user", content: $prompt}
        ],
        temperature: 0.7,
        top_p: 0.8,
        max_tokens: 256,
        stream: false
    }')"

response_json="$(curl \
    --fail-with-body \
    --silent \
    --show-error \
    --max-time 120 \
    -H 'Content-Type: application/json' \
    -d "$request_json" \
    "$api_base/v1/chat/completions")"

if jq -e '.error' >/dev/null 2>&1 <<<"$response_json"; then
    jq -r '.error.message // .error' <<<"$response_json" >&2
    exit 1
fi

answer="$(jq -r '.choices[0].message.content // empty' <<<"$response_json")"

if [[ -z "$answer" ]]; then
    echo "The server returned no answer." >&2
    exit 1
fi

printf '%s\n' "$answer"
