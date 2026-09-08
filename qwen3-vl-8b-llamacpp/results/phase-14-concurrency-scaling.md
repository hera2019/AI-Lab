# Phase 14: llama-server 多模态并发与内存

## 测试目的

在 Mac Studio M2 Max、32 GB Unified Memory 上，测试同一个本地 `llama-server` 同时处理 1、2、4 个图片请求时的：

- 请求是否全部成功
- 请求编号和答案是否串线
- 批次耗时、单请求平均延迟和整体吞吐量
- 服务器进程 RSS 与 swap 变化

## 安全检查

运行前 macOS 已经使用约 9994.56 MB swap。该数值是测试前的系统基线，不是本脚本产生。

```text
physical_memory=32 GiB
memory_free_percentage_before=63%
swap_used_before=9994.56 MB
throttled_pages=0
```

虽然 swap 历史使用量较高，但当时系统内存压力仍有 63% 可用且没有 throttling，因此采用短输出并按 1→2→4 逐级执行。每一级结束后关闭服务器并再次检查 swap。

## 控制条件

- 模型：`Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M`
- llama.cpp commit：`0190529ec450659b541ff608449401e68c27d098`
- Apple Metal，Flash Attention on
- `llama-server -np 4 -c 16384`，即最多 4 个 slot、每 slot 约 4096 context
- 每个并发级别使用全新服务器；服务器加载时间不计入请求批次时间
- 每个请求使用同一张 Dashboard 图片，但携带唯一 request ID
- 每个请求精确读取 `Deployments=12`、`Healthy=9`、`Failed=1`
- 严格 JSON Schema，temperature 0，reasoning off，最多生成 64 token

运行：

```bash
scripts/run_concurrency_scaling.py
```

## 结果

| 并发数 | 正确请求 | 批次耗时 | 平均单请求延迟 | 吞吐量 | 峰值 RSS | 请求期间 RSS 增长 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1/1 | 4.549 s | 4.548 s | 0.220 req/s | 8369.75 MiB | 420.94 MiB |
| 2 | 2/2 | 8.733 s | 8.719 s | 0.229 req/s | 8551.41 MiB | 517.56 MiB |
| 4 | 4/4 | 16.820 s | 16.786 s | 0.238 req/s | 8605.72 MiB | 566.11 MiB |

总计 7/7 请求全部成功，request ID 与 Dashboard 数字全部正确，没有串答案、HTTP 错误、崩溃或超时。

并发 4 相比并发 1：

- 整体吞吐量从 0.220 增至 0.238 req/s，只提高约 8.2%。
- 平均单请求延迟从 4.55 秒增至 16.79 秒，约为 3.69 倍。
- 峰值 RSS 只增加约 236 MiB。
- swap 在每一级测试前后都保持 9994.56 MB，没有新增 swap。

测试结束后系统报告 57% 内存可用，服务器进程已退出。

## 怎么理解

1. **稳定性良好。** 4 个多模态请求能够同时进入服务器并全部得到正确、独立的响应。
2. **吞吐扩展很有限。** M2 Max 上这项视觉工作主要共享同一套 GPU/内存带宽资源；增加 slot 更像排队和交错执行，不会接近四倍加速。
3. **并发会显著增加等待时间。** 如果目标是个人交互体验，限制为 1 个活跃生成请求通常更舒服；后台批处理可以使用 2–4 slot，但不应期待线性加速。
4. **额外内存成本较温和。** 本测试的进程 RSS 从约 8.37 GiB 增至 8.61 GiB。RSS 不是整个 macOS 统一内存和 Metal 工作集的完美度量，适合用于本机相对比较，不应当成绝对显存数字。
5. **高 swap 是前置系统状态。** 本轮没有导致 swap 增长。如果以后在黄色/红色内存压力下运行，应先关闭占内存应用，而不是只看 swap 历史数值。

当前没有新的 llama.cpp issue：四路调度、请求隔离、Metal 推理和 JSON Schema 均正常。

## 结果文件

- `results/concurrency-scaling-summary.json`
- `results/concurrency-c1-server.log`
- `results/concurrency-c2-server.log`
- `results/concurrency-c4-server.log`
- `results/concurrency-c*-raw.json`
- `scripts/run_concurrency_scaling.py`
