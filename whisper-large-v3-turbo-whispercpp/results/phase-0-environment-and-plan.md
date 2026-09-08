# Phase 0：环境、模型选择与构建

## 实际应用意义

Phase 0 的目的不是先得到一条漂亮转写，而是保证后续结果能回答真正的问题：手机录音能否处理、中文日文是否可靠、字幕时间轴能否使用、静音是否会胡编、速度能否跟上录音，以及错误来自模型还是运行框架。

## 本机环境

- Mac Studio，Apple M2 Max，32 GB Unified Memory
- macOS 26.6.2
- AppleClang 21.0.0
- CMake 4.4.2
- FFmpeg 9.0.1
- 可用磁盘约 36 GiB

没有发现本机已有的 `whisper.cpp`，新源码因此放在本项目独立目录，不影响其他项目。

## 模型结论

Phase 1 主模型选为 `large-v3-turbo-q5_0`：

- OpenAI 将 turbo 列为多语言模型，并说明它针对推理速度优化。
- whisper.cpp 官方模型表列出的 Q5_0 文件约 547 MiB。
- 32 GB M2 Max 能轻松容纳；Q5_0 的主要价值是减少磁盘、载入时间和以后移动端试验成本。
- 暂不同时下载多个模型。如果固定测试证明翻译或困难语音不足，再比较 `large-v3-q5_0`。

Whisper 的内建 translation 任务是把源语言语音翻译为英语。日语语音转中文应拆成“日语 ASR + 文字翻译”，不能把 Whisper 的 `--translate` 当成任意目标语言翻译器。

## 源码与构建

```text
repository=https://github.com/ggml-org/whisper.cpp
branch=master
commit=eacbd8234c6654cdbf2c377f72b2106875479bdc
version=1.9.3-dev
git_status=clean
```

成功完成 Release 构建：

```text
GGML_METAL=ON
GGML_METAL_EMBED_LIBRARY=ON
WHISPER_COMMON_FFMPEG=ON
WHISPER_BUILD_TESTS=OFF
```

已生成并验证三个 arm64 工具：

- `worktrees/whisper.cpp/build-release-metal/bin/whisper-cli`
- `worktrees/whisper.cpp/build-release-metal/bin/whisper-server`
- `worktrees/whisper.cpp/build-release-metal/bin/whisper-bench`

Metal 和 Accelerate 均找到；FFmpeg 的库和头文件均成功链接。OpenMP 未找到，但这不是本次 Metal/Accelerate 构建的阻断条件。

## 音频格式边界

当前 `whisper-cli --help` 列出：

```text
flac, mp3, ogg, wav
```

没有列出 M4A。即使 FFmpeg 已链接，也不能在没有运行证据时声称 M4A 直读可用。后续将使用同一音频同时测试：

1. 原始 M4A 直接输入。
2. FFmpeg 转成 16 kHz、单声道、16-bit PCM WAV 后输入。

实际应用意义是保证 iPhone 录音不会因为容器差异静默失败或改变识别结果。

## 测试矩阵

`tests/test-matrix.md` 已覆盖：

- 中、日、英和混合语言
- 手机格式、时间戳、SRT/VTT、长音频
- 噪声、静音幻觉与 VAD
- 翻译成英语
- 说话轮次与身份识别边界
- 空文件、损坏文件和退出码

每项都记录实际应用意义、真值与评分方式。

## 上游协作边界

当前 whisper.cpp 的仓库说明要求 AI 只能辅助，禁止 AI 撰写 PR 描述、commit message 或 reviewer 回复，也要求贡献者能够独立理解和维护代码。本项目会遵守该政策：先学习、复现和解释；如以后发现问题，用户理解并决定设计后再考虑人工主导的贡献。

## Phase 0 最终状态

- 项目骨架：完成
- 官方资料核对：完成
- 测试矩阵：完成
- 独立源码：完成
- Release + Metal + FFmpeg 构建：完成
- 源码状态：干净
- Whisper 模型：未下载
- VAD 模型：未下载
- Core ML 模型：未生成

Phase 0 到此停止。Phase 1 开始前应先展示 547 MiB 主模型的准确下载目标、校验方式和磁盘变化。

## 官方资料

- OpenAI Whisper model card：`https://github.com/openai/whisper/blob/main/model-card.md`
- whisper.cpp README：`https://github.com/ggml-org/whisper.cpp`
- whisper.cpp models：`https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md`
