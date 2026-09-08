#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


EXPECTED_ITEMS = [
    {"quantity": 1, "description": "中華そば", "amount": 748, "row_marker": None},
    {"quantity": 1, "description": "特選セットA", "amount": 1120, "row_marker": None},
    {"quantity": 1, "description": "特セット餃子+3個", "amount": 165, "row_marker": "TP"},
]
DEFAULT_OCR_PATH = (
    Path(__file__).resolve().parent.parent / "results/apple-vision-receipt-ocr.json"
)


def parse_response(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    response = json.loads(path.read_text(encoding="utf-8"))
    if "error" in response:
        raise ValueError(f"API error: {response['error']}")
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, dict):
        data = content
    else:
        content = content.strip()
        if content.startswith("```json") and content.endswith("```"):
            content = content[len("```json") : -len("```")].strip()
        data = json.loads(content)
    return data, response.get("timings", {})


def normalize_description(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return unicodedata.normalize("NFKC", text).replace(" ", "")


def ocr_date_candidates(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    ocr = json.loads(path.read_text(encoding="utf-8"))
    candidates: list[str] = []
    for observation in ocr.get("observations", []):
        texts = [observation.get("text", "")]
        texts.extend(
            candidate.get("text", "")
            for candidate in observation.get("candidates", [])
        )
        for raw_text in texts:
            text = unicodedata.normalize("NFKC", raw_text)
            match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
            if not match:
                continue
            try:
                value = dt.date(*map(int, match.groups())).isoformat()
            except ValueError:
                continue
            if value not in candidates:
                candidates.append(value)
    return candidates


def validate(data: dict[str, Any]) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, actual: Any) -> None:
        checks.append((name, passed, repr(actual)))

    check("merchant", data.get("merchant") == "餃子の王将", data.get("merchant"))
    check("receipt_number", data.get("receipt_number") == "657", data.get("receipt_number"))
    check("table_number", data.get("table_number") == "25", data.get("table_number"))
    check("party_size", data.get("party_size") == 2, data.get("party_size"))
    check("staff_id", data.get("staff_id") == "8", data.get("staff_id"))
    check("staff_name", data.get("staff_name") == "大橋", data.get("staff_name"))
    check("date", data.get("date") == "2026-06-21", data.get("date"))
    check("time", data.get("time") == "17:07", data.get("time"))
    check("subtotal", data.get("subtotal") == 2033, data.get("subtotal"))
    check("tax", data.get("tax") == 0, data.get("tax"))
    check("total", data.get("total") == 2033, data.get("total"))

    items = data.get("items") if isinstance(data.get("items"), list) else []
    check("item_count", len(items) == 3, len(items))
    for index, expected in enumerate(EXPECTED_ITEMS):
        actual = items[index] if index < len(items) else {}
        check(f"item_{index + 1}_quantity", actual.get("quantity") == expected["quantity"], actual.get("quantity"))
        check(
            f"item_{index + 1}_description",
            normalize_description(actual.get("description")) == normalize_description(expected["description"]),
            actual.get("description"),
        )
        check(f"item_{index + 1}_amount", actual.get("amount") == expected["amount"], actual.get("amount"))
        check(f"item_{index + 1}_row_marker", actual.get("row_marker") == expected["row_marker"], actual.get("row_marker"))

    numeric_amounts = [item.get("amount") for item in items if isinstance(item, dict)]
    if numeric_amounts and all(isinstance(value, int) for value in numeric_amounts):
        check("sum_items_equals_subtotal", sum(numeric_amounts) == data.get("subtotal"), sum(numeric_amounts))
    else:
        check("sum_items_equals_subtotal", False, numeric_amounts)

    subtotal = data.get("subtotal")
    tax = data.get("tax")
    total = data.get("total")
    check(
        "subtotal_plus_tax_equals_total",
        isinstance(subtotal, int) and isinstance(tax, int) and subtotal + tax == total,
        (subtotal, tax, total),
    )

    try:
        receipt_date = dt.date.fromisoformat(data.get("date", ""))
        check("date_not_in_future", receipt_date <= dt.date.today(), receipt_date.isoformat())
    except (TypeError, ValueError):
        check("date_not_in_future", False, data.get("date"))

    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ocr",
        type=Path,
        default=DEFAULT_OCR_PATH if DEFAULT_OCR_PATH.exists() else None,
    )
    parser.add_argument("responses", nargs="+", type=Path)
    args = parser.parse_args()

    canonical: list[str] = []
    all_passed = True
    date_candidates = ocr_date_candidates(args.ocr)
    for path in args.responses:
        print(f"===== {path.name} =====")
        try:
            data, timings = parse_response(path)
        except Exception as error:
            print(f"parse_error={error}")
            all_passed = False
            continue

        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        if timings:
            print("timings=" + json.dumps(timings, ensure_ascii=False, sort_keys=True))

        items = data.get("items") if isinstance(data.get("items"), list) else []
        raw_description_matches = sum(
            index < len(items)
            and isinstance(items[index], dict)
            and items[index].get("description") == expected["description"]
            for index, expected in enumerate(EXPECTED_ITEMS)
        )
        print(
            f"raw_description_exact_matches={raw_description_matches}/{len(EXPECTED_ITEMS)}"
        )

        checks = validate(data)
        passed_count = sum(passed for _, passed, _ in checks)
        print(f"checks={passed_count}/{len(checks)}")
        for name, passed, actual in checks:
            print(f"{'PASS' if passed else 'FAIL'} {name} actual={actual}")
        if passed_count != len(checks):
            all_passed = False

        conflicting_dates = [
            candidate
            for candidate in date_candidates
            if candidate != data.get("date")
        ]
        warnings = data.get("warnings") if isinstance(data.get("warnings"), list) else []
        print("ocr_date_candidates=" + json.dumps(date_candidates, ensure_ascii=False))
        print(
            f"ocr_date_conflict={'yes' if conflicting_dates else 'no'}"
        )
        print(
            "model_warning_for_ocr_date_conflict="
            + ("yes" if conflicting_dates and warnings else "no")
        )
        print(
            f"deterministic_review_required={'yes' if conflicting_dates else 'no'}"
        )
        canonical.append(json.dumps(data, ensure_ascii=False, sort_keys=True))

    if canonical:
        print(f"responses_identical={'yes' if len(set(canonical)) == 1 else 'no'}")
    print(f"all_checks_passed={'yes' if all_passed else 'no'}")


if __name__ == "__main__":
    main()
