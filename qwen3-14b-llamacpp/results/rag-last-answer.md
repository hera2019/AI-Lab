# 本地文档问答

**问题：** 这些资料的主要结论是什么？

这些资料的主要结论是：本地文档问答系统已经能够实现对少量个人笔记、实验记录和带文字层 PDF 的离线问答，且在特定任务中，如使用 Q8_0 量化模型时，可以在保持与 F16 相同质量的同时节省内存 [S3]。

- 本地文档问答系统支持 Markdown、TXT 和带文字层的 PDF 文件 [S1]。
- 使用 BM25 检索相关段落，再由本地 Qwen3-14B 模型生成答案 [S1]。
- Q8_0 量化模型在 16K 上下文长度下与 F16 相同质量，但节省了约 1.17 GiB 内存 [S3]。
- 在 Mac Studio 上运行 Qwen3-14B 模型，生成速度约为 30.82 tokens/s [S1]。

## 检索来源

- [S1] `results/phase-7-local-rag.md` (lines 1-43)
- [S2] `results/rag-pdf-demo-answer.md` (lines 1-9)
- [S3] `results/phase-6-analysis.md` (lines 1-35)
- [S4] `results/phase-6b-analysis.md` (lines 1-28)
- [S5] `results/offline-pdf-demo.md` (lines 1-30)
