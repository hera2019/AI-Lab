# Phase 7：完全离线的本地文档问答

RAG 可以理解为“先在文档里找资料，再让模型根据找到的资料回答”。它不会重新训练 Qwen，也不会把整套文件永久塞进模型。

这套第一版流程全部留在本机：

1. 从 Markdown、TXT 或 PDF 提取文字。
2. 把文字切成带文件名、行号或页码的小段。
3. 使用本地 BM25 关键词检索选出最相关的五段。
4. 只把这些段落交给本地 Qwen3-14B。
5. 回答用 `[S1]`、`[S2]` 标出依据，并列出对应文件位置。

## 使用方法

先在一个 Terminal 启动 16K、Q8_0 KV cache 的本地服务：

```bash
scripts/start_chat.sh 16384 off q8_0
```

保持这个窗口打开。在第二个 Terminal 进入项目目录，然后直接询问项目内文档：

```bash
scripts/ask_documents.sh "为什么日常 16K 推荐 Q8_0？"
```

也可以指定一个 PDF：

```bash
scripts/ask_documents.sh "这份报告中的硬件和生成速度是多少？" results/offline-pdf-demo.pdf
```

或指定自己的文件和目录；多个来源依次写在问题后面：

```bash
scripts/ask_documents.sh "安装时有哪些注意事项？" docs/ manual.pdf notes.txt
```

最后一次回答保存在 `results/rag-last-answer.md`，实际送给模型的检索片段保存在 `results/rag-last-retrieval.json`，方便核对模型有没有答非所问。

## 当前边界

- 扫描版 PDF 如果只有图片而没有文字层，需要另加 OCR；当前版本会找不到其中的文字。
- 第一版使用 BM25，不需要额外模型，专有名词、数字和明确关键词表现很好；同义词或含蓄表达不如向量检索。
- 来源标记由模型生成，重要结论仍应打开检索记录核对原文。
- 文档很多时，每次重新扫描会变慢；后续可以增加持久化索引和本地 embedding 模型。
