#!/usr/bin/env python3
"""Verify generated boundary fixtures without invoking a vision model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_DIR / "tests" / "fixtures" / "manifest.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        fail("Unsupported manifest schema.")
    if manifest.get("case_count") != 17:
        fail(f"Expected 17 cases, found {manifest.get('case_count')}.")

    for relative, expected in manifest["files"].items():
        path = PROJECT_DIR / relative
        if not path.is_file():
            fail(f"Missing fixture: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected["sha256"]:
            fail(f"SHA-256 mismatch: {relative}")
        decodable = True
        try:
            with Image.open(path) as image:
                image.load()
        except Exception:
            decodable = False
        if decodable != expected["expected_decodable"]:
            fail(
                f"Unexpected Pillow decode result for {relative}: "
                f"expected {expected['expected_decodable']}, got {decodable}"
            )

    one_pixel = Image.open(PROJECT_DIR / "tests/fixtures/images/01-one-pixel-red.png")
    if one_pixel.size != (1, 1) or one_pixel.getpixel((0, 0)) != (255, 0, 0):
        fail("The 1x1 red fixture is incorrect.")

    alpha = Image.open(PROJECT_DIR / "tests/fixtures/images/03-transparent-hidden-rgb.png")
    if alpha.mode != "RGBA" or alpha.getchannel("A").getextrema() != (0, 255):
        fail("The alpha fixture does not contain both transparent and opaque pixels.")

    exif_path = PROJECT_DIR / "tests/fixtures/images/06-exif-orientation-6.jpg"
    with Image.open(exif_path) as exif_image:
        if exif_image.getexif().get(274) != 6 or exif_image.size != (640, 360):
            fail("The EXIF orientation fixture is incorrect.")
    with Image.open(PROJECT_DIR / "tests/fixtures/images/06-exif-reference.png") as reference:
        if reference.size != (360, 640):
            fail("The EXIF reference dimensions are incorrect.")

    mismatch_path = PROJECT_DIR / "tests/fixtures/images/08-png-bytes-with-jpg-extension.jpg"
    with Image.open(mismatch_path) as mismatch:
        if mismatch.format != "PNG":
            fail("The extension mismatch fixture does not contain PNG bytes.")

    unicode_path = PROJECT_DIR / "tests/fixtures/images/07-unicode-猫-東京-🧪.png"
    if not unicode_path.is_file():
        fail("The Unicode filename fixture is missing.")

    print(f"PASS: {manifest['case_count']} boundary cases")
    print(f"PASS: {len(manifest['files'])} fixture files and SHA-256 values")
    print("PASS: dimensions, alpha, EXIF, extension mismatch, Unicode path")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
