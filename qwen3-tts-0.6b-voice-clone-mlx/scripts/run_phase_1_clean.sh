#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_dir/.venv/bin/python"
reference_audio="$project_dir/private/reference/clean-15s.wav"
model_dir="${QWEN3_TTS_MODEL_DIR:-$HOME/Documents/AI-Models/tts/qwen3-tts-0.6b-base-mlx}"

if [[ ! -f "$reference_audio" ]]; then
    echo "请先运行 scripts/record_reference.sh 录制正式参考音频。" >&2
    exit 2
fi

/usr/bin/time -l "$python" "$project_dir/scripts/clone_voice.py" \
    --model "$model_dir" \
    --reference-audio "$reference_audio" \
    --reference-text "今天阳光很好，我正在测试完全本地的声音克隆。数字是一二三四五，我们希望声音自然、清楚，而且稳定。现在测试结束。" \
    --text "今天的实验很有意思。这个句子没有出现在参考录音里，却使用了相似的声音来说话。" \
    --language chinese \
    --output "$project_dir/results/generated/phase-1-clean-zh-synthetic.wav" \
    --metadata "$project_dir/results/phase-1-clean.json" \
    --consent-confirmed 2>&1 | tee "$project_dir/results/phase-1-clean.log"
