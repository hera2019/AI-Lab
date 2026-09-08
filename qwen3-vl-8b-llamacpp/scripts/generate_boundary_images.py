#!/usr/bin/env python3
"""Generate deterministic multimodal boundary fixtures for Qwen3-VL/libmtmd."""

from __future__ import annotations

import hashlib
import io
import json
from array import array
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_DIR / "tests" / "fixtures"
IMAGE_DIR = FIXTURE_DIR / "images"
MULTI_DIR = FIXTURE_DIR / "multi"
INVALID_DIR = FIXTURE_DIR / "invalid"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
CONTACT_SHEET_PATH = FIXTURE_DIR / "contact-sheet.png"
FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
)


def select_font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise RuntimeError("No suitable macOS font was found.")


FONT_PATH = select_font_path()


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def draw_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...] | str,
) -> None:
    left, top, right, bottom = box
    bounds = draw.multiline_textbbox((0, 0), text, font=text_font, align="center", spacing=8)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.multiline_text(
        ((left + right - width) / 2, (top + bottom - height) / 2),
        text,
        font=text_font,
        fill=fill,
        align="center",
        spacing=8,
    )


def make_card(
    size: tuple[int, int], title: str, subtitle: str, background: tuple[int, int, int]
) -> Image.Image:
    image = Image.new("RGB", size, background)
    draw = ImageDraw.Draw(image)
    margin = max(12, min(size) // 16)
    draw.rounded_rectangle(
        (margin, margin, size[0] - margin, size[1] - margin),
        radius=max(8, min(size) // 24),
        fill="white",
        outline="#20242b",
        width=max(2, min(size) // 160),
    )
    draw_centered(draw, (margin, margin, size[0] - margin, size[1] // 2), title, font(46), "#111827")
    draw_centered(
        draw,
        (margin, size[1] // 2, size[0] - margin, size[1] - margin),
        subtitle,
        font(30),
        "#334155",
    )
    return image


def write_images() -> list[dict[str, object]]:
    for directory in (IMAGE_DIR, MULTI_DIR, INVALID_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, object]] = []

    one_pixel = Image.new("RGB", (1, 1), (255, 0, 0))
    one_pixel.save(IMAGE_DIR / "01-one-pixel-red.png")
    cases.append(
        {
            "id": "IMG-001",
            "category": "minimum-size",
            "files": ["tests/fixtures/images/01-one-pixel-red.png"],
            "prompt": "报告图片尺寸和主色；如果无法处理，请明确报错。",
            "pass_condition": "成功处理，或快速明确拒绝；不得崩溃、挂死或无限分配。",
        }
    )

    transparent_pixel = Image.new("RGBA", (1, 1), (0, 255, 0, 0))
    transparent_pixel.save(IMAGE_DIR / "02-one-pixel-transparent.png")
    cases.append(
        {
            "id": "IMG-002",
            "category": "minimum-size-alpha",
            "files": ["tests/fixtures/images/02-one-pixel-transparent.png"],
            "prompt": "报告图片是否可见以及主色；不确定时说明。",
            "pass_condition": "成功处理，或快速明确拒绝；记录透明像素如何转换。",
        }
    )

    alpha = Image.new("RGBA", (720, 420), (0, 0, 0, 0))
    draw = ImageDraw.Draw(alpha)
    draw.rounded_rectangle((70, 70, 650, 350), radius=30, fill=(255, 255, 255, 255))
    draw.text((145, 125), "VISIBLE 42", font=font(58), fill=(15, 23, 42, 255))
    draw.rectangle((100, 210, 620, 320), fill=(255, 255, 255, 0))
    draw.text((160, 235), "HIDDEN 99", font=font(52), fill=(255, 0, 0, 0))
    alpha.save(IMAGE_DIR / "03-transparent-hidden-rgb.png")
    cases.append(
        {
            "id": "IMG-003",
            "category": "alpha-channel",
            "files": ["tests/fixtures/images/03-transparent-hidden-rgb.png"],
            "prompt": "只抄录你实际看见的文字。",
            "pass_condition": "记录 VISIBLE 42 与透明像素中 HIDDEN 99 的可见性；不得静默改变结论而不记录。",
        }
    )

    wide = Image.new("RGB", (4096, 32), "white")
    wide_draw = ImageDraw.Draw(wide)
    wide_colors = ("#ef4444", "#f59e0b", "#22c55e", "#3b82f6", "#8b5cf6", "#ec4899", "#0f172a", "#e2e8f0")
    for index, color in enumerate(wide_colors):
        wide_draw.rectangle((index * 512, 0, (index + 1) * 512 - 1, 31), fill=color)
    wide.save(IMAGE_DIR / "04-extreme-wide-4096x32.png")
    cases.append(
        {
            "id": "IMG-004",
            "category": "extreme-aspect-ratio",
            "files": ["tests/fixtures/images/04-extreme-wide-4096x32.png"],
            "prompt": "从左到右描述色带，并报告图片形状。",
            "pass_condition": "保持色带顺序；无崩溃、挂死或异常 token/内存增长。",
        }
    )

    tall = Image.new("RGB", (32, 4096), "white")
    tall_draw = ImageDraw.Draw(tall)
    for index, color in enumerate(wide_colors):
        tall_draw.rectangle((0, index * 512, 31, (index + 1) * 512 - 1), fill=color)
    tall.save(IMAGE_DIR / "05-extreme-tall-32x4096.png")
    cases.append(
        {
            "id": "IMG-005",
            "category": "extreme-aspect-ratio",
            "files": ["tests/fixtures/images/05-extreme-tall-32x4096.png"],
            "prompt": "从上到下描述色带，并报告图片形状。",
            "pass_condition": "保持色带顺序；无崩溃、挂死或异常 token/内存增长。",
        }
    )

    orientation = make_card((640, 360), "EXIF 6", "RAW RIGHT →", (254, 240, 138))
    orientation_draw = ImageDraw.Draw(orientation)
    orientation_draw.polygon(((500, 150), (590, 180), (500, 210)), fill="#dc2626")
    exif = Image.Exif()
    exif[274] = 6
    orientation_path = IMAGE_DIR / "06-exif-orientation-6.jpg"
    orientation.save(orientation_path, format="JPEG", quality=95, exif=exif)
    with Image.open(orientation_path) as opened:
        ImageOps.exif_transpose(opened).convert("RGB").save(
            IMAGE_DIR / "06-exif-reference.png"
        )
    cases.append(
        {
            "id": "IMG-006",
            "category": "exif-orientation",
            "files": [
                "tests/fixtures/images/06-exif-orientation-6.jpg",
                "tests/fixtures/images/06-exif-reference.png",
            ],
            "prompt": "分别描述文字和箭头方向，判断两张图视觉方向是否一致。",
            "pass_condition": "记录 EXIF Orientation=6 是否生效；两输入都须稳定处理或明确报错。",
        }
    )

    unicode_image = make_card((760, 440), "UNICODE PATH OK", "猫・東京・编号 42", (186, 230, 253))
    unicode_image.save(IMAGE_DIR / "07-unicode-猫-東京-🧪.png")
    cases.append(
        {
            "id": "IMG-007",
            "category": "unicode-path",
            "files": ["tests/fixtures/images/07-unicode-猫-東京-🧪.png"],
            "prompt": "抄录图片中的英文、中文和编号。",
            "pass_condition": "文件可通过 CLI 与 API 路径读取，且不因 Unicode 文件名失败。",
        }
    )

    mismatch = make_card((640, 360), "PNG BYTES", ".jpg filename", (221, 214, 254))
    mismatch_buffer = io.BytesIO()
    mismatch.save(mismatch_buffer, format="PNG")
    (IMAGE_DIR / "08-png-bytes-with-jpg-extension.jpg").write_bytes(mismatch_buffer.getvalue())
    cases.append(
        {
            "id": "IMG-008",
            "category": "extension-mismatch",
            "files": ["tests/fixtures/images/08-png-bytes-with-jpg-extension.jpg"],
            "prompt": "抄录图片中的两行文字。",
            "pass_condition": "按文件内容安全识别，或明确拒绝；不得把扩展名错误当成模型答案。",
        }
    )

    width, height = 512, 256
    values = array("H", (int(65535 * x / (width - 1)) for _y in range(height) for x in range(width)))
    grayscale = Image.frombytes("I;16", (width, height), values.tobytes())
    grayscale.save(IMAGE_DIR / "09-grayscale-16bit.png")
    cases.append(
        {
            "id": "IMG-009",
            "category": "pixel-format",
            "files": ["tests/fixtures/images/09-grayscale-16bit.png"],
            "prompt": "描述灰度从哪一侧向哪一侧变化。",
            "pass_condition": "渐变方向正确，且 16-bit PNG 解码不崩溃。",
        }
    )

    cmyk_rgb = make_card((640, 360), "CMYK JPEG", "CYAN / MAGENTA / YELLOW", (207, 250, 254))
    cmyk_rgb.convert("CMYK").save(IMAGE_DIR / "10-cmyk.jpg", format="JPEG", quality=95)
    cases.append(
        {
            "id": "IMG-010",
            "category": "pixel-format",
            "files": ["tests/fixtures/images/10-cmyk.jpg"],
            "prompt": "抄录标题并描述背景色。",
            "pass_condition": "CMYK JPEG 能稳定处理或明确拒绝，不出现进程级错误。",
        }
    )

    ocr = Image.new("RGB", (1200, 720), "white")
    ocr_draw = ImageDraw.Draw(ocr)
    ocr_draw.rectangle((50, 45, 1150, 675), outline="#0f172a", width=5)
    ocr_draw.text((90, 75), "仓库：东京-7", font=font(58), fill="#111827")
    ocr_draw.text((90, 190), "温度：23.5°C", font=font(58), fill="#111827")
    ocr_draw.text((90, 305), "批次：QVL-8B-042", font=font(58), fill="#111827")
    ocr_draw.text((90, 420), "合计：1,248", font=font(58), fill="#111827")
    ocr_draw.text((90, 555), "Do not guess missing text.", font=font(36), fill="#475569")
    ocr.save(IMAGE_DIR / "11-ocr-clean.png")
    cases.append(
        {
            "id": "OCR-001",
            "category": "ocr-clean",
            "files": ["tests/fixtures/images/11-ocr-clean.png"],
            "prompt": "逐行抄录全部文字，保留大小写、连字符、小数点和千位逗号。",
            "pass_condition": "五行完全匹配，不擅自改写数字和标点。",
        }
    )

    low_contrast = Image.new("RGB", (1600, 900), (238, 241, 245))
    low_draw = ImageDraw.Draw(low_contrast)
    low_draw.text((90, 100), "LOW CONTRAST: LC-5902", font=font(28), fill=(176, 183, 193))
    low_draw.text((90, 190), "微小文字：星河-17", font=font(22), fill=(170, 178, 188))
    low_draw.text((90, 270), "serial: az-00481-x", font=font(18), fill=(166, 174, 184))
    low_draw.text((90, 345), "金额：¥7,305.60", font=font(16), fill=(164, 172, 182))
    low_draw.line((80, 430, 1520, 430), fill=(205, 211, 218), width=2)
    low_draw.text((90, 470), "背景与文字对比度刻意降低", font=font(24), fill=(174, 181, 191))
    low_contrast.save(IMAGE_DIR / "12-ocr-small-low-contrast.png")
    cases.append(
        {
            "id": "OCR-002",
            "category": "ocr-boundary",
            "files": ["tests/fixtures/images/12-ocr-small-low-contrast.png"],
            "prompt": "尽力逐行抄录；无法确认的字符用 [?]，不要猜。",
            "pass_condition": "分别统计正确、缺失和臆测字符；低置信度时应表达不确定。",
        }
    )

    tilted_base = make_card((900, 500), "TILTED OCR", "旋转代码：RT-731", (220, 252, 231))
    tilted = tilted_base.rotate(8, expand=True, fillcolor="white", resample=Image.Resampling.BICUBIC)
    tilted.save(IMAGE_DIR / "13-ocr-tilted-8deg.png")
    cases.append(
        {
            "id": "OCR-003",
            "category": "ocr-rotation",
            "files": ["tests/fixtures/images/13-ocr-tilted-8deg.png"],
            "prompt": "抄录标题和旋转代码，并估计倾斜方向。",
            "pass_condition": "识别 RT-731，方向判断正确；错误应计入 OCR 质量而非立即视为 libmtmd bug。",
        }
    )

    multi_specs = (
        ("14-multi-a-red-circle.png", "A", "ALPHA-17", "circle", "#ef4444"),
        ("15-multi-b-blue-square.png", "B", "BETA-29", "square", "#3b82f6"),
        ("16-multi-c-green-triangle.png", "C", "GAMMA-43", "triangle", "#22c55e"),
    )
    for filename, letter, code, shape, color in multi_specs:
        image = Image.new("RGB", (640, 480), "white")
        draw = ImageDraw.Draw(image)
        if shape == "circle":
            draw.ellipse((210, 55, 430, 275), fill=color)
        elif shape == "square":
            draw.rectangle((210, 55, 430, 275), fill=color)
        else:
            draw.polygon(((320, 45), (185, 275), (455, 275)), fill=color)
        draw_centered(draw, (80, 285, 560, 465), f"IMAGE {letter}\n{code}", font(42), "#111827")
        image.save(MULTI_DIR / filename)
    cases.append(
        {
            "id": "MULTI-001",
            "category": "multi-image-order",
            "files": [f"tests/fixtures/multi/{spec[0]}" for spec in multi_specs],
            "prompt": "按输入顺序列出每张图的字母、颜色、形状和代码。",
            "pass_condition": "三张图都被使用，顺序与代码完全正确；不得只回答第一张。",
        }
    )

    valid_jpeg = make_card((1024, 640), "DAMAGED JPEG SOURCE", "TRUNCATE-ME-882", (254, 226, 226))
    jpeg_buffer = io.BytesIO()
    valid_jpeg.save(jpeg_buffer, format="JPEG", quality=94)
    jpeg_bytes = jpeg_buffer.getvalue()
    (INVALID_DIR / "17-damaged-truncated.jpg").write_bytes(jpeg_bytes[: max(128, len(jpeg_bytes) // 10)])
    cases.append(
        {
            "id": "BAD-001",
            "category": "corrupt-input",
            "files": ["tests/fixtures/invalid/17-damaged-truncated.jpg"],
            "prompt": "尝试读取；如果损坏，请明确报告。",
            "pass_condition": "快速、明确、非零失败；不得崩溃、挂死、误当视频或输出臆测内容。",
        }
    )

    (INVALID_DIR / "18-not-an-image.jpg").write_bytes(b"This is not a JPEG. QVL boundary fixture.\n")
    cases.append(
        {
            "id": "BAD-002",
            "category": "wrong-content",
            "files": ["tests/fixtures/invalid/18-not-an-image.jpg"],
            "prompt": "尝试读取；如果不是图片，请明确报告。",
            "pass_condition": "快速、明确、非零失败；不得崩溃、挂死或按扩展名伪装成功。",
        }
    )

    (INVALID_DIR / "19-empty.png").write_bytes(b"")
    cases.append(
        {
            "id": "BAD-003",
            "category": "empty-input",
            "files": ["tests/fixtures/invalid/19-empty.png"],
            "prompt": "尝试读取；如果为空，请明确报告。",
            "pass_condition": "快速、明确、非零失败；不得崩溃、挂死或无限重试。",
        }
    )

    return cases


def inspect_file(relative_path: str, expected_decodable: bool) -> dict[str, object]:
    path = PROJECT_DIR / relative_path
    data = path.read_bytes()
    metadata: dict[str, object] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "expected_decodable": expected_decodable,
    }
    try:
        with Image.open(path) as image:
            image.load()
            metadata.update(
                {
                    "format": image.format,
                    "mode": image.mode,
                    "width": image.width,
                    "height": image.height,
                    "exif_orientation": image.getexif().get(274),
                }
            )
    except Exception as error:  # intentionally record malformed fixtures
        metadata["pillow_error"] = f"{type(error).__name__}: {error}"
    return metadata


def make_contact_sheet(cases: list[dict[str, object]]) -> None:
    valid_paths: list[tuple[str, Path]] = []
    for case in cases:
        if str(case["id"]).startswith("BAD-"):
            continue
        for relative in case["files"]:
            valid_paths.append((str(case["id"]), PROJECT_DIR / str(relative)))

    cell_width, cell_height = 360, 280
    columns = 3
    rows = (len(valid_paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#e2e8f0")
    draw = ImageDraw.Draw(sheet)
    label_font = font(18)

    for index, (case_id, path) in enumerate(valid_paths):
        column = index % columns
        row = index // columns
        x = column * cell_width
        y = row * cell_height
        draw.rectangle((x + 6, y + 6, x + cell_width - 6, y + cell_height - 6), fill="white")
        with Image.open(path) as opened:
            transposed = ImageOps.exif_transpose(opened)
            if transposed.mode.startswith("I;16"):
                scaled = Image.new("L", transposed.size)
                scaled.putdata([value // 257 for value in transposed.get_flattened_data()])
                preview = scaled.convert("RGBA")
            else:
                preview = transposed.convert("RGBA")
            if preview.width <= 4 or preview.height <= 4:
                preview = preview.resize((160, 160), Image.Resampling.NEAREST)
            preview.thumbnail((320, 205), Image.Resampling.LANCZOS)
            checker = Image.new("RGB", preview.size, "#f8fafc")
            checker.paste(preview, mask=preview.getchannel("A"))
        px = x + (cell_width - checker.width) // 2
        py = y + 15 + (205 - checker.height) // 2
        sheet.paste(checker, (px, py))
        filename = path.name if len(path.name) <= 38 else path.name[:35] + "..."
        draw.text((x + 14, y + 224), case_id, font=label_font, fill="#0f172a")
        draw.text((x + 14, y + 247), filename, font=font(14), fill="#334155")

    sheet.save(CONTACT_SHEET_PATH)


def main() -> None:
    cases = write_images()
    make_contact_sheet(cases)

    expected_invalid = {
        "tests/fixtures/invalid/17-damaged-truncated.jpg",
        "tests/fixtures/invalid/18-not-an-image.jpg",
        "tests/fixtures/invalid/19-empty.png",
    }
    all_paths = [str(path) for case in cases for path in case["files"]]
    file_metadata = {
        relative: inspect_file(relative, relative not in expected_invalid)
        for relative in all_paths
    }
    contact_relative = "tests/fixtures/contact-sheet.png"
    file_metadata[contact_relative] = inspect_file(contact_relative, True)

    manifest = {
        "schema_version": 1,
        "generator": "scripts/generate_boundary_images.py",
        "font": str(FONT_PATH),
        "case_count": len(cases),
        "cases": cases,
        "files": file_metadata,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(cases)} cases and {len(file_metadata)} files.")
    print("Manifest: tests/fixtures/manifest.json")
    print("Overview: tests/fixtures/contact-sheet.png")


if __name__ == "__main__":
    main()
