#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_dir/.venv/bin/python"
reference_audio="$project_dir/private/reference/iphone-60s-natural.wav"
transcript="$project_dir/private/reference/iphone-60s-natural.txt"
model_dir="${QWEN3_TTS_MODEL_DIR:-$HOME/Documents/AI-Models/tts/qwen3-tts-0.6b-base-mlx}"
output="$project_dir/results/generated/phase-1-iphone-repeat-synthetic.wav"
metadata="$project_dir/results/phase-1-iphone-repeat.json"

for required in "$python" "$reference_audio" "$transcript" "$model_dir/model.safetensors"; do
    if [[ ! -e "$required" ]]; then
        echo "Missing required file: $required" >&2
        exit 2
    fi
done

mkdir -p "$project_dir/results/generated"

/usr/bin/time -l "$python" "$project_dir/scripts/clone_voice.py" \
    --model "$model_dir" \
    --reference-audio "$reference_audio" \
    --reference-text-file "$transcript" \
    --text-file "$transcript" \
    --language chinese \
    --output "$output" \
    --metadata "$metadata" \
    --consent-confirmed 2>&1 | tee "$project_dir/results/phase-1-iphone-repeat.log"
