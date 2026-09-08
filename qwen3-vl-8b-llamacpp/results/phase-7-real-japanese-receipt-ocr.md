# Phase 7：真实日文票据 OCR

执行日期：2026-09-01

本轮使用一张真实手机拍摄的日本餐厅票据，而不是排版干净的合成图。图片包含透视、背景、票据夹遮挡和票据外的相机时间戳。

## 素材

- 文件：`tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg`
- 尺寸：750x1000
- 来源：Wikimedia Commons
- 作者：TKdows 2026
- 许可：CC0 1.0
- SHA-256：`a0f413e83d1c99a6c787a88dccf7d86da41e0a1148e389056b5dd288f1dc2d05`
- 来源与许可记录：`tests/fixtures/receipts/README.md`

## 运行

- 脚本：`scripts/run_real_japanese_receipt_ocr.sh`
- 原始日志：`results/japanese-receipt-ocr-latest.log`
- 模型、projector、Metal 配置和 llama.cpp commit 沿用 `results/system-info.txt`
- reasoning：off
- temperature：0
- 上下文：4096
- 执行方式：独立 `llama-cli` 进程，包含模型加载时间

## 模型原始输出

```text
OH/HP
FOOD SERVICE CO.,LTD
王将
伝票NO= 657
テーブルNo= 25
人数= 2
担当= 8 大橋
宅配事業者
注文コード
数 メニュー 金額
1 中華そば 748
1 特選セットA 1,120
TP 1 特セット餃子+3個 165
小計 2,033
外税 0
合計 2,033
**
新規 **
2026年06月21日
17:07
657
```

## 准确性

严格关键业务字段评分：16/17。

正确字段：

- 传票号 657、桌号 25、人数 2、担当编号 8、担当姓名大桥。
- 日期 2026-06-21、时间 17:07。
- `中华そば` 748 日元。
- `特选セットA` 1,120 日元。
- `特セット饺子+3个` 165 日元。
- 小计 2,033、外税 0、合计 2,033。
- 按要求没有把票据外的相机时间戳 `2026.06.21 17:30` 转录进票据内容。

严格失败字段：

- 商户店标 `餃子の王将` 只识别出 `王将`，英文风格化 logo 也被误读为 `OH/HP`。

其他全文 OCR 偏差包括很小的英文公司名与个别标签。因此 16/17 是实用字段分数，不是逐字符准确率。

## 性能

- 端到端实时间：11.21 秒。
- 图片/提示处理：259.3 token/s。
- 生成：49.7 token/s。
- 最大常驻集：6,828,457,984 字节，约 6.36 GiB。
- swap：0。
- 退出码：0。

11.21 秒包含独立 CLI 进程每次重新加载模型。实际 App 通常让 `llama-server` 常驻，因此后续 API 测试应分开记录首次启动和已加载模型后的单次 OCR 延迟。

## 结论

- 这个 8B Q4_K_M 模型对真实日文票据的核心商品和金额字段很强。
- 主要弱点是风格化 logo、极小英文和全文逐字符保真。
- 本次 Mac 进程的最大常驻集约 6.36 GiB，已超过 6 GB 整机 RAM。考虑 iOS 和 App 自身占用，该 8B 配置不适合直接部署到 iPhone 13 Pro。
- 手机端实验应优先考虑 Qwen3-VL-2B Q4_K_M，或先让 iPhone 作为拍摄与交互端、Mac Studio 作为本地推理服务器。
