# Phase 4：本地模型离线制作 PDF

状态：已完成。

## 流程

1. Qwen3-14B Q4_K_M 使用 Metal 在本机撰写 Markdown。
2. 脚本从 `llama-cli` 的专用 UTF-8 输出中提取 Assistant 正文。
3. ReportLab 使用 macOS 本机中文字体生成 A4 PDF。
4. Poppler 逐页渲染，pdfplumber 提取文字进行交叉检查。

整个生成与转换过程使用本机已有模型和工具，没有访问网络。

## 示例结果

- PDF：`results/offline-pdf-demo.pdf`
- 模型原稿：`results/offline-pdf-demo.md`
- PDF 页数：1
- PDF 大小：71,630 bytes
- 内容：Mac Studio / Qwen3-14B 本地运行体验报告

## 质量检查

- 中文、英文、数字与标点均正常显示。
- 标题、章节、列表、段落与页脚没有截断或重叠。
- PDF 文字提取结果与 Markdown 原稿一致。
- 硬件、模型、速度、8K 与 16K 上下文数据均来自本项目实测。

## 复现

默认示例：

```bash
scripts/generate_pdf.sh
```

自定义内容和文件名：

```bash
scripts/generate_pdf.sh "写一份三页以内的 Flutter 学习计划" flutter-plan
```

这验证了本地模型本身不需要具备“写 PDF”能力：模型负责内容，受控的本机工具负责文件操作。
