# Phase 9: 本地 OCR + 多模态 API + 确定性校验

## 目标

验证一条更接近真实财务应用的票据处理链路：

1. Apple Vision 在本机提取文字、候选和二维坐标。
2. 常驻的 `llama-server` 同时读取原图与 OCR 证据，输出固定结构的 JSON。
3. 普通程序检查金额恒等式、已知真值、重复运行一致性和冲突。

测试只使用本机已有的 Qwen3-VL-8B Q4_K_M 与 Q8_0 projector，没有下载新模型，也没有修改 llama.cpp 源码。

## 测试材料

- 原图：`tests/fixtures/receipts/26-real-japanese-receipt-gyoza-ohsho.jpg`
- Apple Vision JSON：`results/apple-vision-receipt-ocr.json`
- 请求生成：`scripts/build_hybrid_receipt_request.py`
- 三次 API 与服务生命周期：`scripts/run_hybrid_receipt_server.sh`
- 结果校验：`scripts/validate_hybrid_receipt_responses.py`

## 性能

Apple Vision 原图文字识别耗时 `0.7241 s`。包含原图文字识别、文档识别、自动矫正、矫正图文字与文档识别的完整探针耗时 `2.87 s`；实际应用不必每次都运行全部五种探针。

最终一轮 API 测试：

| 阶段 | 耗时 |
| --- | ---: |
| `llama-server` 可用 | 4 s |
| 第一次请求（处理图片与 4655-token prompt） | 19.59 s |
| 第二次请求（命中 prompt cache） | 7.85 s |
| 第三次请求（命中 prompt cache） | 7.86 s |

第一次请求的 prompt 处理速度为 `395.55 tokens/s`，生成速度约 `42.00 tokens/s`。后两次复用了 4654 个 prompt token，只新增处理 1 个 token；主要耗时变成生成 328 个 token。

## 结构化输出测试

第一次尝试把 JSON Schema 放在了错误的字段层级。HTTP 请求仍返回 200，但约束实际为空，模型自行选择了 `price`、`sub_total` 等字段并添加 Markdown 代码围栏。这个对照保存在：

- `results/hybrid-receipt-unconstrained-response-1.json`
- `results/hybrid-receipt-unconstrained-response-2.json`
- `results/hybrid-receipt-unconstrained-response-3.json`

修正为 OpenAI 风格的 `response_format.type=json_schema` 与 `response_format.json_schema.schema` 后，服务器强制输出了完整且可解析的目标结构。结论是：HTTP 200 和“看起来像 JSON”都不能证明结构约束真的生效，客户端仍需解析并校验所有必填字段。

## 识别结果

最终三次响应逐字一致，每次通过 `24/27` 项严格检查。

稳定正确的内容：

- 传票号 `657`
- 桌号 `25`、人数 `2`
- 员工名 `大橋`
- 日期 `2026-06-21`、时间 `17:07`
- 三个菜品名称、数量和金额
- 小计 `2033`、外税 `0`、合计 `2033`
- 相机时间 `2026.06.21 17:30`
- 三项金额求和等于小计，小计加税等于合计

特别有价值的一点：Apple Vision 把票面日期高置信度误读为 `2086年6月21日`，而多模态模型结合原图和相机时间恢复为 `2026-06-21`，并在 `warnings` 中明确记录了冲突。

最终仍有三项严格失败：

- 商户被写成 `OH/HP FOOD SERVICE CO.`，没有可靠恢复票据上的日文品牌 `餃子の王将`，英文也不是准确抄录。
- 员工编号 `8` 被漏掉，尽管 Apple Vision 独立识别到了它。
- 第三行独立左列标记 `TP` 被漏掉，尽管 Apple Vision 保留了它与菜品行的独立坐标。

上一版提示词曾正确保留员工编号和 `TP`，却把前两行的数量 `1` 错填进 `row_marker`。调整字段说明后错误换了位置，并没有消失。两版都是三次完全一致的 `24/27`。这说明重复一致性只能证明输出稳定，不能证明事实正确；继续针对这一张票据调提示词会产生过拟合。

## 财务应用边界

这套组合适合“自动预填 + 标红复核”，不适合在无人确认下直接入账。

可以由普通程序自动确认：

- JSON 是否符合固定 schema。
- 菜品金额之和是否等于小计。
- 小计加税是否等于合计。
- 日期、金额和数量是否合法。
- 多次或多引擎结果是否存在冲突。

必须保留原图并进入复核的情况：

- OCR 与视觉模型在日期、金额、商户或行结构上冲突。
- 关键字段只有一个引擎读到。
- 商户无法通过本地商户字典或历史账目归一化。
- 任何金额恒等式失败。

相机时间只能作为冲突提示，不能未经确认就覆盖票面日期。模型输出的 `warnings` 也不能代替确定性校验。

## 结论

“Apple Vision 本地 OCR + 网络/本地多模态模型填表 + 普通程序验算 + 人工确认异常”是可行方向。它能显著减少手工录入，并且比只相信单个模型安全；但 8B 本地模型在商户 logo、独立小列和小字段上仍会稳定地犯错。本阶段不产生新的 llama.cpp upstream 问题，属于模型能力与应用层校验设计，而不是已证明的 llama.cpp 实现缺陷。

