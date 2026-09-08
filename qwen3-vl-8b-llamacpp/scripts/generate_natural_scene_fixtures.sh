#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"

exec "$python_bin" "$project_dir/scripts/generate_natural_scene_fixtures.py"
