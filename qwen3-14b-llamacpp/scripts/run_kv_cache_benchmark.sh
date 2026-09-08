#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_bench="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-bench"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
context_size="${CONTEXT_SIZE:-16384}"
generation_tokens="${GEN_TOKENS:-128}"
repetitions="${REPETITIONS:-1}"
summary_file="$project_dir/results/phase-6-kv-cache.md"
csv_file="$project_dir/results/kv-cache-benchmark.csv"
temp_dir="$(mktemp -d)"
cache_pairs=("q4_0:q4_0" "q8_0:q8_0" "f16:f16")

trap 'rm -rf "$temp_dir"' EXIT

if [[ ! -x "$llama_bench" ]]; then
    echo "llama-bench not found: $llama_bench" >&2
    exit 1
fi

for value in "$context_size" "$generation_tokens" "$repetitions"; do
    if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
        echo "Context, generation tokens, and repetitions must be positive integers." >&2
        exit 2
    fi
done

captured_at="$(date '+%Y-%m-%d %H:%M:%S %Z')"
swap_before="$(sysctl -n vm.swapusage 2>/dev/null || echo 'unavailable')"
memory_before="$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/{print $2}' || true)"

{
    echo "# Phase 6：KV cache 精度对比"
    echo
    echo "开始时间：$captured_at"
    echo
    echo "- 提示词长度：$context_size tokens"
    echo "- 继续生成：$generation_tokens tokens"
    echo "- 每档重复：$repetitions 次"
    echo "- 测试顺序：Q4_0 -> Q8_0 -> F16"
    echo "- 模型权重：Qwen3-14B Q4_K_M（所有测试相同）"
    echo "- 测试前全局 swap：$swap_before"
    echo "- 测试前系统可用内存压力余量：${memory_before:-unavailable}"
    echo
} >"$summary_file"

: >"$csv_file"
csv_header_written=0

for pair in "${cache_pairs[@]}"; do
    type_k="${pair%%:*}"
    type_v="${pair##*:}"
    label="${type_k}-${type_v}"
    detail_log="$project_dir/results/kv-${label}-latest.log"
    table_file="$temp_dir/${label}.md"
    extracted_csv="$temp_dir/${label}.csv"

    echo
    echo "Testing KV cache K=$type_k, V=$type_v at ${context_size} tokens..."

    if ! /usr/bin/time -l env LLAMA_CACHE="$model_cache" "$llama_bench" \
            --offline \
            -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
            -hff Qwen3-14B-Q4_K_M.gguf \
            -p 0 \
            -n 0 \
            -pg "$context_size,$generation_tokens" \
            -r "$repetitions" \
            -ctk "$type_k" \
            -ctv "$type_v" \
            -ngl -1 \
            -fa on \
            -o md \
            -oe csv \
            >"$table_file" \
            2>"$detail_log"; then
        echo "KV cache test failed. Details: results/kv-${label}-latest.log" >&2
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
    elapsed="$(awk '/ real /{value=$1} END{print value}' "$detail_log")"
    swap_after_test="$(sysctl -n vm.swapusage 2>/dev/null || echo 'unavailable')"
    memory_after_test="$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/{print $2}' || true)"

    {
        echo "## K=$type_k / V=$type_v"
        echo
        cat "$table_file"
        echo
        echo "- 进程最大常驻内存：${max_rss:-unavailable} bytes"
        echo "- 完整进程耗时：${elapsed:-unavailable} seconds"
        echo "- 完成后全局 swap：$swap_after_test"
        echo "- 完成后系统可用内存压力余量：${memory_after_test:-unavailable}"
        echo "- 详细日志：\`results/kv-${label}-latest.log\`"
        echo
    } >>"$summary_file"
done

{
    echo "## 测试边界"
    echo
    echo "该 benchmark 只比较速度和内存，不评估回答质量。KV cache 量化程度越高，潜在质量损失风险越大，是否适合日常使用还需要单独做同题 A/B 测试。"
    echo
    echo "原始数据：\`results/kv-cache-benchmark.csv\`"
} >>"$summary_file"

echo
echo "KV cache comparison complete."
echo "Summary: results/phase-6-kv-cache.md"
echo "Raw data: results/kv-cache-benchmark.csv"
