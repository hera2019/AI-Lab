#!/usr/bin/env python3

from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def make_cutout(reference: Image.Image) -> Image.Image:
    # This fixed crop contains only the center green mug from the three-mug fixture.
    crop = reference.crop((388, 396, 692, 708)).convert("RGB")
    pixels = np.asarray(crop, dtype=np.float32)
    red, green, blue = pixels[..., 0], pixels[..., 1], pixels[..., 2]

    # Identify green material, then expand and feather slightly to retain anti-aliased edges.
    green_material = (
        (green > red * 1.07)
        & (green > blue * 1.025)
        & (green - np.minimum(red, blue) > 10)
    )
    support = Image.fromarray((green_material * 255).astype(np.uint8), mode="L")
    support = support.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.2))

    # The source background is white. Its distance from white supplies a soft edge matte.
    distance_from_white = 255.0 - pixels.min(axis=2)
    white_matte = np.clip((distance_from_white - 1.5) / 24.0, 0.0, 1.0)
    alpha = np.asarray(support, dtype=np.float32) / 255.0
    alpha = np.clip(alpha * white_matte, 0.0, 1.0)

    rgba = np.dstack((pixels.astype(np.uint8), (alpha * 255).astype(np.uint8)))
    cutout = Image.fromarray(rgba, mode="RGBA")
    bbox = cutout.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("failed to isolate the green mug")
    return cutout.crop(bbox)


def tint_for_scene(cutout: Image.Image, warm: bool) -> Image.Image:
    rgb = cutout.convert("RGB")
    if warm:
        rgb = ImageEnhance.Brightness(rgb).enhance(0.78)
        rgb = ImageEnhance.Color(rgb).enhance(0.88)
        values = np.asarray(rgb, dtype=np.float32)
        values[..., 0] = np.clip(values[..., 0] * 1.04 + 4, 0, 255)
        values[..., 1] = np.clip(values[..., 1] * 0.98 + 2, 0, 255)
        values[..., 2] = np.clip(values[..., 2] * 0.78, 0, 255)
        rgb = Image.fromarray(values.astype(np.uint8), mode="RGB")
    else:
        rgb = ImageEnhance.Brightness(rgb).enhance(0.90)
    rgb.putalpha(cutout.getchannel("A"))
    return rgb


def composite(
    scene: Image.Image, cutout: Image.Image, warm: bool, target_size: int
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    base = scene.convert("RGBA")
    mug = tint_for_scene(cutout, warm)
    mug.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

    # The original serving ledge is around y=630; this places the mug beside the blue cat.
    x = 540
    y = 634 - mug.height

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.ellipse((x + 8, 625, x + mug.width - 4, 639), fill=(30, 18, 8, 72))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4.0))
    base = Image.alpha_composite(base, shadow)
    base.alpha_composite(mug, (x, y))
    return base.convert("RGB"), (x, y, x + mug.width, y + mug.height)


def make_refinement_mask(
    size: tuple[int, int], mug_box: tuple[int, int, int, int]
) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    # Include the mug, its contact shadow, and a small amount of nearby counter surface.
    left, top, right, bottom = mug_box
    draw.rounded_rectangle(
        (left - 14, top - 14, right + 18, bottom + 16), radius=14, fill=255
    )
    return mask.filter(ImageFilter.GaussianBlur(4.0))


def main() -> int:
    if len(sys.argv) not in (4, 5):
        print(
            "usage: compose_precise_green_mug.py SCENE MUG_REFERENCE OUTPUT_DIR [TARGET_SIZE]",
            file=sys.stderr,
        )
        return 2

    scene_path = Path(sys.argv[1])
    reference_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    target_size = int(sys.argv[4]) if len(sys.argv) == 5 else 92
    if not 32 <= target_size <= 256:
        raise ValueError("TARGET_SIZE must be between 32 and 256 pixels")
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = Image.open(scene_path).convert("RGB")
    reference = Image.open(reference_path).convert("RGB")
    if scene.size != (1024, 1024) or reference.size != (1024, 1024):
        raise ValueError("this reproducible fixture expects two 1024x1024 inputs")

    cutout = make_cutout(reference)
    cutout.save(output_dir / "green-mug-cutout.png")
    neutral, _ = composite(scene, cutout, warm=False, target_size=target_size)
    warm, mug_box = composite(scene, cutout, warm=True, target_size=target_size)
    neutral.save(output_dir / "01-layer-composite-neutral.png")
    warm.save(output_dir / "02-layer-composite-warm.png")
    make_refinement_mask(scene.size, mug_box).save(output_dir / "refinement-mask.png")

    print(
        "Created deterministic cutout, two exact-placement composites, and refinement "
        f"mask (target_size={target_size}, mug_box={mug_box})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
