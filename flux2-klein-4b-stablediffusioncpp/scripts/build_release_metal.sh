#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${SD_CPP_SOURCE:-$project_dir/worktrees/stable-diffusion.cpp}"
build_dir="${SD_CPP_BUILD:-$source_dir/build-release-metal}"

if [[ ! -f "$source_dir/CMakeLists.txt" ]]; then
    echo "stable-diffusion.cpp source not found: $source_dir" >&2
    exit 2
fi

cmake -S "$source_dir" -B "$build_dir" \
    -DCMAKE_BUILD_TYPE=Release \
    -DSD_METAL=ON \
    -DGGML_CCACHE=OFF \
    -DSD_SERVER_BUILD_FRONTEND=OFF

cmake --build "$build_dir" --target sd-cli sd-server -j "$(sysctl -n hw.physicalcpu)"

echo "Build complete:"
echo "  $build_dir/bin/sd-cli"
echo "  $build_dir/bin/sd-server"
echo
echo "Available compute devices:"
"$build_dir/bin/sd-cli" --list-devices
