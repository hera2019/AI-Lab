#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
fixture="$project_dir/tests/phase-6b-long-context.txt"
summary="$project_dir/results/phase-6b-kv-quality.md"
scores="$project_dir/results/kv-quality-scores.csv"
temp_dir="$(mktemp -d)"
cache_pairs=("q4_0:q4_0" "q8_0:q8_0" "f16:f16")

trap 'rm -rf "$temp_dir"' EXIT

if [[ ! -x "$llama_cli" ]]; then
    echo "llama-cli not found: $llama_cli" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required." >&2
    exit 1
fi

python3 "$project_dir/scripts/generate_kv_quality_fixture.py" "$fixture"

{
    echo "# Phase 6B：KV cache 长上下文质量 A/B"
    echo
    echo "- 文档：110 条虚构巡检记录"
    echo "- 上下文：16K"
    echo "- 测试：5 个跨位置事实、1 个跨段加法、1 个未提及陷阱"
    echo "- 模型权重：Qwen3-14B Q4_K_M"
    echo "- 生成：greedy，seed 42，reasoning off，固定 JSON 字段"
    echo "- 测试顺序：Q4_0 -> Q8_0 -> F16"
    echo
} >"$summary"

echo "cache_type,score,max_score,max_rss_bytes,elapsed_seconds" >"$scores"

for pair in "${cache_pairs[@]}"; do
    type_k="${pair%%:*}"
    type_v="${pair##*:}"
    label="${type_k}-${type_v}"
    transcript="$temp_dir/${label}-transcript.txt"
    answer_tmp="$project_dir/results/kv-quality-${label}-raw.txt"
    answer_file="$project_dir/results/kv-quality-${label}.json"
    log_file="$project_dir/results/kv-quality-${label}-latest.log"

    echo
    echo "Testing quality with K=$type_k, V=$type_v..."

    if [[ -s "$answer_file" && -s "$log_file" ]] \
            && jq -e . "$answer_file" >/dev/null 2>&1 \
            && ! grep -Eq 'Error:|Failed to' "$log_file"; then
        echo "Reusing completed answer: results/kv-quality-${label}.json"
    elif ! /usr/bin/time -l env LLAMA_CACHE="$model_cache" "$llama_cli" \
            --offline \
            -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
            -hff Qwen3-14B-Q4_K_M.gguf \
            --no-mmproj \
            -ngl all \
            -fa on \
            -c 16384 \
            -ctk "$type_k" \
            -ctv "$type_v" \
            -n 256 \
            -s 42 \
            --temp 0 \
            -st \
            --simple-io \
            --log-disable \
            --no-warmup \
            --no-display-prompt \
            --reasoning off \
            -f "$fixture" \
            -o "$transcript" \
            >"$log_file" \
            2>&1; then
        echo "Quality test failed. Details: results/kv-quality-${label}-latest.log" >&2
        tail -n 30 "$log_file" >&2
        exit 1
    else
        if grep -Eq 'Error:|Failed to' "$log_file"; then
            echo "llama-cli reported an internal error. Details: results/kv-quality-${label}-latest.log" >&2
            tail -n 30 "$log_file" >&2
            exit 1
        fi

        awk 'capture { print } /^Assistant:$/ { capture=1 }' "$transcript" \
            | iconv -f UTF-8 -t UTF-8 -c \
            | sed '/^```json$/d; /^```$/d' \
            >"$answer_tmp"

        if ! jq -e . "$answer_tmp" >/dev/null 2>&1; then
            echo "Model output was not valid JSON: results/kv-quality-${label}-raw.txt" >&2
            printf '%s,0,7,,\n' "$label" >>"$scores"
            {
                echo "## K=${type_k} / V=${type_v}：0 / 7（JSON 格式失败）"
                echo
                echo '```text'
                cat "$answer_tmp"
                echo '```'
                echo
            } >>"$summary"
            continue
        fi

        jq . "$answer_tmp" >"$answer_file"
    fi

    score="$(jq '[
        .project_code == "苍鹭",
        .approver == "林澈",
        .temperature_limit_c == 37,
        .cargo_password == "松针-4821",
        .checksum == "K9-M2-731",
        .battery_total == 52,
        .roof_color == "未提及"
    ] | map(select(.)) | length' "$answer_file")"

    max_rss="$(awk '/maximum resident set size/{value=$1} END{print value}' "$log_file")"
    elapsed="$(awk '/ real /{value=$1} END{print value}' "$log_file")"

    printf '%s,%s,7,%s,%s\n' "$label" "$score" "${max_rss:-}" "${elapsed:-}" >>"$scores"

    {
        echo "## K=${type_k} / V=${type_v}：$score / 7"
        echo
        echo '```json'
        cat "$answer_file"
        echo '```'
        echo
        echo "- 峰值常驻内存：${max_rss:-unavailable} bytes"
        echo "- 完整进程耗时：${elapsed:-unavailable} seconds"
        echo
    } >>"$summary"

    echo "Score: $score / 7"
    cat "$answer_file"
done

{
    echo "## 答案标准"
    echo
    echo "- 项目代号：苍鹭"
    echo "- 批准人：林澈"
    echo "- 温度上限：37"
    echo "- 货舱口令：松针-4821"
    echo "- 校验码：K9-M2-731"
    echo "- 电池总数：52"
    echo "- 屋顶颜色：未提及"
} >>"$summary"

echo
echo "Quality A/B complete."
echo "Summary: results/phase-6b-kv-quality.md"
echo "Scores: results/kv-quality-scores.csv"
