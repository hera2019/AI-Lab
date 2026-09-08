# Phase 2：提示遵循拆分测试

日期：2026-09-03

## 实际应用意义

把数量、颜色、空间位置和短文字分别测试，可以判断模型究竟在哪类要求上可靠。真实设计中，商品数量、品牌色、物体布局或招牌文字只要有一项错误，图片即使漂亮也不能直接交付。

## 固定参数

- 输出：1024 × 1024 RGB PNG
- steps：4
- sampler：Euler
- CFG：1.0
- Metal、diffusion flash attention：启用
- CPU offload：启用
- 四次运行 swaps：均为 0
- 生成脚本：`scripts/run_instruction_isolation.sh`
- 原图、prompt 和日志：`results/generated/phase-2-instruction-isolation/`

## 01：数量

- seed：`260905`
- prompt：

```text
A clean studio product photograph on a plain light gray background. Exactly three red apples, no more and no fewer, arranged in one straight horizontal row. No other objects, no text.
```

初步观察：正确生成三个红苹果，排列成一条横线，没有其他物体或文字。右侧苹果顶部看起来有两根果梗，是局部结构瑕疵，但不构成第四个苹果。

## 02：颜色

- seed：`260906`
- prompt：

```text
A clean studio product photograph of exactly three identical ceramic mugs in a straight horizontal row on a plain white background. The mugs are three different solid colors: red, green, and blue. No patterns, no text, no other objects.
```

初步观察：正确生成三个杯子，顺序为红、绿、蓝，横向排列，没有图案、文字或其他物体。杯体造型接近一致，但把手朝向不同，若将“identical”理解为连朝向都一致，则只能算部分满足。

## 03：空间位置

- seed：`260907`
- prompt：

```text
A clean tabletop photograph with only two objects: a red wooden cube on the far left and a blue glass sphere on the far right, with a large empty gap between them. The cube must not be on the right. The sphere must not be on the left. Plain beige background, no text.
```

初步观察：红色木方块在左、蓝色玻璃球在右，中间有明显空隙；只有两个物体且没有文字。核心空间关系完全满足。

## 04：精确短文字

- seed：`260908`
- prompt：

```text
A front-facing photograph of a single rectangular white sign on a plain dark wall. The sign contains only the exact uppercase text LOCAL AI in large black sans-serif letters, centered, perfectly spelled. No other words, logos, symbols, or decorations.
```

初步观察：正确生成大写 `LOCAL AI`，拼写、空格和字母数量均正确，没有额外文字或符号。相较第一张基线把 `AI LAB` 错写成 `AI LLAB`，说明模型不是完全不会写字，而是复杂场景中的文字可靠性更低。

## 性能

| 测试 | 文字条件 | 4 steps 采样 | VAE 解码 | 模型报告总生成 | 墙钟时间 | 最大常驻内存 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 数量 | 3.12 秒 | 45.56 秒 | 8.23 秒 | 56.96 秒 | 57.64 秒 | 8,653,848,576 字节 |
| 02 颜色 | 2.78 秒 | 45.88 秒 | 7.77 秒 | 56.47 秒 | 56.88 秒 | 8,662,646,784 字节 |
| 03 位置 | 2.78 秒 | 45.59 秒 | 8.70 秒 | 57.11 秒 | 57.95 秒 | 8,668,676,096 字节 |
| 04 文字 | 2.85 秒 | 45.83 秒 | 8.77 秒 | 57.50 秒 | 58.33 秒 | 8,664,465,408 字节 |

四次结果非常稳定：墙钟时间相差不到 1.5 秒，内存约 8.1 GiB，未发生 swap。

## 文件哈希（SHA-256）

```text
9c7d02e7262a1c6f1c0fa12ddf10f0831c2af0511223dac47a6128205bc06c2c  01-quantity.png
c6a116284f61789a086862549e7718c5066d8362896e6688781d4ddd660e89db  02-color.png
fdb7d7eb54b7109866a69a6d3f722a673a70e862628f3a8434dd0177cfe6b7ac  03-position.png
7ec33ecfe336899233ae84a4ec033ec9c54a22637008d9c2c042b1403c1fc98d  04-text.png
```

## 请 Hera 人工复核

- 01：是否恰好三个苹果、一条横线、没有其他物体或文字？右侧的双果梗是否影响可用性？
- 02：是否恰好三个杯子、红绿蓝、排成一行？把手方向不同是否应判定“identical”失败？
- 03：是否是红方块最左、蓝玻璃球最右、中间明显留空，而且仅有两个物体？
- 04：是否精确写成大写 `LOCAL AI`，没有错拼或多余符号？

## 阶段结论（待人工确认）

在这些低复杂度、单目标测试里，FLUX.2 klein 4B 的数量、基本颜色、左右布局和英文短文字都表现良好。但第一张基线的文字错误和本次局部结构瑕疵说明，一张成功样本不能证明长期可靠；实际交付仍需要人工检查，后续复杂度测试应逐步增加，而不是把单物体测试的成绩直接外推到海报或复杂商品场景。
