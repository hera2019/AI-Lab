#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_bench="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-bench"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
contexts="${CONTEXTS:-4096 8192 16384}"
generation_tokens="${GEN_TOKENS:-128}"
repetitions="${REPETITIONS:-1}"
summary_file="$project_dir/results/phase-3-context-benchmark.md"
csv_file="$project_dir/results/context-benchmark.csv"
temp_dir="$(mktemp -d)"

trap 'rm -rf "$temp_dir"' EXIT

if [[ ! -x "$llama_bench" ]]; then
    echo "llama-bench not found: $llama_bench" >&2
    exit 1
fi

for value in $contexts "$generation_tokens" "$repetitions"; do
    if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
        echo "Contexts, generation tokens, and repetitions must be positive integers." >&2
        exit 2
    fi
done

captured_at="$(date '+%Y-%m-%d %H:%M:%S %Z')"
swap_before="$(sysctl -n vm.swapusage 2>/dev/null || echo 'unavailable')"
memory_before="$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/{print $2}' || true)"

{
    echo "# Phase 3：长上下文安全扫描"
    echo
    echo "开始时间：$captured_at"
    echo
    echo "- 提示词长度：$contexts tokens"
    echo "- 每档继续生成：$generation_tokens tokens"
    echo "- 每档重复：$repetitions 次"
    echo "- Metal：全部模型层，Flash Attention 开启"
    echo "- 测试前全局 swap：$swap_before"
    echo "- 测试前系统可用内存压力余量：${memory_before:-unavailable}"
    echo
} >"$summary_file"

: >"$csv_file"
csv_header_written=0

for context in $contexts; do
    detail_log="$project_dir/results/context-${context}-latest.log"
    table_file="$temp_dir/context-${context}.md"
    extracted_csv="$temp_dir/context-${context}.csv"

    echo
    echo "Testing ${context}-token prompt + ${generation_tokens}-token generation..."

    if ! /usr/bin/time -l env LLAMA_CACHE="$model_cache" "$llama_bench" \
            --offline \
            -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
            -hff Qwen3-14B-Q4_K_M.gguf \
            -p 0 \
            -n 0 \
            -pg "$context,$generation_tokens" \
            -r "$repetitions" \
            -ngl -1 \
            -fa on \
            -o md \
            -oe csv \
            >"$table_file" \
            2>"$detail_log"; then
        echo "Context test failed. Details: results/context-${context}-latest.log" >&2
        tail -n 30 "$detail_log" >&2
        exit 1
    fi

    cat "$table_file"

    awk '/^build_commit,build_number,/{print; next} /^"/{print}' "$detail_log" >"$extracted_csv"
    if [[ "$csv_header_written" -eq 0 ]]; then
        cat "$extracted_csv" >>"$csv_file"
        csv_header_written=1
    else
        awk '!/^build_commit,build_number,/' "$extracted_csv" >>"$csv_file"
    fi

    max_rss="$(awk '/maximum resident set size/{value=$1} END{print value}' "$detail_log")"
    swap_after_context="$(sysctl -n vm.swapusage 2>/dev/null || echo 'unavailable')"

    {
        echo "## ${context}-token prompt + ${generation_tokens}-token generation"
        echo
        cat "$table_file"
        echo
        echo "- 进程最大常驻内存：${max_rss:-unavailable} bytes"
        echo "- 完成后全局 swap：$swap_after_context"
        echo "- 详细日志：\`results/context-${context}-latest.log\`"
        echo
    } >>"$summary_file"
done

swap_after="$(sysctl -n vm.swapusage 2>/dev/null || echo 'unavailable')"
memory_after="$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/{print $2}' || true)"

{
    echo "## 测试结束"
    echo
    echo "- 测试后全局 swap：$swap_after"
    echo "- 测试后系统可用内存压力余量：${memory_after:-unavailable}"
    echo "- 原始数据：\`results/context-benchmark.csv\`"
} >>"$summary_file"

echo
echo "Context scan complete."
echo "Summary: results/phase-3-context-benchmark.md"
echo "Raw data: results/context-benchmark.csv"
