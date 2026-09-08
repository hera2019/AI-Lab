#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
bundled_python="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
pdf_python="${PDF_PYTHON:-$bundled_python}"
request="${1:-制作一份《第一次在 Mac 上运行本地大模型》的体验报告，介绍硬件、模型、速度、8K 上下文结论和个人感受，两页以内。}"
output_stem="${2:-offline-pdf-demo}"

if [[ ! "$output_stem" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Output name may contain only letters, numbers, dots, dashes, and underscores." >&2
    exit 2
fi

if [[ ! -x "$llama_cli" ]]; then
    echo "llama-cli not found: $llama_cli" >&2
    exit 1
fi

if [[ ! -x "$pdf_python" ]] || ! "$pdf_python" -c 'import reportlab' >/dev/null 2>&1; then
    echo "A Python runtime with reportlab is required." >&2
    echo "Set PDF_PYTHON to a compatible local Python executable." >&2
    exit 1
fi

markdown_file="$project_dir/results/${output_stem}.md"
pdf_file="$project_dir/results/${output_stem}.pdf"
model_log="$project_dir/results/pdf-generation-latest.log"
temp_dir="$(mktemp -d)"
transcript_file="$temp_dir/transcript.txt"

trap 'rm -rf "$temp_dir"' EXIT

model_prompt="你是一名中文技术编辑。请根据用户要求撰写一份适合直接排版成 PDF 的 Markdown 文档。必须有一个一级标题、简短导语、清晰的二级标题和项目符号；内容具体、准确、简洁。不要使用 Markdown 表格，不要输出代码围栏，不要解释你正在做什么，只输出文档正文。只能使用以下实验事实，不得编造或替换硬件、模型和数据：设备是 Mac Studio，Apple M2 Max，32 GB Unified Memory；模型是 Qwen3-14B Q4_K_M，GGUF 文件约 8.38 GiB；运行框架是 llama.cpp，使用 Metal + Apple Accelerate；基准生成速度约 30.82 tokens/s；8K 长上下文峰值常驻内存约 9.81 GiB且未观察到新增全局 swap；16K 可以运行，但引发约 494 MiB 新增全局 swap，因此日常推荐 8K。用户要求：${request}"

echo "1/2 Qwen3-14B is writing the document..."

env LLAMA_CACHE="$model_cache" "$llama_cli" \
    --offline \
    -hf Qwen/Qwen3-14B-GGUF:Q4_K_M \
    -hff Qwen3-14B-Q4_K_M.gguf \
    --no-mmproj \
    -ngl all \
    -fa on \
    -c 4096 \
    -n 900 \
    -st \
    --simple-io \
    --log-disable \
    --no-warmup \
    --no-display-prompt \
    --reasoning off \
    --temp 0.4 \
    --top-k 20 \
    --top-p 0.8 \
    --min-p 0 \
    -p "$model_prompt" \
    -o "$transcript_file" \
    >"$model_log" \
    2>&1

awk 'capture { print } /^Assistant:$/ { capture=1 }' "$transcript_file" \
    | iconv -f UTF-8 -t UTF-8 -c \
    >"$markdown_file"

if ! grep -q '^# ' "$markdown_file"; then
    echo "The model did not produce the expected Markdown document." >&2
    exit 1
fi

echo "2/2 The local PDF tool is laying out the pages..."

"$pdf_python" "$project_dir/scripts/markdown_to_pdf.py" \
    "$markdown_file" \
    "$pdf_file"

echo
echo "PDF created: results/${output_stem}.pdf"
echo "Source text: results/${output_stem}.md"
echo "Model log: results/pdf-generation-latest.log"
