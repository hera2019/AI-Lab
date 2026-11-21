# Qwen3 Embedding 0.6B with llama.cpp

**研究页面（英文）：**[houjun.dev/lab/rag](https://houjun.dev/lab/rag/)

在 Mac Studio（Apple M2 Max、32 GB Unified Memory）上学习并测试本地语义向量检索与 RAG。

## 实际应用意义

关键词搜索要求文字相同；语义检索比较的是含义。它可以让中文问题找到日文或英文资料，也可以在用户用词与文档用词完全不同时找出正确段落。

RAG（Retrieval-Augmented Generation，检索增强生成）在语义检索之后再增加一步：把找出的原文交给聊天模型，让模型依据本地资料回答，并标明资料来源。向量模型负责“找资料”，聊天模型负责“组织答案”，两者不是同一个模型。

## 方案

- 向量模型：`Qwen/Qwen3-Embedding-0.6B-GGUF`
- 量化：`Q8_0`
- 参数量：0.6B
- 向量维度：1024
- 支持语言：100+，包括中文、日文、英文
- 推理框架：llama.cpp
- 加速：Apple Metal
- 模型权重：保存在项目外的 `AI-Models/embeddings/`，项目只保存脚本、测试资料和结果

选择 Q8_0 而不是 Q4，是因为模型仅约 639 MB，本机空间和内存都很充足，而检索排序会受到向量细微误差影响，优先保留精度更合适。

## 阶段计划

### Phase 0：环境与可复现基础（完成）

- 使用独立 llama.cpp worktree；
- 固定源码 commit；
- 编译 Release + Metal 的 `llama-embedding` 与 `llama-server`；
- 固定模型 revision、大小和 SHA-256。

### Phase 1：看得懂的语义检索实验（完成）

- 建立包含本地 AI 实验知识的中日英短段落；
- 使用意思相同但字面不同的问题检索；
- 对比“只索引正文”和“标题 + 正文”两种准备方式；
- 输出前三名、相似度和预期答案排名；
- 保存机器可读 JSON 与人类可读 Markdown。

### Phase 2：真实项目文档检索（完成）

- 读取 AI-Lab 中已有的 README 和研究总结；
- 按标题和段落切块；
- 保存向量索引，避免每次重新计算；
- 交互式输入问题并显示来源。

### Phase 3：本地 RAG

- 加入一个本地聊天模型；
- 只把检索到的少量原文交给聊天模型；
- 要求答案引用文件和段落；
- 测试资料中没有答案时是否会诚实回答“不知道”。

Phase 3 使用 `Qwen3-4B-Instruct-2507 Q8_0` 作为问答模型。检索出的片段会编号为 `[S1]` 至 `[S5]`；程序检查虚构引用和未引用的陈述行，并保存实际提供给模型的完整来源。详细设计见 `docs/03-local-rag.md`，模型选择依据见 `docs/04-generator-model-selection.md`。

## 当前边界

- Phase 1 使用短段落，符合实际 RAG 的切块方式。
- 不把整本书作为一个输入；超长 Metal embedding 在近期 llama.cpp 中存在已知资源边界。
- 相似度是排序信号，不是“答案正确概率”。
- 首轮只验证检索，不把聊天模型的语言能力混入结果。

## 当前结果

- 真实资料：约 70 个 Markdown 文件、约 500 个段落；
- 本地索引：1024 维，约 5.3 MB；
- 首次建库：约一分钟，峰值内存低于 5.5 GiB，swap 为 0；
- 8 个中日英跨项目问题：正确项目 Recall@1 为 8/8；
- 单次独立搜索实测不到一秒；
- 每条结果显示相似度、项目、相对文件路径、行号、章节和原文预览。

同一事实有时存在于阶段报告、README 和总结合集中，因此“找到正确项目”和“找到指定的那份原始报告”是两种不同要求。本轮首选原始报告 Recall@3 为 5/8，说明下一阶段仍可加入关键词混合检索或 reranker 改善精确出处排序。

## 使用

下载或校验模型：

```bash
scripts/download_model.sh
```

运行第一轮语义检索：

```bash
scripts/run_semantic_search.sh
```

主要结果会写入：

- `results/phase-1a-body-only.md`：只索引正文；
- `results/phase-1b-title-body.md`：索引标题与正文；
- 同名 `.json`：完整机器可读结果。

建立或更新全部 AI-Lab 研究资料的本地索引：

```bash
scripts/run_phase_2.sh
```

进入连续提问模式：

```bash
scripts/search_ai_lab.sh
```

也可以只问一次：

```bash
scripts/search_ai_lab.sh "VAE 和 TAE 在视频生成里分别起什么作用？"
```

输入 `q` 退出连续提问模式。索引仅包含顶层/项目 README、`docs/` 和 `results/` 的 Markdown；不包含第三方源码、测试夹具、运行日志、旧模型生成的答案或当前项目自己的结果。

Phase 2 文件：

- `index/ai-lab-index.json`：持久化向量索引；
- `index/manifest.json`：纳入文件的大小、SHA-256 和排除清单；
- `results/phase-2-evaluation.md`：逐题排名；
- `results/phase-2-summary.md`：阶段总结。

下载或校验 Phase 3 问答模型：

```bash
scripts/download_generator_model.sh
```

进入本地 RAG 连续提问模式：

```bash
scripts/ask_ai_lab.sh
```

只问一次：

```bash
scripts/ask_ai_lab.sh "为什么猫眨眼只算部分成功？"
```

最近一次回答保存在 `results/rag-last-answer.md`，其完整来源、提示词、时间和引用检查保存在 `results/rag-last-answer.json`。Phase 3 的中日英有答案测试与无答案拒答测试使用 `scripts/run_phase_3.sh`。
