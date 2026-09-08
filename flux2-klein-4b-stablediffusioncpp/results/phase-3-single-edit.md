# Phase 3：单点图片编辑

日期：2026-09-04

## 实际应用意义

图片编辑的关键不是只生成正确的新内容，而是只改指定位置并保留其余内容。本测试用结构简单、位置明确的原图，把“是否听懂修改要求”和“未编辑区域能否保持”分开观察。

## 输入与目标

- 输入图：`results/generated/phase-2-instruction-isolation/03-position.png`
- 输出图：`results/generated/phase-3-single-edit/01-blue-to-yellow.png`
- seed：`260909`
- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- 参考图模式：`preset=flux2`
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Edit the provided image. Change only the blue glass sphere on the right to yellow glass. Preserve its transparent glass material, reflections, exact size, and exact position. Keep the red wooden cube on the left, beige background, lighting, shadows, camera angle, and composition unchanged. Do not add, remove, or move any objects. Add no text.
```

## 结果观察

- 成功进入 `EDIT mode`，参考图确实参与编辑，不是普通文生图。
- 蓝色玻璃球正确变为黄色玻璃球。
- 球的大小、位置、透明材质和主要反射结构基本保持。
- 红色木方块的位置、形状、纹理和整体颜色在视觉上高度接近原图。
- 没有增加、删除或移动物体，也没有生成文字。
- 球下方的蓝色投影变为黄色，是与球颜色相符的合理物理联动。
- 背景和方块并非逐像素不变；模型生成了一张视觉上高度相似的新图，而不是只替换原图中的球像素。

## 像素变化抽样

`MAE` 是每个 RGB 通道平均相差多少灰度级，满量程为 255；越低越接近。`PSNR` 越高越接近。

| 区域 | MAE | PSNR | 单像素最大通道差 > 20 |
| --- | ---: | ---: | ---: |
| 全图 | 8.780 | 21.59 dB | 7.53% |
| 顶部背景 | 5.456 | 31.69 dB | 0.00% |
| 中央空白背景 | 4.074 | 34.66 dB | 0.03% |
| 方块周围区域 | 5.859 | 30.24 dB | 5.13% |
| 玻璃球区域 | 35.700 | 12.84 dB | 56.64% |

变化主要集中在目标玻璃球；未编辑背景只有轻微色调和纹理变化。因为几乎没有像素做到完全相同，所以不能把这种参考图编辑当作像素级无损局部修改。若真实任务要求背景绝对不动，应使用蒙版合成或把生成结果仅覆盖回目标区域。

## 性能

| 阶段 | 耗时 |
| --- | ---: |
| 参考图 VAE 编码 | 6.14 秒 |
| 文字条件计算 | 6.32 秒 |
| 4 steps 采样 | 99.37 秒 |
| VAE 解码 | 8.08 秒 |
| 模型报告总生成 | 119.92 秒 |
| 实际墙钟时间 | 120.81 秒 |

- 最大常驻内存：8,022,867,968 字节，约 7.47 GiB
- 进程 swaps：0
- 纯生图基线约 57 秒，本次参考图编辑约为其 2.1 倍。

## 文件哈希（SHA-256）

```text
fdb7d7eb54b7109866a69a6d3f722a673a70e862628f3a8434dd0177cfe6b7ac  输入图
4378dfc791120d7c646b5cb151aa1ea47b40a0807faf7395fcd488122ae08b14  输出图
```

## 初步结论

本次单点颜色编辑成功，而且视觉保持能力明显优于从头重新生成一张类似构图。它适合概念图、商品草稿和不要求像素锁定的自然修图；若用于严格的产品素材、UI 截图或证据图片，仍需蒙版和传统图像合成保证未编辑区域完全不变。

## 请 Hera 人工复核

- 黄色是否符合要求，还是偏橙/金色？
- 玻璃球的位置、大小、材质和反射是否足够接近原图？
- 红方块和背景的细微变化是否能被肉眼察觉？
- 作为实际修图结果，你会判定“可直接用”“需轻微后期”还是“不可用”？

## Hera 人工复核结果

- 背景变化比较明显，将输入与输出放在一起时肉眼可以辨认。
- 玻璃球改色、材质、位置和其他主体表现良好。
- 最终判定：编辑目标通过；未编辑背景保持仅部分通过。
- 实际使用建议：普通创意图可用；若要求背景严格不变，需要蒙版或传统图像合成。

---

## 02：精确文字替换

### 实际应用意义

招牌、包装和海报修改经常只需要替换一个词。成功标准不只是拼写正确，还包括保持招牌的位置、尺寸、字体风格、墙面和光影。

### 输入与目标

- 输入图：`results/generated/phase-2-instruction-isolation/04-text.png`
- 输出图：`results/generated/phase-3-single-edit/02-local-ai-to-local-lab.png`
- seed：`260910`
- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- 参考图模式：`preset=flux2`
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Edit the provided image. Replace only the exact uppercase text LOCAL AI with the exact uppercase text LOCAL LAB. The sign must contain only LOCAL LAB, perfectly spelled, in the same large black sans-serif style and centered placement. Preserve the rectangular white sign's exact size and position, the dark wall, lighting, shadows, camera angle, and composition. Do not add any other words, letters, logos, symbols, objects, or decorations.
```

