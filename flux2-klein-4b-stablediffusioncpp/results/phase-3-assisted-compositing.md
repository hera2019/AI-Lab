# Phase 3：辅助工具精确合成与像素锁定

日期：2026-09-04

## 实际应用意义

真实的图片编辑产品通常不会要求生成模型独自完成全部工作。生成模型擅长理解语义和补画自然细节，传统图像工具擅长精确位置、透明背景、尺寸、图层和像素级保护。本测试把两者组合，修正首次多参考图测试中“杯子选对但放错位置、还新增前景桌子”的问题。

目标是把物体参考图中间的绿色杯子放到雨夜店铺的蓝猫右侧柜台，同时做到：

- 杯子位置明确可控；
- 原场景在目标区域外逐像素不变；
- 杯子边缘、光色和接触阴影尽量自然；
- 如实记录 FLUX.2 蒙版局部润色的成功与失败边界。

## 工具组合

1. Pillow + NumPy：按颜色和白色背景分离绿色杯子，产生透明 PNG。
2. 确定性图层合成：缩放、放置、暖色匹配和接触阴影。
3. FLUX.2 klein 4B：只在局部蒙版内尝试改善边缘、光线和阴影。
4. 像素蒙版回填：只保留局部生成结果，蒙版外恢复为确定性合成图，从工程上锁住背景。

## 输入与文件

- 原场景：`results/generated/phase-3-single-edit/03-remove-white-cat.png`
- 三杯物体参考：`results/generated/phase-2-instruction-isolation/02-color.png`
- 透明杯子：`results/generated/phase-3-assisted-composite/green-mug-cutout.png`
- 确定性原色合成：`results/generated/phase-3-assisted-composite/01-layer-composite-neutral.png`
- 确定性暖光合成：`results/generated/phase-3-assisted-composite/02-layer-composite-warm.png`
- 局部蒙版：`results/generated/phase-3-assisted-composite/refinement-mask.png`
- 强润色失败输出：`results/generated/phase-3-assisted-composite/03-flux-mask-refinement-raw.png`
- 保守润色原始输出：`results/generated/phase-3-assisted-composite/04-flux-mask-refinement-conservative-raw.png`
- 像素锁定最终图：`results/generated/phase-3-assisted-composite/05-flux-mask-refinement-locked.png`
- 局部对比图：`results/generated/phase-3-assisted-composite/comparison-detail.png`

## 第一步：确定性抠图与放置

这一阶段没有文字 Prompt，也不调用生成模型。脚本用固定规则从白色背景中分离绿色杯子，将其缩放到约 92 × 92 像素，放在 `x=540`、杯底约 `y=634` 的柜台位置，并增加暖色调整与椭圆形接触阴影。

- 执行时间：约 0.26 秒
- 输出位置、尺寸和数量完全确定
- 背景只在杯子与阴影覆盖区域内改变
- 局限：杯子仍比周围场景更干净锐利，带有一定图层粘贴感

## 第二步 A：较强蒙版润色——失败案例

- seed：`260913`
- 1024 × 1024
- steps：4
- strength：0.75（日志中实际 `target t_enc` 为 3 steps）
- sampler：Euler
- CFG：1.0
- 参考图：原始三杯图
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Refine only the single green ceramic mug already positioned on the wooden serving counter, immediately to the right of the small blue ceramic cat. Keep the mug in exactly the same position, size, and orientation. Preserve its green ceramic material and right-side handle, using the center green mug in the reference image as the product reference. Integrate it naturally into the ramen shop with warm amber indoor lighting, realistic contact shadow, subtle counter reflection, clean edges, and correct perspective. Do not move, resize, duplicate, or remove the mug. Do not change the blue cat, counter, shop, people, sign, lanterns, bicycle, rainy street, composition, or any area outside the local masked region. Add no object, animal, person, text, logo, symbol, or decoration.
```

结果：FLUX.2 没有保留杯子，而是把蒙版区域补成了柜台和店员。蒙版成功约束了“允许变化的位置”，但不能保证模型在蒙版内执行保守润色。较高 strength 对 4-step distilled 模型仍然过强。

### 性能

| 阶段 | 耗时 |
| --- | ---: |
| 原图与参考图 VAE 编码 | 9.83 秒 |
| 文字条件计算 | 3.14 秒 |
| 采样 | 90.66 秒 |
| VAE 解码 | 7.66 秒 |
| 模型报告总生成 | 111.29 秒 |
| 实际墙钟时间 | 112.12 秒 |

- 最大常驻内存：8,363,999,232 字节，约 7.79 GiB
- swaps：0

## 第二步 B：低强度保守润色

- seed：`260914`
- 1024 × 1024
- steps：4
- strength：0.35（日志中实际 `target t_enc` 为 1 step）
- sampler：Euler
- CFG：1.0
- 参考图：已经抠出的单只绿色杯子透明 PNG
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Preserve the one green ceramic mug already present on the wooden serving counter to the right of the blue ceramic cat. The separate reference image shows this exact mug. Keep its exact position, size, silhouette, right-side handle, and green color. Make only subtle local improvements to the mug edge, warm amber lighting, contact shadow, and counter reflection so it looks naturally photographed in the existing shop. Do not erase, replace, move, resize, or duplicate the mug. Do not create any person, animal, cup, furniture, text, or decoration. Do not change anything outside the masked area.
```

