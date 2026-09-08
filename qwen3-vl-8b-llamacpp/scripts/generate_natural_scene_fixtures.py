#!/usr/bin/env python3
"""Create deterministic Phase 12 derivatives from two public sample photos."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_DIR / "tests/fixtures/natural"

SOURCES = {
    "source-bus.jpg": {
        "sha256": "c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63",
        "url": "https://raw.githubusercontent.com/ultralytics/assets/main/im/bus.jpg",
    },
    "source-zidane.jpg": {
        "sha256": "16d73869e3267a7d4ed00de8e860833bd1657c1b252e94c0c348277adc7b6edb",
        "url": "https://raw.githubusercontent.com/ultralytics/assets/main/im/zidane.jpg",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources() -> None:
    for name, metadata in SOURCES.items():
        path = FIXTURE_DIR / name
        if not path.is_file():
            raise RuntimeError(f"missing source image: {path}")
        actual = sha256(path)
        if actual != metadata["sha256"]:
            raise RuntimeError(f"unexpected SHA-256 for {name}: {actual}")


def main() -> None:
    verify_sources()

    zidane = Image.open(FIXTURE_DIR / "source-zidane.jpg").convert("RGB")
    tie_occluded = zidane.copy()
    tie_draw = ImageDraw.Draw(tie_occluded)
    tie_box = [380, 315, 650, 719]
    tie_draw.rectangle(tie_box, fill=(116, 122, 128), outline=(235, 238, 240), width=4)
    tie_occluded_path = FIXTURE_DIR / "34-zidane-tie-occluded.png"
    tie_occluded.save(tie_occluded_path, format="PNG", optimize=True)

    bus = Image.open(FIXTURE_DIR / "source-bus.jpg").convert("RGB")
    route_occluded = bus.copy()
    route_draw = ImageDraw.Draw(route_occluded)
    route_box = [25, 318, 225, 386]
    route_draw.rectangle(route_box, fill=(28, 31, 34), outline=(110, 116, 122), width=3)
    route_occluded_path = FIXTURE_DIR / "35-bus-route-display-occluded.png"
    route_occluded.save(route_occluded_path, format="PNG", optimize=True)

    cases = [
        {
            "id": "NAT-001",
            "file": "source-bus.jpg",
            "purpose": "count complete and edge-cropped pedestrians without counting reflections",
        },
        {
            "id": "NAT-002",
            "file": "source-zidane.jpg",
            "purpose": "read people count, pointing action and image-relative spatial relations",
        },
        {
            "id": "NAT-003",
            "file": tie_occluded_path.name,
            "purpose": "refuse to invent the color of a fully occluded tie",
            "occlusion_box_xyxy": tie_box,
        },
        {
            "id": "NAT-004",
            "file": route_occluded_path.name,
            "purpose": "separate hidden route display from visible city branding",
            "occlusion_box_xyxy": route_box,
        },
    ]

    manifest = {
        "sources": SOURCES,
        "derivation": "Opaque rectangles were added locally; source pixels were otherwise unchanged.",
        "cases": [],
    }
    for case in cases:
        path = FIXTURE_DIR / case["file"]
        with Image.open(path) as image:
            record = dict(case)
            record.update(
                {
                    "width": image.width,
                    "height": image.height,
                    "sha256": sha256(path),
                }
            )
            manifest["cases"].append(record)

    manifest_path = FIXTURE_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for case in manifest["cases"]:
        print(f"{case['id']} {case['file']} {case['width']}x{case['height']} {case['sha256']}")
    print(f"manifest={manifest_path.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
