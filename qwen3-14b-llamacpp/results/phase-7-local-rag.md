# Phase 7：完全离线的本地文档问答

状态：已完成第一版。

## 流程

1. 本地读取 Markdown、TXT 和带文字层的 PDF。
2. 按文件行号或 PDF 页码切分内容。
3. 使用无需额外模型的 BM25 检索相关段落。
4. 只把选出的段落交给本地 Qwen3-14B。
5. 要求回答使用 `[S1]` 等标记引用资料来源。

整个过程没有联网，也没有下载 embedding 模型。

## 端到端演示一：询问项目记录

问题：为什么日常 16K 推荐 Q8_0？它比 F16 少用多少内存？

回答：日常 16K 推荐 Q8_0 是因为其在质量测试中与 F16 表现相同，同时节省了约 1.17 GiB 的内存 `[S3]`。

实际依据是 `results/phase-6b-analysis.md`。检索扫描了项目 README、实验文档和 Markdown 结果，Qwen 没有把其他候选片段强行写入答案。

## 端到端演示二：询问 PDF

问题：这份报告使用什么硬件？模型生成速度是多少？

回答：报告使用 Mac Studio、Apple M2 Max 和 32 GB 统一内存；模型生成速度约为 30.82 tokens/s `[S1]`。

实际依据是 `results/offline-pdf-demo.pdf` 第 1 页，说明 PDF 文字提取和页码来源均正常。

## 产物

- 通用入口：`scripts/ask_documents.sh`
- 检索与 API 客户端：`scripts/local_rag.py`
- 使用说明：`docs/05-local-rag.md`
- 最近一次项目问答：`results/rag-last-answer.md`
- 最近一次项目检索：`results/rag-last-retrieval.json`
- PDF 演示答案：`results/rag-pdf-demo-answer.md`
- PDF 演示检索：`results/rag-pdf-demo-retrieval.json`

## 结论与边界

本版本已经适合对少量个人笔记、实验记录和带文字层 PDF 做离线问答。明确的专有名词、数字和关键词检索效果很好。扫描版 PDF 仍需 OCR；同义词检索和大量文档的重复查询，后续可以用本地 embedding 模型及持久化索引增强。
