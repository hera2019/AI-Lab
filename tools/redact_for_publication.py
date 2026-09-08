#!/usr/bin/env python3

"""公开前脱敏：移除本机绝对路径与本人录音逐字稿。

设计原则
--------
1. 只做**可复现**的机械替换，不做人工判断——判断留在审计报告里。
2. **不破坏可运行性**：脚本中的路径替换为等价表达式，而非占位符。
3. **不破坏可验证性**：所有性能数字、SHA-256、时长等一律保留。
4. **幂等**：重复运行结果不变。

三类处理
--------
路径 · 脚本 (.py)   "/Users/X/REST"  ->  str(Path.home() / "REST")
路径 · 脚本 (.sh)   /Users/X/        ->  $HOME/
路径 · 记录 (.md/.json/.log/.txt/.csv)
                    /Users/X         ->  ~

内容 · 本人录音逐字稿
    JSON 中的 reference_text / target_text 替换为特征描述，
    并加 text_redacted 标记说明原因。分析所需的片段保留在对应的 .md 报告中。

用法
----
    python3 tools/redact_for_publication.py --check    # 只报告，不改
    python3 tools/redact_for_publication.py --apply    # 实际修改
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 本机用户目录前缀。用运行时的 home 推导，不写死任何人的用户名。
HOME_PREFIX = str(Path.home())

SCRIPT_EXT = {".py", ".sh"}
RECORD_EXT = {".md", ".json", ".log", ".txt", ".csv"}

SKIP_DIRS = {
    ".git", "worktrees", "build", ".cache", ".venv", "venv",
    "__pycache__", ".pnpm-store", "node_modules", "private",
}

# 本脚本自身不参与脱敏（它必须保留 Path.home() 的字面写法）
SELF = Path(__file__).resolve()

# 逐字稿脱敏目标：本人录音的完整文字内容
TRANSCRIPT_KEYS = ("reference_text", "target_text")


def ignored_by_git(paths: list[Path]) -> set[Path]:
    """用 git 的忽略规则判定，保证「只脱敏会被发布的文件」。

    没有 git 或不在仓库中时返回空集合，退回为「全部处理」。
    """
    if not paths:
        return set()
    rels = [str(p.relative_to(REPO)) for p in paths]
    try:
        r = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=REPO, input="\n".join(rels),
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return set()
    if r.returncode not in (0, 1):
        return set()
    return {REPO / line for line in r.stdout.splitlines() if line}


def iter_files():
    candidates = []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(REPO).parts):
            continue
        if p.resolve() == SELF:
            continue
        if p.suffix in SCRIPT_EXT or p.suffix in RECORD_EXT:
            candidates.append(p)
    ignored = ignored_by_git(candidates)
    for p in candidates:
        if p not in ignored:
            yield p


def redact_python(text: str) -> tuple[str, int]:
    """字符串字面量 -> str(Path.home() / "...")，在任何表达式位置都合法。"""
    pattern = re.compile(r'"' + re.escape(HOME_PREFIX) + r'/([^"\n]*)"')
    n = len(pattern.findall(text))
    return pattern.sub(lambda m: f'str(Path.home() / "{m.group(1)}")', text), n


def repair_implicit_concat(text: str) -> tuple[str, int]:
    """修复被打断的隐式字符串拼接。

    Python 允许 "a" "b" 自动拼接，但 str(...) "b" 是语法错误。
    脱敏把前一段字面量换成了表达式，因此需要补回显式的 + 号。
    """
    pattern = re.compile(
        r'(str\(Path\.home\(\) / "[^"\n]*"\))(\s*\n\s*)(")'
    )
    n = 0
    while True:
        text, k = pattern.subn(r"\1\2+ \3", text, count=1)
        if not k:
            break
        n += 1
    return text, n


def redact_shell(text: str) -> tuple[str, int]:
    n = text.count(HOME_PREFIX + "/")
    return text.replace(HOME_PREFIX + "/", "$HOME/"), n


def redact_record(text: str) -> tuple[str, int]:
    n = text.count(HOME_PREFIX)
    return text.replace(HOME_PREFIX, "~"), n


def redact_transcripts(path: Path, text: str) -> tuple[str, int]:
    """把 JSON 里本人录音的逐字稿换成特征描述，保留全部客观指标。"""
    if path.suffix != ".json":
        return text, 0
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text, 0
    if not isinstance(data, dict) or data.get("text_redacted"):
        return text, 0

    n = 0
    for key in TRANSCRIPT_KEYS:
        val = data.get(key)
        if isinstance(val, str) and len(val) > 40:
            han = len(re.findall(r"[一-鿿]", val))
            data[key] = (
                f"[已脱敏] 本人录音逐字稿，{han} 个汉字 / {len(val)} 字符。"
                f"原文仅保存在本机 private/，不进入公开仓库。"
            )
            n += 1
    if n:
        data["text_redacted"] = (
            "reference_text / target_text 为本人录音的完整逐字稿，公开前已替换为特征描述。"
            "全部客观指标（时长、采样率、RTF、内存、seed、SHA-256）均未改动。"
            "分析所需的文本片段保留在同目录的 .md 报告中。"
        )
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n", n
    return text, 0


def main() -> int:
    ap = argparse.ArgumentParser(description="公开前脱敏")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="只报告，不修改")
    g.add_argument("--apply", action="store_true", help="实际修改")
    args = ap.parse_args()

    totals = {"path": 0, "transcript": 0, "files": 0}
    missing_pathlib: list[str] = []

    for path in sorted(iter_files()):
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        text, n_path = original, 0
        if HOME_PREFIX in text:
            if path.suffix == ".py":
                text, n_path = redact_python(text)
                if n_path and "from pathlib import Path" not in text:
                    missing_pathlib.append(str(path.relative_to(REPO)))
            elif path.suffix == ".sh":
                text, n_path = redact_shell(text)
            else:
                text, n_path = redact_record(text)

        # 已脱敏过的 .py 也要检查拼接是否完好（幂等修复）
        n_fix = 0
        if path.suffix == ".py":
            text, n_fix = repair_implicit_concat(text)

        text, n_tr = redact_transcripts(path, text)

        if text != original:
            totals["files"] += 1
            totals["path"] += n_path
            totals["transcript"] += n_tr
            rel = path.relative_to(REPO)
            bits = []
            if n_path:
                bits.append(f"路径×{n_path}")
            if n_fix:
                bits.append(f"拼接修复×{n_fix}")
            if n_tr:
                bits.append(f"逐字稿×{n_tr}")
            print(f"  {rel}  ({', '.join(bits)})")
            if args.apply:
                path.write_text(text, encoding="utf-8")

    verb = "将修改" if args.check else "已修改"
    print(f"\n{verb} {totals['files']} 个文件："
          f"绝对路径 {totals['path']} 处，逐字稿 {totals['transcript']} 处")

    if missing_pathlib:
        print("\n⚠ 以下 .py 使用了 Path.home() 但未 import Path，需手动补：")
        for m in missing_pathlib:
            print(f"    {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
