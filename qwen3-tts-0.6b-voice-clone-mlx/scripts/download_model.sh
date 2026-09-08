#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$project_dir/.venv/bin/python"

if [[ ! -x "$python" ]]; then
    echo "Project environment is missing. Create .venv first." >&2
    exit 2
fi

exec "$python" "$project_dir/scripts/download_model.py"
