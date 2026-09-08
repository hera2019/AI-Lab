# Wan2.2 TI2V 5B 本地视频实验总结

日期：2026-09-05（Asia/Tokyo）

## 最终结论

Wan2.2 TI2V 5B `Q4_K_M` 可以在 Mac Studio M2 Max / 32 GB Unified Memory 上通过 stable-diffusion.cpp + Apple Metal 稳定运行，文字生成图片、文字生成视频和图片生成视频均已实际完成。

FastWan2.2 TI2V 5B `Q8_0` 的 3-step LCM 路线也已验证：同样的 832×480、33 帧任务可在约 54–57 秒内完成，较原版 20-step 的约 426–428 秒快约 7.5–7.8 倍。它很适合快速预览，但 I2V 的毛纹、亮度和阴影稳定性弱于原版 20 步。

这台机器的内存不是主要障碍：所有正式测试的最大常驻内存约为 14.0–14.3 GiB，`/usr/bin/time` 均报告 0 swap。真正的限制是完整 Wan2.2 VAE 的视频解码速度。

本次最重要的使用规则：

1. 不要用 416×256 判断 Wan2.2 TI2V 5B 的视频质量。即使 20 步和简单提示词也会输出碎裂、抽象画面。
2. 832×480 的单帧输出正常，证明 Q4 权重、文字编码器、VAE、Metal 和运行时组合有效。
3. 832×480、17 帧的视频仍然失败；832×480、33 帧的视频正常。当前版本下应把 33 帧视为实用下限，而不只是满足 `4n+1` 的数学约束。
4. 完整 VAE 解码 17 帧用了约 25 分钟；TAE 解码 33 帧只用约 2 秒。TAE 纹理较柔、质量上限较低，但非常适合本机预览和参数筛选。
5. I2V 比 T2V 更适合控制具体主体。输入图的猫、背景、构图、尾巴和毛纹都得到良好保持，只产生轻微头部/眼睛变化。

## 环境

- Mac Studio（Mac14,13）
- Apple M2 Max，12 核 CPU
- 32 GB Unified Memory
- macOS 26.6.2（25G83）
- AppleClang 21.0.0
- stable-diffusion.cpp commit：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- Release 构建，Metal 开启，运行时 diffusion flash attention 开启

隐私说明：系统序列号、Hardware UUID 和 Provisioning UDID 没有写入任何项目报告。

## 模型文件

- Wan2.2 TI2V 5B diffusion：`Q4_K_M`
- UMT5-XXL text encoder：`Q5_K_M`
- 完整 Wan2.2 VAE：FP16
- Wan2.2 TAEHV：快速、较低质量的诊断解码器
- Wan2.2 TAEHV Super：官方实验权重；已校验，但当前 stable-diffusion.cpp 最新 `master` 不支持其网络结构
- FastWan2.2 TI2V 5B：社区蒸馏版 `Q8_0`，用于 3-step LCM 快速预览；不是 Wan-AI 官方发布
- 总计精确大小：14,465,074,504 bytes（13.47 GiB）

所有文件的仓库、固定 revision、字节数与 SHA-256：`results/model-plan.txt`。

## 关键测试结果

| 测试 | 尺寸 / 帧数 | 解码器 | 采样 | 解码 | 总生成 | 最大常驻内存 | 结果 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 2-step 冒烟 | 416×256 / 17 | 完整 VAE | 10.29s | 342.17s | 365.93s | 14.00 GiB | 管线成功，画面不可用 |
| 12-step 复杂提示词 | 416×256 / 17 | 完整 VAE | 42.03s | 344.64s | 396.93s | 14.31 GiB | 抽象、无可靠主体 |
| 20-step 简单提示词 | 416×256 / 17 | 完整 VAE | 64.86s | 329.30s | 404.21s | 14.11 GiB | 仍为碎裂画面 |
| 原生单帧 | 832×480 / 1 | 完整 VAE | 53.85s | 113.63s | 178.52s | 14.02 GiB | 清楚、正常的猫 |
| 原生短视频 | 832×480 / 17 | 完整 VAE | 224.33s | 1514.86s | 1749.58s | 14.31 GiB | 时间维度碎裂，失败 |
| 原生 T2V | 832×480 / 33 | TAE | 414.59s | 2.28s | 428.23s | 14.31 GiB | 主体稳定、动作成立 |
| 原生 I2V | 832×480 / 33 | TAE | 412.55s | 2.11s | 426.14s | 14.02 GiB | 输入身份与场景保持良好 |
| FastWan T2V | 832×480 / 33 | TAE | 37.80s | 9.45s | 57.21s | 14.79 GiB | 约快 7.5 倍，结构稳定，构图与原版不同 |
| FastWan I2V | 832×480 / 33 | TAE | 38.10s | 9.42s | 54.39s | 14.87 GiB | 约快 7.8 倍，主体保留，光影与毛纹漂移更明显 |
| FastWan 明显动作 I2V | 832×480 / 65 | TAE | 71.12s | 3.66s | 86.72s | 13.97 GiB | 抬爪动作明显，末段前爪透视放大过度 |
| FastWan 原地转头 I2V | 832×480 / 65 | TAE | 72.99s | 3.61s | 86.88s | 14.31 GiB | 动作清楚自然，无夸张透视，转角超过要求 |
| FastWan 眨眼单项 I2V | 832×480 / 65 | TAE | 69.59s | 3.40s | 83.95s | 14.00 GiB | 双眼闭合成功，但没有重新睁开 |

