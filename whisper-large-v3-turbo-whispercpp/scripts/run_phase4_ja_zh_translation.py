#!/usr/bin/env python3
"""Benchmark Japanese speech transcription and optional local Chinese translation."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO = PROJECT_DIR / "tests/fixtures/audio/asr-ja-001.wav"
DEFAULT_WHISPER_CLI = (
    PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-cli"
)
DEFAULT_WHISPER_MODEL = Path(
    str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin")
)
DEFAULT_LLAMA_CLI = Path(
    str(Path.home() / "Documents/AI-Lab/qwen3-14b-llamacpp/")
    + "worktrees/llama.cpp/build-release-metal/bin/llama-cli"
)
RESULTS_DIR = PROJECT_DIR / "results/phase4-ja-zh"
EXPECTED_CHINESE = "今天是2026年9月2日。会议于下午3点15分开始。订单号是A731。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audio", type=Path, default=Path(os.environ.get("AUDIO", DEFAULT_AUDIO))
    )
    parser.add_argument(
        "--whisper-cli",
        type=Path,
        default=Path(os.environ.get("WHISPER_CLI", DEFAULT_WHISPER_CLI)),
    )
    parser.add_argument(
        "--whisper-model",
        type=Path,
        default=Path(os.environ.get("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)),
    )
    parser.add_argument(
        "--llama-cli",
        type=Path,
        default=Path(os.environ.get("LLAMA_CLI", DEFAULT_LLAMA_CLI)),
    )
    parser.add_argument(
        "--translation-model",
        type=Path,
        default=(
            Path(os.environ["TRANSLATION_MODEL"])
            if os.environ.get("TRANSLATION_MODEL")
            else None
        ),
    )
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def require_file(path: Path, label: str, executable: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeError(f"{label} not found: {resolved}")
    if executable and not os.access(resolved, os.X_OK):
        raise RuntimeError(f"{label} is not executable: {resolved}")
    return resolved


def duration_seconds(path: Path) -> float:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(process.stdout.strip())


def parse_whisper_total_ms(log: str) -> float | None:
    match = re.search(
        r"whisper_print_timings:\s+total time\s+=\s+([0-9.]+) ms", log
    )
    return float(match.group(1)) if match else None


def parse_max_rss_bytes(log: str) -> int | None:
    match = re.search(
        r"^\s*([0-9]+)\s+maximum resident set size\s*$", log, re.MULTILINE
    )
    return int(match.group(1)) if match else None


def run_whisper(
    mode: str,
    whisper_cli: Path,
    whisper_model: Path,
    audio: Path,
    output_dir: Path,
    threads: int,
    translate: bool,
    duration: float,
) -> dict[str, Any]:
    output_base = output_dir / mode
    for suffix in (".txt", ".json", ".log"):
        candidate = Path(str(output_base) + suffix)
        if candidate.exists():
            candidate.unlink()
    command = [
        "/usr/bin/time",
        "-lp",
        str(whisper_cli),
        "--model",
        str(whisper_model),
        "--file",
        str(audio),
        "--language",
        "ja",
        "--threads",
        str(threads),
        "--output-txt",
        "--output-json",
        "--output-file",
        str(output_base),
        "--no-timestamps",
    ]
    if translate:
        command.append("--translate")
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    Path(str(output_base) + ".log").write_text(log, encoding="utf-8")
    text_path = Path(str(output_base) + ".txt")
    actual = text_path.read_text(encoding="utf-8").strip() if text_path.exists() else ""
    total_ms = parse_whisper_total_ms(log)
    return {
        "mode": mode,
        "translate_flag": translate,
        "exit_code": process.returncode,
        "text": actual,
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "whisper_total_ms": total_ms,
        "whisper_realtime_factor": (
            total_ms / 1000 / duration if total_ms is not None else None
        ),
        "max_rss_bytes": parse_max_rss_bytes(log),
        "gpu_layers_argument": "all",
        "metal_log_detected": "ggml_metal" in log.lower(),
    }


def run_chinese_translation(
    llama_cli: Path,
    translation_model: Path,
    japanese_text: str,
    output_dir: Path,
    duration: float,
) -> dict[str, Any]:
    raw_output_path = output_dir / "translate-zh-strict.raw.txt"
    output_path = output_dir / "translate-zh-strict.txt"
    log_path = output_dir / "translate-zh-strict.log"
    for path in (raw_output_path, output_path, log_path):
        if path.exists():
            path.unlink()
    prompt = (
        "请把下面的日文逐句翻译成简体中文。\n"
        "要求：不得省略、合并或添加信息；准确区分上午和下午；"
        "保留所有日期、时间和编号；只输出中文译文，不要解释。\n\n"
        f"日文：\n{japanese_text}"
    )
    command = [
        "/usr/bin/time",
        "-lp",
        str(llama_cli),
        "--model",
        str(translation_model),
        "--gpu-layers",
        "all",
        "--ctx-size",
        "2048",
        "--predict",
        "128",
        "--threads",
        "8",
        "--seed",
        "42",
        "--temp",
        "0.7",
        "--top-k",
        "20",
        "--top-p",
        "0.8",
        "--min-p",
        "0",
        "--presence-penalty",
        "1.5",
        "--reasoning",
        "off",
        "--jinja",
        "--single-turn",
        "--simple-io",
        "--no-display-prompt",
        "--no-warmup",
        "--output",
        str(raw_output_path),
        "--prompt",
        prompt,
    ]
    started = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    wall_seconds = time.perf_counter() - started
    log = process.stdout + process.stderr
    log_path.write_text(log, encoding="utf-8")
    raw_output = (
        raw_output_path.read_text(encoding="utf-8").strip()
        if raw_output_path.exists()
        else ""
    )
    actual = raw_output.rsplit("Assistant:", maxsplit=1)[-1].strip()
    output_path.write_text(actual + ("\n" if actual else ""), encoding="utf-8")
    compact = re.sub(r"[\s，。！？、,.!?]", "", actual)
    checks = {
        "date_2026_09_02": "2026年9月2日" in compact,
        "afternoon": "下午" in compact,
        "time_3_15": "3点15分" in compact or "15:15" in compact,
        "meeting_starts": "会议" in compact and "开始" in compact,
        "order_a731": "订单" in compact and "A731" in compact.upper(),
    }
    return {
        "mode": "translate-ja-text-to-zh",
        "exit_code": process.returncode,
        "text": actual,
        "expected_chinese": EXPECTED_CHINESE,
        "critical_checks": checks,
        "critical_checks_passed": sum(checks.values()),
        "critical_checks_total": len(checks),
        "quality_pass": all(checks.values()),
        "wall_seconds": wall_seconds,
        "wall_realtime_factor": wall_seconds / duration,
        "max_rss_bytes": parse_max_rss_bytes(log),
        "metal_detected": "ggml_metal" in log.lower(),
    }


def main() -> int:
    args = parse_args()
    audio = require_file(args.audio, "audio")
    whisper_cli = require_file(args.whisper_cli, "whisper-cli", executable=True)
    whisper_model = require_file(args.whisper_model, "Whisper model")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = duration_seconds(audio)

    japanese = run_whisper(
        "transcribe-ja",
        whisper_cli,
        whisper_model,
        audio,
        output_dir,
        args.threads,
        False,
        duration,
    )
    english = run_whisper(
        "whisper-translate-en",
        whisper_cli,
        whisper_model,
        audio,
        output_dir,
        args.threads,
        True,
        duration,
    )

    chinese = None
    if args.translation_model is not None:
        llama_cli = require_file(args.llama_cli, "llama-cli", executable=True)
        translation_model = require_file(args.translation_model, "translation model")
        chinese = run_chinese_translation(
            llama_cli,
            translation_model,
            japanese["text"],
            output_dir,
            duration,
        )

    pipeline_wall_seconds = (
        japanese["wall_seconds"] + chinese["wall_seconds"] if chinese else None
    )
    summary = {
        "audio": str(audio),
        "audio_duration_seconds": duration,
        "whisper_model": str(whisper_model),
        "translation_model": (
            str(args.translation_model.expanduser().resolve())
            if args.translation_model is not None
            else None
        ),
        "japanese_transcription": japanese,
        "whisper_builtin_english_translation": english,
        "chinese_translation": chinese,
        "ja_to_zh_pipeline_wall_seconds": pipeline_wall_seconds,
        "ja_to_zh_pipeline_realtime_factor": (
            pipeline_wall_seconds / duration
            if pipeline_wall_seconds is not None
            else None
        ),
        "ja_to_zh_pipeline_faster_than_realtime": (
            pipeline_wall_seconds < duration
            if pipeline_wall_seconds is not None
            else None
        ),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"audio_duration_seconds={duration:.3f}")
    print(f"japanese={japanese['text']}")
    print(
        f"asr_wall_seconds={japanese['wall_seconds']:.3f} "
        f"asr_rtf={japanese['wall_realtime_factor']:.3f}"
    )
    print(f"whisper_translate_target=English")
    print(f"english={english['text']}")
    print(
        f"whisper_translate_wall_seconds={english['wall_seconds']:.3f} "
        f"whisper_translate_rtf={english['wall_realtime_factor']:.3f}"
    )
    if chinese:
        print(f"chinese={chinese['text']}")
        print(
            f"translation_checks={chinese['critical_checks_passed']}/"
            f"{chinese['critical_checks_total']} "
            f"quality_pass={'yes' if chinese['quality_pass'] else 'no'}"
        )
        print(
            f"text_translation_wall_seconds={chinese['wall_seconds']:.3f} "
            f"pipeline_wall_seconds={pipeline_wall_seconds:.3f} "
            f"pipeline_rtf={pipeline_wall_seconds / duration:.3f}"
        )
        print(
            "faster_than_realtime="
            f"{'yes' if pipeline_wall_seconds < duration else 'no'}"
        )
    else:
        print("chinese=not_run_no_translation_model")
    print(f"summary={output_dir / 'summary.json'}")

    required = [japanese, english] + ([chinese] if chinese else [])
    return 0 if all(item["exit_code"] == 0 for item in required) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}")
        raise SystemExit(2) from error
