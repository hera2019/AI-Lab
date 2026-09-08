# Phase 12: 自然照片、空间关系、遮挡与不确定性

## 测试目的

使用真实照片补充此前以文字、票据和合成图为主的测试，观察模型能否：

- 统计完整和被画面边缘截断的人
- 理解画面坐标中的左右关系与人物动作
- 对被不透明区域遮住的细节明确回答 `UNKNOWN`
- 区分同一图片中“仍然可见”和“已经不可见”的文字

## 图片来源与固定真值

两张原始照片来自 Ultralytics 的公开 assets 仓库：

- `tests/fixtures/natural/source-bus.jpg`
  - 来源：`https://raw.githubusercontent.com/ultralytics/assets/main/im/bus.jpg`
  - SHA-256：`c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63`
- `tests/fixtures/natural/source-zidane.jpg`
  - 来源：`https://raw.githubusercontent.com/ultralytics/assets/main/im/zidane.jpg`
  - SHA-256：`16d73869e3267a7d4ed00de8e860833bd1657c1b252e94c0c348277adc7b6edb`

项目脚本校验原图哈希后生成两个派生测试图：一个用不透明矩形完整遮住前景人物的领带区域，另一个遮住公交车前方路线显示屏。除此之外不改变原图像素。坐标和派生文件哈希记录在 `tests/fixtures/natural/manifest.json`。

这些照片仅作为本地模型测试材料；如以后复制到公开仓库或重新分发，应再次核对上游素材许可。

## 运行配置

- 模型：`Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M`
- llama.cpp commit：`0190529ec450659b541ff608449401e68c27d098`
- Apple Metal，context 8192
- 常驻 `llama-server` OpenAI-compatible API
- temperature 0，reasoning off
- 严格 JSON Schema，逐字段精确评分

运行：

```bash
scripts/generate_natural_scene_fixtures.sh
scripts/run_natural_scene_baseline.py
```

## 主用例结果

| ID | 内容 | 结果 | 单次耗时 | 关键结果 |
| --- | --- | --- | ---: | --- |
| NAT-001 | 公交街景计数 | PASS | 4.59 s | 4 人、2 人完整、2 人边缘截断、1 辆公交、无自行车 |
| NAT-002 | 人物动作与空间关系 | FAIL | 4.62 s | 人数、人物位置和指向右侧正确，但动作错误标成 `clapping` |
| NAT-003 | 领带完全遮挡 | PASS | 4.50 s | 判断领带不可见并返回 `UNKNOWN`，没有猜颜色 |
| NAT-004 | 路线牌遮挡 | PASS | 4.40 s | 路线牌返回 `UNKNOWN`，同时正确读取仍可见的 `EMT MADRID` |

主用例严格得分为 **3/4**。

## NAT-002 拆解诊断

未拆解的 NAT-002 独立运行两次，两次都产生同一个内部矛盾：

```json
{
  "people_count": 2,
  "foreground_action": "clapping",
  "pointing_direction": "image_right",
  "background_person_position": "image_right"
}
```

模型已经知道手指指向右侧，却仍选择“拍手”。随后改为先报告可见原子事实，再选择动作：

```json
{
  "right_arm_extended": true,
  "index_finger_points_right": true,
  "hands_touching": false,
  "action": "pointing"
}
```

诊断用例精确通过。这说明图片信息本身已经被模型看见，错误发生在直接压缩成动作标签时；把可见证据拆开询问能够纠正本例。

这与 Phase 11 的柱状图错误不同：柱状图即使先列出 `18` 和 `15`，仍把“是否下降”答错；本次动作题则能被证据分解修正。不能假设同一种 prompt 技巧会修复所有错误。

## 真值修正记录

首轮测试中，NAT-004 返回完整可见标识 `EMT MADRID`，最初标准答案只写了 `MADRID`。图片和问题要求的是城市品牌文字，模型答案更完整，因此在最终运行前将标准答案修正为 `EMT MADRID`。

这是评测标准错误，不是模型错误。保留这条记录是为了避免为了维持原标准而错误处罚正确答案。

## 结论

1. 自然照片中的人物计数、边缘截断和基本空间方向表现良好。
2. 两个遮挡案例都没有编造不可见信息，能把隐藏内容与仍可见证据分开。
3. 高层标签可能与模型自己的低层观察互相矛盾。可靠流程应保存人数、方向、接触状态等原子事实，再由规则或第二步生成动作标签。
4. 目前没有新的 llama.cpp/libmtmd issue：所有图片正常解码，Metal/API/JSON Schema 行为稳定，观察到的是模型答案质量问题。
5. 测试脚本最终返回非零状态，是因为 NAT-002 主用例精确评分失败，不代表服务器运行失败。

## 结果文件

- `results/natural-scene-latest.log`
- `results/natural-scene-server.log`
- `results/natural-scene-nat-001.json`
- `results/natural-scene-nat-002.json`
- `results/natural-scene-nat-002-diagnostic.json`
- `results/natural-scene-nat-003.json`
- `results/natural-scene-nat-004.json`
- `tests/fixtures/natural/manifest.json`
- `scripts/generate_natural_scene_fixtures.py`
- `scripts/generate_natural_scene_fixtures.sh`
- `scripts/run_natural_scene_baseline.py`
