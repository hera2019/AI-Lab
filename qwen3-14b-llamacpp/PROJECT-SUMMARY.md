# 本地 AI 实验项目总结

完成日期：2026-08-30

## 一、项目概览

这次实验从一个空目录开始，最终搭建出一套可复现、可交互、可测试的本地大模型工作台。

项目目录由 `AITest` 更名为 `AI-Lab`，第一个项目为 `qwen3-14b-llamacpp`。项目文件与大体积模型权重分开保存：

- 当前目录：代码、说明、测试和结果。
- `~/Documents/AI-Models/huggingface`：统一保存模型权重缓存。

最终使用的核心组合：

| 项目 | 配置 |
| --- | --- |
| 设备 | Mac Studio，Apple M2 Max |
| 内存 | 32 GB Unified Memory |
| 系统 | macOS 26.6.2，arm64 |
| 模型 | Qwen3-14B Q4_K_M |
| 模型格式 | GGUF，约 8.38 GiB |
| 推理框架 | llama.cpp |
| 加速 | Apple Metal + Apple Accelerate |
| llama.cpp 构建 | Release + Metal，commit `bebc9350e`，build 10700 |
| 日常推荐 | 8K 上下文、Reasoning off、Q8_0 KV cache |
| 长文档推荐 | 16K 上下文、Reasoning off、Q8_0 KV cache |

## 二、完成的阶段

### Phase 0：环境与隔离构建

- 检查了 macOS、芯片、内存、磁盘和 AppleClang。
- 找到已有的 llama.cpp 仓库，并保持原仓库与已有分支不变。
- 基于当时最新的 `origin/master` 建立独立 detached worktree：`worktrees/llama.cpp`。
- 编译 Release + Metal 版本的 `llama-cli`、`llama-server` 和 `llama-bench`。
- 确认 Metal 后端、Apple Accelerate 和 Apple M2 Max GPU 可用。
- 本阶段没有下载模型、运行慢速测试、提交或推送 Git 变更。

环境记录：`results/system-info.txt`。

### Phase 1：模型下载与首次推理

- 只下载官方 `Qwen/Qwen3-14B-GGUF` 中的 `Qwen3-14B-Q4_K_M.gguf`，没有下载整个仓库或其他量化版本。
- SHA-256 校验通过。
- 41/41 个模型层全部卸载到 Metal GPU。
- 中文回答、三句话限制和单句长度限制全部通过。
- 暖缓存离线加载与单 token 验证约 1.72 秒。

首次功能测试的生成速度约为 29.1 tokens/s。记录见 `results/phase-1-smoke-test.txt`。

### Phase 2：正式性能基准

| 测试 | 平均速度 |
| --- | ---: |
| 处理 512-token 提示词 | 262.25 ± 0.53 tokens/s |
| 生成 128 tokens | 29.83 ± 0.03 tokens/s |

- 三次重复结果稳定。
- 峰值常驻内存约 8.60 GiB。
- 正式基准前、中、后的全局 swap 都是 3192.75 MiB，没有新增。
- 结论：这台 32 GB Mac Studio 可以流畅运行该模型的单人对话。

记录见 `results/phase-2-baseline.md` 和 `results/benchmark.csv`。

### Phase 3：4K、8K、16K 长上下文

| 上下文测试 | 综合速度 | 峰值常驻内存 | 全局 swap 变化 |
| --- | ---: | ---: | ---: |
| 4K + 128 | 198.47 tokens/s | 约 8.67 GiB | 无新增 |
| 8K + 128 | 199.27 tokens/s | 约 9.81 GiB | 无新增 |
| 16K + 128 | 183.88 tokens/s | 约 11.02 GiB | 新增约 494 MiB |

结论：8K 在速度、内存和系统余量之间最平衡；16K 可以运行，但对当时系统的内存压力明显更高。

记录见 `results/phase-3-context-benchmark.md`。

### 交互聊天与 Reasoning

