# Phase 13: 提示词鲁棒性与答案漂移

## 测试目的

固定图片、模型、系统提示、JSON Schema、temperature 和标准答案，只改变用户问题的措辞，检查同一视觉事实是否会因为以下变化而改变答案：

- 简短中文
- 带明确定义的中文
- 英文
- 要求先检查可见证据再回答

选择此前已经出现错误的两张图片：

- Phase 11 的季度柱状图：四个数字正确，但曾把 `18→15` 判断为没有下降。
- Phase 12 的人物照片：指向方向正确，但曾把动作标成 `clapping`。

## 控制条件

- 模型：`Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M`
- llama.cpp commit：`0190529ec450659b541ff608449401e68c27d098`
- Apple Metal，context 8192
- temperature 0，reasoning off
- 同一任务的四种提示共用完全相同的图片与 JSON Schema
- 每轮使用全新 `llama-server`
- 正序独立运行两次，再使用全新服务器倒序运行一次

每种提示实际运行三次，总计 24 次请求。三轮结果模式完全一致。

脚本会覆写同名的正序结果文件，因此目录中保留最后一次正序和一次倒序的 16 份原始响应；第一次正序运行通过终端输出完成核对。所有用例都可用下列命令重新生成。

运行：

```bash
scripts/run_prompt_robustness.py
scripts/run_prompt_robustness.py --order reverse
```

## 结果矩阵

### 柱状图

标准答案为 `Q1=12`、`Q2=18`、`Q3=15`、`Q4=27`、`q2_to_q3_decreased=true`。

| 提示风格 | 三次结果 | 评分 |
| --- | --- | --- |
| 简短中文 | 三次完全一致，全部字段正确 | PASS |
| 中文明确定义 `Q3 < Q2` | 三次完全一致，全部字段正确 | PASS |
| 英文明确定义 | 三次完全一致，全部字段正确 | PASS |
| 中文证据优先 + 明确不等式 | 三次完全一致，全部字段正确 | PASS |

柱状图为 **4/4 提示通过**，四种提示只产生一种答案。

值得注意的是，Phase 11 中语义相近的提问曾稳定返回 `false`。因此本轮 4/4 不能推翻此前错误，而是进一步证明：看似细微的整体请求差异会改变模型答案。

### 人物动作

标准答案为 2 人、前景人物 `pointing`、方向 `image_right`。

| 提示风格 | 三次结果 | 评分 |
| --- | --- | --- |
| 简短中文 | `pointing` / `image_right` | PASS |
| 中文定义 pointing 与 clapping | `pointing` / `image_right` | PASS |
| 普通英文 | `pointing` / `image_right` | PASS |
| 中文“先在内部检查证据” | `clapping` / `image_right` | FAIL |

人物动作为 **3/4 提示通过**，四种提示产生两种互相冲突的动作标签。

失败提示连续三次都出现：

```json
{
  "people_count": 2,
  "foreground_action": "clapping",
  "pointing_direction": "image_right"
}
```

即使把该提示从最后一个移到全新服务器的第一个请求，仍得到同样结果，因此不是请求顺序或 prompt cache 污染。

## 与 Phase 11/12 的对照

- Phase 11 柱状图：要求先列数字再判断，仍错误。
- Phase 13 柱状图：简短、定义、英文和证据优先四种问法都正确。
- Phase 12 动作诊断：把手臂、食指、双手接触作为输出字段时，能够纠正为 `pointing`。
- Phase 13 动作测试：只要求模型“在内部检查”而不把证据作为输出字段时，反而稳定返回 `clapping`。

关键差异是：**要求模型在内部考虑证据，不等于让模型把证据显式输出并接受校验。** 后者在本例中更可靠。

## 怎么应用

1. 不能只凭一条“精心优化”的 prompt 判断模型可靠。应使用生产环境的完整 system prompt、user prompt、schema 和字段顺序做固定回归测试。
2. 对金额、趋势、动作等可推导字段，优先输出原子证据，再由普通程序计算或校验。
3. 如果必须让模型生成高层标签，应同时返回支撑字段，并拒绝内部自相矛盾的组合，例如 `clapping + hands_touching=false`。
4. temperature 0 让本次错误稳定复现，但不让错误自动消失；确定性不等于正确性。
5. 当前没有新的 llama.cpp/libmtmd issue。服务器重启、正序和倒序运行均稳定，差异来自模型对请求内容的响应。

测试脚本因 1 个提示变体精确评分失败而返回非零退出码，这不是服务器故障。

## 结果文件

- `results/prompt-robustness-latest.log`
- `results/prompt-robustness-latest-reverse.log`
- `results/prompt-robustness-server.log`
- `results/prompt-robustness-server-reverse.log`
- `results/prompt-robustness-pr-*.json`
- `scripts/run_prompt_robustness.py`
