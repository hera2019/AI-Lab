# Phase 4：本地模型离线制作 PDF

这个流程把“写内容”和“创建文件”拆开：

1. Qwen3-14B 在本机生成 Markdown 正文。
2. 本机 Python + ReportLab 使用系统中文字体排版。
3. 生成真正的 PDF 文件，全程不访问网络。

## 默认示例

```bash
scripts/generate_pdf.sh
```

生成：

- `results/offline-pdf-demo.md`
- `results/offline-pdf-demo.pdf`
- `results/pdf-generation-latest.log`

## 自定义内容

第一个参数是写作要求，第二个参数是英文文件名：

```bash
scripts/generate_pdf.sh "写一份三页以内的 Flutter 学习计划" flutter-plan
```

## 边界

- Qwen 负责撰写文本，但不直接操作 PDF。
- `scripts/markdown_to_pdf.py` 负责本地排版和文件写入。
- 当前支持标题、段落、列表和代码块等简单 Markdown。
- 运行需要 Codex 已提供的本地 Python + ReportLab；不需要联网。