- 使用 `llama-server` 自带 Web UI 在 `http://127.0.0.1:8080` 与模型交互。
- 测试了 system prompt、上下文长度和 Reasoning 模式。
- Reasoning 只是允许模型输出或使用更长的推理过程，不保证它一定推对；逻辑题仍可能因为错误前提或自我循环而失败。
- system prompt 可以影响语气、角色和输出规则，但无法保证解除模型训练阶段形成的所有行为倾向。

### Phase 4：完全离线生成 PDF

- Qwen 负责撰写 Markdown 内容。
- 本机 ReportLab 负责排版和生成 A4 PDF。
- Poppler 与 PDF 文字提取工具负责视觉和内容核对。
- 中文、标题、列表、段落和页脚均正常，没有截断或重叠。

这说明大模型不需要“天生会写 PDF”：模型负责文字，本机程序负责可靠地生成文件。

示例：`results/offline-pdf-demo.pdf`。记录见 `results/phase-4-offline-pdf.md`。

### Phase 5：本地 API

- `llama-server` 成功提供 OpenAI Chat Completions 风格接口。
- 地址只监听本机：`http://127.0.0.1:8080`。
- `/health`、JSON 请求、中文参数和 `choices[0].message.content` 提取全部通过。
- 验证了其他本机程序可以像调用云端模型一样调用 Qwen，同时不把内容发到互联网。

记录见 `results/phase-5-local-api.md`。

### Phase 6：KV cache 精度与内存

模型权重始终是 Qwen3-14B Q4_K_M；这里变化的是模型聊天记忆所使用的 KV cache 精度。

| KV cache | 16K 综合速度 | 峰值内存 | 相对 F16 节省 |
| --- | ---: | ---: | ---: |
| F16 | 181.25 tokens/s | 11.06 GiB | - |
| Q8_0 | 183.08 tokens/s | 9.88 GiB | 1.17 GiB |
| Q4_0 | 182.38 tokens/s | 9.21 GiB | 1.85 GiB |

三档速度基本相同。随后使用同一份 110 条长文档进行 7 项自动评分：

| KV cache | 得分 |
| --- | ---: |
| F16 | 7 / 7 |
| Q8_0 | 7 / 7 |
| Q4_0 | 7 / 7 |

本次测试没有发现 KV cache 量化造成的答案损失，但这不代表 Q4_0 在所有写作、代码、推理和更长上下文中都与 F16 完全等价。

当前建议：日常使用 Q8_0；需要为更长上下文或其他程序多留内存时使用 Q4_0；F16 保留为最高精度基准。

记录见 `results/phase-6-analysis.md` 和 `results/phase-6b-analysis.md`。

### Phase 7：离本文档问答（RAG）

第一版已经支持 Markdown、TXT 和带文字层的 PDF：

1. 在本机提取并切分文字。
2. 使用 BM25 关键词检索选出相关片段。
3. 只把这些片段交给本地 Qwen。
4. 要求回答用 `[S1]`、`[S2]` 标注来源。
5. 保存实际检索片段，便于人工核对。

端到端测试成功回答了 Q8_0 的内存结论，也从 PDF 第 1 页正确读出了硬件和 30.82 tokens/s 的生成速度。

记录见 `results/phase-7-local-rag.md` 和 `docs/05-local-rag.md`。

## 三、几个容易混淆的概念

### Metal 是什么

Metal 是 Apple 的 GPU 计算接口。llama.cpp 使用它把适合并行计算的模型运算交给 M2 Max GPU。CPU 仍负责程序控制、分词和部分数据处理，所以 Metal 加速不等于 CPU 完全不工作。

### 模型 Q4_K_M 与 KV cache F16/Q8/Q4

它们不是二选一，而是两个不同对象：

- Q4_K_M：压缩长期不变的模型权重，决定模型文件大小和主要内存占用。
- F16、Q8_0、Q4_0 KV cache：压缩本次对话逐渐增长的临时记忆。

