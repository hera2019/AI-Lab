#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_dir/.venv/bin/python"
reference_audio="$project_dir/private/reference/archive-zh-8.8s.wav"
model_dir="${QWEN3_TTS_MODEL_DIR:-$HOME/Documents/AI-Models/tts/qwen3-tts-0.6b-base-mlx}"
output="$project_dir/results/generated/phase-1-archive-8s-zh-synthetic.wav"
metadata="$project_dir/results/phase-1-archive-8s.json"

for required in "$python" "$reference_audio" "$model_dir/model.safetensors"; do
    if [[ ! -e "$required" ]]; then
        echo "Missing required file: $required" >&2
        exit 2
    fi
done

mkdir -p "$project_dir/results/generated"

/usr/bin/time -l "$python" "$project_dir/scripts/clone_voice.py" \
    --model "$model_dir" \
    --reference-audio "$reference_audio" \
    --reference-text "今天是二零二六年九月三日，会议在下午三点十五分开始，订单号是 A 七三一。" \
    --text "你好，这是一次完全在本地完成的声音克隆实验。这句话从来没有在参考录音里出现过。" \
    --language chinese \
    --output "$output" \
    --metadata "$metadata" \
    --consent-confirmed 2>&1 | tee "$project_dir/results/phase-1-archive-8s.log"
