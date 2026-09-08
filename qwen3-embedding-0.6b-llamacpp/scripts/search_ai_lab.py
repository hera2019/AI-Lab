#!/usr/bin/env python3

"""Search the persistent AI-Lab vector index from the command line."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_ai_lab_index import discover_markdown
from embedding_runtime import cosine, embed_texts, query_text


def load_index(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"找不到索引，请先运行构建脚本：{path}") from exc
    if not payload.get("chunks"):
        raise SystemExit(f"索引没有可搜索的段落：{path}")
    return payload


def preview(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"


def freshness(index_path: Path, index: dict) -> tuple[bool, str]:
    manifest_path = index_path.parent / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False, "找不到有效的 index/manifest.json"

    root = Path(index["source_root"])
    files, _ = discover_markdown(root)
    expected = {row["path"]: row for row in manifest["included_files"]}
    current_paths = {path.relative_to(root).as_posix() for path in files}
    if current_paths != set(expected):
        return False, "纳入范围中的文件已增加或删除"
    for path in files:
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        if len(raw) != expected[relative]["bytes"]:
            return False, f"文件大小已变化：{relative}"
        if hashlib.sha256(raw).hexdigest() != expected[relative]["sha256"]:
            return False, f"文件内容已变化：{relative}"
    return True, "资料与索引清单一致"


def search(index: dict, query_vector: list[float], top_k: int) -> list[dict]:
    ranked = sorted(
        (
            {
                "score": cosine(query_vector, chunk["vector"]),
                "project": chunk["project"],
                "path": chunk["path"],
                "heading": chunk["heading"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "text": chunk["text"],
            }
            for chunk in index["chunks"]
        ),
        key=lambda row: row["score"],
        reverse=True,
    )
    return ranked[:top_k]


def print_results(query: str, results: list[dict], elapsed: float) -> None:
    print("\n" + "═" * 72)
    print(f"问题：{query}")
    print(f"检索耗时：{elapsed:.3f} 秒")
    for rank, row in enumerate(results, start=1):
        line_range = (
            str(row["start_line"])
            if row["start_line"] == row["end_line"]
            else f"{row['start_line']}-{row['end_line']}"
        )
        print("\n" + "─" * 72)
        print(f"{rank}. 相似度 {row['score']:.4f} · {row['project']}")
        print(f"   {row['path']}:{line_range}")
        print(f"   章节：{row['heading']}")
        print(f"   {preview(row['text'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the local AI-Lab research index")
    parser.add_argument("query", nargs="*", help="问题；不填写时进入连续提问模式")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    index = load_index(args.index)
    model = args.model or Path(index["model_path"])
    for label, path in (("llama-embedding", args.binary), ("模型", model)):
        if not path.exists():
            raise SystemExit(f"找不到{label}：{path}")
    if args.top_k < 1:
        raise SystemExit("--top-k 必须大于 0")

    print(
        f"🔎 AI-Lab 本地语义搜索 · {index['file_count']} 个文件 · "
        f"{index['chunk_count']} 个段落"
    )
    is_fresh, freshness_message = freshness(args.index, index)
    if is_fresh:
        print(f"索引状态：{freshness_message}")
    else:
        print(f"⚠️ 索引可能已过期：{freshness_message}")
        print("请运行 scripts/run_phase_2.sh 后再搜索最新资料。")
    print("相似度用于排序，不是答案正确概率。输入 q 退出。")

    initial = " ".join(args.query).strip()
    pending = [initial] if initial else []
    while True:
        if pending:
            query = pending.pop(0)
        else:
            try:
                query = input("\n你想找什么？ ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n已结束。")
                return
        if not query:
            if initial:
                return
            continue
        if query.lower() in {"q", "quit", "exit"}:
            print("已结束。")
            return

        vectors, elapsed, _ = embed_texts(
            args.binary, model, [query_text(query)], prompt_batch=1, batch_size=2048
        )
        print_results(query, search(index, vectors[0], args.top_k), elapsed)
        if initial:
            return


if __name__ == "__main__":
    main()
