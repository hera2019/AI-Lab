#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$project_dir/scripts/apple_vision_receipt_ocr.swift"
receipt_image="${1:-$project_dir/tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg}"
rectified_image="$project_dir/tests/fixtures/receipts/27-real-japanese-receipt-rectified.png"
ocr_json="$project_dir/results/apple-vision-receipt-ocr.json"
log_file="$project_dir/results/apple-vision-receipt-ocr-latest.log"
build_dir="$(mktemp -d -t apple-vision-receipt.XXXXXX)"
binary="$build_dir/apple-vision-receipt-ocr"

cleanup() {
    rm -rf -- "$build_dir"
}
trap cleanup EXIT

if [[ ! -f "$receipt_image" ]]; then
    echo "Missing receipt image: $receipt_image" >&2
    exit 1
fi

xcrun swiftc \
    -O \
    -parse-as-library \
    -module-cache-path "$build_dir/module-cache" \
    "$source_file" \
    -o "$binary"

exec > >(tee "$log_file") 2>&1

echo "===== APPLE-VISION-RECEIPT-001 ====="
/usr/bin/time -lp "$binary" "$receipt_image" "$rectified_image" "$ocr_json"
