#!/usr/bin/env python3

import argparse
import base64
import json
from pathlib import Path


def nullable(value_type: str) -> dict:
    return {"type": [value_type, "null"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--ocr", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    ocr = json.loads(args.ocr.read_text(encoding="utf-8"))
    ocr_evidence = {
        "coordinate_origin": "lower-left",
        "observations": ocr["observations"],
    }
    image_data = base64.b64encode(args.image.read_bytes()).decode("ascii")

    item_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "quantity": {
                **nullable("integer"),
                "description": "Numeric count from the receipt quantity column.",
            },
            "description": nullable("string"),
            "amount": nullable("integer"),
            "row_marker": {
                **nullable("string"),
                "description": "Optional non-quantity marker in a separate far-left column; null when absent.",
            },
        },
        "required": ["quantity", "description", "amount", "row_marker"],
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "merchant": {
                **nullable("string"),
                "description": "Consumer-facing merchant or store brand printed on the receipt.",
            },
            "receipt_number": nullable("string"),
            "table_number": nullable("string"),
            "party_size": nullable("integer"),
            "staff_id": nullable("string"),
            "staff_name": nullable("string"),
            "date": nullable("string"),
            "time": nullable("string"),
            "items": {
                "type": "array",
                "items": item_schema,
                "maxItems": 20,
            },
            "subtotal": nullable("integer"),
            "tax": nullable("integer"),
            "total": nullable("integer"),
            "camera_timestamp": nullable("string"),
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 20,
            },
        },
        "required": [
            "merchant",
            "receipt_number",
            "table_number",
            "party_size",
            "staff_id",
            "staff_name",
            "date",
            "time",
            "items",
            "subtotal",
            "tax",
            "total",
            "camera_timestamp",
            "warnings",
        ],
    }

    instructions = """Extract structured accounting data from the receipt image.

The image is the primary evidence. Apple Vision OCR observations are supporting evidence and can contain errors even when confidence is 1.0. Coordinates are normalized with a lower-left origin. Blocks with similar y values are on the same visual row, while different x values can represent separate columns.

Preserve table structure. quantity is the numeric value under the quantity column. row_marker is only for a separate non-quantity block farther left; a leading numeric quantity such as 1 must never be copied into row_marker. Set row_marker to null when that separate marker is absent. A marker must not be prefixed to the item description.

For merchant, prefer the consumer-facing Japanese store or brand name printed on the receipt over a corporate legal name when both are visible. Use integer yen amounts without separators. Use YYYY-MM-DD for date and HH:MM for time. The camera timestamp is outside the paper receipt and must be stored separately. Use null for unreadable values. Do not invent missing text. Return only the schema-constrained JSON.

Apple Vision evidence:
""" + json.dumps(ocr_evidence, ensure_ascii=False, separators=(",", ":"))

    request = {
        "model": "qwen3-vl-8b",
        "messages": [
            {
                "role": "system",
                "content": "You extract receipt data conservatively. Preserve source layout and never treat OCR confidence as proof.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64," + image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": instructions,
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 512,
        "chat_template_kwargs": {"enable_thinking": False},
        "reasoning_effort": "none",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "receipt_accounting",
                "strict": True,
                "schema": schema,
            },
        },
    }

    args.output.write_text(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
