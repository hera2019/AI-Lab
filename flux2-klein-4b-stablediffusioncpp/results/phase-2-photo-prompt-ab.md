# Phase 2：照片提示词 A/B

日期：2026-09-03

## 实际应用意义

在不增加 LoRA、ControlNet、细节修复、放大模型或 ComfyUI 工作流的情况下，用同一模型、同一 seed 和同一采样参数比较简单描述与专业摄影描述，判断提示词本身能带来多少质量改善。

## 固定参数

- 模型、VAE、stable-diffusion.cpp commit：与第一张基线相同
- seed：`260904`
- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- Metal 与 diffusion flash attention：启用
- 运行期间 swaps：两次均为 0

## Prompt A：简单描述

```text
A realistic photograph of an adult Japanese woman sitting by a cafe window, holding a ceramic coffee cup.
```

结果：画面自然、环境信息丰富、色彩讨喜，整体更接近手机或消费级相机的随手人像；人物皮肤稍显平滑，杯子不是白色，手部在第一眼可用但细看仍有生成痕迹。

## Prompt B：专业摄影描述

```text
An unretouched candid 50mm photograph of an adult Japanese woman in her early thirties sitting beside a large cafe window on an overcast afternoon, holding a simple white ceramic coffee cup with both hands. Natural relaxed expression, anatomically correct hands fully visible, realistic skin texture with subtle pores and fine facial hair, individual strands of dark hair, soft window light, gentle shadow falloff, neutral color grading, shallow depth of field, believable modern cafe background, documentary photography, no beauty retouching.
```

结果：白杯、双手、阴天窗光、浅景深、中性色调和纪实构图均明显响应；皮肤比 A 少一些美颜感，但“anatomically correct”并不能保证手指完全自然，局部仍需人工检查。

## 性能

| 指标 | A 简单 prompt | B 详细 prompt |
| --- | ---: | ---: |
| 文字条件计算 | 5.36 秒 | 3.17 秒 |
| 4 steps 采样 | 46.70 秒 | 46.22 秒 |
| VAE 解码 | 8.36 秒 | 8.91 秒 |
| 模型报告总生成 | 60.47 秒 | 58.34 秒 |
| 实际墙钟时间 | 61.33 秒 | 59.28 秒 |
| 最大常驻内存 | 8,563,965,952 字节 | 8,672,985,088 字节 |

本次 B 更快属于正常运行波动，不能据此认为长 prompt 更快。两者主要耗时都是扩散采样；从 20 tokens 增加到 104 tokens 没有造成有实际意义的总时间增长。

## 结论

详细摄影 prompt 确实能控制杯子颜色、用手方式、光线、景深和色彩风格，但不会自动修复所有解剖与真实感问题。基础模型已经能生成相当可用的照片草稿；若目标是高成功率成片，后续再有针对性地比较参考图编辑、细节修复或高精度扩散权重，而不是一次性堆叠许多组件。
