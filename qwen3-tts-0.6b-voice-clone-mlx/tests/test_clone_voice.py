#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from clone_voice import resolve_text, standard_rtf
from record_reference import dbfs


class VoiceCloneMetricTests(unittest.TestCase):
    def test_standard_rtf_below_one_is_faster_than_realtime(self) -> None:
        self.assertAlmostEqual(standard_rtf(2.0, 5.0), 0.4)

    def test_standard_rtf_rejects_empty_audio(self) -> None:
        with self.assertRaises(ValueError):
            standard_rtf(1.0, 0.0)

    def test_dbfs(self) -> None:
        self.assertAlmostEqual(dbfs(1.0), 0.0)
        self.assertAlmostEqual(dbfs(0.5), -6.0206, places=3)
        self.assertEqual(dbfs(0.0), float("-inf"))

    def test_resolve_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            text_file = Path(temp_dir) / "transcript.txt"
            text_file.write_text("  测试文字。\n", encoding="utf-8")
            self.assertEqual(resolve_text(None, text_file, "Text"), "测试文字。")

    def test_resolve_text_rejects_empty_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "Target text must not be empty"):
            resolve_text("  ", None, "Target text")


if __name__ == "__main__":
    unittest.main()
