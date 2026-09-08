#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
whisper_dir="$project_dir/worktrees/whisper.cpp"
build_dir="$whisper_dir/build-release-metal-stream"
sdl_prefix="${SDL2_PREFIX:-$(brew --prefix sdl2-compat)}"
output="$project_dir/tools/bin/mic-silero-capture"

mkdir -p "$(dirname "$output")"

c++ -std=c++17 -O3 \
    "$project_dir/tools/mic_silero_capture.cpp" \
    "$build_dir/examples/libcommon-sdl.a" \
    -I"$whisper_dir/include" \
    -I"$whisper_dir/ggml/include" \
    -I"$whisper_dir/examples" \
    -I"$sdl_prefix/include/SDL2" \
    -L"$build_dir/bin" \
    -lwhisper \
    -lggml \
    -L"$sdl_prefix/lib" \
    -lSDL2 \
    -Wl,-rpath,"$build_dir/bin" \
    -o "$output"

echo "Built: $output"
