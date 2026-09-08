# Phase 0：环境、模型与测试设计

## 为什么先做 Phase 0

语音识别不能只用一段“听起来不错”的录音判断。真实应用会遇到语言切换、背景噪声、静音、截断、不同容器和不准确时间戳。先设计标准答案，可以区分模型错误、音频转换错误和 whisper.cpp 实现问题，也能避免下载不必要的多个大模型。

## 模型选择

主候选：`large-v3-turbo-q5_0`。

- OpenAI 将 turbo 描述为为推理速度优化的多语言 Whisper 模型。
- whisper.cpp 官方模型表给出的 Q5_0 文件约 547 MiB。
- M2 Max 32 GB 不受内存容量限制，选择 Q5_0 主要为了磁盘、载入速度和以后移动端评估，而不是因为模型装不下。
- 如果翻译成英语或困难语音表现不足，再考虑 `large-v3-q5_0`；不在 Phase 0 重复下载。

## Apple 加速路线

第一基线使用 Metal，因为 whisper.cpp 在 Apple Silicon 上可以通过 Metal 使用 GPU。

Core ML 是另一条可选路线：它把 encoder 放到 Apple Neural Engine，官方说明相对 CPU-only 可能显著加速。它需要额外生成 Core ML 模型和安装依赖，因此应在 Metal 基线完成后单独 A/B，不能把两条路径混在第一组结果里。

## 音频输入

whisper.cpp 官方 CLI 的稳定基线格式是 16 kHz、单声道、16-bit PCM WAV。项目已安装 FFmpeg，可将 M4A、MP3、MOV 等真实文件确定性转换为该格式：

```bash
ffmpeg -i input.m4a -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

原始文件和转换后文件都应保留 SHA-256，避免把转换变化误判成模型变化。

## 官方资料

- OpenAI Whisper model card：`https://github.com/openai/whisper/blob/main/model-card.md`
- whisper.cpp：`https://github.com/ggml-org/whisper.cpp`
- whisper.cpp models：`https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md`

## Phase 0 停止条件

- 项目骨架和测试矩阵完成
- 独立 whisper.cpp 源码准备完成
- Release + Metal 工具编译完成
- 系统、工具版本和源码 commit 已记录
- 没有下载任何 Whisper 或 VAD 权重
