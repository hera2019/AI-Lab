# FLUX.2 klein 4B with stable-diffusion.cpp

**研究页面（英文）：**[houjun.dev/lab/image](https://houjun.dev/lab/image/)

在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上研究本地图片生成与编辑。

## 实际应用意义

这个项目把本地 AI 从“理解文字、图片和语音”推进到“生成和修改图片”。目标不是只生成一张好看的图，而是判断这套本地方案能否稳定用于概念图、配图、设计草稿、带文字海报和受控图片编辑。

本地运行的价值包括隐私、离线可用、固定 seed 可复现和不按张付费；代价是模型较大、速度取决于本机 Metal 实现，而且图片可能看似漂亮却没有遵循数量、空间关系或文字要求。

## 选择方案

- 模型：`black-forest-labs/FLUX.2-klein-4B`
- 推理框架：`stable-diffusion.cpp`
- 加速：Apple Metal
- 初始精度：扩散模型 `Q4_0`，文字编码器 Qwen3-4B `Q4_K_M`
- 标准尺寸：先从 `1024 × 1024`、4 steps 开始
- 能力：text-to-image、image-to-image、多参考图编辑
- 许可：Apache 2.0

选择 4B distilled 版本的实际意义是：官方设计为 4 steps 的低延迟生成，并称原始版本约需 13 GB 显存；32 GB Unified Memory 理论上有余量。官方速度数据来自其他 GPU，不能代表 M2 Max，所以本项目必须实测 Metal 的加载时间、单张耗时、峰值内存和 swap。

## 预计下载预算

只下载运行所需的精确文件，不下载整个量化仓库：

| 组件 | 初始选择 | 预计大小 |
| --- | --- | ---: |
| FLUX.2 klein 4B 扩散模型 | `flux-2-klein-4b-Q4_0.gguf` | 2.46 GB |
| Qwen3-4B 文字编码器 | `Qwen3-4B-Q4_K_M.gguf` | 2.50 GB |
| FLUX.2 VAE 替代方案 | `full_encoder_small_decoder.safetensors` | 250 MB |
| 合计 | 不含源码和构建 | 约 5.21 GB（4.85 GiB） |

三个文件均固定到下载前核对过的仓库 revision，并用官方文件清单中的 SHA-256 验证。`full_encoder_small_decoder.safetensors` 是 stable-diffusion.cpp FLUX.2 文档明确列出的替代 VAE，保留编码能力以支持后续图片编辑。

## 阶段计划

### Phase 0：环境与可复现构建

- 检查磁盘、Xcode/AppleClang、CMake 和已有源码
- 记录 `stable-diffusion.cpp` commit，建立独立工作目录
- 构建 Release + Metal 的 `sd-cli` 和可用服务器/网页入口
- 验证 Metal 后端确实加载，不用“能运行”冒充“GPU 已启用”
- 只设计测试，不下载模型

实际应用意义：先证明运行框架与本机兼容，避免下载 5 GB 后才发现构建或 Metal 路线不可用。

### Phase 1：最小可用生图与性能基线

- 下载并校验三个精确模型文件
- 固定 seed 生成第一张英文提示图和第一张中文提示图
- 记录模型加载、文字编码、4 个采样 steps、VAE 解码和总耗时
- 记录峰值内存、swap、输出尺寸、PNG 元数据与文件哈希
- 同一 seed 重复生成，验证可复现性

实际应用意义：确认“这台 Mac 真能生成图”，并得到以后所有质量测试的速度和稳定性基线。

### Phase 2：提示遵循与文字渲染

- 物体数量、颜色、左右/前后关系和否定要求
- 中文、英文及中英混排短文字
- 人物手指、几何结构、细小物体和复杂场景
- 中英文提示表达同一场景时的一致性
- 使用固定 seed 和人工/OCR 双重核对，不凭审美印象评分

实际应用意义：实际设计工作最怕“图很好看，但关键要求错了”；本阶段专门测试可控性。

### Phase 3：图片编辑与多参考图

- 修改一个指定物体，同时检查背景和其他物体是否被误改
- 改颜色、增删物体、替换图片中的短文字
- 单图与多参考图输入
- 不同宽高比、EXIF 旋转、透明 PNG 和 Unicode 文件名

实际应用意义：编辑比从零生图更接近日常修图和产品设计，同时更容易暴露输入处理与保持区域的问题。

### Phase 4：压力、错误处理与 upstream 价值

- 512、768、1024 分辨率和横竖构图的时间/内存曲线
- Q4_0 与更高精度是否值得额外空间和耗时
- 损坏图片、缺失模型、错误参数和不可写输出路径的非零退出码
- CLI、内置 Web UI/API 的行为一致性
- Metal 与 CPU 的最小对照，不运行无意义的超慢全套测试
- 查重后再决定是否向 `stable-diffusion.cpp` 提交 Issue/PR

实际应用意义：把一次演示变成可自动化、能发现真实工程问题的测试项目。

## 边界

- 模型卡明确说明：它不提供事实信息，可能生成错误或扭曲文字，也可能不遵循提示。
- 只使用自己生成或明确获准的参考图，不测试冒充真人、欺骗性内容或未经同意的人脸编辑。
- 本项目不把主观“好看”当作唯一指标；原始提示、seed、参数、耗时和输出图必须一起保存。
- 模型权重统一放在项目外的 `AI-Models`，项目目录只保存代码、测试设计、缩略结果和记录。

## 当前状态

Phase 0–4 已全部完成，项目正式告一段落。Release + Metal 运行稳定；512–1024 的正式生图测试全部为 0 swap，墙钟时间约 27–55 秒。单参考图编辑约 108–121 秒，双参考图约 177 秒。提示遵循、文字、单点编辑、多参考图、辅助合成、横竖画幅和四类错误退出均已覆盖。

最终结论：它非常适合本地概念图、配图、设计草稿和人工监督下的照片编辑，但复杂场景中的精确数量、落位、文字、现实尺度与背景保持不能只靠自然语言。对于严格编辑，已验证“传统图层确定位置与尺寸 + FLUX 低强度局部润色 + 蒙版外像素回填”的组合流程；64 像素杯子修正版由 Hera 人工复核通过。完整总结见 `results/final-project-summary.md`，Phase 4 见 `results/phase-4-performance-errors.md`。

清理记录：2026-09-05 已删除项目外的 FLUX.2 klein 4B 模型权重，释放约 4.85 GiB。README、脚本、日志、报告、生成图和 stable-diffusion.cpp 工作目录均保留；如需再次运行，需要重新下载模型。

## 资料

- https://github.com/leejet/stable-diffusion.cpp
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/build.md
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/flux2.md
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/tree/main
- https://huggingface.co/unsloth/Qwen3-4B-GGUF/tree/main
