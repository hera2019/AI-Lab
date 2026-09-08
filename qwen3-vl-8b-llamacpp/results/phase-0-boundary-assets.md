# Phase 0A：多模态边界测试资产

状态：已完成；尚未下载或运行 Qwen3-VL 模型。

## 生成结果

- 固定测试：17 个。
- 测试输入文件：20 个。
- 视觉总览：1 个。
- manifest 记录文件总数：21 个。
- 生成器：`scripts/generate_boundary_images.py`。
- 校验器：`scripts/verify_boundary_images.py`。
- 一键入口：`scripts/generate_boundary_images.sh`。

覆盖范围：

- 1×1 RGB 与全透明 PNG。
- 透明像素下隐藏 RGB 内容。
- 4096×32 与 32×4096 极端宽高比。
- EXIF Orientation=6 与已旋转参考图。
- 中文、日文和 emoji 的 Unicode 文件名。
- PNG 内容配 `.jpg` 扩展名。
- 16-bit 灰度 PNG 与 CMYK JPEG。
- 清晰、小字号低对比、倾斜 OCR。
- 三张图的颜色、形状、代码和顺序。
- 截断 JPEG、伪装 JPEG 与 0-byte PNG。

## 自动校验

`scripts/generate_boundary_images.sh` 已成功运行：

```text
PASS: 17 boundary cases
PASS: 21 fixture files and SHA-256 values
PASS: dimensions, alpha, EXIF, extension mismatch, Unicode path
```

manifest 为每个文件记录大小、SHA-256、Pillow 解码结果、格式、像素模式、尺寸和 EXIF Orientation。三个故意损坏的输入均被本地校验器判定为不可解码。

## 视觉检查

- 1×1 图片只在联系表中使用最近邻放大，原文件仍保持 1×1。
- alpha-aware 联系表只显示 `VISIBLE 42`；透明区域中的 `HIDDEN 99` 不可见。
- EXIF JPEG 与参考 PNG 在正确处理方向后外观一致。
- 16-bit 灰度图从黑到白平滑变化。
- 清晰 OCR、倾斜 OCR 与三张多图素材没有裁切。
- 低对比 OCR 刻意保持难读，用于测量边界，不是制图缺陷。
- 损坏文件不放进联系表，避免图片预览器提前替测试程序处理错误。

## 位置

- 测试矩阵：`tests/boundary-cases.md`
- 机器可读清单：`tests/fixtures/manifest.json`
- 联系表：`tests/fixtures/contact-sheet.png`
- 单图：`tests/fixtures/images/`
- 多图：`tests/fixtures/multi/`
- 坏输入：`tests/fixtures/invalid/`

## 当前边界

这些检查只证明测试素材自身正确，还没有证明 llama.cpp/libmtmd 或 Qwen3-VL 能通过测试。只有在独立 worktree 的最新构建上运行后，才能记录 accept、clean reject、crash、hang、资源异常和模型答案质量。

当前没有足够证据提交 upstream issue/PR。下一步先建立第二项目的独立 worktree，显式构建 `llama-cli`、`llama-server` 与 `llama-mtmd-cli`，再列出精确下载文件和空间；仍不应在未经核对时下载。
