# Wan2.2 TI2V 5B with stable-diffusion.cpp

**研究页面（英文）：**[houjun.dev/lab/video](https://houjun.dev/lab/video/)

在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上测试本地文字生成视频与图片生成视频。

## 实际应用意义

图片模型只需要保证一帧看起来合理；视频模型还要保持人物、物体、背景和运动在连续帧中一致。本项目重点判断这台 Mac 能否在可接受的时间与内存范围内生成短视频，以及画面是否存在闪烁、变形、物体漂移或动作不连贯。

## 方案

- 视频模型：`Wan-AI/Wan2.2-TI2V-5B` 的 `Q4_K_M` GGUF
- 快速预览模型：FastWan2.2 TI2V 5B `Q8_0` 社区蒸馏版
- 文字编码器：UMT5-XXL `Q5_K_M` GGUF
- 视频 VAE：Wan2.2 VAE
- 快速预览解码器：Wan2.2 TAEHV
- 实验解码器：官方 Wan2.2 TAEHV Super（已验证当前 stable-diffusion.cpp 尚不兼容）
- 推理框架：`stable-diffusion.cpp`
- 加速：Apple Metal + diffusion flash attention
- 目标能力：Text-to-Video 与 Image-to-Video
- 首次运行：低帧数、较低分辨率，先测稳定性和资源占用，再逐步提高

选择 5B 而不是 14B/22B 的实际意义是：它同时支持文字和图片输入，模型文件与运行内存更适合 32 GB Unified Memory。扩散模型使用 Q4_K_M 控制体积；文字编码器使用稍高的 Q5_K_M，尽量减少长提示词理解损失。

## 阶段计划

### Phase 0：环境、构建和模型清单

- 建立独立项目与源码目录；
- 固定 stable-diffusion.cpp commit；
- 构建 Release + Metal；
- 只下载运行必需的三个权重并校验哈希。

实际应用意义：先保证每个文件来源明确、版本可复现，避免因错误模型组合浪费数小时生成时间。

### Phase 1：最短视频冒烟测试

- 先生成短帧数、低分辨率视频；
- 记录模型加载、文字编码、采样、VAE 解码、总耗时、峰值内存和 swap；
- 用 ffprobe/ffmpeg 检查帧数、尺寸、帧率和文件可解码性。

实际应用意义：先回答“能否稳定完成”，再谈质量；视频任务若在最后解码阶段失败，前面的等待都会白费。

### Phase 2：文字生成视频

- 固定 seed 测试简单动作、镜头运动和复杂场景；
- 检查主体身份、物体数量、背景、运动连续性和闪烁；
- 比较不同帧数与分辨率的时间、内存和质量。

### Phase 3：图片生成视频

- 使用本项目自己生成或明确获准的图片；
- 测试微动作、明显动作、镜头推进与静止背景；
- 检查首帧保持、面部/物体变形和场景漂移。

### Phase 4：边界与工程可靠性

- 错误输入、缺失模型、损坏图片和不可写输出；
- 中途终止后的临时文件与退出码；
- 判断是否存在值得提交给 stable-diffusion.cpp 的 Issue/PR。

### Phase 5：FastWan 3-step 加速

- 使用 FastWan `Q8_0` + TAEHV；
- 以 Euler + LCM、3 步、CFG 1.0 复跑相同 T2V 与 I2V 题材；
- 与原版 20 步基线比较总时间、采样时间、内存、主体和光影稳定性。

实际应用意义：把约 7 分钟的预览压到约 1 分钟，使本机反复试动作和 Prompt 真正可用，再把少数满意候选交给较慢的原版 20 步生成。

## 边界

- 不测试未经同意的真人冒充或欺骗性视频。
- 不把一段成功样片当作稳定能力，所有结论都保存 Prompt、seed、参数与日志。
- 首轮不追求 720p 长视频；先根据实测内存和耗时决定上限。
- 模型权重放在项目外，项目只保存研究成果与可复现脚本。

## 当前状态

Phase 0 已完成：源码版本、Release + Metal 构建及三个模型文件均已固定并校验。

Phase 1 已完成：2 步、416×256、17 帧的端到端冒烟测试成功，峰值常驻内存约 14.00 GiB，未发生 swap。

Phase 2 已完成：确认 416×256 和 17 帧均不是 Wan2.2 TI2V 5B 的可靠视频工作区；832×480 单帧正常，832×480、33 帧 + TAE 的 T2V 正常。

Phase 3 已完成：832×480、33 帧 I2V 成功保持输入猫的身份、构图与背景，并完成微动作。

Phase 4 已完成：缺失图片、空图片、伪 JPEG 与缺失模型均快速返回 exit code 1。完整结论见 `results/PROJECT-SUMMARY.md`。

Phase 5 已完成：FastWan 3-step T2V 与 I2V 分别约 57 秒和 54 秒完成，0 swap，较原版完整生成快约 7.5–7.8 倍。65 帧动作测试中，抬爪版动作清楚但末段透视过大，原地转头版更自然稳定，眨眼单项版能闭合双眼但未重新睁开。详细结果见 `results/phase-5-fastwan.md`。

Phase 5 收尾兼容性测试也已完成：官方 `taew2_2_super` 权重校验正确，但 stable-diffusion.cpp 最新 `master` 在模型元数据验证阶段返回 exit code 1，未开始采样。原因是 Super 使用了不同于当前实现的 `SuperMemBlock` 与 PixelShuffle 网络结构。证据与边界见 `results/phase-5-super-tae-compatibility.md`。
