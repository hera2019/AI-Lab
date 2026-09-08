# Phase 5 收尾：Super TAE 兼容性测试

日期：2026-09-05（Asia/Tokyo）

## 实际应用意义

普通 TAE 解码极快，但毛发和细节偏柔。官方 `taew2_2_super` 的目标是在仍然轻量的前提下提高细节和时间稳定性。本测试原计划固定 FastWan、Prompt、seed 和全部生成参数，只更换 TAE 解码器，以判断更好的本地快速解码是否可用。

## 固定版本

- stable-diffusion.cpp：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- 远端 `master`（测试时）：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- TAEHV 仓库 revision：`011dfc2112197741c540e0bdd5b7b67bcc930771`
- 文件：`taew2_2_super.safetensors`
- 大小：40,986,488 bytes
- SHA-256：`cf6d8bdadb77d9f9741ae28b5b4659bb74cf9b0be6d08fc4afed3cb50c39364c`

## 测试设计

测试入口：`scripts/run_phase5_fastwan_t2v_super_tae.sh`

与 `scripts/run_phase5_fastwan_t2v.sh` 的普通 TAE 基线保持相同：

- 相同 Prompt 与 negative prompt；
- seed `260905`；
- 832×480、33 帧、24 fps；
- FastWan Q8_0；
- 3 steps、CFG 1.0、Euler、LCM、flow shift 3.0；
- 只把 `taew2_2.safetensors` 换为 `taew2_2_super.safetensors`。

选择 T2V 而不是 I2V，是为了只比较输出解码。I2V 还会使用 TAE 编码输入图片，会把编码器差异也混入结果。

## 实际结果

- exit code：1
- 实耗：0.38 秒
- 最大常驻内存：155,074,560 bytes（约 148 MiB）
- swap：0
- 扩散采样：未开始
- 输出视频：未创建

关键错误：

```text
VAE tensor 'tae.decoder.1.bias' not in model metadata
VAE tensor 'tae.decoder.10.conv.0.weight' has wrong shape in model metadata:
got [7, 7, 1, 512], expected [3, 3, 256, 128]
model metadata validation failed
new_sd_ctx_t failed
```

完整日志：`results/generated/phase-5-fastwan/06-fastwan-cat-t2v-3step-super-tae.log`

完整 Prompt：`results/generated/phase-5-fastwan/06-fastwan-cat-t2v-3step-super-tae-prompt.txt`

## 根因

文件大小和 SHA-256 均正确，失败不是下载损坏、内存不足、Metal 错误或生成参数问题。程序在建立推理上下文时发现网络结构不匹配并安全停止。

官方 Super 解码器不是普通 TAE 的简单加宽版：

- 通道为 `[512, 256, 128, 64]`；
- 首层是无 bias 的 1×1 convolution；
- 使用 `SuperMemBlock`：7×7 depthwise convolution 加 1×1 inverted bottleneck；
- 空间放大使用 PixelShuffle。

当前 stable-diffusion.cpp 的 `is_wide` 路线则是另一套结构：

- 通道为 `[1024, 512, 256, 64]`；
- 首层是 3×3 convolution；
- 使用 `WideMemBlock`：1×1、grouped 3×3、1×1、grouped 3×3；
- 使用 nearest-neighbor upscale 加 convolution；
- 通过查找 `.3.conv.6.weight` 判断 wide 权重，而官方 Super 文件没有这个参数名。

因此程序把 Super 文件按普通 TAE 结构装载，随后报告大量缺失参数与形状不匹配。

## 上游状态

截至 2026-09-05：

- 本地测试 commit 与 GitHub 远端最新 `master` 相同；
- 用 `taew2_2_super`、`SuperMemBlock`、`super TAE` 检索 stable-diffusion.cpp 的 Issue 和 Pull Request，没有发现已有支持或重复报告；
- TAEHV 官方明确把 `taew2_2_super` 描述为 Wan2.2 5B 的高质量轻量解码器；
- stable-diffusion.cpp 当前文档与实现支持普通 `taew2_2`，但尚未实现这套 Super 架构。

官方参考：

- <https://github.com/madebyollin/taehv>
- <https://github.com/leejet/stable-diffusion.cpp/blob/master/src/model/vae/tae.hpp>

## 结论

普通 TAE 与 Super TAE 的画质 A/B 暂时无法在当前 stable-diffusion.cpp 上完成。已确认的是一个明确、可复现的功能缺口，而不是本机性能问题。

如果以后要向上游反馈，适合提交 feature request：支持 TAEHV 的 `SuperMemBlock` / `taew2_2_super`，并附上本报告中的固定 commit、权重哈希、复现脚本与元数据错误。当前项目不修改 stable-diffusion.cpp 源码。
