# Gemini 网络模型票据 A/B 测试

## 目的

用同一张真实日文票据、同一份 Apple Vision OCR 证据和同一套 JSON Schema，对比：

- 本地 `Qwen3-VL-8B Q4_K_M`
- 网络 `Gemini 3.7 Flash`

这不是让网络模型参考本地 Qwen 的答案。两者分别处理原图和 OCR 证据，最后由同一个普通程序按相同真值和账目规则评分。

## 当前状态

请求构建和离线干跑已经通过：

```text
model=gemini-3.7-flash
thinking_level=low
request_bytes=89122
runs=1
max_attempts=1
dry_run=yes
network_request_sent=no
```

初次搭建时终端没有设置 `GEMINI_API_KEY`，因此离线干跑没有产生网络请求或费用。后续实际请求仍通过 Terminal 隐藏输入 key，项目没有保存密钥。

后续实际测试中，`gemini-3.7-flash` 因持续高负载四次返回 HTTP 500；切换为同样支持图片和结构化输出的稳定模型 `gemini-3.6-flash` 后成功。完整对比见 `results/phase-10-gemini-receipt-ab.md`。

## 为什么使用 Interactions API

Google 从 2026 年 6 月起把 Interactions API 作为新项目的默认接口；它可以直接接收 base64 图片，并通过 `response_format` 强制 JSON Schema。这里没有使用已被列为 legacy 的 `generateContent` 新建实现。

- Gemini API：https://ai.google.dev/gemini-api/docs
- 图片输入：https://ai.google.dev/gemini-api/docs/image-understanding
- 结构化输出：https://ai.google.dev/gemini-api/docs/structured-output

默认模型为 `gemini-3.7-flash`，思考等级为 `low`，两者都可以通过参数修改。没有使用已不适用于该模型的 `temperature`、`top_p` 或 `top_k`。

## 安全运行

推荐直接在 Terminal 运行：

```bash
cd ~/Documents/AI-Lab/qwen3-vl-8b-llamacpp
scripts/run_gemini_receipt_ab.sh --runs 1
```

如果没有环境变量，程序会显示：

```text
Gemini API key (hidden, not saved):
```

在这里输入 key。输入内容不会回显，也不会写入项目、请求文件或日志。

确认第一次请求正常后，再测试三次一致性：

```bash
scripts/run_gemini_receipt_ab.sh --runs 3
```

如果返回 `429` 或 `500/502/503/504` 等临时容量错误，可以明确允许最多三次尝试。等待时间依次为 5 秒、10 秒：

```bash
scripts/run_gemini_receipt_ab.sh --runs 1 --max-attempts 3
```

脚本只会重试这些临时状态码；认证失败、请求错误或其他非临时错误会立即停止。也可以用 `--model` 对比另一个账户可用的 Gemini 模型，但不同模型的结果应单独记录，不能混进同一组一致性测试。

也可以只在当前 shell 临时设置：

```bash
export GEMINI_API_KEY='你的 key'
scripts/run_gemini_receipt_ab.sh --runs 1
unset GEMINI_API_KEY
```

不要把 key 写进脚本、README、Git、截图或 issue。

## 网络与费用边界

本测试会把票据原图和 Apple Vision OCR 结果发送给 Google。当前测试图为公开的 CC0 图片，不包含用户隐私。将来换成真实个人票据之前，需要重新考虑隐私、保存策略、供应商条款和财务数据处理要求。

截至 2026-09-01，Google 官方页面列出的 Gemini 3.7 Flash 标准付费价格为每百万输入 token 0.75 美元、每百万输出/思考 token 3.75 美元（优惠价格有效至 2026-12-31）；免费层是否可用由账户和地区决定。测试默认只运行一次，避免无意重复计费。

- 官方价格：https://ai.google.dev/gemini-api/docs/pricing

## 输出

成功运行后会生成：

- `results/gemini-receipt-raw-1.json`：Google 原始响应
- `results/gemini-receipt-response-1.json`：转换为本项目统一格式的响应
- `results/gemini-receipt-api-latest.log`：耗时、严格检查和失败字段
- `results/phase-10-gemini-receipt-ab.md`：本地 Qwen、Apple Vision 与 Gemini 的最终 A/B 结论

运行三次时编号扩展为 `1`、`2`、`3`。密钥不会出现在这些文件中。

## 判定原则

网络模型即使达到 27/27，也不能单独证明可以无人确认入账。最终仍检查：

- JSON Schema 是否真的生效。
- 菜品金额之和、小计、税额与合计是否一致。
- 本地 OCR、网络模型和原图之间是否冲突。
- 商户、日期、金额等关键字段是否需要人工确认。
- 三次一致是否只是稳定地犯同一个错误。
