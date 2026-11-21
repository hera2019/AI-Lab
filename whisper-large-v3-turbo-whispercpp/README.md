# Whisper large-v3-turbo with whisper.cpp

**研究页面（英文）：**[houjun.dev/lab/speech](https://houjun.dev/lab/speech/)

在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上研究本地语音识别。

## 实际应用

- 把会议、采访和语音备忘录变成可搜索文字
- 为视频生成带时间轴的 SRT/VTT 字幕
- 将中文、日文、英文和混合语言录音转写为原语言文字
- 将非英语语音直接翻译为英语
- 在本机离线处理不适合上传网络的录音
- 为以后评估 iPhone 离线语音识别积累数据

## 目标配置

- 主模型：`large-v3-turbo-q5_0`
- 主模型预计大小：约 547 MiB
- 推理框架：`whisper.cpp`
- 加速：Apple Metal
- 音频预处理：FFmpeg
- 模型权重：放在项目外的统一模型目录，不复制进项目

选择 turbo 的实际意义是优先获得较高准确率和较快响应；选择 Q5_0 的实际意义是显著减少磁盘与内存，同时保留足够的识别质量。是否需要非量化版或 `large-v3-q5_0`，必须由固定测试结果决定，而不是预先下载一堆模型。

## 重要边界

- Whisper 转写为语音原语言；其内建翻译任务主要是翻译成英语，不是任意语言互译。
- Whisper 可能在静音、噪声或模糊语音中生成并不存在的文字，必须专门测试。
- Whisper 本身不是可靠的说话人身份识别系统。说话轮次标记与“确认某个人是谁”是两件事。
- 对重要会议、医疗、法律或财务内容，自动转写不能代替人工复核。
- 未经同意录制和转写他人谈话可能涉及隐私与法律问题；测试只使用明确获准的录音或自行生成的固定音频。

## 计划阶段

当前状态：**Phase 0、Phase 1、Phase 2A、Phase 3、Phase 4A、Phase 4B、Phase 4C 和 Phase 4D 均已完成，本地语音识别研究大阶段结束**。清晰中、日、英语音的关键字段为 9/9；WAV、M4A、MP3、MOV 与字幕输出均已验证。Phase 3 证明 VAD 能消除静音幻觉、加速稀疏录音并收紧字幕结束时间。VAD 字幕时间轴异常已用官方 JFK 样例独立复现，但上游已有 Issue #3634/#3584，因此不另开重复报告。Phase 4A 使用 Whisper + Qwen3-4B 完成日语语音到中文测试。Phase 4B 正常速度播放模拟中的稳定日文/中文平均结束延迟为 0.753/0.953 秒。Phase 4C 已用真实耳机麦克风跑通中文原文以及日英翻译。Phase 4D 又完成逐句自动中、日、英判断与互译：标准音频三种语言的检测置信度均超过 0.998，真人麦克风验证了实际发音、停顿、短句和翻译边界，并修复实测发现的字幕字段与固定词误过滤问题。详见各阶段 `results/phase-*.md`。

归档状态：模型权重已于 2026-09-03 清理，释放约 2.98 GiB；项目代码、构建、音频、日志和研究文档均保留。重新运行测试前需要按照脚本默认路径重新准备 Whisper、Silero VAD 和 Qwen3-4B 模型。详见 `results/cleanup-2026-09-03.md`。

### Phase 0：环境、模型和测试设计

- 核对磁盘、编译环境、FFmpeg 和现有源码
- 只使用官方资料选择模型
- 建立固定音频与逐字标准答案
- 准备独立 whisper.cpp 源码和 Release + Metal 构建
- 暂不下载模型

### Phase 1：清晰语音基线

- 下载并校验 `large-v3-turbo-q5_0`
- 测试中文、日文、英文和混合语言
- 记录逐字准确率、标点、速度、内存和 Metal

状态：已完成。

### Phase 2：实际录音与字幕

- 手机录音、M4A/MP3/MOV 转换
- 时间戳、SRT/VTT 和长音频
- 计算实时系数，判断是否能跟上录音长度

状态：格式兼容和可控字幕基线已完成（Phase 2A）；真人 iPhone 麦克风录音和长音频仍待测试。

### Phase 3：噪声、静音与 VAD

- 咖啡馆/街道噪声、低音量和长静音
- 检查静音幻觉和重复文字
- 对比启用/关闭 VAD 的速度与切分质量

状态：已完成。纯静音会生成 `Thank you.`；VAD 可消除。67 秒稀疏录音约 2.19 倍加速。字幕时间轴异常已独立复现并完成上游查重。

### Phase 4：翻译、说话轮次与 upstream 评估

- 测试日语/中文语音翻译为英语
- 区分说话轮次与身份识别
- 将真实实现问题压缩为最小复现，再决定是否报告上游

状态：已完成。Phase 4A 验证日语语音到中文翻译，Phase 4B 验证正常速度播放模拟，Phase 4C 验证中文真实麦克风三语字幕，Phase 4D 验证逐句自动判断中文、日文或英文并补齐三语字幕。`Qwen3-0.6B` 速度快但质量失败；最终使用 `Qwen3-4B Q4_K_M`。Silero 流式 VAD 取代会重复和产生静音幻觉的简易滑动窗口。真人多语测试的定稿后计算平均约 1.92 秒，加句末静音确认后完整字幕平均约 2.75 秒；日语发音、句内长停顿、极短词和字母数字仍需人工核对。

运行中文麦克风三语字幕：

```bash
scripts/run_microphone_trilingual.sh
```

默认每次运行都会建立独立的 `results/microphone-trilingual/runs/YYYYMMDD-HHMMSS-PID/`，不会覆盖此前的录音和 `summary.json`。翻译只使用最近两句已确认中文作为消歧上下文，并且只输出当前句；中文听写原文不会被大模型改写。

运行逐句自动中日英识别和互译：

```bash
scripts/run_microphone_multilingual.sh
```

真人固定朗读稿为 `tests/microphone-multilingual-script.md`。默认结果保存在独立的 `results/microphone-multilingual/runs/YYYYMMDD-HHMMSS-PID/`；语言置信度低于 0.50 时会提示重点核对。

## 目录

```text
whisper-large-v3-turbo-whispercpp/
├── README.md
├── docs/
├── scripts/
├── tests/
│   └── fixtures/audio/
├── results/
└── worktrees/
```
