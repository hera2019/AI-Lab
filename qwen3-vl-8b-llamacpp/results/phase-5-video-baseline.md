# Phase 5：原生视频理解基线

执行日期：2026-09-01

本轮使用 llama.cpp 的 `--video` 路径，不是手动抽帧后伪装成多图输入。模型、projector、Metal 配置和 llama.cpp commit 沿用 `results/system-info.txt`。

## 测试素材

`scripts/generate_video_fixtures.sh` 使用现有三张多图素材生成两个自包含视频：

| ID | 文件 | 时间顺序 |
| --- | --- | --- |
| VIDEO-001 | `tests/fixtures/video/20-video-abc.mp4` | A -> B -> C |
| VIDEO-002 | `tests/fixtures/video/21-video-cba-猫-東京-🧪.mp4` | C -> B -> A |

两个文件均为 6 秒、640x480、6 FPS、H.264、无音频。每个画面阶段持续 2 秒。第二个文件名同时覆盖中文、日文和 emoji 路径。

## 运行配置

- 入口：`scripts/run_video_baseline.sh`
- 视频采样：`--video-fps 1`
- 时间戳间隔：`--video-timestamp-interval 1000`
- 上下文：8192
- reasoning：off
- temperature：0

## VIDEO-001：A -> B -> C

模型输出：

```text
Stage 1: Position [0m0.00s] - Letter A - Color Red - Shape Circle - Code ALPHA-17

Stage 2: Position [0m2.00s] - Letter B - Color Blue - Shape Square - Code BETA-29

Stage 3: Position [0m4.00s] - Letter C - Color Green - Shape Triangle - Code GAMMA-43
```

- 时间顺序：PASS
- 阶段切换时间：PASS
- 字母、颜色、形状、代码：PASS
- 图像/提示处理：268.5 token/s
- 生成：47.1 token/s
- 退出码：0

## VIDEO-002：C -> B -> A + Unicode 路径

模型输出：

```text
Stage 1: Position [0m0.00s] - Letter C - Color Green - Shape Triangle - Code IMAGE C GAMMA-43

Stage 2: Position [0m2.00s] - Letter B - Color Blue - Shape Square - Code IMAGE B BETA-29

Stage 3: Position [0m4.00s] - Letter A - Color Red - Shape Circle - Code IMAGE A ALPHA-17
```

- Unicode 视频路径：PASS
- 时间顺序：PASS
- 阶段切换时间：PASS
- 字母、颜色、形状、代码：PASS
- 严格输出格式：轻微 FAIL，代码前额外输出了 `IMAGE A/B/C`
- 图像/提示处理：271.6 token/s
- 生成：47.4 token/s
- 退出码：0

## 结论

- Qwen3-VL-8B 通过 llama.cpp 原生视频路径成功读取了短 MP4。
- 模型保留了视频时间顺序，包括反字母顺序 C -> B -> A，没有自动重排。
- 模型给出的 0、2、4 秒切换点与视频真值完全一致。
- 未发现加载失败、帧顺序丢失、crash 或 hang；本轮不构成新的 upstream issue。
- 这是最小正常视频基线，还没有覆盖可变帧率、moov 位置、极短视频、损坏容器和视频资源压力。
