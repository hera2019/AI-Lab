# Phase 6：KV cache 精度对比结论

状态：性能与内存测试已完成；后续 Phase 6B 质量测试也已完成，三档均为 7/7。

## 16K + 128-token 结果

| KV cache | 综合速度 | 峰值内存 | 相对 F16 节省 |
| --- | ---: | ---: | ---: |
| F16 / F16 | 181.25 tokens/s | 11.06 GiB | - |
| Q8_0 / Q8_0 | 183.08 tokens/s | 9.88 GiB | 1.17 GiB（约 10.6%） |
| Q4_0 / Q4_0 | 182.38 tokens/s | 9.21 GiB | 1.85 GiB（约 16.8%） |

三档速度差距约 1%，在单次扫描中可视为同一水平。KV cache 量化明显节省内存，没有观察到明显速度惩罚。

## Swap

- 测试前：6481.38 MiB used
- Q4_0 后：6473.38 MiB used
- Q8_0 后：6457.38 MiB used
- F16 后：6186.06 MiB used
- 三个 benchmark 进程都报告 0 swaps

全局 swap 没有因本轮测试增加，反而由 macOS 在后台自然回收约 295 MiB。测试前已有较高 swap，主要是此前长 reasoning 等负载留下的历史状态，因此不能把存量 swap 归因于本轮 KV cache 测试。

## 当前建议

- 8K 或 16K 日常聊天：推荐 Q8_0。本次质量测试与 F16 相同，并能留出更多内存。
- Q4_0：需要给更长上下文或其他应用腾出更多内存时使用；本次质量测试同样为 7/7。
- F16：作为最高精度基准保留；本次没有观察到回答质量优势。

## 边界

`llama-bench` 使用合成 token，只测吞吐量与内存，不判断答案是否正确。后续质量 A/B 已记录在 `results/phase-6b-analysis.md`；这仍只是一份固定测试，不能代表所有任务都完全无损。

自动生成的逐档记录见 `results/phase-6-kv-cache.md`，原始数据见 `results/kv-cache-benchmark.csv`。
