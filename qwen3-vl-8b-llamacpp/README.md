# Qwen3-VL-8B with llama.cpp

本项目用于在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上实验本地多模态模型。

## 当前状态

Phase 0 至 Phase 14 已完成，项目进入总结状态。图片/OCR、多图、格式边界、视频、真实日文票据、Apple Vision、本地 API、Gemini A/B、视觉推理、自然照片、提示鲁棒性和 1/2/4 并发均已实测。4 并发共 7/7 请求正确且没有串线或新增 swap，但吞吐只比单并发提高约 8.2%，平均延迟从 4.55 秒增至 16.79 秒。完整项目结论见 `PROJECT-SUMMARY.md`。

OCR-001 成功完成本地图片输入与生成，但严格字符匹配发现 `°C` 被输出为视觉等价的单字符 `℃`，因此严格评分为 FAIL，而不是把“看起来一样”误报成完全正确。详见 `results/phase-1-download-and-smoke.md`。

## 目标配置

- 模型仓库：`Qwen/Qwen3-VL-8B-Instruct-GGUF`
- 模型主体量化：`Q4_K_M`
- 推理框架：llama.cpp
- 加速：Apple Metal
- 硬件：Mac Studio，Apple M2 Max，32 GB Unified Memory
- 模型权重：实验完成后已从项目外统一缓存清理；需要重跑时可由 `-hf` 重新下载

多模态模型还需要独立视觉投影文件。本项目运行时由 llama.cpp 的 `--mmproj-auto` 自动配对官方 `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf`。项目结束后，主模型和 projector 缓存已删除，只保留实验成果；详见 `results/model-cache-cleanup.md`。

## 实验目标

1. **图片理解**
   - 描述图片主体、场景、关系和细节。
   - 测试照片、截图、图表、插图和 UI 界面。

2. **OCR**
   - 识别中英文印刷文字、数字和简单表格。
   - 观察小字号、低对比度、旋转、模糊和复杂排版的边界。

3. **多图输入**
   - 比较、排序和关联多张图片。
   - 检查图片顺序、来源标记和跨图引用是否可靠。

4. **视频理解**
   - 核实当前 llama.cpp 与 libmtmd 实际支持的输入形式。
   - 区分原生视频输入与“抽帧后按多图输入”的能力，不把两者混为一谈。

5. **libmtmd / multimodal 边界测试**
   - 图片数量、尺寸、格式和长宽比。
   - 上下文占用、内存、Metal 路径和错误处理。
   - 不支持或异常输入能否明确失败，而不是静默产生错误答案。

6. **寻找有价值的 upstream issue / PR**
   - 先构造最小可复现测试。
   - 区分模型能力、模型转换、模板、libmtmd 和 llama.cpp 实现问题。
   - 只有证据充分、当前上游未解决时，才考虑报告 issue 或准备修复。

## 计划阶段

### Phase 0：环境与能力核查

- 检查磁盘、现有 llama.cpp 状态和当前多模态支持。
- 核实模型仓库所需的模型主体与视觉投影文件。
- 设计独立 worktree 和 Release + Metal 构建。
- 记录 libmtmd 相关工具、参数和已知限制。

### Phase 1：最小图片烟雾测试

- 只下载运行所需的 Q4_K_M 模型主体和对应多模态文件。
- 校验文件完整性。
- 使用一张版权清晰、内容简单的测试图片验证加载、Metal 和中文回答。

### Phase 2：图片理解与 OCR 基线

- 建立固定图片集和答案标准。
- 分开记录描述能力、文字识别、数字准确率与幻觉。

### Phase 3：多图与视频边界

- 测试多图关系、顺序和上下文消耗。
- 如当前路径不支持直接视频，则使用可复现的本地抽帧流程进行测试并明确标注。

### Phase 4：回归测试与 upstream 评估

- 将真实问题压缩成最小复现。
- 检查最新上游状态与已有 issue / PR。
- 再决定仅记录结论、提交 issue，还是实现回归测试和修复。

## 项目边界

- 项目内路径统一使用相对路径。
- 模型文件不放进项目目录。
- 每次下载前先列出准确文件和预计空间。
- 不修改已有贡献分支；源码实验使用独立 worktree。
- 不在没有复现和上游核查的情况下提交 issue 或 PR。
- benchmark、日志、测试材料和结论保存在 `results/` 与 `tests/`。

