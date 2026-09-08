#!/usr/bin/env python3
"""Auto-detect each Chinese, Japanese, or English utterance and show three subtitles."""

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
from datetime import datetime
from pathlib import Path
from typing import Any

from run_microphone_trilingual import (
    DEFAULT_CAPTURE_BIN,
    DEFAULT_LLAMA_SERVER,
    DEFAULT_TRANSLATION_MODEL,
    DEFAULT_VAD_MODEL,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_WHISPER_SERVER,
    ManagedServer,
    PROJECT_DIR,
    extract_json_object,
    is_suspicious_silence_output,
    multipart_body,
    require_file,
    wait_for_url,
)


LANGUAGE_NAMES = {"zh": "中文", "ja": "日本語", "en": "English"}
LANGUAGE_JSON_KEYS = {"zh": "chinese", "ja": "japanese", "en": "english"}
FULL_LANGUAGE_TO_CODE = {
    "chinese": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "english": "en",
    "zh": "zh",
    "ja": "ja",
    "en": "en",
}
SPACE_RE = re.compile(r"\s+")
COLON_MINUTE_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})分")


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
    parser.add_argument(
        "--audio-file",
        action="append",
        type=Path,
        default=[],
        help="process an existing WAV instead of opening the microphone; may repeat",
    )
    parser.add_argument("--existing-llama-server", action="store_true")
    parser.add_argument("--existing-whisper-server", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="exact result directory; default creates a timestamped run directory",
    )
    return parser.parse_args()


def language_code(value: object) -> str:
    return FULL_LANGUAGE_TO_CODE.get(str(value).strip().lower(), "unknown")


def normalize_transcript(text: str, code: str) -> str:
    cleaned = SPACE_RE.sub(" ", text).strip()
    if code == "zh":
        cleaned = cleaned.replace(" ", "").replace(",", "，")
        cleaned = COLON_MINUTE_RE.sub(r"\1点\2分", cleaned)
    return cleaned


def transcribe_auto(port: int, wav_path: Path) -> dict[str, Any]:
    body, content_type = multipart_body(
        {
            "temperature": "0.0",
            "temperature_inc": "0.0",
            "language": "auto",
            "response_format": "verbose_json",
        },
        wav_path,
    )
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=45)
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

    result = json.loads(payload)
    detected_name = result.get("detected_language", result.get("language", ""))
    detected_code = language_code(detected_name)
    probabilities = result.get("language_probabilities", {})
    if not isinstance(probabilities, dict):
        probabilities = {}
    probability = result.get("detected_language_probability")
    if probability is None and detected_code in probabilities:
        probability = probabilities[detected_code]
    return {
        "text": normalize_transcript(str(result.get("text", "")), detected_code),
        "language": detected_code,
        "language_name": str(detected_name),
        "language_probability": float(probability) if probability is not None else None,
        "language_probabilities": {
            str(key): float(value)
            for key, value in probabilities.items()
            if key in LANGUAGE_NAMES
        },
    }