结果：杯子被保留，位置仍在蓝猫右侧柜台；杯沿、杯柄、边缘和接触关系比纯图层合成更接近生成场景。不过 FLUX.2 仍重新解释了杯子的尺寸、轮廓、亮度以及蒙版内的少量柜台细节，因此它不适合要求商品外形绝对一致的正式产品图。

### 性能

| 阶段 | 耗时 |
| --- | ---: |
| 原图与参考图 VAE 编码 | 9.88 秒 |
| 文字条件计算 | 2.71 秒 |
| 采样 | 47.04 秒 |
| VAE 解码 | 7.58 秒 |
| 模型报告总生成 | 67.21 秒 |
| 实际墙钟时间 | 68.06 秒 |

- 最大常驻内存：8,360,296,448 字节，约 7.79 GiB
- swaps：0

## 第三步：像素级背景锁定

最终只把保守润色图的局部蒙版区域覆盖到确定性暖光合成图。蒙版外不采用 FLUX.2 的 VAE 重建结果。

与原始无杯场景比较：

- 变化包围框：`x=516..658`、`y=517..657`
- 发生变化的像素：18,601，占全图约 1.7739%
- `x=500..679`、`y=500..679` 目标保护框以外的变化像素：0
- 保护框以外最大单通道差：0
- 全图 MAE：0.6068
- 目标框内 MAE：19.6376

因此“背景完全一致”不是主观观察，而是逐像素验证的结果。

## SHA-256

```text
514e22714c35d8362df0b677b7a1d904bafce56d74fd40586531c8ee596aa13c  原场景
1d2a87d25fc8e6235d7cb8c69d94d5c363f5c00cb35206e2dce459424b705508  确定性暖光合成
40692933a7d0632c8fffc18a9e76b7e85d812d31f0ab27557e723977d3f93212  强润色失败输出
05a71ea8fba914296e7b256682fd356c8582387777a64d5004fdfbc0dabad543  保守润色原始输出
b7945f685255f2a3bc2158b39b6207dfbe1cfa69f7fb947b7e7fef4023bf0506  像素锁定最终图
```

## 结论

多工具流程能弥补 FLUX.2 klein 4B 的主要短板：传统工具保证对象选择、透明背景、位置、尺寸和背景像素；FLUX.2 只负责局部自然化；最后再用蒙版把生成影响限制在可审计的区域。

但本次也说明，FLUX.2 的局部润色不是无损滤镜：强度稍高会直接删除目标，强度很低仍可能改变商品轮廓和局部细节。若任务优先级是商品真实性，应以确定性合成为主，只让模型生成阴影或单独的辅助图层；若优先级是视觉自然，可以接受低强度局部生成后再像素锁定。

## Hera 人工复核：初版杯子比例过大

Hera 指出初版柜台杯子几乎赶上自行车车筐大小，缺乏合理的物体尺度。根因不完全是 FLUX.2：确定性合成脚本先把杯子设为约 92 × 92 像素，之后 Prompt 又要求 `Keep its exact position, size`，所以模型被要求保留了一个已经错误的上游尺寸。