## 目录结构

```text
qwen3-vl-8b-llamacpp/
├── README.md
├── docs/       # 环境、模型和实验说明
├── scripts/    # 可复用运行与测试脚本
├── tests/      # 固定图片、问题与答案标准
└── results/    # 环境记录、日志、基准和结论
```

OCR、多图顺序以及 10 种合法图片格式边界、3 种损坏输入均已完成。真实日文餐厅票据的 Qwen3-VL 严格关键业务字段为 16/17，独立 CLI 端到端耗时 11.21 秒。Apple Vision 原图文字 OCR 为 0.72 秒，保留了 `TP` 的独立坐标，但存在高置信度日期误读且未检出表格。Phase 9 已实际跑通 Apple Vision OCR、常驻 OpenAI-compatible 多模态 API、强制 JSON Schema 与确定性账目校验；三次结果完全一致但只有 24/27 项严格正确。Phase 10 使用相同图片、OCR 和 schema 完成 Gemini 3.6 Flash A/B：5.47 秒，原始字符 26/27，Unicode NFKC 后业务字段 27/27；但模型没有主动报告 OCR 日期冲突，最终仍由确定性规则标记人工复核。`gemini-3.7-flash` 同期因高负载连续返回 HTTP 500，也验证了网络服务必须有有限重试和备用模型。原生 `--video` 路径的顺序、Unicode 路径、极短视频、头部/尾部 `moov`、可变时间戳和损坏容器边界已完成。透明 alpha 和无效媒体退出码已经压缩为不依赖模型回答的最小复现：alpha 问题由 libmtmd 像素探针直接证明；退出码问题由 `llama-mtmd-cli` 的正确失败对照和标准 `llama-cli` 的代码路径定位。EXIF 是已有上游限制。

项目资料：

- `docs/01-phase-0-capability-check.md`
- `docs/02-gemini-receipt-ab-test.md`
- `tests/boundary-cases.md`
- `scripts/generate_boundary_images.sh`
- `results/phase-0-boundary-assets.md`
- `results/system-info.txt`
- `results/phase-1-download-and-smoke.md`
- `results/phase-2-ocr-baseline.md`
- `results/phase-2-multi-image-order.md`
- `results/phase-3-image-boundaries.md`
- `results/phase-4-minimal-reproductions.md`
- `results/phase-5-video-baseline.md`
- `results/phase-6-video-boundaries.md`
- `results/phase-7-real-japanese-receipt-ocr.md`
- `results/phase-8-apple-vision-hybrid-ocr.md`
- `results/phase-9-hybrid-receipt-api.md`
- `results/phase-10-gemini-receipt-ab.md`
- `results/phase-11-visual-reasoning.md`
- `results/phase-12-natural-scene-reliability.md`
- `results/phase-13-prompt-robustness.md`
- `results/phase-14-concurrency-scaling.md`
- `results/model-cache-cleanup.md`
- `scripts/run_ocr_smoke.sh`
- `scripts/run_image_boundary_baseline.sh`
- `scripts/run_mtmd_decode_probe.sh`
- `scripts/repro_invalid_media_exit_code.sh`
- `scripts/generate_video_fixtures.sh`
- `scripts/run_video_baseline.sh`
- `scripts/run_video_boundary_tests.sh`
- `scripts/run_real_japanese_receipt_ocr.sh`
- `scripts/apple_vision_receipt_ocr.swift`
- `scripts/run_apple_vision_receipt_ocr.sh`
- `scripts/build_hybrid_receipt_request.py`
- `scripts/validate_hybrid_receipt_responses.py`
- `scripts/run_hybrid_receipt_server.sh`
- `scripts/run_gemini_receipt_ab.py`
- `scripts/run_gemini_receipt_ab.sh`
- `scripts/generate_visual_reasoning_fixtures.sh`
- `scripts/run_visual_reasoning_baseline.py`
- `scripts/generate_natural_scene_fixtures.sh`
- `scripts/run_natural_scene_baseline.py`
- `scripts/run_prompt_robustness.py`
- `scripts/run_concurrency_scaling.py`
