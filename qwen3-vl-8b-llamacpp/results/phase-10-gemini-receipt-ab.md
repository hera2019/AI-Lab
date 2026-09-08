# Phase 10: 本地 Qwen 与 Gemini 票据 A/B

## 测试目的

使用完全相同的材料比较本地与网络多模态模型：

- 同一张公开日文餐厅票据图片
- 同一份 Apple Vision OCR 文字、候选与坐标
- 同一套结构化字段与财务校验规则
- 同一套已知真值

网络请求使用 Google Gemini Interactions API。API key 只在 Terminal 隐藏输入，没有写入脚本、项目或结果文件。

## 服务可用性

`gemini-3.7-flash` 共尝试四次，均返回 HTTP 500：

```text
gemini-3.7-flash is currently experiencing high demand
```

这不是认证、图片或 JSON Schema 错误，而是模型容量错误。脚本随后加入了仅针对 `429/500/502/503/504` 的有限指数退避；不会重试认证和请求格式错误。

切换到稳定的上一代完整 Flash 模型 `gemini-3.6-flash` 后，第一次请求成功。

## Gemini 3.6 Flash 结果

```text
wall_seconds=5.469642
attempts=1
input_tokens=4994
image_input_tokens=1064
text_input_tokens=3930
output_tokens=301
thought_tokens=0
total_tokens=5295
```

结构化输出完整恢复：

- 商户：`餃子の王将`
- 传票号：`657`
- 桌号：`25`
- 人数：`2`
- 员工编号与姓名：`8`、`大橋`
- 日期与时间：`2026-06-21`、`17:07`
- 三个菜品、数量、金额和独立列 `TP`
- 小计 `2033`、外税 `0`、合计 `2033`
- 相机时间 `2026-06-21 17:30`

原始字符严格比较为 `26/27`，唯一差异是标准答案 `+3` 与输出 `＋３` 的全角/半角形式。使用 Unicode NFKC 归一化后，两者都是 `+3`，财务语义检查为 `27/27`。原始响应仍保留全角字符，没有被覆盖。

## A/B 对比

| 路径 | 业务字段 | 耗时 | 主要问题 |
| --- | ---: | ---: | --- |
| Apple Vision 原图 OCR | 不直接填表 | 0.72 s | 日期高置信度错成 2086，商户与员工名较弱 |
| 本地 Qwen3-VL-8B，首次混合请求 | 24/27 | 19.59 s | 商户、员工编号、`TP` 失败 |
| 本地 Qwen3-VL-8B，prompt cache 后 | 24/27 | 约 7.85 s | 与首次相同，稳定但不等于正确 |
| Gemini 3.6 Flash | 27/27（NFKC） | 5.47 s | 没有主动报告 OCR 日期冲突 |

云端和本地耗时不是完全相同的指标：本地第一次包含完整图片和 prompt 计算，后续可以复用缓存；Gemini 的 5.47 秒包含网络往返，但服务端模型已经常驻。

## 确定性复核

Apple Vision 的纸面日期候选为：

```text
2086-06-21
```

Gemini 输出为：

```text
2026-06-21
```

Gemini 的字段值是正确的，但 `warnings=[]`。更新后的普通校验程序不依赖模型自觉报告，独立输出：

```text
ocr_date_conflict=yes
model_warning_for_ocr_date_conflict=no
deterministic_review_required=yes
```

作为对照，本地 Qwen 的字段准确率较低，却主动在 `warnings` 中说明了 `2086` 与 `2026` 的冲突。因此两个模型的优势不同：Gemini 本次抄表更准，Qwen 本次风险说明更谨慎。无论使用哪一个，确定性规则都不能省略。

## 费用估算

按 2026-09-01 Google 官方列出的 Gemini 3.6/3.7 Flash 优惠标准价格估算：输入每百万 token 0.75 美元，输出与思考每百万 token 3.75 美元。

本次成功请求若按付费层计价，约为：

```text
4994 × $0.75 / 1,000,000 + 301 × $3.75 / 1,000,000
= $0.00487425
```

即约半美分。免费层可能不收费，实际账单以账户控制台为准。失败的 HTTP 500 请求是否计入用量，应以 Google 账单记录为准，项目不自行假定。

- 官方价格：https://ai.google.dev/gemini-api/docs/pricing

## 实际产品建议

推荐的票据流程已经得到验证：

1. Apple Vision 在设备上快速 OCR，保存原始候选和坐标。
2. Gemini 等网络视觉模型读取原图和 OCR，填充固定 JSON。
3. 普通程序做金额恒等式、Unicode 归一化、日期冲突和必填字段检查。
4. 只把冲突或缺失字段交给用户确认。
5. 保存原图、原始 OCR、模型原始响应和最终人工确认值，便于审计。

还必须准备供应商故障策略：有限重试、备用模型、明确超时和人工录入。`gemini-3.7-flash` 的持续容量错误证明，网络模型准确率再高也不能被当成永远可用的单点服务。

## 结果文件

- `results/gemini-receipt-raw-1.json`
- `results/gemini-receipt-response-1.json`
- `results/gemini-receipt-api-latest.log`
- `scripts/run_gemini_receipt_ab.py`
- `scripts/run_gemini_receipt_ab.sh`
- `scripts/validate_hybrid_receipt_responses.py`

