# Phase 0：多模态能力与测试设计核查

核查日期：2026-08-31

## 官方模型仓库

官方仓库：<https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-GGUF>

仓库当前明确提供：

| 组件 | 选定文件 | 准确字节数 |
| --- | --- | ---: |
| 语言模型 | `Qwen3VL-8B-Instruct-Q4_K_M.gguf` | 5,027,784,800 |
| 视觉 projector | `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` | 752,289,728 |

官方页面给出 `llama-server -hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M` 和 `llama-cli -hf ...` 的用法，并要求使用最新 llama.cpp。

下载前通过官方响应头锁定仓库 revision `f982a07559d4a2f6c8744d840bf6fccab30eea96`。选定 Q4_K_M 主模型 + Q8_0 projector，合计 5,780,074,528 字节（约 5.38 GiB）。调用 `-hf` 时保留默认开启的 `--mmproj-auto`，用实际缓存结果验证自动配对，而不是手工猜文件。

## llama.cpp / libmtmd

官方资料：

- <https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md>
- <https://github.com/ggml-org/llama.cpp/blob/master/tools/mtmd/README.md>
- <https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md>

当前官方 CLI 文档说明：

- `-hf` 在仓库存在 projector 时会自动下载它。
- `--mmproj-auto` 默认开启，可用 `--no-mmproj` 禁用。
- `--image`、`--audio`、`--video` 接受多模态文件；多个文件可以逗号分隔。
- 视频接口包含目标 FPS、时间戳间隔和 ffmpeg/ffprobe 路径参数。

libmtmd README 同时明确警告：多模态是 llama.cpp 内快速开发的子项目，breaking changes 在预期之内。主模型与 projector 通常是两个 GGUF 文件。

## 本机源码与构建

- 原仓库：`~/dev/opensource/llama.cpp`
- 原仓库工作分支：`master`，保持未修改。
- 第二项目刷新并固定 `origin/master`：`0190529ec450659b541ff608449401e68c27d098`。
- 独立 detached worktree：`worktrees/llama.cpp/`，不会切换或修改原仓库分支。
- 构建目录：`worktrees/llama.cpp/build-release-metal/`。
- 配置：Release、`GGML_METAL=ON`、嵌入式 Metal library、`MTMD_VIDEO=ON`。
- 已成功构建 `llama-cli`、`llama-server` 和 `llama-mtmd-cli`；版本输出为 build 10706 / commit `0190529ec`。
- `llama-mtmd-cli --help` 已确认 mmproj 自动选择、图片、多图、音频、视频、视频 FPS 与 ffmpeg 路径参数。
- 本机已有 `/opt/homebrew/bin/ffmpeg` 与 `/opt/homebrew/bin/ffprobe`。
- 第一项目当时只指定构建 `llama-cli`、`llama-server`、`llama-bench`，所以没有 `llama-mtmd-cli` 二进制。后续第二项目需要在独立 worktree 中显式加入该目标。

本机代码的通用图片入口使用 `stbi_load_from_memory(..., 3)` 解码为 RGB；WebP 与视频另走 ffmpeg 路径。这使 alpha、EXIF 方向、扩展名错配和损坏图片回退路径都值得单独记录，而不是预先假设行为。

## Phase 0 测试策略

先生成完全本地、无版权依赖、结果确定的测试图片，再下载模型。测试矩阵见 `tests/boundary-cases.md`。

优先观察的 upstream 信号：

- 合法输入导致 crash、assert、hang 或异常内存增长。
- 坏输入没有明确失败，反而进入错误的视频回退或长期等待。
- 多图输入只处理第一张、顺序错乱或 CLI/API 行为不一致。
- 自动 mmproj 选择错误、漏下载或精度组合不可解释。
- 同一输入在最小复现中稳定触发，并且最新 upstream 尚无相同 issue/PR。

模型普通识别错误、OCR 漏字或推理错误不自动视为 llama.cpp bug，必须先定位到解码、预处理、模板、projector 或接口层。

## Phase 0 结论

官方仓库、本机 llama.cpp、独立 worktree、Release + Metal 构建与边界资产均已满足进入多模态实验的前提。下一步只下载上述两份已锁定文件，并用 `tests/fixtures/images/11-ocr-clean.png` 做最小烟雾测试。
