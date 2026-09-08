#!/usr/bin/env python3

from pathlib import Path
import sys

import numpy as np
from PIL import Image


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: lock_refined_region.py BASE REFINED MASK OUTPUT", file=sys.stderr)
        return 2

    base_path, refined_path, mask_path, output_path = map(Path, sys.argv[1:])
    base = Image.open(base_path).convert("RGB")
    refined = Image.open(refined_path).convert("RGB")
    mask = Image.open(mask_path).convert("L")
    if base.size != refined.size or base.size != mask.size:
        raise ValueError("base, refined image, and mask must have identical dimensions")

    base_values = np.asarray(base, dtype=np.float32)
    refined_values = np.asarray(refined, dtype=np.float32)
    alpha = np.asarray(mask, dtype=np.float32)[..., None] / 255.0
    result = np.rint(base_values * (1.0 - alpha) + refined_values * alpha)
    output = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8), mode="RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)
    print(f"Locked refinement saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
