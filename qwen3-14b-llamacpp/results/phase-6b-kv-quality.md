# Phase 6B：KV cache 长上下文质量 A/B

- 文档：110 条虚构巡检记录
- 上下文：16K
- 测试：5 个跨位置事实、1 个跨段加法、1 个未提及陷阱
- 模型权重：Qwen3-14B Q4_K_M
- 生成：greedy，seed 42，reasoning off，固定 JSON 字段
- 测试顺序：Q4_0 -> Q8_0 -> F16

## K=q4_0 / V=q4_0：7 / 7

```json
{
  "project_code": "苍鹭",
  "approver": "林澈",
  "temperature_limit_c": 37,
  "cargo_password": "松针-4821",
  "checksum": "K9-M2-731",
  "battery_total": 52,
  "roof_color": "未提及"
}
```

- 峰值常驻内存：9923608576 bytes
- 完整进程耗时：36.40 seconds

## K=q8_0 / V=q8_0：7 / 7

```json
{
  "project_code": "苍鹭",
  "approver": "林澈",
  "temperature_limit_c": 37,
  "cargo_password": "松针-4821",
  "checksum": "K9-M2-731",
  "battery_total": 52,
  "roof_color": "未提及"
}
```

- 峰值常驻内存：10604216320 bytes
- 完整进程耗时：36.14 seconds

## K=f16 / V=f16：7 / 7

```json
{
  "project_code": "苍鹭",
  "approver": "林澈",
  "temperature_limit_c": 37,
  "cargo_password": "松针-4821",
  "checksum": "K9-M2-731",
  "battery_total": 52,
  "roof_color": "未提及"
}
```

- 峰值常驻内存：11859542016 bytes
- 完整进程耗时：35.01 seconds

## 答案标准

- 项目代号：苍鹭
- 批准人：林澈
- 温度上限：37
- 货舱口令：松针-4821
- 校验码：K9-M2-731
- 电池总数：52
- 屋顶颜色：未提及