Super TAE 同参数 A/B 在模型元数据验证阶段以 exit code 1 提前停止，实耗 0.38 秒，没有开始采样、没有生成视频，因此不能列作速度或画质结果。确认原因是官方 `taew2_2_super` 使用新的 `SuperMemBlock` 与 PixelShuffle 架构，而当前 stable-diffusion.cpp 的 TAEHV 实现不兼容。详见 `results/phase-5-super-tae-compatibility.md`。

原版正式质量测试使用 Euler、20 步、CFG 6.0、flow shift 3.0；FastWan 测试使用 Euler + LCM、3 步、CFG 1.0、flow shift 3.0。所有正式生成均记录完整 Prompt、negative prompt、seed、参数和日志。

## FastWan 3-step 结论

FastWan 的实用价值已经成立：不是只快一两倍，而是把一次约 7 分钟的 33 帧生成压缩到约 1 分钟。采样本身从约 413–415 秒降到约 38 秒，快约 10.8–11.0 倍；把模型加载、文字编码和解码算进去，完整生成仍快约 7.5–7.8 倍。

T2V 三帧中猫的结构、脸、耳朵、胡须和毛纹均正常，头部转动明确。与原版使用相同 seed 仍得到不同构图：FastWan 是灰背景近景，原版是白背景全身远景，所以 seed 只能保证各自复现，不能让不同模型输出相同画面。

I2V 保留了猫的位置、体型、尾巴、橙色背景和白色台面，但中后段脸部与腿部花纹变深，右侧阴影增强。原版 20 步在身份、色彩和光照一致性上更可靠。

前两次 FastWan 命令按社区示例启用了 `--vae-conv-direct`，33 帧 TAE 解码约 9.4 秒。65 帧测试取消该选项后，解码只用 3.66 秒。虽然不是严格的单变量 A/B，但结果强烈表明这台 M2 Max 在内存足够时应优先使用默认卷积，把 `--vae-conv-direct` 留作内存不足时的兼容选项。

65 帧明显动作测试证明 I2V 可以制造清楚的抬爪动画：总生成 86.72 秒，0 swap。主体和背景保持良好，但模型把爪子举过了指定的胸口高度，并在末段朝镜头伸出，造成前爪透视过大。它说明动作幅度可以通过更长时长和更明确的单一动作 Prompt 提升，但精确运动轨迹仍不是该本地模型的强项。

进一步的 65 帧原地转头测试取得了更自然的结果：猫连续向画面右侧转头，两只前爪保持落地，没有物体向镜头放大。实际角度约 60–75°，超过提示词要求的 45°；脸部花纹与阴影仍有一定漂移。因此，明确的单一旋转动作比涉及前爪深度变化的动作更容易得到稳定结果。

眨眼单项测试中，猫的双眼能够从睁开逐渐闭合，但闭合后一直保持到结尾，没有完成重新睁开的阶段。这表明 FastWan 在该 seed 和参数下能表达单阶段微表情，却不能可靠执行同一部位的“闭合—停留—重开”时间序列。结果记为部分成功、完整眨眼失败，而不是完全没有理解眨眼。

详细记录：`results/phase-5-fastwan.md`。

## 质量观察

### 正常的 33 帧 T2V

- 生成同一只白色长毛猫；
- 首、中、末帧主体一致；
- 头部与眼睛有可见变化；
- 背景稳定；
- TAE 使毛发细节偏柔，但结构清楚；
- 原速约 1.33 秒，另保存 2 倍慢速检查版。