def translate_three(
    port: int,
    source_language: str,
    source_text: str,
    previous_segments: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    if source_language not in LANGUAGE_NAMES:
        raise RuntimeError(
            "the detected language is outside the supported zh/ja/en set: "
            f"{source_language}"
        )

    context = (previous_segments or [])[-2:]
    context_text = "\n".join(
        f"[{item['language']}] {item['text']}" for item in context
    )
    if not context_text:
        context_text = "（无前文 / no previous context）"
    source_name = LANGUAGE_NAMES[source_language]
    target_languages = [code for code in ("zh", "ja", "en") if code != source_language]
    target_keys = [LANGUAGE_JSON_KEYS[code] for code in target_languages]
    target_description = "、".join(
        f"{LANGUAGE_NAMES[code]}（键 {LANGUAGE_JSON_KEYS[code]}）"
        for code in target_languages
    )
    prompt = (
        "你是字幕翻译器。输入只包含一条当前字幕及最多两条只读前文。"
        f"源语言是{source_name}；只把当前字幕翻译为{target_description}。"
        "不要输出源语言原文，程序会自行保留它。"
        "前文只用于判断省略、代词和短句语气，严禁翻译、重复或拼接前文。"
        "不得省略、添加或解释信息；姓名、日期、时间、数字、单位和编号必须保留。"
        "禁止在日语句子中无故夹入英语。中文回应‘好，我知道了’是肯定和确认，"
        "应译为日语‘はい、わかりました’、英语‘Okay, I understand’，"
        "绝不能译成否定的‘いいえ/No’，也不能译成问候语‘こんにちは/Hello’。"
        "严格保持说话视角：英语‘I’是说话者，‘you’是对方；"
        "‘Yes, I can understand you clearly.’的自然日语是"
        "‘はい、あなたの言っていることがよくわかります。’，不能颠倒主客体。"
        "输出前检查两种译文是否与当前字幕表达同一件事。"
        f"只输出一个 JSON 对象，键必须恰好为 {'、'.join(target_keys)}，"
        "不得包含其他键，不要输出 Markdown。\n\n"
        f"最近已确认前文：\n{context_text}\n\n"
        f"当前源语言：{source_language}（{source_name}）\n"
        f"当前字幕：{source_text}"
    )
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "seed": 42,
            "max_tokens": 384,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=45)
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
    subtitles = {source_language: source_text}
    for code in target_languages:
        subtitles[code] = str(translated.get(LANGUAGE_JSON_KEYS[code], "")).strip()
    if any(not text for text in subtitles.values()):
        raise RuntimeError(f"translation JSON is missing text: {content}")
    return subtitles


def show_event(event: dict[str, Any]) -> None:
    code = str(event["detected_language"])
    probability = event.get("language_probability")
    confidence = f"{float(probability):.2f}" if probability is not None else "unknown"
    print("────────────────────────────────────────")
    print(f"检测语言：{LANGUAGE_NAMES[code]}（置信度 {confidence}）")
    source_suffix = "（原文）"
    print(f"中文{source_suffix if code == 'zh' else ''}：{event['chinese']}")
    print(f"日本語{source_suffix if code == 'ja' else ''}：{event['japanese']}")
    print(f"English{source_suffix if code == 'en' else ''}: {event['english']}")
    print(
        f"识别 {event['asr_seconds']:.3f} 秒 + "
        f"翻译 {event['translation_seconds']:.3f} 秒",
        flush=True,
    )
    if event.get("suspicious_stock_phrase"):
        print("⚠️ 这句与常见静音幻觉相同，但检测到持续人声，已保留，请核对。", flush=True)
    if probability is not None and float(probability) < 0.50:
        print("⚠️ 语言置信度较低，请重点核对这一句。", flush=True)


def process_audio(
    wav_path: Path,
    whisper_port: int,
    llama_port: int,
    context: list[dict[str, str]],
    audio_seconds: float | None = None,
    vad_peak: float | None = None,
) -> tuple[dict[str, Any], bool]:
    asr_started = time.monotonic()
    transcription = transcribe_auto(whisper_port, wav_path)
    asr_seconds = time.monotonic() - asr_started
    text = str(transcription["text"])

    if not text:
        return {
            "audio": str(wav_path),
            "reason": "empty transcription",
            **transcription,
        }, True
    suspicious_stock_phrase = is_suspicious_silence_output(text)
    if (
        suspicious_stock_phrase
        and audio_seconds is not None
        and audio_seconds < 0.75
    ):
        return {
            "audio": str(wav_path),
            "audio_seconds": audio_seconds,
            "vad_peak_probability": vad_peak,
            "reason": "suspicious stock phrase",
            **transcription,
        }, True

    code = str(transcription["language"])
    translation_started = time.monotonic()
    prior_context = [dict(item) for item in context[-2:]]
    subtitles = translate_three(llama_port, code, text, prior_context)
    translation_seconds = time.monotonic() - translation_started
    event = {
        "audio": str(wav_path),
        "audio_seconds": audio_seconds,
        "vad_peak_probability": vad_peak,
        "source_text": text,
        "detected_language": code,
        "detected_language_name": transcription["language_name"],
        "language_probability": transcription["language_probability"],
        "language_probabilities": transcription["language_probabilities"],
        "suspicious_stock_phrase": suspicious_stock_phrase,
        "translation_context": prior_context,
        "chinese": subtitles["zh"],
        "japanese": subtitles["ja"],
        "english": subtitles["en"],
        "asr_seconds": asr_seconds,
        "translation_seconds": translation_seconds,
        "processing_seconds": asr_seconds + translation_seconds,
        "error": None,
    }
    context.append({"language": code, "text": text})
    return event, False


