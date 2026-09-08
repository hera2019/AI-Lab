#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


FONT_CANDIDATES = (
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
)


def register_cjk_font() -> str:
    for font_path in FONT_CANDIDATES:
        if not font_path.exists():
            continue
        try:
            pdfmetrics.registerFont(
                TTFont("LocalCJK", str(font_path), subfontIndex=0)
            )
            return "LocalCJK"
        except Exception:
            continue
    raise RuntimeError("No compatible local Chinese font was found.")


def inline_markup(text: str) -> str:
    value = html.escape(text.strip())
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(
        r"`([^`]+)`",
        r'<font color="#0F766E">\1</font>',
        value,
    )
    return value


def build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCJK",
            parent=base["Title"],
            fontName=font_name,
            fontSize=24,
            leading=32,
            textColor=colors.HexColor("#102A43"),
            alignment=TA_CENTER,
            spaceAfter=16,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "Heading2CJK",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#0F766E"),
            spaceBefore=13,
            spaceAfter=7,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "Heading3CJK",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#334E68"),
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "BodyCJK",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor("#243B53"),
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "BulletCJK",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.5,
            leading=17,
            leftIndent=14,
            firstLineIndent=-10,
            textColor=colors.HexColor("#243B53"),
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "CodeCJK",
            parent=base["Code"],
            fontName=font_name,
            fontSize=8.7,
            leading=13,
            leftIndent=8,
            rightIndent=8,
            borderPadding=8,
            backColor=colors.HexColor("#F0F4F8"),
            borderColor=colors.HexColor("#BCCCDC"),
            borderWidth=0.5,
            spaceBefore=4,
            spaceAfter=9,
            wordWrap="CJK",
        ),
    }


def markdown_story(markdown: str, styles: dict[str, ParagraphStyle]):
    story = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    title_seen = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(
                Paragraph(inline_markup(" ".join(paragraph_lines)), styles["body"])
            )
            paragraph_lines.clear()

    def flush_code() -> None:
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            code_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                flush_code()
            in_code = not in_code
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            continue

        if stripped in {"---", "***"}:
            flush_paragraph()
            story.append(Spacer(1, 4 * mm))
            continue

        if stripped == "<!-- pagebreak -->":
            flush_paragraph()
            story.append(PageBreak())
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            style = styles["title"] if not title_seen else styles["h2"]
            title_seen = True
            story.append(Paragraph(inline_markup(stripped[2:]), style))
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[3:]), styles["h2"]))
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[4:]), styles["h3"]))
            continue

        bullet_match = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", stripped)
        if bullet_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    "• " + inline_markup(bullet_match.group(1)), styles["bullet"]
                )
            )
            continue

        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_code()
    return story


def create_pdf(markdown_path: Path, output_path: Path) -> None:
    font_name = register_cjk_font()
    styles = build_styles(font_name)
    markdown = markdown_path.read_text(encoding="utf-8")
    story = markdown_story(markdown, styles)

    if not story:
        raise ValueError("The Markdown source is empty.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=markdown_path.stem,
        author="Qwen3-14B + AI Lab",
    )

    def decorate_page(canvas, doc):
        canvas.saveState()
        width, _ = A4
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#627D98"))
        canvas.drawString(20 * mm, 9 * mm, "AI Lab - 本地离线生成")
        canvas.drawRightString(width - 20 * mm, 9 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert simple Markdown to PDF.")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    create_pdf(args.markdown, args.output)


if __name__ == "__main__":
    main()
