# Phase 3：图片格式与解码边界

执行日期：2026-08-31

模型与运行环境沿用 `results/system-info.txt`。合法图片批次的完整控制台输出保存在 `results/image-boundary-latest.log`（可重新生成，不纳入版本管理）。可使用 `scripts/run_image_boundary_baseline.sh` 重跑。

## 合法图片结果

| ID | 输入 | 结果 | 判定 |
| --- | --- | --- | --- |
| IMG-001 | 1×1 红色 RGB PNG | 稳定加载，主色红色正确；模型声称尺寸为 1000×1000 | 解码 PASS；原始尺寸回答 FAIL |
| IMG-002 | 1×1、RGBA=(0,255,0,0) | 模型称图片可见且为绿色 | 稳定加载；alpha 语义 FAIL |
| IMG-003 | 透明 PNG，含透明文字 | 同时读出 `VISIBLE 42` 和完全透明的 `HIDDEN 99` | alpha 语义 FAIL |
| IMG-004 | 4096×32、8 段色带 | 稳定加载；严格复测输出 `红,橙,黄,绿,青,蓝,紫,黑` | 稳定性 PASS；颜色序列 FAIL |
| IMG-005 | 32×4096、8 段色带 | 输出 `红,橙,绿,蓝,紫,粉红,黑,白` | PASS，最后两色为近似命名 |
| IMG-006 | EXIF Orientation=6 JPEG + 物理旋转参考 PNG | 图片1横向、图片2纵向、视觉方向不一致 | 稳定性 PASS；EXIF FAIL |
| IMG-007 | 中文与 emoji 文件名 | 路径加载成功；内容全部识别，`・` 输出为 `·` | 路径 PASS；严格 Unicode FAIL |
| IMG-008 | PNG 内容、`.jpg` 后缀 | 正确抄录 `PNG BYTES` / `.jpg filename` | PASS，按内容而非扩展名解码 |
| IMG-009 | 16-bit 灰度 PNG | 正确识别从左黑到右白的渐变 | PASS |
| IMG-010 | CMYK JPEG | 正确识别 `CMYK JPEG` 与浅蓝背景 | PASS |

所有合法输入都以退出码 0 结束，没有 crash、hang 或异常内存增长。

## Alpha 通道证据

IMG-002 的唯一像素为完全透明的绿色；IMG-003 中 `HIDDEN 99` 的像素具有 RGB 数据但 alpha 为 0。模型仍看到绿色与隐藏文字。

当前源码 `worktrees/llama.cpp/tools/mtmd/mtmd-helper.cpp` 使用：

```cpp
stbi_load_from_memory(buf, len, &nx, &ny, &nc, 3)
```

最后一个参数强制输出 3 通道 RGB，alpha 没有被合成到确定背景，因此透明像素下的 RGB 直接进入视觉模型。该现象不依赖模型猜测，具备最小复现与直接代码证据。

影响：透明图层中本应不可见的文字、水印或其他 RGB 内容可能被模型读取。应进一步决定规范是合成到白色、黑色、棋盘格，还是让调用方显式选择；未明确规范前不直接提交修复。

## EXIF 方向证据

Orientation=6 JPEG 被作为横图处理，而使用相同像素、预先执行 EXIF 旋转的参考 PNG 被作为竖图处理。

上游已有 [issue #20870](https://github.com/ggml-org/llama.cpp/issues/20870)。维护者说明 `stb_image` 不支持 EXIF；该 issue 后来因 [PR #24196](https://github.com/ggml-org/llama.cpp/pull/24196) 关闭，但 PR 只在 Web UI 上传阶段读取并烘焙旋转，未改变 CLI/libmtmd 解码路径。因此本次 CLI 复现是已知限制，不应新开重复 issue。

## 损坏与无效输入

| ID | 输入 | 实际行为 | 退出码 | 判定 |
| --- | --- | --- | ---: | --- |
| BAD-001 | 截断至约 10% 的 JPEG | 被接受为图片，模型对残余像素生成内容描述 | 0 | FAIL |
| BAD-002 | 纯文本伪装成 `.jpg` | 明确显示 `Error: Failed to load image or audio file` | 0 | 错误信息 PASS；退出码 FAIL |
| BAD-003 | 0 字节 `.png` | 明确显示相同错误 | 0 | 错误信息 PASS；退出码 FAIL |

BAD-002 与 BAD-003 会先回退尝试 ffprobe，然后正确拒绝；提示中出现 `(is ffprobe in PATH?)`，但本机 ffprobe 实际存在，因此该附加提示在“输入本来就无效”时具有误导性。

## Upstream 评估

1. **EXIF**：已有报告与 UI 层修复，不重复提交。
2. **透明 alpha**：当前未搜索到相同 issue/PR；证据强，值得作为下一候选继续核查设计预期与跨模型行为。
3. **无效媒体退出码 0**：当前未搜索到完全相同报告；对脚本和 CI 有实际影响，值得用不依赖模型回答的最小 CLI 复现继续定位。
4. **截断 JPEG 容忍**：可能来自 stb_image 的容错策略。需要定义“损坏但可部分解码”是否应拒绝，暂不直接定性为 bug。

本阶段没有提交 issue、PR、commit 或 push。
