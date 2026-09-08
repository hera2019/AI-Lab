#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundled_python="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
image_python="${IMAGE_PYTHON:-$bundled_python}"

if [[ ! -x "$image_python" ]] || ! "$image_python" -c 'import PIL' >/dev/null 2>&1; then
    echo "A Python runtime with Pillow is required." >&2
    echo "Set IMAGE_PYTHON to a compatible local Python executable." >&2
    exit 1
fi

"$image_python" "$project_dir/scripts/generate_visual_reasoning_fixtures.py"
