#!/usr/bin/env python3

"""Run grounded-answer and refusal tests against the local AI-Lab RAG."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from rag_ai_lab import REFUSAL, answer_question
from search_ai_lab import freshness, load_index


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
    return rows


def assess(case: dict, payload: dict) -> dict:
    answer = payload["answer"]
    citation = payload["citation_report"]
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    add(
        "citation_syntax",
        citation["citation_syntax_valid"],
        f"cited={citation['cited_ids']} unknown={citation['unknown_ids']} "
        f"uncited_lines={citation['uncited_claim_lines']}",
    )
    language = case["language"]
    if language == "ja":
        language_ok = bool(re.search(r"[\u3040-\u30ff]", answer))
    elif language == "en":
        language_ok = not bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", answer))
    else:
        language_ok = bool(re.search(r"[\u3400-\u9fff]", answer))
    add("answer_language", language_ok, f"expected={language}")
    if case["answerable"]:
        add("did_not_refuse", not citation["refused"], answer[:160])
        projects = {source["project"] for source in payload["sources"]}
        add(
            "expected_project_retrieved",
            case["expected_project"] in projects,
            f"retrieved_projects={sorted(projects)}",
        )
        for required in case.get("required_all", []):
            add(f"contains:{required}", required.lower() in answer.lower(), answer[:200])
        alternatives = case.get("required_any", [])
        if alternatives:
            add(
                "contains_expected_meaning_marker",
                any(term.lower() in answer.lower() for term in alternatives),
                f"accepted={alternatives}",
            )
    else:
        add("exact_refusal", answer.strip() == REFUSAL, answer)

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def write_results(markdown_path: Path, json_path: Path, payload: dict) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Phase 3：本地 RAG 评测",
        "",
        f"- 测试：{payload['passed_cases']}/{payload['case_count']} 自动检查通过",
        f"- 全部测试墙钟时间：{payload['wall_seconds']:.3f} 秒",
        "",
        "自动检查只能验证关键事实标记、拒答句式和引用编号；最终语义质量仍需人工阅读。",
        "",
    ]
    for result in payload["results"]:
        case = result["case"]
        run = result["run"]
        assessment = result["assessment"]
        lines.extend(
            [
                f"## {case['id']}（{case['language']}）— {'PASS' if assessment['passed'] else 'FAIL'}",
                "",
                f"问题：{case['question']}",
                "",
                "回答：",
                "",
                run["answer"],
                "",
                "来源：",
                "",
            ]
        )
        for source in run["sources"]:
            line_range = (
                str(source["start_line"])
                if source["start_line"] == source["end_line"]
                else f"{source['start_line']}-{source['end_line']}"
            )
            lines.append(
                f"- [{source['id']}] `{source['path']}:{line_range}` — "
                f"{source['heading']}（{source['score']:.4f}）"
            )
        lines.extend(["", "检查：", ""])
        for check in assessment["checks"]:
            lines.append(
                f"- {'PASS' if check['passed'] else 'FAIL'} `{check['name']}`：{check['detail']}"
            )
        lines.extend(
            [
                "",
                f"时间：检索 {run['timings']['retrieval_seconds']:.3f} 秒；"
                f"问答模型 {run['timings']['generation_process_seconds']:.3f} 秒；"
                f"合计 {run['timings']['total_seconds']:.3f} 秒。",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local grounded RAG answers")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--embedding-binary", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--generator-binary", type=Path, required=True)
    parser.add_argument("--generator-model", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    index = load_index(args.index)
    is_fresh, freshness_message = freshness(args.index, index)
    if not is_fresh:
        raise SystemExit(f"Index is stale: {freshness_message}")
    cases = read_jsonl(args.queries)
    started = time.perf_counter()
    results = []
    for number, case in enumerate(cases, start=1):
        print(f"[{number}/{len(cases)}] {case['id']} {case['question']}", flush=True)
        run = answer_question(
            question=case["question"],
            index=index,
            embedding_binary=args.embedding_binary,
            embedding_model=args.embedding_model,
            generator_binary=args.generator_binary,
            generator_model=args.generator_model,
        )
        assessment = assess(case, run)
        results.append({"case": case, "run": run, "assessment": assessment})
        print(
            f"  {'PASS' if assessment['passed'] else 'FAIL'} · "
            f"检索 {run['timings']['retrieval_seconds']:.3f}s · "
            f"问答 {run['timings']['generation_process_seconds']:.3f}s"
        )
        print(f"  {run['answer']}", flush=True)

    wall_seconds = time.perf_counter() - started
    passed_cases = sum(result["assessment"]["passed"] for result in results)
    payload = {
        "model": "Qwen3-4B-Instruct-2507 Q8_0",
        "case_count": len(cases),
        "passed_cases": passed_cases,
        "wall_seconds": wall_seconds,
        "results": results,
    }
    write_results(args.markdown_output, args.json_output, payload)
    print(f"\nPhase 3: {passed_cases}/{len(cases)} cases passed in {wall_seconds:.3f}s")
    print(f"结果：{args.markdown_output}")


if __name__ == "__main__":
    main()
