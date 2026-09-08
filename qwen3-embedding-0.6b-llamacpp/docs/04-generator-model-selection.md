# Phase 3 问答模型选择

## 选择

- 原始模型：`Qwen/Qwen3-4B-Instruct-2507`
- GGUF：`ggml-org/Qwen3-4B-Instruct-2507-Q8_0-GGUF`
- 文件：`qwen3-4b-instruct-2507-q8_0.gguf`
- 量化：Q8_0
- 参数量：约 4B
- 上下文上限：模型元数据为 262144；本项目主动限制为 8192
- 许可证：Apache-2.0

## 为什么适合本地 RAG

`Instruct-2507` 是只输出最终答案的指令模型，不生成 `<think>` reasoning 区块。RAG 的重点是忠实阅读提供的短资料、遵守拒答要求并生成清楚引用，不需要为每个问题做很长的内部推理。

Q8_0 文件约 4.28 GB。与 Q4 相比，它为文字、数字和多语言回答保留更多权重精度；与此前 14B Q4 模型相比，它更小、更快。AI-Lab 当前有约 130 GiB 可用空间，Mac Studio 有 32 GB 统一内存，容量充足。

向量模型与问答模型不会同时常驻：查询向量完成后 `llama-embedding` 退出，然后才启动 `llama-cli`。因此不能把两个进程的峰值内存简单相加。

## 固定下载信息

- 仓库 revision：`e6f794d44f9395d0184a966c27b5ae99ea356fcb`
- 预期大小：4,280,403,520 bytes
- SHA-256：`ae916ede1c010a26955ee8ae2e908bf8815a3f135ec860439ab924701c69d5f1`
- 下载脚本：`scripts/download_generator_model.sh`

下载器先写 `.part`，支持断点续传。只有大小和 SHA-256 均正确时才改为正式文件名。

## 来源

- Qwen 原模型：https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- llama.cpp 维护方 GGUF：https://huggingface.co/ggml-org/Qwen3-4B-Instruct-2507-Q8_0-GGUF
- Qwen llama.cpp 指南：https://github.com/QwenLM/Qwen3/blob/main/docs/source/run_locally/llama.cpp.md
