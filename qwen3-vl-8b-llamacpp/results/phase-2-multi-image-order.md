# Phase 2：多图顺序基线

执行日期：2026-08-31

模型与运行环境沿用 `results/system-info.txt`。每轮一次性传入三张图片，关闭 reasoning，温度为 0，上下文为 8192，使用 Metal。

## A → B → C

原始输出：

```text
IMAGE A, red, circle, ALPHA-17
IMAGE B, blue, square, BETA-29
IMAGE C, green, triangle, GAMMA-43
```

速度：图片/提示处理 261.5 token/s，生成 49.8 token/s。

判定：PASS。三张图片、输入顺序、颜色、形状与代码全部正确。

## C → A → B：普通顺序提示

原始输出：

```text
IMAGE A, red, circle, ALPHA-17
IMAGE B, blue, square, BETA-29
IMAGE C, green, triangle, GAMMA-43
```

速度：图片/提示处理 267.6 token/s，生成 51.2 token/s。

判定：FAIL。三张内容都识别正确，但模型无视输入顺序，按字母重排成 A → B → C。

## A → A → C：重复图片

原始输出：

```text
IMAGE A
红色
圆形
ALPHA-17
IMAGE A
红色
圆形
ALPHA-17
IMAGE C
绿色
三角形
GAMMA-43
```

速度：图片/提示处理 262.2 token/s，生成 51.8 token/s。

判定：内容与顺序 PASS，格式约束 FAIL。模型没有忽略或去重第二张 A，但没有遵守“每张一行”。

## C → A → B：强制位置编号复核

提示明确要求把输入图片编号为 1、2、3，并禁止按字母排序。

原始输出：

```text
1: C, 绿色, 三角形, IMAGE GAMMA-43
2: A, 红色, 圆形, IMAGE ALPHA-17
3: B, 蓝色, 正方形, IMAGE BETA-29
```

速度：图片/提示处理 270.8 token/s，生成 46.5 token/s。

判定：位置顺序 PASS。模型在更强约束下正确输出 C → A → B，证明图片位置没有在 llama.cpp/libmtmd 传输阶段丢失。代码字段多带了 `IMAGE` 前缀，属于格式遵循的小误差。

## 结论

- 三张图片都能被加载并理解，重复图片也不会被底层自动去重。
- 普通“按输入顺序”提示不够可靠，模型可能依据图片标签自行整理。
- 需要可靠位置关系时，应明确使用“图片 1 / 图片 2 / 图片 3”，并写明禁止重排。
- 目前没有证据表明 libmtmd 改变了图片顺序，不构成 upstream issue。
