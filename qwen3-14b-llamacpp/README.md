# Qwen3-14B with llama.cpp

**研究页面（英文）：**[houjun.dev/lab/llm](https://houjun.dev/lab/llm/)

本项目用于在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上实验本地大语言模型推理。

完整阶段总结与日后使用入口见 `PROJECT-SUMMARY.md`。

## Target

- Model: Qwen3-14B
- Quantization: Q4_K_M
- Runtime: llama.cpp
- Acceleration: Apple Metal
- Format: GGUF

## Phase 0

本阶段只建立环境基线、隔离的 llama.cpp worktree 与 Release + Metal 构建；不下载模型，不运行慢速测试。

状态：已完成。

## Phase 1

已完成官方 `Qwen/Qwen3-14B-GGUF` 的单文件 `Q4_K_M` 下载、完整性校验与首次中文 Metal 推理。

关键结果：

- 模型大小：9,001,752,960 bytes（约 8.38 GiB）
- SHA-256：`500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0`
- Metal：41/41 层卸载到 Apple M2 Max GPU
- Prompt processing：83.8 tokens/s
- Generation：29.1 tokens/s
- 首次测试：中文正常、严格输出三句话、无 crash；该进程由 `/usr/bin/time` 报告 0 次 swap

注意：Phase 1 没有运行前的全局 swap 基线，因此不能单独归因；Phase 2 已补做运行前、运行中、运行后三个采样点，并确认正式基准期间全局 swap 没有增加。

## Phase 2

已完成 Qwen3-14B Q4_K_M 的 Metal 基准测试，每项预热后重复 3 次：

- Prompt processing（512 tokens）：262.25 ± 0.53 tokens/s
- Generation（128 tokens）：29.83 ± 0.03 tokens/s
- 41/41 层由 Metal 处理，Flash Attention 开启
- 进程最大常驻内存：约 8.60 GiB
- 测试前 / 运行中 / 测试后的全局 swap 都是 3192.75 MiB，没有增加
- 系统可用内存压力余量：62% → 33% → 62%

这意味着该模型在这台 32 GB Mac Studio 上有足够余量稳定运行；接下来可以测试上下文长度、不同量化或并发服务。

## Phase 3

长上下文安全扫描已准备好，默认依次测试 4K、8K、16K 提示词，并在每档继续生成 128 tokens。首次运行每档只测 1 次，以控制等待时间；结果安全后再做 3 次稳定性复测。

```bash
scripts/run_context_benchmark.sh
```

运行时不要同时开启 `llama-server` 或其他大型模型。完成后查看 `results/phase-3-context-benchmark.md`；原始数据保存在 `results/context-benchmark.csv`。

## Web Chat

日常聊天推荐 8K 上下文和 Q8_0 KV cache。在项目目录运行：

```bash
scripts/start_chat.sh
```

随后打开 `http://127.0.0.1:8080`。启动脚本所在的 Terminal 窗口需要保持打开；按 Control-C 停止服务。也可以用 `scripts/start_chat.sh 4096` 或 `scripts/start_chat.sh 16384` 临时选择其他上下文。

复杂数学、逻辑或代码任务可以开启 reasoning：

```bash
scripts/start_chat.sh 8192 on
```

第二个参数可选 `off`、`on` 或 `auto`；默认仍为 `off`。

第三个参数可选 `q8_0`、`q4_0` 或 `f16`；默认是经过 Phase 6 验证的 `q8_0`。

## Phase 4

离线 PDF 工具链让 Qwen 负责写作、本机工具负责生成文件：

```bash
scripts/generate_pdf.sh
```

默认结果是 `results/offline-pdf-demo.pdf`。详细说明见 `docs/03-offline-pdf.md`。

状态：已完成。首份 A4 中文 PDF 已通过逐页渲染与文字提取检查；详细结果见 `results/phase-4-offline-pdf.md`。

## Phase 5

本地 API 调用脚本：

```bash
scripts/ask_local_model.sh "请用三点说明本地模型的优点"
```

运行前先用 `scripts/start_chat.sh` 启动服务。详细说明见 `docs/04-local-api.md`。

状态：已完成。首次 `/v1/chat/completions` 中文请求成功，详细结果见 `results/phase-5-local-api.md`。

## Phase 6

比较 16K 上下文的 F16、Q8_0、Q4_0 KV cache：

```bash
scripts/run_kv_cache_benchmark.sh
```

模型权重始终是 Q4_K_M，只有聊天记忆的 K/V 精度发生变化。脚本从低内存配置开始测试，避免前一档高内存压力干扰后续观察。

状态：性能测试已完成。Q8_0 相比 F16 节省约 1.17 GiB，Q4_0 节省约 1.85 GiB，三档速度基本相同。结论见 `results/phase-6-analysis.md`。

Phase 6B 使用相同的 110 条长文档、问题、随机种子和固定 JSON 字段，对三档 KV cache 做可自动评分的质量测试：

```bash
scripts/run_kv_quality_ab.sh
```

状态：已完成。Q4_0、Q8_0、F16 均为 7/7；本次测试未发现 KV cache 量化造成的答案损失。日常 16K 聊天推荐 Q8_0，需要更多内存余量时可用 Q4_0。结论见 `results/phase-6b-analysis.md`。

## Phase 7

完全离线地询问本机 Markdown、TXT 和 PDF 文档：

```bash
scripts/start_chat.sh 16384 off q8_0
```

在另一个 Terminal 运行：

```bash
scripts/ask_documents.sh "为什么日常 16K 推荐 Q8_0？"
```

脚本先在本机检索相关段落，再让 Qwen 根据段落回答并标注来源。详细说明见 `docs/05-local-rag.md`。

状态：第一版已完成。项目 Markdown 问答和 PDF 页码引用都已通过端到端测试；结果见 `results/phase-7-local-rag.md`。

详细记录：

- `docs/01-setup.md`
- `results/system-info.txt`
- `results/phase-1-smoke-test.txt`
- `results/benchmark.csv`
- `results/phase-2-baseline.md`
- `results/phase-3-context-benchmark.md`
- `results/phase-4-offline-pdf.md`
- `results/phase-5-local-api.md`
- `results/phase-6-kv-cache.md`
- `results/phase-6-analysis.md`
- `results/phase-6b-kv-quality.md`
- `results/phase-6b-analysis.md`
- `results/kv-quality-scores.csv`
- `results/phase-7-local-rag.md`
- `results/rag-last-answer.md`
- `results/rag-last-retrieval.json`
- `results/rag-pdf-demo-answer.md`
- `results/rag-pdf-demo-retrieval.json`
- `docs/05-local-rag.md`
- `results/kv-cache-benchmark.csv`
- `results/offline-pdf-demo.pdf`
- `scripts/run_smoke_test.sh`
- `scripts/run_benchmark.sh`
- `scripts/run_context_benchmark.sh`
- `scripts/start_chat.sh`
- `scripts/generate_pdf.sh`
- `scripts/markdown_to_pdf.py`
- `scripts/ask_local_model.sh`
- `scripts/run_kv_cache_benchmark.sh`
- `scripts/run_kv_quality_ab.sh`
- `scripts/generate_kv_quality_fixture.py`
- `scripts/ask_documents.sh`
- `scripts/local_rag.py`

运行 `scripts/run_benchmark.sh` 会显示适合人眼阅读的表格，并把详细 Metal 与内存信息保存到 `results/benchmark-latest.log`。需要机器可读格式时，可运行 `scripts/run_benchmark.sh csv`。

## Layout

- `docs/`: 实验文档
- `scripts/`: 可复用脚本
- `tests/`: 项目测试
- `results/`: 环境与实验结果
- `worktrees/`: 本地源码 worktree（不纳入版本控制）

项目内路径均以本目录为基准使用相对路径。模型权重保存在项目外的统一缓存中，不在项目内复制。
