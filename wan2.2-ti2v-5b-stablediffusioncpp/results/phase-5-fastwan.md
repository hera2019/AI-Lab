# Phase 5：FastWan 3-step 加速测试

日期：2026-09-05（Asia/Tokyo）

## 实际应用意义

原版 Wan2.2 TI2V 5B 在本机生成 832×480、33 帧视频约需 7 分钟。FastWan 是面向极少步数的社区蒸馏模型；本阶段判断它能否把预览时间压到约 1 分钟，同时保留足够的主体结构和运动连续性。

推荐工作流不是用快版取代所有正式生成，而是：先用 FastWan 反复试 Prompt、动作与 seed，再对少数满意候选使用原版 20 步。

## 模型与固定版本

- FastWan 仓库：`Green-Sky/FastWan2.2-TI2V-5B-FullAttn-GGUF`
- Revision：`3e8fe5537b1200654868aa24ea8d0f4012fb3a1e`
- 文件：`FastWan2.2-TI2V-5B-q8_0.gguf`
- 精确大小：5,412,844,128 bytes
- SHA-256：`b62f50ff87c4dfa2910c6883d45015e05b709366581698b302e259e7f25c9208`
- 性质：社区蒸馏模型，不是 Wan-AI 官方发布
- stable-diffusion.cpp：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`

选择 Q8_0 是为了先判断蒸馏本身的速度和质量，避免再叠加激进量化造成的质量损失。32 GB Unified Memory 实测可以承载该组合。

## 共同参数

- 832×480
- 33 帧，24 fps
- 3 steps
- CFG 1.0
- Euler sampler
- LCM scheduler
- flow shift 3.0
- UMT5-XXL Q5_K_M
- TAEHV
- Apple Metal
- diffusion flash attention
- offload parameters to CPU
- 前两轮启用 VAE direct convolution；65 帧测试使用默认卷积

完整 Prompt、negative prompt 和 seed 已分别保存在同名 `*-prompt.txt` 文件中。

## 结果

| 测试 | 采样 | TAE 解码 | 模型内部总生成 | 脚本实耗 | 最大常驻内存 | swap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FastWan T2V | 37.80s | 9.45s | 57.21s | 58.93s | 14.79 GiB | 0 |
| FastWan I2V | 38.10s | 9.42s | 54.39s | 56.19s | 14.87 GiB | 0 |
| FastWan 65-frame visible-motion I2V | 71.12s | 3.66s | 86.72s | 89.07s | 13.97 GiB | 0 |
| FastWan 65-frame head-turn I2V | 72.99s | 3.61s | 86.88s | 89.20s | 14.31 GiB | 0 |
| FastWan 65-frame blink-only I2V | 69.59s | 3.40s | 83.95s | 86.28s | 14.00 GiB | 0 |

官方 `taew2_2_super` 的同参数 T2V A/B 没有进入本表，因为当前最新版 stable-diffusion.cpp 在模型元数据检查阶段即拒绝该权重，没有开始扩散采样，也没有生成视频。它不是一次可比较的性能测试。详见 `results/phase-5-super-tae-compatibility.md`。

与原版 20 步基线相比：

| 测试 | 原版总生成 | FastWan 总生成 | 总生成加速 | 原版采样 | FastWan 采样 | 采样加速 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T2V | 428.23s | 57.21s | 7.49× | 414.59s | 37.80s | 10.97× |
| I2V | 426.14s | 54.39s | 7.84× | 412.55s | 38.10s | 10.83× |

两段输出均为可完整解码的 VP8 WebM，832×480、24 fps、约 1.333 秒；同时保存 H.264 MP4、2 倍慢速检查版和首/中/末帧接触表。

## 画质观察

### T2V

- 三个检查帧中的猫结构稳定，没有额外肢体或明显面部崩坏；
- 头部转动明显，主体连续；
- 胡须、耳朵和毛发细节清楚；
- 与原版相同 seed 仍得到不同构图：快版为灰背景近景，原版为白背景全身远景；
- Prompt 中的白色表面、居中全身构图在快版中遵从较弱。

### I2V

- 保留输入图的猫、位置、体型、尾巴、橙色背景和白色台面；
- 中后段脸部和腿部花纹明显变深；
- 右侧阴影增强，说明光照一致性弱于原版 20 步；
- 快版适合检查动作方向，不应仅凭首帧判断身份稳定性。

### 65 帧明显动作 I2V

第三轮把时长增加到 65 帧（2.667 秒），并把任务收敛成一个清楚动作：猫抬起画面左侧的前爪到胸口高度并停住。

- 猫完成了连续、肉眼清楚的抬爪动作；
- 主体保持坐姿，没有增加额外肢体，背景构图基本稳定；
- 模型没有严格停在胸口高度，而是继续把爪子举过头顶，末段又朝镜头伸出；
- 末段前爪因透视被夸张放大，动作语义成立，但精确轨迹控制不足；
- 帧数从 33 增至 65 后，采样约为 1.87 倍，总生成约为 1.59 倍，仍控制在约 1.5 分钟。

这说明前两轮“几乎不动”主要来自微动作 Prompt 和 1.33 秒时长，而不是 I2V 完全无法制造明显运动。

前两轮启用 `--vae-conv-direct` 时，33 帧 TAE 解码约 9.4 秒。65 帧测试取消该选项后，帧数接近翻倍，解码却只用 3.66 秒。虽然不是只改变单一变量的严格 A/B 测试，但结果强烈表明这台 M2 Max 在内存足够时应优先使用默认卷积，把 `--vae-conv-direct` 留作内存不足时的兼容选项。

### 65 帧原地转头 I2V

第四轮把运动限制为头部原地向画面右侧转动约 45°，明确禁止头部靠近镜头、身体和前爪运动。

- 转头方向和连续性正确，没有出现头部或前爪的夸张透视放大；
- 两只前爪始终落地，身体与尾巴基本保持原位；
- 实际转角约 60–75°，大于要求的 45°，说明角度控制仍是近似的；
- 中后段脸部花纹和右侧阴影变深，FastWan 的纹理与光照漂移仍然存在；
- 相比抬爪测试，这一动作更自然、更稳定，也更适合作为本机 I2V 的成功样例。

### 65 帧眨眼单项 I2V

第五轮删除转头和其他动作，只要求猫在中段缓慢完成一次双眼眨眼。逐帧检查第 20–64 帧后确认：

- 双眼从睁开逐渐闭合，眼睑运动清楚且基本对称；
- 双眼闭合后一直保持到最后一帧，没有重新睁开；
- 因此结果不是完整眨眼，而是“睁眼 → 闭眼 → 保持闭眼”；
- 模型能够理解单阶段眼睑动作，但没有可靠执行“闭合 → 短暂停留 → 重新睁开”的多阶段时间顺序；
- 该 seed 和参数下应记为部分成功、完整眨眼失败。单次失败不能证明所有 seed 都无法眨眼，但说明这不是可靠能力。

### Super TAE 兼容性边界

最后尝试使用官方 `taew2_2_super.safetensors`，以与 FastWan T2V 基线完全相同的 Prompt、seed 和生成参数做解码器 A/B。

- 权重下载与 SHA-256 校验成功；文件本身没有损坏；
- stable-diffusion.cpp `6b3edaaf32cc19e5bb2d819c788bd557eddc8eba` 同时是测试时远端最新 `master`；
- 程序在模型元数据验证阶段返回 exit code 1，实耗 0.38 秒，未开始采样，未生成输出视频；
- 官方 Super 模型使用 `SuperMemBlock`、7×7 depthwise convolution、1×1 inverted bottleneck、PixelShuffle 和 `[512, 256, 128, 64]` 通道；
- 当前 stable-diffusion.cpp 的所谓 `is_wide` 路线是另一种 `WideMemBlock` 结构，并不能读取这份 Super 权重；
- 截至 2026-09-05，以 `taew2_2_super`、`SuperMemBlock` 和 `super TAE` 检索上游 Issue/PR，没有发现已有支持或重复报告。

因此本轮没有得到“普通 TAE 与 Super TAE 谁更好”的画质结论。得到的是更基础的兼容性结论：当前 stable-diffusion.cpp 尚不支持官方 `taew2_2_super` 架构。该功能缺口可以日后整理为 feature request；本项目不修改上游源码。

## 使用建议

- 快速找动作、构图和 seed：FastWan 3-step + TAE。
- 需要更稳定的身份、纹理与光照：原版 20-step + TAE。
- 最终高质量解码：只有候选非常满意时才考虑完整 VAE；本机完整 VAE 视频解码非常慢。
- 不同模型之间即使 seed 相同，也不应期待相同画面；seed 的作用是让同一模型与同一参数可复现。

## 结果文件

- T2V：`results/generated/phase-5-fastwan/01-fastwan-cat-t2v-3step.mp4`
- T2V 慢速：`results/generated/phase-5-fastwan/01-fastwan-cat-t2v-3step-slow-2x.mp4`
- I2V：`results/generated/phase-5-fastwan/02-fastwan-cat-i2v-3step.mp4`
- I2V 慢速：`results/generated/phase-5-fastwan/02-fastwan-cat-i2v-3step-slow-2x.mp4`
- 65 帧明显动作 I2V：`results/generated/phase-5-fastwan/03-fastwan-cat-i2v-visible-motion-65frame.mp4`
- 65 帧明显动作慢速版：`results/generated/phase-5-fastwan/03-fastwan-cat-i2v-visible-motion-65frame-slow-2x.mp4`
- 65 帧原地转头 I2V：`results/generated/phase-5-fastwan/04-fastwan-cat-i2v-head-turn-65frame.mp4`
- 65 帧原地转头慢速版：`results/generated/phase-5-fastwan/04-fastwan-cat-i2v-head-turn-65frame-slow-2x.mp4`
- 65 帧眨眼单项 I2V：`results/generated/phase-5-fastwan/05-fastwan-cat-i2v-blink-65frame.mp4`
- 65 帧眨眼单项慢速版：`results/generated/phase-5-fastwan/05-fastwan-cat-i2v-blink-65frame-slow-2x.mp4`
- Super TAE 兼容性报告：`results/phase-5-super-tae-compatibility.md`
- Super TAE 失败日志：`results/generated/phase-5-fastwan/06-fastwan-cat-t2v-3step-super-tae.log`
- Super TAE 完整 Prompt：`results/generated/phase-5-fastwan/06-fastwan-cat-t2v-3step-super-tae-prompt.txt`
- T2V 左右对比：`results/generated/phase-5-fastwan/comparisons/t2v-original-left-fastwan-right-slow.mp4`
- I2V 左右对比：`results/generated/phase-5-fastwan/comparisons/i2v-original-left-fastwan-right-slow.mp4`

左右对比视频固定为：左边原版 20 步，右边 FastWan 3 步。
