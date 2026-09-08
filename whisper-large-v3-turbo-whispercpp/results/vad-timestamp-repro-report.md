# VAD 字幕时间轴独立复现

日期：2026-09-02

## 实际应用意义

VAD 可以删除长录音中的静音，但字幕时间仍必须对应原始录音。若时间映射错误，字幕可能在说话前数秒出现、跨过整段静音，或导致剪辑软件跳到错误位置。这个问题不影响转写文字本身，却会直接影响视频字幕、会议定位和语音片段检索。

## 结论

- 使用 whisper.cpp 官方 `samples/jfk.wav` 构造了不依赖本项目合成语音的独立复现。
- `large-v3-turbo-q5_0` 在默认解码和 greedy 解码下都稳定出现后续字幕提前。
- `base.en` 没有出现同样的“后续字幕提前”，但每条字幕延续到下一条开始，2 秒静音没有作为字幕空隙保留。
- 因此，具体 segment 边界受 Whisper 模型和解码影响；共同问题是 VAD 处理后的 segment 时间不能可靠反映原始音频的静音间隔。
- 上游已有高度重合的 Issue #3634 和 #3584，不建议新建重复 Issue。当前最新版和官方样例的结果适合补充到 #3634。

## 固定环境

- whisper.cpp commit：`eacbd8234c6654cdbf2c377f72b2106875479bdc`
- 主模型：`large-v3-turbo-q5_0`，574,041,195 bytes
- 对照模型：`base.en`，147,964,211 bytes
- VAD：`silero-v6.2.0`，885,098 bytes
- 构建：Release + Metal + Accelerate + FFmpeg
- 输入 SHA-256：`9ce1e9d977d28a13b4e620155b1bd4505c2a33ae636e0394dd2061aa365da773`

## 输入设计

将官方 JFK 样例重复三次，中间各插入 2 秒数字静音：

```text
JFK 0.000–11.000 s
silence 11.000–13.000 s
JFK 13.000–24.000 s
silence 24.000–26.000 s
JFK 26.000–37.000 s
```

Silero 检出的每份录音第一处人声分别从 0.320、13.310、26.310 秒开始，说明 VAD 的原始定位正确。

## large-v3-turbo-q5_0

| 录音副本 | 副本实际开始 | 第一处 VAD 人声 | 不启用 VAD 的 SRT 开始 | 启用 VAD 的 SRT 开始 | 相对副本开始 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.000 | 0.320 | 0.000 | 0.320 | +0.320 s |
| 2 | 13.000 | 13.310 | 12.840 | **10.370** | **-2.630 s** |
| 3 | 26.000 | 26.310 | 25.840 | **24.940** | **-1.060 s** |

第二条字幕在第二份音频开始前 2.630 秒出现；第三条字幕落在 24–26 秒的静音中。三条文字均正确，因此这不是内容错配造成的假象。`--beam-size 1 --best-of 1` 对照仍为 10.350 和 24.940 秒，说明它不是一次偶然的 beam-search 选择。

## base.en 对照

| 录音副本 | 副本实际开始 | 第一处 VAD 人声 | 不启用 VAD 的 SRT 开始 | 启用 VAD 的 SRT 开始 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.000 | 0.320 | 0.000 | 0.320 |
| 2 | 13.000 | 13.310 | 13.000 | 13.340 |
| 3 | 26.000 | 26.310 | 26.000 | 26.340 |

这个模型没有提前开始，但启用 VAD 后三条 SRT 是 0.320–13.340、13.340–26.340、26.340–36.670；前两条一直显示到下一条开始，原本的 2 秒字幕空隙消失。

## 源码对照

当前 `examples/cli/cli.cpp` 的字幕输出读取 `whisper_full_get_segment_t0/t1()`。这两个 segment getter 在 `src/whisper.cpp` 中调用 `map_processed_to_original_time()`，在映射点之间进行线性插值。

2026-07-01 合并的 PR #3910 为 **token** 时间新增了 segment-aware 映射：token 时间若落在被删除的静音中，会吸附到最近的语音边界。segment getter 仍使用原来的通用线性映射。结合本轮数据，这可能解释为何模型生成的 segment 边界会被映射到原音频静音内部；这是源码推断，不是已经证明的唯一根因。

## 上游查重

- https://github.com/ggml-org/whisper.cpp/issues/3634
- https://github.com/ggml-org/whisper.cpp/issues/3584
- https://github.com/ggml-org/whisper.cpp/pull/3910

Issue #3634 与本轮最接近：VAD 正确找到语音区间，但最终字幕时间线连续、静音空隙消失。Issue #3584 也报告了 SRT 不遵循 VAD 时间。两者目前均为开放状态。

## 可重复运行

脚本：`scripts/repro_vad_segment_timestamps.py`

主模型结果：

```text
copy  audio_start  first_vad  srt_without_vad  srt_with_vad  delta
   1        0.000      0.320            0.000         0.320  +0.320
   2       13.000     13.310           12.840        10.370  -2.630
   3       26.000     26.310           25.840        24.940  -1.060
bug_reproduced=yes
```

完整机器可读结果：

- `results/vad-timestamp-repro/automated-large/summary.json`
- `results/vad-timestamp-repro/automated-base-en/summary.json`

## 建议

不新开 Issue。若要反馈上游，先由使用者核对并理解 `docs/vad-timestamp-issue-3634-comment-draft.md`，再作为 #3634 的补充评论发布。它的价值在于证明当前 master 仍能复现，并提供官方样例、精确时间和跨模型对照。
