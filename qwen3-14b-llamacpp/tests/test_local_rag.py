#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from local_rag import Chunk, chunk_lines, rank_chunks  # noqa: E402


class LocalRagTests(unittest.TestCase):
    def test_chinese_and_technical_terms_retrieve_relevant_chunk(self):
        chunks = [
            Chunk("a.md", "lines 1-2", "今天讨论苹果和晚餐。"),
            Chunk("b.md", "lines 8-12", "Q8_0 相比 F16 节省约 1.17 GiB 内存。"),
            Chunk("c.md", "lines 2-3", "Metal 负责使用 Apple GPU 加速计算。"),
        ]
        ranked = rank_chunks("Q8_0 比 F16 节省多少内存？", chunks, 2)
        self.assertEqual(ranked[0].chunk.path, "b.md")

    def test_chunk_overlap_keeps_context(self):
        lines = ["甲" * 40, "关键事实" * 8, "乙" * 40, "结尾"]
        chunks = chunk_lines(lines, "note.md", "", max_chars=100, overlap_chars=20)
        self.assertGreaterEqual(len(chunks), 2)
        matches = [chunk for chunk in chunks if "关键事实" in chunk.text]
        self.assertGreaterEqual(len(matches), 2)


if __name__ == "__main__":
    unittest.main()
