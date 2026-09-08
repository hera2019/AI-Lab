# 官方资料核对

核对日期：2026-09-03

## stable-diffusion.cpp

- 项目 README 明确支持 macOS、Metal、GGUF、FLUX.2-klein、图片生成和图片编辑。
- 构建文档使用 `-DSD_METAL=ON`，同时提醒 Metal 在很大矩阵上的效率仍可能有问题。因此 M2 Max 性能必须实测。
- FLUX.2 文档为 klein 4B 指定扩散模型、VAE 和 Qwen3-4B 文字编码器，并给出 4 steps、CFG 1.0、diffusion flash attention 与 CPU offload 示例。

## FLUX.2 klein 4B

- Black Forest Labs 模型卡：4B 参数、Apache 2.0、支持 text-to-image、image editing 和 multi-reference。
- 模型卡称约需 13 GB VRAM，并以消费级 NVIDIA GPU 描述性能；这不是 Apple M2 Max 的基准。
- 模型卡明确提醒文字可能错误/扭曲、提示可能不被遵循，因此文字和提示遵循必须单列测试。

## 下载预算来源

- `leejet/FLUX.2-klein-4B-GGUF`：Q4_0 为 2.46 GB，Q8_0 为 4.30 GB。
- `unsloth/Qwen3-4B-GGUF`：Q4_K_M 为 2.50 GB。
- 官方 `FLUX.2-small-decoder` 的 `full_encoder_small_decoder.safetensors`：249,519,092 字节。stable-diffusion.cpp 文档将它列为 FLUX.2 标准 VAE 的替代方案。

本次固定 revision：

- `leejet/FLUX.2-klein-4B-GGUF`：`3b1f5a9dc3abb32238b053aeb3d823c30afdacbd`
- `unsloth/Qwen3-4B-GGUF`：`22c9fc8a8c7700b76a1789366280a6a5a1ad1120`
- `black-forest-labs/FLUX.2-small-decoder`：`a3efc24f613ef42d9428af62fdbd6f5fd8856c4a`

正式下载时必须再次读取仓库文件清单，防止文件名或 revision 已变化，并保存实际 commit/revision 与 SHA-256。