### 结果观察

- 正确将 `LOCAL AI` 替换为 `LOCAL LAB`，大小写、拼写和空格均正确。
- 没有产生多余文字、符号、图标或物体。
- 招牌的矩形形状、位置、尺寸、正面视角和阴影基本保持。
- 仍为大号黑色无衬线字体并保持居中；为了容纳更长文字，字形和字距发生了合理的重新排版。
- 墙面和招牌空白区仍有轻微纹理与色调漂移，但低于第一次改色测试的背景变化。

### 像素变化抽样

| 区域 | MAE | PSNR | 单像素最大通道差 > 20 |
| --- | ---: | ---: | ---: |
| 全图 | 7.311 | 18.51 dB | 2.91% |
| 顶部墙面 | 3.490 | 35.96 dB | 0.00% |
| 底部墙面 | 1.867 | 40.55 dB | 0.00% |
| 招牌上部空白 | 3.226 | 37.12 dB | 0.00% |
| 招牌下部空白 | 1.656 | 41.92 dB | 0.00% |
| 文字区域 | 38.493 | 9.72 dB | 20.45% |

差异按预期高度集中在文字区域。未编辑墙面与招牌空白区并非逐像素相同，但没有像素出现大于 20 灰度级的明显单通道变化。

### 性能

| 阶段 | 耗时 |
| --- | ---: |
| 参考图 VAE 编码 | 5.56 秒 |
| 文字条件计算 | 4.53 秒 |
| 4 steps 采样 | 91.48 秒 |
| VAE 解码 | 7.68 秒 |
| 模型报告总生成 | 109.24 秒 |
| 实际墙钟时间 | 110.04 秒 |

- 最大常驻内存：8,277,032,960 字节，约 7.71 GiB
- 进程 swaps：0
- SHA-256：`71c61094def68289a139e202798c9a465b45c49c800eed6b23c1c0c5120d7d1a`

### 初步结论（待 Hera 人工确认）

精确英文短文字替换通过，而且背景保持比第一次改色更好。它已经具备修改简单招牌草稿的实用价值；若用于品牌正式成品，仍应检查字体一致性，并以原图背景配合蒙版合成，避免任何未指定区域漂移。

### Hera 人工复核结果

- 整体评价：挺好。
- 最终判定：精确文字替换通过，输出具备实际可用性。
- 保留限制：未编辑区域并非逐像素不变；严格品牌素材仍建议人工检查或蒙版合成。

---

## 03：复杂场景物体移除

### 实际应用意义

从照片中移除路人、杂物或多余产品时，模型不仅要识别正确对象，还要合理补出其遮挡的背景，并尽量不改变其他主体。本测试让 FLUX.2 删除自己在基线图中擅自生成的白猫。

