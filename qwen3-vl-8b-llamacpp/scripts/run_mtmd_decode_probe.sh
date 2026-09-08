#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
worktree_dir="$project_dir/worktrees/llama.cpp"
build_bin="$worktree_dir/build-release-metal/bin"
source_file="$project_dir/tests/probes/mtmd_decode_probe.cpp"
probe_dir="$project_dir/.cache/mtmd-decode-probe"
probe_bin="$probe_dir/mtmd_decode_probe"

mkdir -p "$probe_dir"

xcrun clang++ \
    -std=c++17 \
    -I "$worktree_dir/include" \
    -I "$worktree_dir/ggml/include" \
    -I "$worktree_dir/tools/mtmd" \
    -L "$build_bin" \
    -Wl,-rpath,"$build_bin" \
    "$source_file" \
    -lmtmd \
    -o "$probe_bin"

echo "===== fully transparent green 1x1 PNG ====="
"$probe_bin" "$project_dir/tests/fixtures/images/02-one-pixel-transparent.png"

echo
echo "===== PNG containing alpha=0 red text ====="
"$probe_bin" "$project_dir/tests/fixtures/images/03-transparent-hidden-rgb.png"
