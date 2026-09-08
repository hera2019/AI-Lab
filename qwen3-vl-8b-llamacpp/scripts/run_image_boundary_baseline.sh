#!/usr/bin/env bash

set -uo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
llama_cli="$project_dir/worktrees/llama.cpp/build-release-metal/bin/llama-cli"
model_cache="${LLAMA_CACHE:-$HOME/Documents/AI-Models/huggingface}"
fixture_dir="$project_dir/tests/fixtures/images"
log_file="$project_dir/results/image-boundary-latest.log"

if [[ ! -x "$llama_cli" ]]; then
    echo "Missing llama-cli: worktrees/llama.cpp/build-release-metal/bin/llama-cli" >&2
    exit 1
fi

exec > >(tee "$log_file") 2>&1

run_case() {
    local case_id="$1"
    local image_arg="$2"
    local prompt="$3"

    echo
    echo "===== $case_id ====="
    LLAMA_CACHE="$model_cache" "$llama_cli" \
        -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M \
        --image "$image_arg" \
        -p "$prompt" \
        -ngl all \
        -fa on \
        -c 4096 \
        -n 96 \
        --no-warmup \
        --temp 0 \
        --reasoning off \
        --simple-io \
        --single-turn
    local status=$?
    echo "===== $case_id exit=$status ====="
}

run_case "IMG-001" "$fixture_dir/01-one-pixel-red.png" \
    "报告图片尺寸和主色；如果无法处理，请明确报错。"
run_case "IMG-002" "$fixture_dir/02-one-pixel-transparent.png" \
    "报告图片是否可见以及主色；不确定时说明。"
run_case "IMG-003" "$fixture_dir/03-transparent-hidden-rgb.png" \
    "只抄录你实际看见的文字。"
run_case "IMG-004" "$fixture_dir/04-extreme-wide-4096x32.png" \
    "从左到右描述色带，并报告图片形状。"
run_case "IMG-005" "$fixture_dir/05-extreme-tall-32x4096.png" \
    "从上到下描述色带，并报告图片形状。"
run_case "IMG-006" "$fixture_dir/06-exif-orientation-6.jpg,$fixture_dir/06-exif-reference.png" \
    "图片1和图片2分别是什么方向？抄录文字、描述箭头方向，并判断两张视觉方向是否一致。"
run_case "IMG-007" "$fixture_dir/07-unicode-猫-東京-🧪.png" \
    "抄录图片中的英文、中文和编号。"
run_case "IMG-008" "$fixture_dir/08-png-bytes-with-jpg-extension.jpg" \
    "抄录图片中的两行文字。"
run_case "IMG-009" "$fixture_dir/09-grayscale-16bit.png" \
    "描述灰度从哪一侧向哪一侧变化。"
run_case "IMG-010" "$fixture_dir/10-cmyk.jpg" \
    "抄录标题并描述背景色。"