def main() -> int:
    args = parse_args()
    llama_server_bin = require_file(args.llama_server, "llama-server", executable=True)
    translation_model = require_file(args.translation_model, "translation model")
    whisper_server_bin = require_file(
        args.whisper_server, "whisper-server", executable=True
    )
    whisper_model = require_file(args.whisper_model, "Whisper model")
    audio_files = [require_file(path, "audio file") for path in args.audio_file]
    microphone_mode = not audio_files

    capture_bin: Path | None = None
    vad_model: Path | None = None
    if microphone_mode:
        capture_bin = require_file(
            args.capture_bin, "Silero microphone capture", executable=True
        )
        vad_model = require_file(args.vad_model, "Silero VAD model")

    run_started_at = datetime.now().astimezone()
    if args.output_dir is None:
        run_name = f"{run_started_at:%Y%m%d-%H%M%S}-{os.getpid()}"
        output_dir = (
            PROJECT_DIR / "results/microphone-multilingual/runs" / run_name
        ).resolve()
    else:
        output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

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
    if not args.existing_whisper_server:
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
                "auto",
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
    context: list[dict[str, str]] = []

    try:
        wait_for_url(
            f"http://127.0.0.1:{args.llama_port}/health",
            llama_managed.process if llama_managed else None,
        )
        wait_for_url(
            f"http://127.0.0.1:{args.whisper_port}/",
            whisper_managed.process if whisper_managed else None,
        )

        if audio_files:
            for audio_path in audio_files:
                print(f"正在处理：{audio_path.name}", flush=True)
                try:
                    event, should_ignore = process_audio(
                        audio_path, args.whisper_port, args.llama_port, context
                    )
                    if should_ignore:
                        ignored.append(event)
                        print(f"已忽略：{event['reason']}（{event.get('text', '')}）")
                    else:
                        events.append(event)
                        show_event(event)
                except Exception as error:  # noqa: BLE001 - preserve batch errors
                    events.append({"audio": str(audio_path), "error": str(error)})
                    print(f"处理错误：{error}")
        else:
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
                        if capture_process is not None
                        and capture_process.poll() is None
                        else None
                    ),
                )
                timer.daemon = True
                timer.start()

            print("🎙️ 中日英自动识别与三语字幕")
            print("每句请主要使用一种语言，句末安静约 1 秒；按 Ctrl-C 停止。")
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
                    print("\r" + " " * 72 + "\r正在识别语言、转写并翻译……", flush=True)
                    try:
                        event, should_ignore = process_audio(
                            audio_path,
                            args.whisper_port,
                            args.llama_port,
                            context,
                            audio_seconds,
                            vad_peak,
                        )
                        if should_ignore:
                            ignored.append(event)
                            print(f"已忽略：{event['reason']}（{event.get('text', '')}）")
                        else:
                            events.append(event)
                            show_event(event)
                    except Exception as error:  # noqa: BLE001 - preserve live errors
                        events.append(
                            {
                                "audio": str(audio_path),
                                "audio_seconds": audio_seconds,
                                "vad_peak_probability": vad_peak,
                                "error": str(error),
                            }
                        )
                        print(f"处理错误：{error}", flush=True)
            except KeyboardInterrupt:
                if capture_process.poll() is None:
                    os.killpg(capture_process.pid, signal.SIGINT)
            capture_process.wait(timeout=10)
            capture_log.close()

        summary = {
            "run_started_at": run_started_at.isoformat(),
            "output_directory": str(output_dir),
            "mode": "microphone" if microphone_mode else "audio files",
            "input_languages": ["zh", "ja", "en"],
            "language_mode": "automatic per utterance",
            "output_languages": ["zh", "ja", "en"],
            "vad_mode": "Silero streaming" if microphone_mode else None,
            "vad_threshold": args.vad_thold if microphone_mode else None,
            "events": events,
            "ignored": ignored,
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            displayed_summary_path = summary_path.relative_to(PROJECT_DIR)
        except ValueError:
            displayed_summary_path = summary_path
        print(f"\n已停止。共完成 {len(events)} 个稳定字幕块。")
        print(f"结果：{displayed_summary_path}")
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