### 输入与目标

- 输入图：`results/generated/phase-1-baseline/flux2-klein-4b-seed-260903.png`
- 输出图：`results/generated/phase-3-single-edit/03-remove-white-cat.png`
- seed：`260911`
- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- 参考图模式：`preset=flux2`
- Metal、diffusion flash attention、CPU offload：启用

Prompt：

```text
Edit the provided image. Remove only the small white or cream-colored cat sitting on the right side of the serving counter. Replace the area it occupied with a natural continuation of the wooden counter and the shop interior behind it. Keep the small blue ceramic cat on the left side of the counter exactly unchanged. Preserve every other existing element: the red bicycle, all five paper lanterns, the storefront, rainy street, reflections, lighting, shadows, camera angle, composition, and the exact current sign text AI LLAB. Do not correct or alter the sign. Do not add any new object, animal, person, text, logo, or decoration.
```

### 结果观察

- 白/米色猫被完全移除，没有残留肢体或动物轮廓。
- 原来被白猫遮挡的位置自然补成柜台和店内显示器，没有明显空洞或破碎边缘。
- 左侧蓝色陶瓷猫保留，位置和形态在视觉上高度接近原图。
- 红色自行车、五盏灯笼、店面结构、雨夜街道和构图均保留。
- 招牌仍是原来的错误拼写 `AI LLAB`；模型没有擅自修正，这是单点控制成功的重要证据。
- 未编辑区域仍有轻微色调、雨滴和纹理重绘，不能视为逐像素不变。

### 像素变化抽样

| 区域 | MAE | PSNR | 单像素最大通道差 > 20 |
| --- | ---: | ---: | ---: |
| 全图 | 5.926 | 29.18 dB | 3.55% |
| 被移除白猫区域 | 22.133 | 16.35 dB | 34.74% |
| 蓝色陶瓷猫区域 | 5.859 | 29.99 dB | 5.93% |
| 招牌区域 | 5.357 | 30.98 dB | 2.90% |
| 自行车区域 | 6.290 | 29.45 dB | 4.89% |
| 左侧街道 | 6.635 | 29.08 dB | 4.74% |

目标区域的平均变化约为其他主要区域的 3–4 倍，说明编辑重点正确。复杂雨景中的非目标区域仍整体经过生成式重绘，但视觉结构保持良好。

### 性能

| 阶段 | 耗时 |
| --- | ---: |
| 参考图 VAE 编码 | 5.48 秒 |
| 文字条件计算 | 3.97 秒 |
| 4 steps 采样 | 90.33 秒 |
| VAE 解码 | 7.66 秒 |
| 模型报告总生成 | 107.44 秒 |
| 实际墙钟时间 | 108.33 秒 |

- 最大常驻内存：7,564,640,256 字节，约 7.04 GiB
- 进程 swaps：0
- SHA-256：`514e22714c35d8362df0b677b7a1d904bafce56d74fd40586531c8ee596aa13c`

### 初步结论（待 Hera 人工确认）

复杂场景物体移除通过：目标识别正确、遮挡区域补全自然、其他显著元素和原有错误文字均被保留。它已经具备普通照片杂物移除的实用价值；需要严格保留原始证据或产品像素时，仍应使用蒙版合成。

### 请 Hera 人工复核

- 白猫原位置的柜台和显示器是否自然，有没有可疑涂抹或结构断裂？
- 蓝色陶瓷猫、自行车、灯笼和招牌是否保持得足够好？
- 整体雨景、色温和亮度变化是否肉眼明显？
- 最终评价：可直接用、需轻微后期，还是不合格？

### Hera 人工复核结果

- 整体评价：效果不错。
- 不把输入与输出并排比较时，看不出其他区域的变化。
- 最终判定：复杂场景物体移除通过，视觉保持达到普通照片修图的可用水平。
- 保留限制：像素并非原样保留，不适合未经蒙版合成就用于需要严格原始性的图片。
