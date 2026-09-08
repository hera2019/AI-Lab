#!/usr/bin/env python3
"""Add deterministic semantic checks to the strict Phase 1 ASR scores."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable


PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"
BASELINE_PATH = RESULTS_DIR / "phase1-clean-baseline-summary.json"
DIAGNOSTICS_PATH = RESULTS_DIR / "phase1-diagnostics-summary.json"


def compact(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        char
        for char in normalized
        if not unicodedata.category(char).startswith(("P", "S", "Z"))
        and not char.isspace()
    )


def has_all(*needles: str) -> Callable[[str], bool]:
    return lambda text: all(compact(needle) in compact(text) for needle in needles)


def matches(pattern: str) -> Callable[[str], bool]:
    return lambda text: re.search(pattern, unicodedata.normalize("NFKC", text), re.I) is not None


def any_of(*predicates: Callable[[str], bool]) -> Callable[[str], bool]:
    return lambda text: any(predicate(text) for predicate in predicates)


CHECKS: dict[str, list[tuple[str, str, Callable[[str], bool]]]] = {
    "ASR-ZH-001": [
        ("date", "2026-09-02", has_all("2026年9月2日")),
        ("time", "15:15", has_all("下午3点15分")),
        ("order_id", "A731", has_all("A731")),
        ("sentence_content", "three intended statements", has_all("今天是", "会议将在", "开始", "订单编号是")),
    ],
    "ASR-JA-001": [
        ("date", "2026-09-02", has_all("2026年9月2日")),
        ("time", "15:15", has_all("午後3時15分")),
        ("order_id", "A731", has_all("A731")),
        ("sentence_content", "three intended statements", has_all("今日は", "会議は", "始まります", "注文番号は")),
    ],
    "ASR-EN-001": [
        ("date", "2026-09-02", has_all("september 2", "2026")),
        ("time", "15:15", matches(r"3[.:]?15\s*p\.?m\.?(?:\b|$)")),
        ("order_id", "A731", has_all("A731")),
        ("sentence_content", "three intended statements", has_all("today is", "meeting starts", "order number is")),
    ],
    "ASR-MIX-001": [
        ("zh_segment", "项目代号是海风七号", has_all("项目代号是海风七号")),
        ("ja_segment", "次の会議は東京で開きます", has_all("次の会議は東京で開きます")),
        ("en_segment", "Please upload the final report by Friday", has_all("Please upload the final report by Friday")),
    ],
}


SEGMENT_CHECKS = {
    "MIX-SEG-ZH": any_of(has_all("项目代号是海风七号"), has_all("项目代号是海风7号")),
    "MIX-SEG-JA": has_all("次の会議は東京で開きます"),
    "MIX-SEG-EN": has_all("Please upload the final report by Friday"),
}


def evaluate_checks(case_id: str, actual: str) -> list[dict[str, Any]]:
    return [
        {"name": name, "expected_meaning": expected, "passed": predicate(actual)}
        for name, expected, predicate in CHECKS[case_id]
    ]


def main() -> int:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    diagnostics = json.loads(DIAGNOSTICS_PATH.read_text(encoding="utf-8"))

    cases = []
    for case in baseline["cases"]:
        checks = evaluate_checks(case["id"], case["actual"])
        cases.append(
            {
                "id": case["id"],
                "strict_score": case["score"],
                "semantic_checks": checks,
                "semantic_passed": sum(item["passed"] for item in checks),
                "semantic_total": len(checks),
                "semantic_content_pass": all(item["passed"] for item in checks),
            }
        )

    diagnostic_segments = []
    for case in diagnostics["cases"]:
        if case["id"] in SEGMENT_CHECKS:
            diagnostic_segments.append(
                {
                    "id": case["id"],
                    "expected": case["expected"],
                    "actual": case["actual"],
                    "passed": SEGMENT_CHECKS[case["id"]](case["actual"]),
                }
            )

    monolingual = [item for item in cases if item["id"] != "ASR-MIX-001"]
    monolingual_field_checks = [
        check
        for item in monolingual
        for check in item["semantic_checks"]
        if check["name"] in {"date", "time", "order_id"}
    ]
    mixed = next(item for item in cases if item["id"] == "ASR-MIX-001")
    result = {
        "method": "deterministic case-specific checks; strict CER/WER remains unchanged",
        "cases": cases,
        "monolingual_critical_fields": {
            "passed": sum(item["passed"] for item in monolingual_field_checks),
            "total": len(monolingual_field_checks),
        },
        "monolingual_semantic_cases": {
            "passed": sum(item["semantic_content_pass"] for item in monolingual),
            "total": len(monolingual),
        },
        "full_clip_mixed_segments": {
            "passed": mixed["semantic_passed"],
            "total": mixed["semantic_total"],
        },
        "separately_transcribed_mixed_segments": {
            "passed": sum(item["passed"] for item in diagnostic_segments),
            "total": len(diagnostic_segments),
            "cases": diagnostic_segments,
        },
    }
    output_path = RESULTS_DIR / "phase1-semantic-analysis.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nsummary={output_path.relative_to(PROJECT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
