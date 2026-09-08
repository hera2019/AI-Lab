#!/usr/bin/env python3
"""Play a WAV in real time and show simulated live Japanese/Chinese subtitles."""

from __future__ import annotations

import argparse
import array
import http.client
import json
import math
import os
import queue
import re
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO = PROJECT_DIR / "tests/fixtures/audio/asr-ja-001.wav"
DEFAULT_WHISPER_SERVER = (
    PROJECT_DIR / "worktrees/whisper.cpp/build-release-metal/bin/whisper-server"
)
DEFAULT_VAD_CLI = (
    PROJECT_DIR
    / "worktrees/whisper.cpp/build-release-metal/bin/whisper-vad-speech-segments"
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
VAD_RE = re.compile(
    r"Speech segment \d+: start = (?P<start>[0-9.]+), end = (?P<end>[0-9.]+)"
)


@dataclass(frozen=True)
class SpeechSegment:
    index: int
    start: float
    end: float


@dataclass(frozen=True)
class Job:
    kind: str
    segment: SpeechSegment
    audio_end: float
    scheduled_at: float


class ManagedServer:
    def __init__(self, name: str, command: list[str], log_path: Path) -> None:
        self.name = name
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
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--whisper-server", type=Path, default=DEFAULT_WHISPER_SERVER)
    parser.add_argument("--vad-cli", type=Path, default=DEFAULT_VAD_CLI)
    parser.add_argument("--whisper-model", type=Path, default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--vad-model", type=Path, default=DEFAULT_VAD_MODEL)
    parser.add_argument("--llama-server", type=Path, default=DEFAULT_LLAMA_SERVER)
    parser.add_argument(
        "--translation-model", type=Path, default=DEFAULT_TRANSLATION_MODEL
    )
    parser.add_argument("--whisper-port", type=int, default=18081)
    parser.add_argument("--llama-port", type=int, default=18082)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--partial-interval", type=float, default=1.35)
    parser.add_argument("--finalize-delay", type=float, default=0.25)
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--existing-servers", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_DIR / "results/realtime-playback-demo",
    )
    return parser.parse_args()


def require_file(path: Path, label: str, executable: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeError(f"{label} not found: {resolved}")
    if executable and not os.access(resolved, os.X_OK):
        raise RuntimeError(f"{label} is not executable: {resolved}")
    return resolved


def read_wav(path: Path) -> tuple[wave._wave_params, bytes]:
    with wave.open(str(path), "rb") as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(params.nframes)
    if params.sampwidth != 2 or params.nchannels != 1:
        raise RuntimeError("demo requires 16-bit mono PCM WAV")
    return params, frames


def write_wav_slice(
    output: Path,
    params: wave._wave_params,
    frames: bytes,
    start_seconds: float,
    end_seconds: float,
) -> None:
    bytes_per_frame = params.sampwidth * params.nchannels
    start_frame = max(0, int(start_seconds * params.framerate))
    end_frame = min(params.nframes, int(end_seconds * params.framerate))
    payload = frames[start_frame * bytes_per_frame : end_frame * bytes_per_frame]
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setparams(params)
        wav_file.writeframes(payload)


def detect_segments(vad_cli: Path, vad_model: Path, audio: Path, threads: int) -> list[SpeechSegment]:
    process = subprocess.run(
        [
            str(vad_cli),
            "--file",
            str(audio),
            "--vad-model",
            str(vad_model),
            "--threads",
            str(threads),
            "--no-prints",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"VAD failed: {process.stdout}{process.stderr}")
    text = process.stdout + process.stderr
    segments = [
        SpeechSegment(
            index=index,
            start=float(match.group("start")) / 100,
            end=float(match.group("end")) / 100,
        )
        for index, match in enumerate(VAD_RE.finditer(text))
    ]
    if not segments:
        raise RuntimeError("VAD detected no speech")
    return segments


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
            "temperature_inc": "0.2",
            "language": "ja",
            "response_format": "json",
        },
        wav_path,
    )
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.request("POST", "/inference", body=body, headers={"Content-Type": content_type})
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    if response.status != 200:
        raise RuntimeError(f"Whisper HTTP {response.status}: {payload.decode(errors='replace')}")
    return str(json.loads(payload)["text"]).strip()


def translate(port: int, japanese: str) -> str:
    prompt = (
        "你是日中实时字幕翻译器。请把下面日文翻译成自然、完整的简体中文。"
        "不得省略、合并或添加信息；准确区分上午和下午；保留日期、时间和编号；"
        "不得保留日语词语或假名，例如「注文番号」必须译为「订单号」。"
        "只输出中文译文。\n\n"
        f"日文：{japanese}"
    )
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "seed": 42,
            "max_tokens": 128,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.request(
        "POST", "/v1/chat/completions", body=body, headers={"Content-Type": "application/json"}
    )
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    if response.status != 200:
        raise RuntimeError(f"Qwen HTTP {response.status}: {payload.decode(errors='replace')}")
    return str(json.loads(payload)["choices"][0]["message"]["content"]).strip()


def wait_for_url(url: str, process: subprocess.Popen[str] | None, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"server exited early with status {process.returncode}: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def audio_level(
    params: wave._wave_params, frames: bytes, position_seconds: float, window: float = 0.10
) -> float:
    bytes_per_frame = params.sampwidth * params.nchannels
    start = max(0, int(position_seconds * params.framerate))
    end = min(params.nframes, int((position_seconds + window) * params.framerate))
    samples = array.array("h", frames[start * bytes_per_frame : end * bytes_per_frame])
    if not samples:
        return 0.0
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return min(1.0, rms / 9000.0)


def create_jobs(segments: list[SpeechSegment], interval: float, finalize_delay: float) -> list[Job]:
    jobs: list[Job] = []
    for segment in segments:
        partial_time = segment.start + interval
        while partial_time < segment.end - 0.30:
            jobs.append(Job("partial", segment, partial_time, partial_time))
            partial_time += interval
        jobs.append(Job("final", segment, segment.end, segment.end + finalize_delay))
    return sorted(jobs, key=lambda item: item.scheduled_at)


def format_clock(seconds: float) -> str:
    return f"{int(seconds) // 60:02d}:{seconds % 60:04.1f}"


def render(
    elapsed: float,
    duration: float,
    level: float,
    partial: str,
    japanese_lines: list[str],
    chinese_lines: list[str],
    pending: int,
) -> str:
    width = 34
    filled = round(level * width)
    bar = "█" * filled + "·" * (width - filled)
    ja = "\n".join(f"  {line}" for line in japanese_lines) or "  （等待句子完成）"
    zh = "\n".join(f"  {line}" for line in chinese_lines) or "  （等待翻译）"
    return (
        "🎧 本地实时字幕模拟\n"
        f"时间  {format_clock(elapsed)} / {format_clock(duration)}\n"
        f"声音  {bar}\n\n"
        f"临时日文（可能修改）\n  {partial or '（聆听中…）'}\n\n"
        f"稳定日文\n{ja}\n\n"
        f"中文字幕\n{zh}\n\n"
        f"处理中任务：{pending}"
    )


def main() -> int:
    args = parse_args()
    if args.rate <= 0:
        raise RuntimeError("--rate must be greater than zero")
    audio = require_file(args.audio, "audio")
    vad_cli = require_file(args.vad_cli, "VAD CLI", executable=True)
    vad_model = require_file(args.vad_model, "VAD model")
    whisper_model = require_file(args.whisper_model, "Whisper model")
    translation_model = require_file(args.translation_model, "translation model")
    whisper_server_bin = require_file(args.whisper_server, "whisper-server", executable=True)
    llama_server_bin = require_file(args.llama_server, "llama-server", executable=True)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    params, frames = read_wav(audio)
    duration = params.nframes / params.framerate
    segments = [
        SpeechSegment(
            index=segment.index,
            start=max(0.0, min(duration, segment.start)),
            end=max(0.0, min(duration, segment.end)),
        )
        for segment in detect_segments(vad_cli, vad_model, audio, args.threads)
    ]
    jobs = create_jobs(segments, args.partial_interval, args.finalize_delay)

    managed: list[ManagedServer] = []
    if not args.existing_servers:
        whisper = ManagedServer(
            "whisper",
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
                "ja",
                "--no-timestamps",
            ],
            output_dir / "whisper-server.log",
        )
        llama = ManagedServer(
            "llama",
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
        managed = [whisper, llama]
        for server in managed:
            server.start()

    playback: subprocess.Popen[str] | None = None
    temporary = tempfile.TemporaryDirectory(prefix="whisper-live-demo-")
    temp_dir = Path(temporary.name)
    job_queue: queue.Queue[Job | None] = queue.Queue()
    result_queue: queue.Queue[dict[str, Any]] = queue.Queue()
    events: list[dict[str, Any]] = []
    japanese_lines: list[str] = []
    chinese_lines: list[str] = []
    partial = ""
    stop_worker = threading.Event()
    start_time = 0.0

    def worker() -> None:
        while not stop_worker.is_set():
            job = job_queue.get()
            if job is None:
                job_queue.task_done()
                return
            clip = temp_dir / f"{job.kind}-{job.segment.index}-{job.audio_end:.2f}.wav"
            clip_start = max(0.0, job.segment.start - 0.10)
            clip_end = min(duration, job.audio_end + (0.08 if job.kind == "final" else 0.0))
            write_wav_slice(clip, params, frames, clip_start, clip_end)
            requested = time.monotonic()
            try:
                text_ja = transcribe(args.whisper_port, clip)
                asr_done = time.monotonic()
                text_zh = ""
                translated = asr_done
                if job.kind == "final" and text_ja:
                    text_zh = translate(args.llama_port, text_ja)
                    translated = time.monotonic()
                result_queue.put(
                    {
                        "kind": job.kind,
                        "segment": job.segment.index,
                        "audio_start": job.segment.start,
                        "audio_end": job.audio_end,
                        "scheduled_at": job.scheduled_at,
                        "request_started_at": requested - start_time,
                        "asr_completed_at": asr_done - start_time,
                        "translation_completed_at": translated - start_time,
                        "asr_seconds": asr_done - requested,
                        "translation_seconds": translated - asr_done,
                        "asr_latency_after_audio": (
                            asr_done - start_time - job.audio_end / args.rate
                        ),
                        "translation_latency_after_audio": (
                            translated - start_time - job.audio_end / args.rate
                        ),
                        "japanese": text_ja,
                        "chinese": text_zh,
                        "error": None,
                    }
                )
            except Exception as error:  # noqa: BLE001 - preserve demo errors in results
                result_queue.put(
                    {
                        "kind": job.kind,
                        "segment": job.segment.index,
                        "audio_end": job.audio_end,
                        "error": str(error),
                    }
                )
            finally:
                job_queue.task_done()

    try:
        wait_for_url(
            f"http://127.0.0.1:{args.whisper_port}/",
            managed[0].process if managed else None,
        )
        wait_for_url(
            f"http://127.0.0.1:{args.llama_port}/health",
            managed[1].process if managed else None,
        )

        warmup = temp_dir / "warmup.wav"
        write_wav_slice(warmup, params, frames, 0.0, min(1.0, duration))
        transcribe(args.whisper_port, warmup)
        translate(args.llama_port, "今日は晴れです。")

        thread = threading.Thread(target=worker, name="subtitle-worker", daemon=True)
        thread.start()
        if not args.no_play:
            playback = subprocess.Popen(["afplay", "-r", str(args.rate), str(audio)])

        start_time = time.monotonic()
        next_job = 0
        last_render = ""
        while True:
            elapsed_real = time.monotonic() - start_time
            timeline_audio = elapsed_real * args.rate
            display_audio = min(duration, timeline_audio)
            while next_job < len(jobs) and jobs[next_job].scheduled_at <= timeline_audio:
                job_queue.put(jobs[next_job])
                next_job += 1

            while True:
                try:
                    result = result_queue.get_nowait()
                except queue.Empty:
                    break
                events.append(result)
                if result.get("error"):
                    partial = f"错误：{result['error']}"
                elif result["kind"] == "partial":
                    partial = result["japanese"]
                    if args.plain:
                        print(
                            f"PARTIAL t={result['asr_completed_at']:.3f}s "
                            f"lag={result['asr_latency_after_audio']:.3f}s "
                            f"ja={result['japanese']}"
                        )
                else:
                    partial = ""
                    japanese_lines.append(result["japanese"])
                    chinese_lines.append(result["chinese"])
                    if args.plain:
                        print(
                            f"FINAL t={result['translation_completed_at']:.3f}s "
                            f"asr_lag={result['asr_latency_after_audio']:.3f}s "
                            f"zh_lag={result['translation_latency_after_audio']:.3f}s\n"
                            f"  ja={result['japanese']}\n  zh={result['chinese']}"
                        )
                result_queue.task_done()

            if not args.plain:
                screen = render(
                    display_audio,
                    duration,
                    audio_level(params, frames, display_audio),
                    partial,
                    japanese_lines,
                    chinese_lines,
                    job_queue.unfinished_tasks,
                )
                if screen != last_render:
                    print("\033[2J\033[H" + screen, end="", flush=True)
                    last_render = screen

            all_scheduled = next_job == len(jobs)
            all_processed = all_scheduled and job_queue.unfinished_tasks == 0
            if timeline_audio >= duration and all_processed and result_queue.empty():
                break
            time.sleep(0.05 if args.rate <= 2 else 0.01)

        if playback is not None:
            playback.wait(timeout=5)
        job_queue.put(None)
        job_queue.join()
        thread.join(timeout=2)

        final_events = [event for event in events if event.get("kind") == "final" and not event.get("error")]
        summary = {
            "audio": str(audio),
            "audio_duration_seconds": duration,
            "playback_rate": args.rate,
            "audio_played": not args.no_play,
            "segments": [segment.__dict__ for segment in segments],
            "events": events,
            "final_japanese": japanese_lines,
            "final_chinese": chinese_lines,
            "average_final_asr_latency_after_audio_seconds": (
                sum(event["asr_latency_after_audio"] for event in final_events) / len(final_events)
                if final_events
                else None
            ),
            "average_final_translation_latency_after_audio_seconds": (
                sum(event["translation_latency_after_audio"] for event in final_events)
                / len(final_events)
                if final_events
                else None
            ),
            "errors": [event for event in events if event.get("error")],
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if not args.plain:
            print("\n\n", end="")
        print("演示完成")
        print(f"稳定日文：{' '.join(japanese_lines)}")
        print(f"中文字幕：{' '.join(chinese_lines)}")
        print(
            "日文平均定稿延迟："
            f"{summary['average_final_asr_latency_after_audio_seconds']:.3f} 秒"
        )
        print(
            "中文平均定稿延迟："
            f"{summary['average_final_translation_latency_after_audio_seconds']:.3f} 秒"
        )
        print(f"结果：{summary_path}")
        return 0 if not summary["errors"] else 1
    finally:
        stop_worker.set()
        if playback is not None and playback.poll() is None:
            playback.terminate()
        temporary.cleanup()
        for server in reversed(managed):
            server.stop()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}")
        raise SystemExit(2) from error
