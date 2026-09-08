#!/usr/bin/env python3

"""Build a persistent semantic index from selected AI-Lab Markdown files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from embedding_runtime import embed_texts


CURRENT_PROJECT = "qwen3-embedding-0.6b-llamacpp"
GENERATED_ANSWERS = {
    "qwen3-14b-llamacpp/results/offline-pdf-demo.md",
    "qwen3-14b-llamacpp/results/rag-last-answer.md",
    "qwen3-14b-llamacpp/results/rag-pdf-demo-answer.md",
}
PRUNED_DIRECTORIES = {".git", "worktrees", "__pycache__", ".venv", "node_modules"}
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify(relative: Path) -> tuple[bool, str]:
    parts = relative.parts
    posix = relative.as_posix()
    if any(part in {"tests", "test", "fixtures"} for part in parts):
        return False, "test-or-fixture"
    if posix in GENERATED_ANSWERS:
        return False, "model-generated-answer"
    if parts and parts[0] == CURRENT_PROJECT and "results" in parts:
        return False, "current-project-result"
    if relative == Path("README.md"):
        return True, "lab-readme"
    if len(parts) == 2 and parts[1] == "README.md":
        return True, "project-readme"
    if "docs" in parts:
        return True, "documentation"
    if "results" in parts:
        return True, "research-result"
    return False, "outside-scope"


def discover_markdown(root: Path) -> tuple[list[Path], list[dict]]:
    included: list[Path] = []
    excluded: list[dict] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in PRUNED_DIRECTORIES)
        directory_path = Path(directory)
        for filename in sorted(filenames):
            if not filename.lower().endswith(".md"):
                continue
            path = directory_path / filename
            relative = path.relative_to(root)
            use, reason = classify(relative)
            if use:
                included.append(path)
            else:
                excluded.append({"path": relative.as_posix(), "reason": reason})
    return sorted(included), sorted(excluded, key=lambda row: row["path"])


def split_long_paragraph(
    paragraph: list[tuple[int, str]], max_chars: int
) -> list[list[tuple[int, str]]]:
    groups: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    length = 0
    for line_number, line in paragraph:
        if len(line) > max_chars:
            if current:
                groups.append(current)
                current = []
                length = 0
            for offset in range(0, len(line), max_chars):
                groups.append([(line_number, line[offset : offset + max_chars])])
            continue
        added = len(line) + (1 if current else 0)
        if current and length + added > max_chars:
            groups.append(current)
            current = []
            length = 0
        current.append((line_number, line))
        length += len(line) + (1 if len(current) > 1 else 0)
    if current:
        groups.append(current)
    return groups


def pack_section(
    lines: list[tuple[int, str]], max_chars: int
) -> list[tuple[int, int, str]]:
    paragraphs: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for numbered_line in lines:
        if numbered_line[1].strip():
            current.append(numbered_line)
        elif current:
            paragraphs.extend(split_long_paragraph(current, max_chars))
            current = []
    if current:
        paragraphs.extend(split_long_paragraph(current, max_chars))

    chunks: list[tuple[int, int, str]] = []
    packed: list[tuple[int, str]] = []
    length = 0
    for paragraph in paragraphs:
        text = "\n".join(line for _, line in paragraph).strip()
        if not text:
            continue
        added = len(text) + (2 if packed else 0)
        if packed and length + added > max_chars:
            chunks.append(
                (packed[0][0], packed[-1][0], "\n".join(line for _, line in packed).strip())
            )
            packed = []
            length = 0
        if packed:
            packed.append((paragraph[0][0], ""))
            length += 1
        packed.extend(paragraph)
        length += len(text) + (1 if packed else 0)
    if packed:
        chunks.append(
            (packed[0][0], packed[-1][0], "\n".join(line for _, line in packed).strip())
        )
    return chunks


def markdown_chunks(path: Path, root: Path, max_chars: int) -> list[dict]:
    relative = path.relative_to(root).as_posix()
    project = relative.split("/", 1)[0] if "/" in relative else "AI-Lab"
    text = path.read_text(encoding="utf-8", errors="replace")
    heading_stack: list[str] = []
    section_heading = path.stem
    section_lines: list[tuple[int, str]] = []
    sections: list[tuple[str, list[tuple[int, str]]]] = []
    fence_marker: str | None = None

    def flush() -> None:
        nonlocal section_lines
        if any(line.strip() for _, line in section_lines):
            sections.append((section_heading, section_lines))
        section_lines = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if fence_marker is None:
                fence_marker = marker
            elif fence_marker == marker:
                fence_marker = None
            section_lines.append((line_number, line))
            continue
        match = HEADING.match(line) if fence_marker is None else None
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
            section_heading = " > ".join(heading_stack)
        else:
            section_lines.append((line_number, line))
    flush()

    chunks: list[dict] = []
    for heading, lines in sections:
        for start_line, end_line, body in pack_section(lines, max_chars):
            if len(body.strip()) < 20:
                continue
            stable = f"{relative}\0{heading}\0{start_line}\0{end_line}".encode()
            chunks.append(
                {
                    "id": hashlib.sha1(stable).hexdigest()[:16],
                    "project": project,
                    "path": relative,
                    "heading": heading,
                    "start_line": start_line,
                    "end_line": end_line,
                    "text": body,
                    "embedding_text": (
                        f"Project: {project}\nFile: {relative}\nSection: {heading}\n{body}"
                    ),
                }
            )
    return chunks


def git_version(binary: Path) -> str:
    completed = subprocess.run(
        [str(binary), "--version"], check=False, capture_output=True, text=True
    )
    return (completed.stdout + completed.stderr).strip().replace("\n", " | ")


def write_json_atomic(path: Path, payload: object, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if compact:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    temporary.write_text(serialized + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local AI-Lab vector index")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--index-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--max-chars", type=int, default=1400)
    parser.add_argument("--prompt-batch", type=int, default=12)
    args = parser.parse_args()

    for label, path in (("source root", args.source_root), ("binary", args.binary), ("model", args.model)):
        if not path.exists():
            raise SystemExit(f"Missing {label}: {path}")
    if args.max_chars < 200:
        raise SystemExit("--max-chars must be at least 200")

    files, excluded = discover_markdown(args.source_root)
    if not files:
        raise SystemExit("No Markdown files matched the index scope")

    file_rows = []
    chunks: list[dict] = []
    for path in files:
        raw = path.read_bytes()
        relative = path.relative_to(args.source_root).as_posix()
        file_chunks = markdown_chunks(path, args.source_root, args.max_chars)
        file_rows.append(
            {
                "path": relative,
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
                "chunks": len(file_chunks),
            }
        )
        chunks.extend(file_chunks)

    if not chunks:
        raise SystemExit("Selected Markdown files produced no non-empty chunks")

    print(f"发现 {len(files)} 个研究文档，切成 {len(chunks)} 个段落。", flush=True)

    def progress(done: int, total: int, elapsed: float) -> None:
        print(f"向量进度 {done}/{total}（本批 {elapsed:.2f} 秒）", flush=True)

    vectors, embedding_seconds, invocations = embed_texts(
        args.binary,
        args.model,
        [chunk.pop("embedding_text") for chunk in chunks],
        prompt_batch=args.prompt_batch,
        batch_size=2048,
        progress=progress,
    )
    for chunk, vector in zip(chunks, vectors):
        chunk["vector"] = vector

    now = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    manifest = {
        "schema_version": 1,
        "created_at": now,
        "source_root": str(args.source_root),
        "scope": "AI-Lab README files plus docs/**/*.md and results/**/*.md",
        "included_files": file_rows,
        "excluded_markdown": excluded,
        "included_file_count": len(file_rows),
        "excluded_file_count": len(excluded),
        "chunk_count": len(chunks),
    }
    manifest_digest = sha256_bytes(
        json.dumps(file_rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    index = {
        "schema_version": 1,
        "created_at": now,
        "source_root": str(args.source_root),
        "manifest_sha256": manifest_digest,
        "model": "Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
        "model_path": str(args.model),
        "pooling": "last",
        "normalization": "L2",
        "dimension": len(vectors[0]),
        "max_chunk_chars": args.max_chars,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "embedding_seconds": embedding_seconds,
        "embedding_invocations": invocations,
        "llama_embedding_version": git_version(args.binary),
        "chunks": chunks,
    }
    write_json_atomic(args.manifest_output, manifest)
    write_json_atomic(args.index_output, index, compact=True)
    print(
        f"索引完成：{len(files)} 个文件，{len(chunks)} 个段落，"
        f"向量计算 {embedding_seconds:.2f} 秒，维度 {len(vectors[0])}。"
    )
    print(f"索引：{args.index_output}")
    print(f"清单：{args.manifest_output}")


if __name__ == "__main__":
    main()
