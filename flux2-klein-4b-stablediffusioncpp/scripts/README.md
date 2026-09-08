# Scripts

本目录放置可重复执行的构建、精确下载、生成和 benchmark 脚本。

脚本要求：

- 默认使用项目外的统一模型目录
- 每次生成建立独立结果目录，不覆盖旧图
- 保存完整参数、seed、commit、耗时和退出码
- 下载前显示目标 URL、文件名、预计大小和剩余空间
- 不静默回退到 CPU

## 已有脚本

- `build_release_metal.sh`：构建 Release + Metal 的 `sd-cli` 与无前端 `sd-server`，随后列出计算设备。
- `download_models.sh`：只下载三个固定 revision 的模型文件；支持断点续传，并逐一核对字节数与 SHA-256。
- `run_first_baseline.sh`：以固定 prompt、seed `260903`、`1024 × 1024` 和 4 steps 生成第一张可复现基线图，同时记录完整日志与 macOS 资源统计。
- `run_photo_prompt_ab.sh`：同 seed 对比简单提示词与专业摄影提示词，观察不增加其他模型/节点时的照片质量上限。
- `run_instruction_isolation.sh`：把数量、颜色、空间位置和短文字拆成四张独立图片，供人工逐项检查。

模型默认放在 `~/Documents/AI-Models/stable-diffusion/flux2-klein-4b`，不会混入项目目录。
