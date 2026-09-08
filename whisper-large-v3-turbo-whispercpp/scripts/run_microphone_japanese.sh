#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stream_bin="${WHISPER_STREAM:-$project_dir/worktrees/whisper.cpp/build-release-metal-stream/bin/whisper-stream}"
model="${WHISPER_MODEL:-$HOME/Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin}"

if [[ ! -x "$stream_bin" ]]; then
    echo "whisper-stream not found or not executable: $stream_bin" >&2
    exit 2
fi

if [[ ! -f "$model" ]]; then
    echo "Whisper model not found: $model" >&2
    exit 2
fi

echo "Mac may ask for microphone permission on the first run."
echo "Speak Japanese; press Ctrl-C to stop."

exec "$stream_bin" \
    --model "$model" \
    --language "${LANGUAGE:-ja}" \
    --threads "${THREADS:-8}" \
    --step "${STEP_MS:-500}" \
    --length "${LENGTH_MS:-5000}" \
    --keep "${KEEP_MS:-200}" \
    --no-fallback
