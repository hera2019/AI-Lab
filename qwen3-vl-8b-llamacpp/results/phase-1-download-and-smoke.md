# Phase 1：下载与图片烟雾测试

执行日期：2026-08-31

## 下载清单

只下载了 Qwen 官方仓库 `Qwen/Qwen3-VL-8B-Instruct-GGUF` 的以下两份文件：

| 组件 | 文件 | 字节数 | SHA-256 |
| --- | --- | ---: | --- |
| 主模型 | `Qwen3VL-8B-Instruct-Q4_K_M.gguf` | 5,027,784,800 | `67d1659bfe71b89d50b45a4ad1a9e5b997e5bb16ce5da66a6a6167abd569e9e2` |
| projector | `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` | 752,289,728 | `c6ba85508d82f42590e6eb77d5340369ab6fecf107a7561d809523d8aa5f3bfd` |

仓库 revision：`f982a07559d4a2f6c8744d840bf6fccab30eea96`。

llama.cpp 的 `-hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M` 与默认 `--mmproj-auto` 自动选中了上述 Q8_0 projector。下载后对两个完整文件重新计算 SHA-256，均与官方响应头一致；缓存中没有残留 `.downloadInProgress` 文件。

模型权重保存在项目外的统一缓存中，未复制进项目目录。缓存实际占用 5,652,612 KiB（约 5.39 GiB）。

## 运行环境

- llama.cpp：build 10706，commit `0190529ec450659b541ff608449401e68c27d098`
- 构建：Release + Metal + Apple Accelerate
- 设备：`MTL0: Apple M2 Max`
- 工具报告的模态：text、vision、video
- 测试脚本：`scripts/run_ocr_smoke.sh`

## OCR-001

输入：`tests/fixtures/images/11-ocr-clean.png`

要求：逐行抄录全部文字，只返回抄录结果。

模型输出：

```text
仓库：东京-7
温度：23.5℃
批次：QVL-8B-042
合计：1,248
Do not guess missing text.
```

速度：

- 图片/提示处理：242.3 token/s
- 生成：51.1 token/s

严格判定：**FAIL（非常接近）**。

原图第二行是 `温度：23.5°C`，其中 `°C` 是两个字符（U+00B0 + U+0043）；模型输出的 `℃` 是单个字符（U+2103）。视觉含义相同，但不满足“逐字符完全匹配”。其余四行完全正确。

这属于 OCR/Unicode 表达结果，目前没有证据表明是 llama.cpp 或 libmtmd bug。后续评分应同时记录：

1. 严格字符匹配结果。
2. Unicode NFKC 归一化后的语义等价结果。

## 结论

下载、自动 projector 配对、完整性校验、Metal 设备识别、图片传入和本地生成均成功。可以进入固定图片集的基线测试；第一优先级是 OCR-002、OCR-003，然后再做三图顺序测试。