这说明 `Keep size` 只表示保持输入图中的像素尺寸，并不等于模型会重新判断现实世界中的合理尺寸。精确编辑流程必须先确定正确的尺寸，再要求生成模型保持。

## 比例修正版

### 实际应用意义

商品摆放不能只判断“有没有放进去”，还需要符合场景尺度。可控的生产流程应把尺寸作为明确参数，而不是完全交给生成模型猜测。

修正内容：

- 确定性合成尺寸从约 92 × 92 像素降为约 64 × 64 像素；
- 固定杯底柜台线不变；
- 杯子初始包围框：`x=540..603`、`y=570..633`；
- 根据新尺寸自动缩小局部蒙版；
- FLUX 继续使用低强度 0.35，只做局部光影融合；
- 最后再次用像素蒙版恢复外围背景。

文件：

- 图层合成：`results/generated/phase-3-assisted-composite/scale-corrected/02-layer-composite-warm.png`
- FLUX 原始润色：`results/generated/phase-3-assisted-composite/scale-corrected/03-flux-mask-refinement-raw.png`
- 像素锁定最终图：`results/generated/phase-3-assisted-composite/scale-corrected/04-flux-mask-refinement-locked.png`
- 尺寸对比：`results/generated/phase-3-assisted-composite/scale-corrected/comparison-scale.png`

Prompt：

```text
Preserve the one realistically small green ceramic mug already positioned on the wooden serving counter to the right of the blue ceramic cat. The separate reference image shows this exact mug. Keep its current exact small size, position, silhouette, right-side handle, and green color. A normal drinking mug should remain smaller than the nearby blue cat ornament and appropriately scaled for the counter. Make only subtle local improvements to its edge, warm amber lighting, contact shadow, and counter reflection. Do not enlarge, move, erase, replace, or duplicate the mug. Do not create any person, animal, cup, furniture, text, or decoration. Do not change anything outside the masked area.
```

参数：

- seed：`260915`
- 输出：1024 × 1024
- steps：4
- strength：0.35，实际 `target t_enc` 为 1 step
- sampler：Euler
- CFG：1.0
- 参考图：单只绿色杯子透明 PNG
- Metal、diffusion flash attention、CPU offload：启用

性能：

| 阶段 | 耗时 |
| --- | ---: |
| 原图与参考图 VAE 编码 | 10.60 秒 |
| 文字条件计算 | 4.81 秒 |
| 采样 | 48.03 秒 |
| VAE 解码 | 7.81 秒 |
| 模型报告总生成 | 71.25 秒 |
| 实际墙钟时间 | 71.99 秒 |

- 最大常驻内存：8,282,898,432 字节，约 7.71 GiB
- swaps：0

像素锁定验证：

- 与无杯原场景相比，变化包围框：`x=516..630`、`y=547..657`
- 发生变化的像素：11,364，占全图约 1.0838%
- 新目标保护框外变化像素：0
- 保护框外最大单通道差：0
- 全图 MAE：0.2728
- 目标框内 MAE：15.1361

SHA-256：

```text
c527ba49bc621bf9ac960f725f452704fba68df43207de9ea4fb2d44298a3695  64 像素图层合成
ef877894ed34756de59330ed80c6203177aece2b652552fc10619b535babfc65  FLUX 原始润色
2580684399d9c2449da8e8bf85f77b598689e3d297f525c5f443a4fed535da0a  比例修正、像素锁定最终图
```

初步判断：比例问题已明显改善，FLUX 没有重新放大杯子，并将它压暗到更接近店内环境；背景继续保持逐像素锁定。最终尺度和自然度仍需 Hera 人工确认。

### Hera 人工复核结果

- 杯子大小正常。
- 整体评价：非常好。
- 最终判定：比例修正版通过；采用 `64 × 64` 确定性初始尺寸、低强度 FLUX 局部润色和像素背景锁定的组合流程有效。

## 请 Hera 人工复核

- 纯图层暖光版是否过于像贴图？
- 低强度 FLUX 版是否更自然？
- FLUX 版对杯子尺寸、形状和蒙版内柜台细节的变化是否可以接受？
- 最终更倾向保留“商品更准确的纯图层版”，还是“融合更自然的 FLUX + 像素锁定版”？
- 比例修正版中的杯子是否已经符合柜台和自行车车筐的尺度关系？
