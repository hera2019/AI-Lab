# Phase 6：视频容器与时间边界

执行日期：2026-09-01

本轮测试极短视频、MP4 `moov` 位置、可变帧率和损坏容器。模型、projector、Metal 配置和 llama.cpp commit 沿用 `results/system-info.txt`。

## 素材与入口

- 生成：`scripts/generate_video_fixtures.sh`
- 运行：`scripts/run_video_boundary_tests.sh`
- 原始日志：`results/video-boundary-latest.log`

| ID | 输入 | 重点 |
| --- | --- | --- |
| VIDEO-003 | `tests/fixtures/video/22-video-a-very-short.mp4` | 0.2 秒、2 帧 |
| VIDEO-004A | `tests/fixtures/video/20-video-abc.mp4` | `moov` 位于头部的对照 |
| VIDEO-004B | `tests/fixtures/video/23-video-abc-moov-tail.mp4` | `moov` 位于尾部 |
| VIDEO-005 | `tests/fixtures/video/24-video-vfr-abc.mp4` | 稀疏可变时间戳 |
| VIDEO-BAD-001 | `tests/fixtures/video/25-not-a-video.mp4` | 文本伪装成 MP4 |

## VIDEO-003：0.2 秒极短视频

模型正确识别 A、红色、圆形和 `ALPHA-17`，并正确判断视频没有切换到其他场景。

判定：PASS。极短视频稳定加载，无 crash 或 hang。

## VIDEO-004：`moov` 头部与尾部

实际 atom 偏移：

```text
20-video-abc.mp4
36:moov
1293:mdat

23-video-abc-moov-tail.mp4
44:mdat
19708:moov
```

两个视频解码为 RGB 像素后的 SHA-256 完全一致：

```text
d78f13947525cc896e8e7bf5b4ebd0dff21a91dca6eefe2e52e149501c1b17cf
```

使用同一提示后，两者的模型输出也完全一致：

```text
[0m0.00s] A, red, circle, ALPHA-17
[0m2.00s] B, blue, square, ALPHA-29
[0m4.00s] C, green, triangle, GAMMA-43
```

两者都将图中的 `BETA-29` 误读为 `ALPHA-29`。因为头部与尾部 `moov` 的解码像素和输出都一致，这是模型 OCR 误差，不是 MP4 atom 位置导致的实现问题。

判定：`moov` 头部 PASS；`moov` 尾部 PASS；视频文字严格匹配 FAIL。

## VIDEO-005：可变时间戳

视频帧时间点为 0、1、4、6 秒，画面真值为：

- A：约 0-1 秒，持续 1 秒。
- B：约 1-4 秒，持续 3 秒。
- C：约 4-6 秒，持续 2 秒。

模型正确输出了三个时间段、颜色、形状和代码，但最后将 C 判定为最长阶段。这与它自己输出的时间段矛盾；正确答案是 B。

判定：容器解码 PASS；帧顺序 PASS；时间段提取 PASS；时长比较 FAIL。这是模型推理误差，当前不是 llama.cpp/libmtmd issue。

## VIDEO-BAD-001：损坏 MP4

ffprobe 对素材的直接检查结果为 `moov atom not found`。`llama-cli` 约 2 秒内显示解码错误，没有触发 30 秒超时保护，也没有 crash 或 hang。

```text
mtmd_helper_video_init_from_buf: ffprobe failed on buffer (is ffprobe in PATH?)
mtmd_helper_bitmap_init_from_buf: failed to decode buffer as either image/audio/video
Error: Failed to load image or audio file
```

标准 `llama-cli` 仍以退出码 0 结束。这是已提交的无效媒体退出码问题的又一个输入类型，不新开重复 issue。

## 结论

- llama.cpp/libmtmd 稳定处理了极短 MP4、尾部 `moov` 和可变时间戳。
- 未发现帧顺序丢失、像素差异、crash、hang 或新的实现层问题。
- 模型在视频文字识别和简单时长比较上仍会犯错，应与底层视频支持分开评分。
- 损坏 MP4 快速明确拒绝，但退出码仍错误地为 0，属于已知并已报告的问题。
