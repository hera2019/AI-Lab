# Phase 4：尺寸、画幅与错误处理

日期：2026-09-04

## 实际应用意义

尺寸测试用于选择预览、迭代和最终出图的合理分辨率，并观察横竖画幅是否影响提示遵循。错误处理测试用于确认 `sd-cli` 适合被脚本、ComfyUI 或 App 调用：输入或保存失败时必须返回非零退出码，不能让上层自动流程误以为成功。

## 固定生成参数

- seed：`260903`
- steps：4
- sampler：Euler
- CFG：1.0
- Metal、diffusion flash attention：启用
- CPU offload：启用
- 扩散模型：FLUX.2 klein 4B `Q4_0`
- 文字编码器：Qwen3-4B `Q4_K_M`
- stable-diffusion.cpp：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- 脚本：`scripts/run_phase4_size_aspect.sh`
- 图片、完整日志和 prompt：`results/generated/phase-4-size-aspect/`

完整 Prompt：

```text
A cinematic realistic photograph of a tiny ramen shop on a quiet Tokyo side street at night in the rain, viewed through wet glass. Exactly three warm paper lanterns hang above the entrance. One red bicycle is parked on the left side. A small blue ceramic cat sits on the counter. Warm amber interior light contrasts with cool teal rain, detailed reflections, natural proportions, 35mm photography. A simple clean sign above the door clearly reads AI LAB.
```

## 性能结果

| 画幅 | 像素数 | 文字条件 | 4 steps 采样 | 模型报告总生成 | 墙钟时间 | 最大常驻内存 | swap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 512 × 512 | 262,144 | 6.04 秒 | 18.48 秒 | 26.61 秒 | 27.29 秒 | 7.58 GiB | 0 |
| 768 × 768 | 589,824 | 3.03 秒 | 28.87 秒 | 36.35 秒 | 37.18 秒 | 7.51 GiB | 0 |
| 1024 × 768 横图 | 786,432 | 3.13 秒 | 36.40 秒 | 45.60 秒 | 46.51 秒 | 7.58 GiB | 0 |
| 768 × 1024 竖图 | 786,432 | 3.25 秒 | 36.44 秒 | 45.75 秒 | 46.68 秒 | 8.03 GiB | 0 |
| 1024 × 1024 方图（Phase 1 热运行） | 1,048,576 | 2.76 秒 | 44.03 秒 | 54.78 秒 | 55.42 秒 | 8.06 GiB | 0 |

首次 512 运行的文字条件计算较慢，主要是进程与系统冷启动差异，不能据此认为 512 的文字编码本身更慢。采样时间随像素数增加而上升；峰值内存约 7.5–8.1 GiB，四次都没有使用交换空间。

## 画面观察

### 512 × 512

- 正好三盏灯笼；
- 一辆红色自行车位于左侧；
- 一只蓝色猫摆件位于柜台；
- `AI LAB` 拼写正确；
- 四张中提示遵循最完整，但远处细节最少。

### 768 × 768

- 三盏灯笼、自行车位置和 `AI LAB` 均正确；
- 蓝猫更像毛绒动物，陶瓷材质表达不够准确；
- 画面细节和迭代速度较均衡。

### 1024 × 768 横图

- 三盏灯笼与左侧红色自行车正确；
- 出现两只猫，违反“单只蓝猫”；
- `AI LAB` 被放到门的下部，不在门上方；上方另有乱码式招牌；
- 横向环境表现好，但对象数量与文字位置的遵循下降。

### 768 × 1024 竖图

- `AI LAB` 拼写和位置正确，自行车仍在左侧；
- 实际生成四盏灯笼和两只猫；
- 竖向构图自然，没有明显拉伸，但数量约束下降。

结论：相同 seed 在不同尺寸下不会得到同一张图的缩放版本，而是使用不同形状的噪声画布重新生成。因此，分辨率越高不保证指令越准确，横竖画幅也必须分别人工检查。

推荐实际用法：

- `512 × 512`：快速验证 prompt、物体和文字要求；
- `768 × 768`：速度与细节均衡的普通草稿；
- `1024 × 768` 或 `768 × 1024`：横竖构图确认；
- `1024 × 1024`：确定 prompt 后的最终候选图；仍需逐张核对数量、文字和尺度。

## 文件哈希（SHA-256）

```text
620976e28e5d70865e92f0daa52460ac6fbe380bab39bc46e9a88f3dddb33d82  01-square-512.png
eb29e962cc8ebd651088422c22fdff4552c1d36d4b2db2debcb3c0a3470029f7  02-square-768.png
c3b18347a89ba1802d6cd6ddf9d5eb2b31deed2ae1852fb861c1f025986f746f  03-landscape-1024x768.png
9321f7aabad585298110d97b011a6a9bba638783026f92e464c4141f75b1d0fb  04-portrait-768x1024.png
```

## 错误处理

脚本：`scripts/run_phase4_error_handling.sh`

| 案例 | 预期 | 实际退出码 | 结果 |
| --- | --- | ---: | --- |
| 未知命令行参数 | 非零 | 1 | 通过 |
| 扩散模型路径不存在 | 非零 | 1 | 通过 |
| 参考图片不存在 | 非零 | 1 | 通过 |
| 图像生成后无法保存到目标 | 非零 | 1 | 通过 |

```text
01-unknown-option exit_code=1
01-unknown-option correctly_failed=yes
02-missing-model exit_code=1
02-missing-model correctly_failed=yes
03-missing-reference exit_code=1
03-missing-reference correctly_failed=yes
04-save-failure exit_code=1
04-save-failure correctly_failed=yes
unexpected_successes=0
```

最后一个案例用 64 × 64、1 step 完成最小生成，再故意把输出目标设置为同名目录。日志显示 `0/1 images saved`，进程正确返回 1。测试产生的临时文件已自动删除，只保留日志和摘要。

## 本阶段范围说明

- 没有下载更高精度权重；Q4_0 已满足本项目体验与能力边界判断，继续下载会增加数 GB 占用，却不能保证解决构图、数量和编辑保持问题。
- 没有跑 CPU 全生成对照；本机目标是 Metal，本项目已有明确的 Metal 成功证据，纯 CPU 慢测没有足够实际收益。
- 没有重复做 Web/API 功能测试；CLI 已覆盖核心生成和失败传播，本项目也不以开发 App 为目标。
- 本阶段没有发现值得立即提交 upstream 的新问题。

## Phase 4 结论

FLUX.2 klein 4B 在 M2 Max 上从 512 预览到 1024 最终图都能稳定运行，速度随像素数合理上升、内存有余量且无 swap。基础命令行错误能够可靠返回非零状态。它适合本地概念图、配图、视觉草稿和人工监督下的编辑；不适合把物体数量、文字、尺度和未编辑区域完全交给模型自行保证。
