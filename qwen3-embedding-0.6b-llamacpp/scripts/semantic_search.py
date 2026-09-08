#!/usr/bin/env python3

import argparse
import json
import subprocess
import time
from pathlib import Path


TASK = "Given a search query, retrieve relevant passages from a local AI experiment notebook that answer the query"
SEPARATOR = "<#qwen3EmbeddingSeparator#>"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON in {path} line {line_number}: {exc}") from exc
    return rows


def query_text(query: str) -> str:
    return f"Instruct: {TASK}\nQuery: {query}"


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def run_embeddings(binary: Path, model: Path, texts: list[str]) -> tuple[list[list[float]], float]:
    if any(SEPARATOR in text for text in texts):
        raise SystemExit("Input unexpectedly contains the embedding separator")

    command = [
        str(binary),
        "--model", str(model),
        "--prompt", SEPARATOR.join(texts),
        "--pooling", "last",
        "--embd-normalize", "2",
        "--embd-output-format", "array",
        "--embd-separator", SEPARATOR,
        "--n-gpu-layers", "all",
        "--batch-size", "256",
        "--ubatch-size", "256",
        "--no-warmup",
    ]

    started = time.perf_counter()
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise SystemExit(
            f"llama-embedding failed with exit code {completed.returncode}:\n{completed.stderr[-4000:]}"
        )

    # Current llama-embedding writes both diagnostic logs and the requested
    # embedding array through its logging stream (stderr on macOS). Extract the
    # one complete JSON-array line instead of assuming it is on stdout.
    json_lines = [
        line.strip()
        for stream in (completed.stdout, completed.stderr)
        for line in stream.splitlines()
        if line.lstrip().startswith("[[") and line.rstrip().endswith("]]" )
    ]
    if not json_lines:
        raise SystemExit(
            "llama-embedding returned success but did not emit an embedding array.\n"
            + (completed.stderr[-2000:] or completed.stdout[-2000:])
        )
    try:
        vectors = json.loads(max(json_lines, key=len))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse llama-embedding output: {max(json_lines, key=len)[:1000]}") from exc

    if len(vectors) != len(texts):
        raise SystemExit(f"Expected {len(texts)} vectors, received {len(vectors)}")
    if not vectors or not all(len(vector) == len(vectors[0]) for vector in vectors):
        raise SystemExit("Embedding vectors are empty or have inconsistent dimensions")
    return vectors, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multilingual semantic-search demonstration")
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--passages", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--include-title", action="store_true")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    passages = read_jsonl(args.passages)
    queries = read_jsonl(args.queries)
    passage_texts = [
        f"{row['title']}\n{row['text']}" if args.include_title else row["text"]
        for row in passages
    ]
    texts = passage_texts + [query_text(row["query"]) for row in queries]
    vectors, elapsed = run_embeddings(args.binary, args.model, texts)

    passage_vectors = vectors[: len(passages)]
    query_vectors = vectors[len(passages) :]
    results = []
    correct_at_1 = 0
    correct_at_3 = 0

    for query, vector in zip(queries, query_vectors):
        ranked = sorted(
            (
                {
                    "rank": 0,
                    "id": passage["id"],
                    "title": passage["title"],
                    "score": cosine(vector, passage_vector),
                    "text": passage["text"],
                }
                for passage, passage_vector in zip(passages, passage_vectors)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank

        expected_rank = next(item["rank"] for item in ranked if item["id"] == query["expected"])
        correct_at_1 += expected_rank == 1
        correct_at_3 += expected_rank <= 3
        results.append({**query, "expected_rank": expected_rank, "top3": ranked[:3]})

    payload = {
        "model": "Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
        "pooling": "last",
        "normalization": "euclidean",
        "passage_input": "title + body" if args.include_title else "body only",
        "dimension": len(vectors[0]),
        "passage_count": len(passages),
        "query_count": len(queries),
        "embedding_seconds": elapsed,
        "correct_at_1": correct_at_1,
        "correct_at_3": correct_at_3,
        "results": results,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Phase 1：多语言语义检索结果",
        "",
        f"- 文档块：{len(passages)}",
        f"- 查询：{len(queries)}",
        f"- 向量维度：{len(vectors[0])}",
        f"- 文档输入：{'标题 + 正文' if args.include_title else '仅正文'}",
        f"- 一次加载并计算全部向量：{elapsed:.3f} 秒",
        f"- Recall@1：{correct_at_1}/{len(queries)}",
        f"- Recall@3：{correct_at_3}/{len(queries)}",
        "",
        "相似度只用于同一查询下的相对排序，不是正确概率。查询使用英文检索任务指令，文档块不加指令。",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result['id']}（{result['language']}）",
                "",
                f"问题：{result['query']}",
                "",
                f"预期文档：`{result['expected']}`；实际排名：{result['expected_rank']}",
                "",
                "| 排名 | 相似度 | 文档 |",
                "| ---: | ---: | --- |",
            ]
        )
        for item in result["top3"]:
            marker = " ✅" if item["id"] == result["expected"] else ""
            lines.append(f"| {item['rank']} | {item['score']:.4f} | {item['title']} (`{item['id']}`){marker} |")
        lines.append("")

    args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("🧭 多语言语义检索")
    input_label = "标题 + 正文" if args.include_title else "仅正文"
    print(f"文档块 {len(passages)} 个 · 查询 {len(queries)} 个 · 向量 {len(vectors[0])} 维 · {input_label}")
    print(f"全部向量计算耗时 {elapsed:.3f} 秒")
    print(f"Recall@1 {correct_at_1}/{len(queries)} · Recall@3 {correct_at_3}/{len(queries)}")
    for result in results:
        print("\n" + "─" * 64)
        print(f"{result['id']} [{result['language']}] {result['query']}")
        for item in result["top3"]:
            marker = "✓" if item["id"] == result["expected"] else " "
            print(f"  {item['rank']}. {item['score']:.4f} {marker} {item['title']} [{item['id']}]")
    print(f"\n结果：{args.markdown_output}")


if __name__ == "__main__":
    main()
