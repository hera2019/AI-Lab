#!/usr/bin/env python3
"""Capture Chinese speech and show stable Chinese, Japanese, and English subtitles."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CAPTURE_BIN = PROJECT_DIR / "tools/bin/mic-silero-capture"
DEFAULT_WHISPER_SERVER = (
    PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-server"
)
DEFAULT_WHISPER_MODEL = Path(
    str(Path.home() / "Documents/AI-Models/whispercpp/ggml-large-v3-turbo-q5_0.bin")
)
DEFAULT_VAD_MODEL = Path(
    str(Path.home() / "Documents/AI-Models/whispercpp/ggml-silero-v6.2.0.bin")
)
DEFAULT_LLAMA_SERVER = Path(
    str(Path.home() / "Documents/AI-Lab/qwen3-14b-llamacpp/")
    + "worktrees/llama.cpp/build-release-metal/bin/llama-server"
)
DEFAULT_TRANSLATION_MODEL = Path(
    str(Path.home() / "Documents/AI-Models/huggingface/")
    + "models--Qwen--Qwen3-4B-GGUF/snapshots/"
    "bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf"
)
SPACE_RE = re.compile(r"\s+")
PUNCTUATION_RE = re.compile(r"[\s,.!?，。！？、…]+")
COLON_MINUTE_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})分")
SUSPICIOUS_SILENCE_OUTPUTS = {
    "感谢观看",
    "谢谢观看",
    "感谢收看",
    "ご視聴ありがとうございました",
    "thankyou",
    "thankyouforwatching",
}


class ManagedServer:
    def __init__(self, command: list[str], log_path: Path) -> None:
        self.command = command
        self.log_path = log_path
        self.process: subprocess.Popen[str] | None = None
        self.log_file: Any = None

    def start(self) -> None:
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            self.command,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
        if self.log_file is not None:
            self.log_file.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-bin", type=Path, default=DEFAULT_CAPTURE_BIN)
    parser.add_argument("--whisper-server", type=Path, default=DEFAULT_WHISPER_SERVER)
    parser.add_argument("--whisper-model", type=Path, default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--vad-model", type=Path, default=DEFAULT_VAD_MODEL)
    parser.add_argument("--llama-server", type=Path, default=DEFAULT_LLAMA_SERVER)
    parser.add_argument(
        "--translation-model", type=Path, default=DEFAULT_TRANSLATION_MODEL
    )
    parser.add_argument("--whisper-port", type=int, default=18081)
    parser.add_argument("--llama-port", type=int, default=18082)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--capture", type=int, default=-1)
    parser.add_argument("--vad-thold", type=float, default=0.20)
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=0.0,
        help="stop automatically after N seconds; zero means run until Ctrl-C",
    )
    parser.add_argument("--existing-llama-server", action="store_true")
    parser.add_argument("--existing-whisper-server", action="store_true")
    parser.add_argument(
        "--self-test",
        metavar="CHINESE_TEXT",
        help="test Japanese/English translation without opening the microphone",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="PREVIOUS_CHINESE_TEXT",
        help="previous subtitle for self-test context; may be repeated",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="exact result directory; default creates a timestamped run directory",
    )
    return parser.parse_args()


def require_file(path: Path, label: str, executable: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeError(f"{label} not found: {resolved}")
    if executable and not os.access(resolved, os.X_OK):
        raise RuntimeError(f"{label} is not executable: {resolved}")
    return resolved


def wait_for_url(
    url: str, process: subprocess.Popen[str] | None, timeout: float = 45.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"translation server exited with {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("translation server did not become ready")


def multipart_body(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = f"codex-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            b"Content-Type: audio/wav\r\n\r\n",
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def transcribe(port: int, wav_path: Path) -> str:
    body, content_type = multipart_body(
        {
            "temperature": "0.0",
            "temperature_inc": "0.0",
            "language": "zh",
            "response_format": "json",
        },
        wav_path,
    )
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.request(
        "POST", "/inference", body=body, headers={"Content-Type": content_type}
    )
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    if response.status != 200:
        raise RuntimeError(
            f"Whisper HTTP {response.status}: {payload.decode(errors='replace')}"
        )
    return str(json.loads(payload)["text"]).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError(f"translation did not return JSON: {text}")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise RuntimeError("translation JSON is not an object")
    return value


def translate(
    port: int, chinese: str, previous_chinese: list[str] | None = None
) -> tuple[str, str]:
    context = (previous_chinese or [])[-2:]
    context_text = "\n".join(
        f"前文{index + 1}：{text}" for index, text in enumerate(context)
    )
    if not context_text:
        context_text = "（无前文）"
    prompt = (
        "你是三语字幕翻译器。将下面的简体中文分别翻译为自然日语和自然英语。"
        "不得省略、合并、解释或添加信息；保留姓名、日期、时间、数字和编号。"
        "前文只用于判断当前句的语气和省略内容；严禁翻译或重复前文，"
        "JSON 中只能放当前字幕的译文。"
        "仔细区分时间表达式后的动词，例如‘下午3点15分开会’中的‘开会’是举行会议，"
        "不能误解成‘分开’。"
        "如果当前字幕只有‘好’，它是对话回应，应根据前文译为日语‘はい’、"
        "‘わかりました’或‘いいですね’，英语‘Okay’或‘Good’，绝不能译为问候语"
        "‘こんにちは’或‘Hello’；只有明确出现‘你好’才是问候。"
        "输出前在心中校对日语助词、时态和英语语法。"
        "例如中文‘今天是2026年9月3日’应译为日语‘今日は2026年9月3日です’，"
        "不能写成不自然的‘今日のは’。"
        "只输出一个 JSON 对象，键必须是 japanese 和 english，不要输出 Markdown。\n\n"
        f"最近的已确认前文：\n{context_text}\n\n"
        f"当前待翻译字幕：{chinese}"
    )
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "seed": 42,
            "max_tokens": 256,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.request(
        "POST",
        "/v1/chat/completions",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    if response.status != 200:
        raise RuntimeError(
            f"Qwen HTTP {response.status}: {payload.decode(errors='replace')}"
        )
    content = str(json.loads(payload)["choices"][0]["message"]["content"])
    translated = extract_json_object(content)
    japanese = str(translated.get("japanese", "")).strip()
    english = str(translated.get("english", "")).strip()
    if not japanese or not english:
        raise RuntimeError(f"translation JSON is missing text: {content}")
    return japanese, english


def normalized(text: str) -> str:
    return PUNCTUATION_RE.sub("", text).lower()


def is_suspicious_silence_output(text: str) -> bool:
    return normalized(text) in SUSPICIOUS_SILENCE_OUTPUTS


def normalize_chinese_subtitle(text: str) -> str:
    cleaned = SPACE_RE.sub("", text).replace(",", "，")
    return COLON_MINUTE_RE.sub(r"\1点\2分", cleaned)


def main() -> int:
    args = parse_args()
    llama_server_bin = require_file(args.llama_server, "llama-server", executable=True)
    translation_model = require_file(args.translation_model, "translation model")
    run_started_at = datetime.now().astimezone()
    if args.output_dir is None:
        run_name = f"{run_started_at:%Y%m%d-%H%M%S}-{os.getpid()}"
        output_dir = (
            PROJECT_DIR / "results/microphone-trilingual/runs" / run_name
        ).resolve()
    else:
        output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    capture_bin: Path | None = None
    whisper_server_bin: Path | None = None
    whisper_model: Path | None = None
    vad_model: Path | None = None
    if not args.self_test:
        capture_bin = require_file(args.capture_bin, "Silero microphone capture", executable=True)
        whisper_server_bin = require_file(
            args.whisper_server, "whisper-server", executable=True
        )
        whisper_model = require_file(args.whisper_model, "Whisper model")
        vad_model = require_file(args.vad_model, "Silero VAD model")

    managed: list[ManagedServer] = []
    llama_managed: ManagedServer | None = None
    if not args.existing_llama_server:
        llama_managed = ManagedServer(
            [
                str(llama_server_bin),
                "--model",
                str(translation_model),
                "--gpu-layers",
                "all",
                "--ctx-size",
                "2048",
                "--parallel",
                "1",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.llama_port),
                "--jinja",
                "--reasoning",
                "off",
            ],
            output_dir / "llama-server.log",
        )
        managed.append(llama_managed)

    whisper_managed: ManagedServer | None = None
    if not args.self_test and not args.existing_whisper_server:
        assert whisper_server_bin is not None
        assert whisper_model is not None
        whisper_managed = ManagedServer(
            [
                str(whisper_server_bin),
                "--model",
                str(whisper_model),
                "--host",
                "127.0.0.1",
                "--port",
                str(args.whisper_port),
                "--threads",
                str(args.threads),
                "--language",
                "zh",
                "--no-timestamps",
            ],
            output_dir / "whisper-server.log",
        )
        managed.append(whisper_managed)

    for server in managed:
        server.start()

    capture_process: subprocess.Popen[str] | None = None
    capture_log: Any = None
    timer: threading.Timer | None = None
    events: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    context_chinese: list[str] = []

    try:
        wait_for_url(
            f"http://127.0.0.1:{args.llama_port}/health",
            llama_managed.process if llama_managed else None,
        )

        if args.self_test:
            chinese = normalize_chinese_subtitle(args.self_test)
            started = time.monotonic()
            japanese, english = translate(
                args.llama_port, chinese, args.context[-2:]
            )
            elapsed = time.monotonic() - started
            self_test_summary = {
                "run_started_at": run_started_at.isoformat(),
                "mode": "translation self-test",
                "chinese": chinese,
                "translation_context": args.context[-2:],
                "japanese": japanese,
                "english": english,
                "translation_seconds": elapsed,
            }
            summary_path = output_dir / "summary.json"
            summary_path.write_text(
                json.dumps(self_test_summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"中文字幕：{chinese}")
            print(f"日本語字幕：{japanese}")
            print(f"English: {english}")
            print(f"翻译耗时：{elapsed:.3f} 秒")
            print(f"结果：{summary_path}")
            return 0

        wait_for_url(
            f"http://127.0.0.1:{args.whisper_port}/",
            whisper_managed.process if whisper_managed else None,
        )

        segment_dir = output_dir / "segments"
        segment_dir.mkdir(parents=True, exist_ok=True)
        capture_log = (output_dir / "mic-silero-capture.log").open(
            "w", encoding="utf-8"
        )
        assert capture_bin is not None
        assert vad_model is not None
        capture_process = subprocess.Popen(
            [
                str(capture_bin),
                "--vad-model",
                str(vad_model),
                "--output-dir",
                str(segment_dir),
                "--capture",
                str(args.capture),
                "--threshold",
                str(args.vad_thold),
            ],
            stdout=subprocess.PIPE,
            stderr=capture_log,
            text=True,
            bufsize=1,
            start_new_session=True,
        )

        if args.max_seconds > 0:
            timer = threading.Timer(
                args.max_seconds,
                lambda: (
                    os.killpg(capture_process.pid, signal.SIGINT)
                    if capture_process is not None and capture_process.poll() is None
                    else None
                ),
            )
            timer.daemon = True
            timer.start()

        print("🎙️ 中文麦克风三语字幕")
        print("Silero VAD 已启用。请说中文，说完后安静约 1 秒；按 Ctrl-C 停止。")
        print("正在等待真正的人声……", flush=True)

        assert capture_process.stdout is not None
        try:
            for raw_line in capture_process.stdout:
                line = raw_line.strip()
                if line.startswith("LEVEL\t"):
                    parts = line.split("\t")
                    if len(parts) != 3:
                        continue
                    rms = float(parts[1])
                    probability = float(parts[2])
                    width = 24
                    filled = round(min(1.0, rms / 0.025) * width)
                    bar = "█" * filled + "·" * (width - filled)
                    print(
                        f"\r声音 {bar}  人声概率 {probability:0.2f}",
                        end="",
                        flush=True,
                    )
                    continue
                if not line.startswith("SEGMENT\t"):
                    continue

                parts = line.split("\t")
                if len(parts) != 4:
                    continue
                audio_path = Path(parts[1])
                audio_seconds = float(parts[2])
                vad_peak = float(parts[3])
                print("\r" + " " * 72 + "\r正在识别并翻译……", flush=True)

                asr_started = time.monotonic()
                try:
                    chinese = normalize_chinese_subtitle(
                        transcribe(args.whisper_port, audio_path)
                    )
                    asr_seconds = time.monotonic() - asr_started
                    if not chinese:
                        ignored.append(
                            {
                                "audio": str(audio_path),
                                "reason": "empty transcription",
                            }
                        )
                        continue
                    if is_suspicious_silence_output(chinese):
                        ignored.append(
                            {
                                "audio": str(audio_path),
                                "reason": "suspicious stock phrase",
                                "text": chinese,
                            }
                        )
                        print(f"已忽略疑似静音幻觉：{chinese}", flush=True)
                        continue

                    translation_started = time.monotonic()
                    prior_context = context_chinese[-2:]
                    japanese, english = translate(
                        args.llama_port, chinese, prior_context
                    )
                    translation_seconds = time.monotonic() - translation_started
                    event = {
                        "audio": str(audio_path),
                        "audio_seconds": audio_seconds,
                        "vad_peak_probability": vad_peak,
                        "chinese": chinese,
                        "translation_context": prior_context,
                        "japanese": japanese,
                        "english": english,
                        "asr_seconds": asr_seconds,
                        "translation_seconds": translation_seconds,
                        "processing_seconds": asr_seconds + translation_seconds,
                        "error": None,
                    }
                    print("────────────────────────────────────────")
                    print(f"中文字幕：{chinese}")
                    print(f"日本語字幕：{japanese}")
                    print(f"English: {english}")
                    print(
                        f"识别 {asr_seconds:.3f} 秒 + 翻译 {translation_seconds:.3f} 秒",
                        flush=True,
                    )
                    context_chinese.append(chinese)
                except Exception as error:  # noqa: BLE001 - preserve live errors
                    event = {
                        "audio": str(audio_path),
                        "audio_seconds": audio_seconds,
                        "vad_peak_probability": vad_peak,
                        "error": str(error),
                    }
                    print(f"处理错误：{error}", flush=True)
                events.append(event)
        except KeyboardInterrupt:
            if capture_process.poll() is None:
                os.killpg(capture_process.pid, signal.SIGINT)

        capture_process.wait(timeout=10)
        capture_log.close()
        summary = {
            "run_started_at": run_started_at.isoformat(),
            "output_directory": str(output_dir),
            "input_language": "zh",
            "output_languages": ["zh", "ja", "en"],
            "vad_mode": "Silero streaming",
            "vad_threshold": args.vad_thold,
            "events": events,
            "ignored": ignored,
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n已停止。共完成 {len(events)} 个稳定字幕块。")
        print(f"结果：{summary_path}")
        return 0 if all(event.get("error") is None for event in events) else 1
    finally:
        if timer is not None:
            timer.cancel()
        if capture_process is not None and capture_process.poll() is None:
            os.killpg(capture_process.pid, signal.SIGTERM)
            try:
                capture_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(capture_process.pid, signal.SIGKILL)
        if capture_log is not None and not capture_log.closed:
            capture_log.close()
        for server in reversed(managed):
            server.stop()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}")
        raise SystemExit(2) from error
