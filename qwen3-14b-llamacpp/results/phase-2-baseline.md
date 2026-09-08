# Phase 2：Qwen3-14B Metal 基准

时间：2026-08-30 18:44 JST

## 测试对象

- 模型：Qwen3-14B Q4_K_M（14,768,307,200 parameters）
- 模型文件大小：8,995,793,920 bytes（GGUF 内记录）
- llama.cpp：`bebc9350e`，build 10700
- 后端：Metal + Apple Accelerate
- GPU：Apple M2 Max
- GPU layers：`-1`，即全部可卸载层
- Flash Attention：开启
- Threads：8
- Batch / micro-batch：2048 / 512
- KV cache：F16 / F16
- 每项重复：3 次（含工具自身的预热）

备注：此版本的 `llama-bench` 用 `-ngl -1` 表示全部 GPU 层；它不像 `llama-cli` 那样接受 `-ngl all`。

## 结果

| 测试 | 平均速度 | 标准差 |
| --- | ---: | ---: |
| 处理 512-token 提示词（pp512） | 262.251968 tokens/s | 0.534516 tokens/s |
| 生成 128 tokens（tg128） | 29.827901 tokens/s | 0.027795 tokens/s |

三轮结果非常稳定：提示词处理的相对波动约 0.20%，生成的相对波动约 0.09%。原始数据见 `results/benchmark.csv`。

## 内存与交换空间

| 时间点 | 系统可用内存压力余量 | 全局 swap |
| --- | ---: | ---: |
| 运行前 18:44:21 | 62% | 3192.75 MiB |
| 运行中 18:44:59 | 33% | 3192.75 MiB |
| 结束后 18:45:27 | 62% | 3192.75 MiB |

- `/usr/bin/time` 报告进程最大常驻内存 9,233,448,960 bytes（约 8.60 GiB）。
- 该进程自身报告 0 次 swap。
- 全局 swap 在三个采样点完全相同，因此本次基准没有观察到新增 swap。
- 系统磁盘测试前后均剩余约 43 GiB。

## 结论

Qwen3-14B Q4_K_M 在 Apple M2 Max / 32 GB Unified Memory 上可稳定全量 Metal 推理。约 29.8 tokens/s 的生成速度足以进行流畅单人对话；内存也有明显余量。

本阶段没有下载新模型、没有运行 slow tests、没有修改任何现有贡献分支，也没有提交或推送 Git 变更。

## 复现

在项目目录运行：

```bash
scripts/run_benchmark.sh
```

默认输出终端表格，并把详细启动与内存日志写入 `results/benchmark-latest.log`。如需 CSV：

```bash
scripts/run_benchmark.sh csv
```
