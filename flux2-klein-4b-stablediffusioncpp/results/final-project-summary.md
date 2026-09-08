# FLUX.2 klein 4B 本地实验最终总结

日期：2026-09-04

## 一句话结论

在 Mac Studio M2 Max / 32 GB Unified Memory 上，FLUX.2 klein 4B + stable-diffusion.cpp + Apple Metal 已完整验证：本地生图质量很好、4-step 速度可用、基础指令遵循不错、参考图编辑具有实用价值；但复杂场景中的精确数量、位置、文字、现实尺度和背景保持仍需要人工检查或传统图像工具辅助。

## 实验配置

- 扩散模型：FLUX.2 klein 4B `Q4_0`
- 文字编码器：Qwen3-4B `Q4_K_M`
- VAE：`full_encoder_small_decoder.safetensors`
- 推理框架：stable-diffusion.cpp
- commit：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- 构建：Release + Metal
- 机器：Mac Studio / Apple M2 Max / 32 GB Unified Memory
- 模型下载时占用：约 4.85 GiB
- 清理状态：2026-09-05 已删除项目外的模型权重，实验文档、脚本、日志和图片全部保留。

## 各阶段结论

### Phase 0：环境与模型准备

- Release + Metal 构建成功；`sd-cli` 和 `sd-server` 可用。
- Metal 正确识别 Apple M2 Max 和统一内存。
- 三个模型文件按固定 revision 下载并核对 SHA-256。

### Phase 1：第一张基线图

- 1024 × 1024、4 steps 的热运行墙钟时间约 55 秒。
- 峰值内存约 8 GiB，swap 为 0。
- 同 prompt、seed、参数、权重和 commit 两次得到逐字节一致的 PNG。
- 视觉质量很好，但复杂场景中出现多余猫、灯笼数量错误和 `AI LLAB` 拼写错误。

### Phase 2：提示遵循

- 简单场景中的三苹果、红绿蓝杯子、左右位置和 `LOCAL AI` 短文字全部成功。
- 详细摄影 prompt 能明显控制光线、杯子颜色、构图、景深和风格，但不能保证手部等细节完全正确。
- 结论：模型“能理解要求”，但成功率会随场景复杂度下降；一张成功图不能代表稳定可靠。

### Phase 3：图片编辑与多参考图

- 单参考改色成功，目标区域变化明显、非目标区域视觉上接近，但并非逐像素不变。
- 精确文字替换和复杂场景物体移除达到普通修图可用水平，Hera 人工复核通过。
- 双参考图能选对绿色杯子并自然融合，但放错位置，还擅自生成新桌子。
- 传统抠图与图层负责精确位置、尺寸和背景保护，FLUX 只做低强度局部自然化，再用蒙版回填，可把背景锁定为目标框外变化像素 0。
- 初版杯子过大暴露了一个重要事实：`Keep size` 只会保持输入像素尺寸，不会替人判断现实尺度。修正为 64 像素后，Hera 复核“大小正常、非常好”。

### Phase 4：性能与工程可靠性

- 512 方图约 27 秒，768 方图约 37 秒，1024 × 768 与 768 × 1024 约 47 秒，1024 方图约 55 秒。
- 所有正式尺寸测试均为 0 swap，峰值内存约 7.5–8.1 GiB。
- 512 图本次提示遵循最好；更高分辨率提供更多细节，但没有提高数量与位置准确率。
- 未知参数、缺失模型、缺失参考图、保存失败全部正确返回退出码 1。
- 没有发现新的 upstream 候选问题。

## 最实用的工作流

### 从零生成

1. 先用 512 检查 prompt 的主体、数量、文字和构图。
2. 用 768 做快速候选。
3. 确认方向后用目标横竖画幅或 1024 生成最终候选。
4. 人工检查文字、手、数量、左右位置、尺度和反射。

### 修改已有图片

1. 普通创意修图可直接用单参考编辑。
2. 位置和尺寸必须精确时，先用传统图层或蒙版确定物体。
3. 只让 FLUX 在小蒙版中、低 strength 下润色边缘与光影。
4. 用原图回填蒙版外像素，避免整张图被 VAE 轻微重绘。
5. 商品真实性优先时，宁可保留轻微贴图感，也不要让模型重画商品形状。

## 推荐默认值

- steps：4
- sampler：Euler
- CFG：1.0
- seed：显式固定并记录
- Metal：开启
- diffusion flash attention：开启
- CPU offload：开启
- 预览尺寸：512 × 512
- 普通草稿：768 × 768
- 最终候选：1024 或目标横竖画幅
- 保守局部润色：strength 约 0.35，并配合小蒙版与像素回填

## 已确认的边界

- 图片好看不等于指令完全正确。
- 更高分辨率不等于更强的文字、数量或空间推理。
- 固定 seed 只在其他参数和画布尺寸也相同时代表同一可复现样本。
- 参考图编辑会重绘全图的轻微纹理；自然语言不能保证未编辑区域完全不变。
- 多参考图可以选对对象，但精确落位不够可靠。
- 模型缺乏稳定的现实物体尺度判断，Prompt 也可能把错误尺寸锁死。
- 生成文字在简单场景可能正确，在复杂场景仍会拼错或乱写。

## 成果入口

- 环境与下载：`results/phase-0-and-download.md`
- 基线与复现：`results/phase-1-first-baseline.md`
- 摄影 prompt A/B：`results/phase-2-photo-prompt-ab.md`
- 指令拆分：`results/phase-2-instruction-isolation.md`
- 单点编辑：`results/phase-3-single-edit.md`
- 多参考图：`results/phase-3-multi-reference.md`
- 辅助工具精确合成：`results/phase-3-assisted-compositing.md`
- 尺寸、画幅与错误处理：`results/phase-4-performance-errors.md`
- 系统信息：`results/system-info.txt`
- 可重跑脚本：`scripts/`
- 完整图片、Prompt 和日志：`results/generated/`

## 项目状态

Phase 0–4 已完成，本项目正式告一段落。没有修改 upstream 源码、没有提交或推送 Git 变更。2026-09-05 清理了 `flux2-klein-4b` 模型目录，释放约 4.85 GiB；源码工作目录和全部研究成果仍保留。以后若继续体验，可复用现有脚本，但需要重新下载模型权重。