主要结果：

- `results/generated/phase-2-t2v/05-native-cat-33-frame-tae.webm`
- `results/generated/phase-2-t2v/05-native-cat-33-frame-tae.mp4`
- `results/generated/phase-2-t2v/05-native-cat-33-frame-tae-slow-2x.mp4`
- `results/generated/phase-2-t2v/05-native-cat-33-frame-tae-contact-sheet.png`

### 正常的 33 帧 I2V

输入为项目生成的 832×480 猫图。输出保持了橙色背景、白色台面、主体位置、尾巴、胸毛和脸部花纹；动作幅度小，没有变成另一只猫，也没有明显背景漂移。

主要结果：

- 输入：`results/generated/phase-2-t2v/03-native-resolution-single-frame.png`
- 原速：`results/generated/phase-3-i2v/01-cat-head-turn-33-frame-tae.mp4`
- 慢速：`results/generated/phase-3-i2v/01-cat-head-turn-33-frame-tae-slow-2x.mp4`
- 对照图：`results/generated/phase-3-i2v/01-cat-head-turn-33-frame-tae-contact-sheet.png`

## 完整 VAE 与 TAE 的取舍

完整 VAE 的 17 帧原生视频解码耗时 1514.86 秒；TAE 的 33 帧解码耗时 2.28 秒。虽然帧数更多，TAE 仍快约 665 倍。

- 参数筛选、动作试验、构图预览：优先 TAE。
- 最终纹理与细节：完整 VAE 理论质量更高，但当前 Mac 上代价很大。
- 不应先用完整 VAE 反复试 Prompt；应先用 TAE 找到满意 seed 与动作，再决定是否值得做一次完整解码。

## 工程可靠性

以下错误均在生成前快速失败并返回 exit code 1：

- 不存在的输入图片；
- 0 字节 PNG；
- 文本伪装的 JPEG；
- 不存在的 diffusion model。

结果：`results/phase-4-boundaries/summary.txt`。未发现错误返回 0 的问题。

## 可复现入口

- `scripts/download_models.sh`：验证或下载所有固定版本模型；已有正确文件时只校验，不重复下载。
- `scripts/run_phase1_smoke.sh`：最短端到端冒烟测试。
- `scripts/run_phase2_quality_baseline.sh`：416×256、12 步质量基线。
- `scripts/run_phase2_simple_20step.sh`：416×256、20 步简单提示词对照。
- `scripts/run_phase2_native_frame.sh`：832×480 单帧诊断。
- `scripts/run_phase2_native_video.sh`：832×480、17 帧完整 VAE 对照；非常慢且本次结果失败。
- `scripts/run_phase2_tae_33frame.sh`：832×480、33 帧 T2V 推荐基线。
- `scripts/run_phase3_i2v_cat.sh`：832×480、33 帧 I2V 推荐基线。
- `scripts/run_phase4_error_boundaries.sh`：快速错误输入与退出码检查。
- `scripts/run_phase5_fastwan_t2v.sh`：FastWan 3-step T2V 快速预览。
- `scripts/run_phase5_fastwan_i2v.sh`：FastWan 3-step I2V 快速预览。
- `scripts/run_phase5_fastwan_i2v_visible_motion.sh`：FastWan 65 帧明显动作 I2V。
- `scripts/run_phase5_fastwan_i2v_head_turn.sh`：FastWan 65 帧原地转头 I2V。
- `scripts/run_phase5_fastwan_i2v_blink.sh`：FastWan 65 帧眨眼单项 I2V。
- `scripts/run_phase5_fastwan_t2v_super_tae.sh`：官方 Super TAE 兼容性探针；当前最新版会在元数据验证阶段正确返回非零状态。

## 后续建议

项目已达到阶段性完成标准。若以后继续玩，优先顺序建议：

1. 使用现有 I2V 脚本替换自己的图片与 Prompt；
2. 日常先用 FastWan 3-step + TAE 在约一分钟内筛选动作与 Prompt；
3. 对身份和光照一致性要求较高时，再用原版 20-step + TAE 重跑；
4. 只对真正满意的候选考虑完整 VAE；
5. 若需要数秒、高清、快速出片，云端视频模型仍比当前本机方案更实用。

当前模型总计约 13.47 GiB，可以暂时保留；项目代码、日志、Prompt 和生成结果与模型权重分离，日后删除模型不会损坏研究成果。
