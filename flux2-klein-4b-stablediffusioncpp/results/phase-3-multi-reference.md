# Phase 3：多参考图组合编辑

日期：2026-09-04

## 实际应用意义

多参考图编辑可以把一张产品图中的指定商品放入另一张场景图，常见于电商展示、广告草图和室内陈列预览。本测试重点不是让模型随意生成一个绿色杯子，而是同时完成三件事：从第二张参考图选对中间的绿色杯子、把它放到第一张参考图的指定位置，并尽量不改动原场景。

## 输入与目标

- 场景参考图：`results/generated/phase-3-single-edit/03-remove-white-cat.png`
- 物体参考图：`results/generated/phase-2-instruction-isolation/02-color.png`
- 输出图：`results/generated/phase-3-multi-reference/01-green-mug-in-ramen-shop.png`
- seed：`260912`
- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- 两张参考图，参考图模式：`preset=flux2`
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Use reference image 1 as the base scene. From reference image 2, take only the solid green ceramic mug in the center, not the red mug and not the blue mug. Place exactly one green ceramic mug on the right side of the wooden serving counter in reference image 1, in the empty space to the right of the small blue ceramic cat. Match the shop's warm lighting, perspective, scale, contact shadow, and reflections so the mug sits naturally on the counter. Preserve every other part of reference image 1: the blue ceramic cat, red bicycle, all five paper lanterns, storefront, rainy street, people, lighting, composition, and the exact current sign text AI LLAB. Do not alter or correct the sign. Do not add any red or blue mug, extra cup, cat, animal, person, word, logo, symbol, or decoration.
```

## 结果观察

### 成功部分

- 两张参考图都被实际编码，确实进入多参考图编辑流程。
- 正确选取第二张参考图中间的绿色陶瓷杯，没有带入红杯或蓝杯。
- 只生成一只杯子，没有额外杯子、动物、人物或文字。
- 杯子的绿色、圆柱造型和右侧杯柄与物体参考图一致，具有明确的跨图参考特征。
- 杯子的暖色环境反射、接触阴影和桌面倒影自然，作为独立合成物体具有较好的真实感。
- 原场景中的蓝猫、五盏灯笼、红色自行车、人物和错误招牌文字 `AI LLAB` 均保留。

### 失败部分

- 指令要求把杯子放在店内木质服务柜台上、蓝猫右侧；输出没有遵循这一精确位置。
- 模型在右下角新生成了一张占据前景的大桌子，再把杯子放到新桌子上。
- Prompt 明确要求保留构图且不增加其他物体，因此新增桌子同时违反了位置约束、构图保持和禁止新增物体三项要求。
- 原本指定的柜台区域几乎没有发生目标编辑，证明这不是轻微落位误差，而是模型重新解释了场景结构。
- 场景其他区域仍有生成式纹理漂移，尤其是左侧雨景和自行车；主要物体结构则基本保持。

## 像素变化抽样

`MAE` 是每个 RGB 通道平均相差多少灰度级，满量程为 255；越低越接近。`PSNR` 越高越接近。

| 区域 | MAE | PSNR | 单像素最大通道差 > 20 |
| --- | ---: | ---: | ---: |
| 全图 | 9.818 | 22.58 dB | 12.44% |
| 上部场景 | 6.936 | 28.90 dB | 6.27% |
| 新增桌子与杯子区域 | 27.519 | 15.02 dB | 49.67% |
| 原本指定的蓝猫右侧柜台 | 6.235 | 29.73 dB | 3.62% |
| 蓝色陶瓷猫 | 5.952 | 30.08 dB | 3.98% |
| 招牌 | 5.498 | 30.40 dB | 4.11% |
| 自行车 | 7.783 | 27.94 dB | 7.55% |
| 左侧街道 | 7.984 | 27.73 dB | 8.73% |

最大变化集中在右下角新桌子和杯子；指定柜台区域的变化反而接近普通背景漂移。这与视觉判断一致。

## 性能

| 阶段 | 耗时 |
| --- | ---: |
| 两张参考图 VAE 编码 | 10.24 秒 |
| 文字条件计算 | 4.32 秒 |
| 4 steps 采样 | 154.03 秒 |
| VAE 解码 | 7.80 秒 |
| 模型报告总生成 | 176.39 秒 |
| 实际墙钟时间 | 177.27 秒 |

- 最大常驻内存：8,313,389,056 字节，约 7.74 GiB
- 进程 swaps：0
- 与同一复杂场景的单参考物体移除相比，总时间从 107.44 秒增至 176.39 秒，约为 1.64 倍。
- 最大常驻内存从约 7.04 GiB 增至约 7.74 GiB。

## 文件哈希（SHA-256）

```text
514e22714c35d8362df0b677b7a1d904bafce56d74fd40586531c8ee596aa13c  场景参考图
c6a116284f61789a086862549e7718c5066d8362896e6688781d4ddd660e89db  物体参考图
1116f714d322316f2f30d967a05c7e1a7229a3529dad76778b42eb8493b97631  输出图
```

## 初步结论

本次多参考图测试是“对象选择与自然融合成功，精确落位与场景保持失败”。模型已经能理解两张图的不同角色，并把指定产品的主要视觉特征带入新场景；但仅靠文字描述不足以可靠控制复杂场景中的精确放置位置。实际产品合成若要求物体必须落在指定区域，应增加蒙版、坐标/框选或传统图层合成，而不能只依赖自然语言。

## 请 Hera 人工复核

- 绿色杯子是否明显继承了第二张图中间杯子的造型和颜色？
- 杯子的光线、阴影、比例和桌面倒影是否自然？
- 新增的前景桌子是否可以接受，还是应判定为明显违反要求？
- 除右下角外，蓝猫、灯笼、自行车、招牌和雨夜场景的变化是否容易察觉？
- 作为电商或广告草图，你会判定“可直接用”“构思可用但需重做落位”还是“不合格”？
