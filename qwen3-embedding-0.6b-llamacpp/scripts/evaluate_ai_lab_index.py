#!/usr/bin/env python3

"""Evaluate multilingual, cross-project retrieval against the real AI-Lab index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from embedding_runtime import cosine, embed_texts, query_text


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


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the real AI-Lab vector index")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    index = json.loads(args.index.read_text(encoding="utf-8"))
    queries = read_jsonl(args.queries)
    vectors, elapsed, invocations = embed_texts(
        args.binary,
        args.model,
        [query_text(row["query"]) for row in queries],
        prompt_batch=len(queries),
        batch_size=2048,
    )

    results = []
    project_at_1 = 0
    project_at_3 = 0
    preferred_at_3 = 0
    for query, vector in zip(queries, vectors):
        ranked = sorted(
            (
                {
                    "score": cosine(vector, chunk["vector"]),
                    "project": chunk["project"],
                    "path": chunk["path"],
                    "heading": chunk["heading"],
                    "start_line": chunk["start_line"],
                }
                for chunk in index["chunks"]
            ),
            key=lambda row: row["score"],
            reverse=True,
        )
        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank

        project_rank = next(
            (item["rank"] for item in ranked if item["project"] == query["expected_project"]),
            None,
        )
        preferred_rank = next(
            (item["rank"] for item in ranked if item["path"] == query["preferred_path"]),
            None,
        )
        project_at_1 += project_rank == 1
        project_at_3 += project_rank is not None and project_rank <= 3
        preferred_at_3 += preferred_rank is not None and preferred_rank <= 3
        results.append(
            {
                **query,
                "project_rank": project_rank,
                "preferred_file_rank": preferred_rank,
                "top5": ranked[:5],
            }
        )

    payload = {
        "model": index["model"],
        "index_created_at": index["created_at"],
        "file_count": index["file_count"],
        "chunk_count": index["chunk_count"],
        "query_count": len(queries),
        "query_embedding_seconds": elapsed,
        "embedding_invocations": invocations,
        "project_recall_at_1": project_at_1,
        "project_recall_at_3": project_at_3,
        "preferred_file_recall_at_3": preferred_at_3,
        "results": results,
    }
    write_json(args.json_output, payload)

    lines = [
        "# Phase 2：真实 AI-Lab 文档检索评测",
        "",
        f"- 索引文件：{index['file_count']} 个",
        f"- 索引段落：{index['chunk_count']} 个",
        f"- 查询：{len(queries)} 个（中文、日文、英文）",
        f"- 查询向量计算：{elapsed:.3f} 秒",
        f"- 正确项目 Recall@1：{project_at_1}/{len(queries)}",
        f"- 正确项目 Recall@3：{project_at_3}/{len(queries)}",
        f"- 首选原始报告 Recall@3：{preferred_at_3}/{len(queries)}",
        "",
        "“正确项目”用于判断是否找到正确实验；“首选原始报告”要求命中记录该事实的详细报告。",
        "相似度是同一问题下的相对排序信号，不是正确概率。",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result['id']}（{result['language']}）",
                "",
                f"问题：{result['query']}",
                "",
                f"正确项目排名：{result['project_rank']}；首选报告排名：{result['preferred_file_rank']}",
                "",
                "| 排名 | 相似度 | 项目 | 来源 | 章节 |",
                "| ---: | ---: | --- | --- | --- |",
            ]
        )
        for item in result["top5"]:
            marker = " ✅" if item["path"] == result["preferred_path"] else ""
            lines.append(
                f"| {item['rank']} | {item['score']:.4f} | {item['project']} | "
                f"`{item['path']}:{item['start_line']}`{marker} | {item['heading']} |"
            )
        lines.append("")
    args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("🧪 Phase 2 跨项目检索评测")
    print(
        f"文件 {index['file_count']} · 段落 {index['chunk_count']} · "
        f"查询 {len(queries)} · 查询向量 {elapsed:.3f} 秒"
    )
    print(
        f"正确项目 Recall@1 {project_at_1}/{len(queries)} · "
        f"Recall@3 {project_at_3}/{len(queries)} · "
        f"首选报告 Recall@3 {preferred_at_3}/{len(queries)}"
    )
    for result in results:
        first = result["top5"][0]
        print(
            f"{result['id']} [{result['language']}] project_rank={result['project_rank']} "
            f"preferred_rank={result['preferred_file_rank']} · top1={first['path']}"
        )
    print(f"结果：{args.markdown_output}")


if __name__ == "__main__":
    main()