因此可以同时使用“Q4_K_M 模型权重 + Q8_0 KV cache”。

### Context 与 swap

- Context 是模型一次能看到的 token 窗口，越大可以放入越长的对话或资料。
- 更大的 Context 会增加 KV cache 和内存占用。
- swap 是 macOS 把一部分暂时不用的内存内容放到磁盘；它不等于立即出错，但大量新增通常意味着内存压力变高，并可能影响速度。

### Hugging Face cache

Hugging Face 是模型与数据集托管平台。本项目的 cache 是下载到本机后重复使用的模型文件缓存，不是浏览器缓存。使用 `--offline` 时，llama.cpp 只读取这份本地缓存。

## 四、语义向量检索是什么

当前 Phase 7 使用 BM25，主要依据关键词是否出现。语义向量检索则使用一个 embedding 模型，把问题和每个文档片段转换成固定长度的数字数组，也就是向量。

```text
文档片段 -> embedding 模型 -> 文档向量 -> 本地索引
用户问题 -> embedding 模型 -> 问题向量 -> 相似度比较 -> 相关片段 -> Qwen 回答
```

向量空间中，意思相近的文字通常距离更近。例如资料写的是“为其他应用腾出更多内存”，用户问“电脑快撑不住了，怎样少占资源”，即使没有完全相同的关键词，向量检索也有机会找到它。

| 方法 | 优点 | 局限 |
| --- | --- | --- |
| BM25 关键词检索 | 简单、快、无需额外模型；数字和专有名词很准 | 同义词和含蓄表达较弱 |
| 语义向量检索 | 措辞不同也能按意思寻找 | 需要 embedding 模型和索引；可能找到意思相似但事实无关的段落 |
| 混合检索 | 同时利用精确词和语义，通常最稳 | 系统更复杂，需要排序与调参 |

当前资料规模较小，BM25 已足够。以后文档数量增多时，最合理的升级不是完全替换 BM25，而是加入本地 embedding，形成混合检索。

## 五、以后怎么使用

### 普通网页聊天

```bash
scripts/start_chat.sh
```

浏览器打开 `http://127.0.0.1:8080`。按 Control-C 停止。

### 开启 Reasoning

```bash
scripts/start_chat.sh 8192 on q8_0
```

### 启动 16K 文档问答服务

Terminal 1：

```bash
scripts/start_chat.sh 16384 off q8_0
```

Terminal 2：

```bash
scripts/ask_documents.sh "你的问题" 文件或目录
```

不指定文件时，脚本默认检索项目 README、`docs/` 和 Markdown 实验记录。

### 调用本地 API

启动服务后：

```bash
scripts/ask_local_model.sh "你的问题"
```

### 离线生成 PDF

```bash
scripts/generate_pdf.sh "文档要求" output-name
```

## 六、目录结构

```text
qwen3-14b-llamacpp/
├── PROJECT-SUMMARY.md     # 本文件
├── README.md              # 项目入口与常用命令
├── docs/                  # 分阶段说明
├── scripts/               # 可复用脚本
├── tests/                 # 自动测试与固定测试材料
├── results/               # 基准、日志、答案和实验结论
└── worktrees/llama.cpp/   # 隔离的 llama.cpp 源码与构建
```

模型权重没有复制进项目，仍统一放在 `~/Documents/AI-Models/huggingface`。

## 七、最终状态

- 所有计划中的 Phase 0-7 均已完成。
- 当前没有运行中的 llama-server。
- 没有修改原 llama.cpp 贡献分支。
- 没有创建 Git commit，也没有推送任何变更。
- 脚本、结果和说明均保留在本项目中，可随时恢复实验。

这是本项目第一阶段的正式收尾。未来可选方向包括扫描 PDF 的 OCR、本地 embedding + 混合检索、语音交互，以及测试其他模型；它们不是当前项目完成所必需的工作。
