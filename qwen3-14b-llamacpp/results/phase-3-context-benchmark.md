# Phase 3：长上下文安全扫描

开始时间：2026-08-30 19:14:32 JST

- 提示词长度：4096 8192 16384 tokens
- 每档继续生成：128 tokens
- 每档重复：1 次
- Metal：全部模型层，Flash Attention 开启
- 测试前全局 swap：total = 4096.00M  used = 3184.75M  free = 911.25M  (encrypted)
- 测试前系统可用内存压力余量：62%

## 4096-token prompt + 128-token generation

| model                          |       size |     params | backend    | threads |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   1 |    pp4096+tg128 |        198.47 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：9304129536 bytes
- 完成后全局 swap：total = 4096.00M  used = 3184.75M  free = 911.25M  (encrypted)
- 详细日志：`results/context-4096-latest.log`

## 8192-token prompt + 128-token generation

| model                          |       size |     params | backend    | threads |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   1 |    pp8192+tg128 |        199.27 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：10531487744 bytes
- 完成后全局 swap：total = 4096.00M  used = 3184.75M  free = 911.25M  (encrypted)
- 详细日志：`results/context-8192-latest.log`

## 16384-token prompt + 128-token generation

| model                          |       size |     params | backend    | threads |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --: | --------------: | -------------------: |
| qwen3 14B Q4_K - Medium        |   8.38 GiB |    14.77 B | MTL,BLAS   |       8 |   1 |   pp16384+tg128 |        183.88 ± 0.00 |

build: bebc9350e (10700)

- 进程最大常驻内存：11830886400 bytes
- 完成后全局 swap：total = 4096.00M  used = 3678.38M  free = 417.62M  (encrypted)
- 详细日志：`results/context-16384-latest.log`

## 测试结束

- 测试后全局 swap：total = 4096.00M  used = 3678.38M  free = 417.62M  (encrypted)
- 测试后系统可用内存压力余量：32%
- 原始数据：`results/context-benchmark.csv`
