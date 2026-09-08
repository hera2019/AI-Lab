# Phase 6：KV cache 精度对比

开始时间：2026-08-30 21:39:22 JST

- 提示词长度：16384 tokens
- 继续生成：128 tokens
- 每档重复：1 次
- 测试顺序：Q4_0 -> Q8_0 -> F16
- 模型权重：Qwen3-14B Q4_K_M（所有测试相同）
- 测试前全局 swap：total = 8192.00M  used = 6481.38M  free = 1710.62M  (encrypted)
- 测试前系统可用内存压力余量：68%

## K=q4_0 / V=q4_0

| model                          |       size |     params | backend    | threads | type_k | type_v |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | -----: | -----: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   q4_0 |   q4_0 |   1 |   pp16384+tg128 |        182.38 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：9885089792 bytes
- 完整进程耗时：178.28 seconds
- 完成后全局 swap：total = 8192.00M  used = 6473.38M  free = 1718.62M  (encrypted)
- 完成后系统可用内存压力余量：45%
- 详细日志：`results/kv-q4_0-q4_0-latest.log`

## K=q8_0 / V=q8_0

| model                          |       size |     params | backend    | threads | type_k | type_v |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | -----: | -----: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   q8_0 |   q8_0 |   1 |   pp16384+tg128 |        183.08 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：10613571584 bytes
- 完整进程耗时：173.61 seconds
- 完成后全局 swap：total = 8192.00M  used = 6457.38M  free = 1734.62M  (encrypted)
- 完成后系统可用内存压力余量：42%
- 详细日志：`results/kv-q8_0-q8_0-latest.log`

## K=f16 / V=f16

| model                          |       size |     params | backend    | threads |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   1 |   pp16384+tg128 |        181.25 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：11874549760 bytes
- 完整进程耗时：175.68 seconds
- 完成后全局 swap：total = 7168.00M  used = 6186.06M  free = 981.94M  (encrypted)
- 完成后系统可用内存压力余量：49%
- 详细日志：`results/kv-f16-f16-latest.log`

## 测试边界

该 benchmark 只比较速度和内存，不评估回答质量。KV cache 量化程度越高，潜在质量损失风险越大，是否适合日常使用还需要单独做同题 A/B 测试。

原始数据：`results/kv-cache-benchmark.csv`
