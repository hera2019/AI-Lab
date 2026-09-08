#!/usr/bin/env python3

"""Small, dependency-free wrapper around llama-embedding."""

from __future__ import annotations

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Callable


SEPARATOR = "<#qwen3EmbeddingSeparator#>"


def query_text(query: str) -> str:
    task = (
        "Given a search query, retrieve relevant passages from a local AI "
        "experiment notebook that answer the query"
    )
    return f"Instruct: {task}\nQuery: {query.strip()}"


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"Vector dimensions differ: {len(left)} != {len(right)}")
    return sum(a * b for a, b in zip(left, right))


def _extract_vectors(stdout: str, stderr: str) -> list[list[float]]:
    candidates = [
        line.strip()
        for stream in (stdout, stderr)
        for line in stream.splitlines()
        if line.lstrip().startswith("[[") and line.rstrip().endswith("]]" )
    ]
    if not candidates:
        detail = (stderr or stdout)[-3000:]
        raise RuntimeError(
            "llama-embedding returned success but emitted no embedding array.\n" + detail
        )
    try:
        vectors = json.loads(max(candidates, key=len))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Could not parse llama-embedding JSON output") from exc
    if not isinstance(vectors, list) or not vectors:
        raise RuntimeError("Embedding output is empty")
    return vectors


def _run_once(
    binary: Path,
    model: Path,
    texts: list[str],
    batch_size: int,
) -> tuple[list[list[float]], float]:
    if not texts:
        return [], 0.0
    if any(SEPARATOR in text for text in texts):
        raise ValueError("Input unexpectedly contains the embedding separator")

    command = [
        str(binary),
        "--model",
        str(model),
        "--prompt",
        SEPARATOR.join(texts),
        "--pooling",
        "last",
        "--embd-normalize",
        "2",
        "--embd-output-format",
        "array",
        "--embd-separator",
        SEPARATOR,
        "--n-gpu-layers",
        "all",
        "--batch-size",
        str(batch_size),
        "--ubatch-size",
        str(batch_size),
        "--threads",
        "8",
        "--no-warmup",
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"llama-embedding failed with exit code {completed.returncode}:\n"
            + completed.stderr[-4000:]
        )

    vectors = _extract_vectors(completed.stdout, completed.stderr)
    if len(vectors) != len(texts):
        raise RuntimeError(f"Expected {len(texts)} vectors, received {len(vectors)}")
    dimension = len(vectors[0])
    if dimension == 0 or any(len(vector) != dimension for vector in vectors):
        raise RuntimeError("Embedding vectors have inconsistent dimensions")
    for vector in vectors:
        if any(not math.isfinite(value) for value in vector):
            raise RuntimeError("Embedding vector contains NaN or infinity")
        norm = math.sqrt(sum(value * value for value in vector))
        if not 0.99 <= norm <= 1.01:
            raise RuntimeError(f"Embedding vector is not L2-normalized: norm={norm}")
    return vectors, elapsed


def embed_texts(
    binary: Path,
    model: Path,
    texts: list[str],
    *,
    prompt_batch: int = 12,
    batch_size: int = 2048,
    progress: Callable[[int, int, float], None] | None = None,
) -> tuple[list[list[float]], float, int]:
    """Embed texts in bounded groups, returning vectors, elapsed time and calls."""

    if prompt_batch < 1:
        raise ValueError("prompt_batch must be positive")
    all_vectors: list[list[float]] = []
    total_elapsed = 0.0
    calls = 0
    for start in range(0, len(texts), prompt_batch):
        group = texts[start : start + prompt_batch]
        vectors, elapsed = _run_once(binary, model, group, batch_size)
        all_vectors.extend(vectors)
        total_elapsed += elapsed
        calls += 1
        if progress:
            progress(len(all_vectors), len(texts), elapsed)
    return all_vectors, total_elapsed, calls
