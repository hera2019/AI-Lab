#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec "$project_dir/.venv/bin/python" "$project_dir/scripts/record_reference.py" \
    --output "$project_dir/private/reference/clean-15s.wav" \
    --metadata "$project_dir/private/reference/clean-15s.json" \
    --seconds 15 \
    --consent-confirmed
