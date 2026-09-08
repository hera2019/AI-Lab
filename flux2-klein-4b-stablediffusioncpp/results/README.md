# Results

本目录保存环境信息、命令参数、benchmark、评分汇总和精选缩略图。

大批量原始生成图放在 `results/generated/`，默认不作为长期研究文档的一部分；项目结束清理模型前，先保留能证明结论的固定样本、哈希和摘要。

## 当前结果

- `phase-0-and-download.md`：环境、构建和模型下载记录。
- `phase-1-first-baseline.md`：首张 1024 × 1024 基线图、性能、提示遵循与逐字节复现结果。
- `phase-2-photo-prompt-ab.md`：同 seed 的简单/专业照片提示词 A/B、性能和人工观察。
- `phase-2-instruction-isolation.md`：数量、颜色、左右位置与精确英文短文字的独立测试和人工复核清单。
- `phase-3-single-edit.md`：参考图单点改色、精确文字替换与复杂场景物体移除，以及未编辑区域保持程度、像素差异和性能记录。
- `phase-3-multi-reference.md`：从独立产品参考图提取指定绿色杯子并组合到复杂场景，记录跨图对象选择、自然融合、精确落位失败和双参考性能。
- `phase-3-assisted-compositing.md`：用透明抠图、确定性图层、FLUX 局部蒙版润色和像素回填修正杯子落位，验证目标区外背景逐像素不变。
- `phase-4-performance-errors.md`：512–1024 与横竖画幅的速度、内存、提示遵循，以及四类命令行失败的退出状态。
- `final-project-summary.md`：Phase 0–4 的最终结论、推荐默认参数、实用工作流与已知边界。
