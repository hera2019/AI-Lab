# Phase 2：真实 AI-Lab 文档检索评测

- 索引文件：70 个
- 索引段落：497 个
- 查询：8 个（中文、日文、英文）
- 查询向量计算：0.888 秒
- 正确项目 Recall@1：8/8
- 正确项目 Recall@3：8/8
- 首选原始报告 Recall@3：5/8

“正确项目”用于判断是否找到正确实验；“首选原始报告”要求命中记录该事实的详细报告。
相似度是同一问题下的相对排序信号，不是正确概率。

## P2-Q01（zh）

问题：为什么猫眨眼的测试最后只能算部分成功？

正确项目排名：1；首选报告排名：1

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.7271 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-fastwan.md:105` ✅ | Phase 5：FastWan 3-step 加速测试 > 画质观察 > 65 帧眨眼单项 I2V |
| 2 | 0.5864 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:59` | Phase 4：尺寸、画幅与错误处理 > 画面观察 > 1024 × 768 横图 |
| 3 | 0.5811 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:53` | Phase 4：尺寸、画幅与错误处理 > 画面观察 > 768 × 768 |
| 4 | 0.5611 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:45` | Phase 4：尺寸、画幅与错误处理 > 画面观察 > 512 × 512 |
| 5 | 0.5433 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/PROJECT-SUMMARY.md:104` | Wan2.2 TI2V 5B 本地视频实验总结 > 质量观察 > 正常的 33 帧 I2V |

## P2-Q02（ja）

问题：レシートの TP は商品名の一部ですか、それとも別の列ですか。

正确项目排名：1；首选报告排名：5

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.5518 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-7-real-japanese-receipt-ocr.md:29` | Phase 7：真实日文票据 OCR > 模型原始输出 |
| 2 | 0.4744 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-7-real-japanese-receipt-ocr.md:55` | Phase 7：真实日文票据 OCR > 准确性 |
| 3 | 0.4626 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-10-gemini-receipt-ab.md:28` | Phase 10: 本地 Qwen 与 Gemini 票据 A/B > Gemini 3.6 Flash 结果 |
| 4 | 0.4496 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-9-hybrid-receipt-api.md:48` | Phase 9: 本地 OCR + 多模态 API + 确定性校验 > 识别结果 |
| 5 | 0.4403 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-8-apple-vision-hybrid-ocr.md:41` ✅ | Phase 8：Apple Vision 本地 OCR 与混合票据方案 > 表格结构 |

## P2-Q03（en）

问题：What caused the green mug to become almost as large as the bicycle basket?

正确项目排名：1；首选报告排名：1

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.5640 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-3-assisted-compositing.md:152` ✅ | Phase 3：辅助工具精确合成与像素锁定 > 比例修正版 > 实际应用意义 |
| 2 | 0.5187 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-3-assisted-compositing.md:144` ✅ | Phase 3：辅助工具精确合成与像素锁定 > Hera 人工复核：初版杯子比例过大 |
| 3 | 0.5150 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-3-multi-reference.md:94` | Phase 3：多参考图组合编辑 > 请 Hera 人工复核 |
| 4 | 0.5131 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-3-assisted-compositing.md:80` ✅ | Phase 3：辅助工具精确合成与像素锁定 > 第二步 B：低强度保守润色 |
| 5 | 0.5122 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:53` | Phase 4：尺寸、画幅与错误处理 > 画面观察 > 768 × 768 |

## P2-Q04（zh）

问题：麦克风多语言字幕从说完到完整显示，平均需要等多久？

正确项目排名：1；首选报告排名：7

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.7646 | whisper-large-v3-turbo-whispercpp | `whisper-large-v3-turbo-whispercpp/results/phase-4c-microphone-trilingual.md:104` | Phase 4C：中文麦克风与中日英字幕 > 结论与边界 |
| 2 | 0.7280 | whisper-large-v3-turbo-whispercpp | `whisper-large-v3-turbo-whispercpp/results/phase-4b-realtime-playback-demo.md:66` | Phase 4B：实时字幕播放模拟 > 结论 |
| 3 | 0.7148 | whisper-large-v3-turbo-whispercpp | `whisper-large-v3-turbo-whispercpp/results/phase-4b-realtime-playback-demo.md:7` | Phase 4B：实时字幕播放模拟 > 实际应用意义 |
| 4 | 0.6898 | whisper-large-v3-turbo-whispercpp | `whisper-large-v3-turbo-whispercpp/results/phase-4c-microphone-trilingual.md:41` | Phase 4C：中文麦克风与中日英字幕 > 最终真实麦克风结果 |
| 5 | 0.6846 | whisper-large-v3-turbo-whispercpp | `whisper-large-v3-turbo-whispercpp/results/phase-4b-realtime-playback-demo.md:11` | Phase 4B：实时字幕播放模拟 > 测试方式与边界 |

## P2-Q05（ja）

问题：Super TAE の比較動画が生成されなかった理由は何ですか。

正确项目排名：1；首选报告排名：1

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.7530 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-super-tae-compatibility.md:93` ✅ | Phase 5 收尾：Super TAE 兼容性测试 > 结论 |
| 2 | 0.7106 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-super-tae-compatibility.md:3` ✅ | Phase 5 收尾：Super TAE 兼容性测试 |
| 3 | 0.7019 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-super-tae-compatibility.md:58` ✅ | Phase 5 收尾：Super TAE 兼容性测试 > 根因 |
| 4 | 0.7013 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-super-tae-compatibility.md:7` ✅ | Phase 5 收尾：Super TAE 兼容性测试 > 实际应用意义 |
| 5 | 0.6941 | wan2.2-ti2v-5b-stablediffusioncpp | `wan2.2-ti2v-5b-stablediffusioncpp/results/PROJECT-SUMMARY.md:62` | Wan2.2 TI2V 5B 本地视频实验总结 > 关键测试结果 |

## P2-Q06（en）

问题：Did four concurrent multimodal requests substantially improve throughput, and what happened to latency?

正确项目排名：1；首选报告排名：1

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.7305 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:44` ✅ | Phase 14: llama-server 多模态并发与内存 > 结果 |
| 2 | 0.7110 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:63` ✅ | Phase 14: llama-server 多模态并发与内存 > 怎么理解 |
| 3 | 0.6706 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:5` ✅ | Phase 14: llama-server 多模态并发与内存 > 测试目的 |
| 4 | 0.6355 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:73` ✅ | Phase 14: llama-server 多模态并发与内存 > 结果文件 |
| 5 | 0.6318 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:27` ✅ | Phase 14: llama-server 多模态并发与内存 > 控制条件 |

## P2-Q07（zh）

问题：第一个文字模型在 8192 token 上下文测试时，处理速度是多少？

正确项目排名：1；首选报告排名：2

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.6200 | qwen3-14b-llamacpp | `qwen3-14b-llamacpp/results/phase-2-baseline.md:23` | Phase 2：Qwen3-14B Metal 基准 > 结果 |
| 2 | 0.5961 | qwen3-14b-llamacpp | `qwen3-14b-llamacpp/results/phase-3-context-benchmark.md:3` ✅ | Phase 3：长上下文安全扫描 |
| 3 | 0.5816 | qwen3-14b-llamacpp | `qwen3-14b-llamacpp/results/phase-3-context-benchmark.md:26` ✅ | Phase 3：长上下文安全扫描 > 8192-token prompt + 128-token generation |
| 4 | 0.5759 | flux2-klein-4b-stablediffusioncpp | `flux2-klein-4b-stablediffusioncpp/results/phase-1-first-baseline.md:25` | Phase 1：第一张可复现基线图 > 性能 |
| 5 | 0.5725 | qwen3-14b-llamacpp | `qwen3-14b-llamacpp/results/phase-3-context-benchmark.md:38` ✅ | Phase 3：长上下文安全扫描 > 16384-token prompt + 128-token generation |

## P2-Q08（zh）

问题：票据日期为什么不能只信模型输出，而必须加确定性校验？

正确项目排名：1；首选报告排名：7

| 排名 | 相似度 | 项目 | 来源 | 章节 |
| ---: | ---: | --- | --- | --- |
| 1 | 0.6403 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-10-gemini-receipt-ab.md:66` | Phase 10: 本地 Qwen 与 Gemini 票据 A/B > 确定性复核 |
| 2 | 0.6395 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/docs/02-gemini-receipt-ab-test.md:102` | Gemini 网络模型票据 A/B 测试 > 判定原则 |
| 3 | 0.6053 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-9-hybrid-receipt-api.md:73` | Phase 9: 本地 OCR + 多模态 API + 确定性校验 > 财务应用边界 |
| 4 | 0.5969 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-9-hybrid-receipt-api.md:48` | Phase 9: 本地 OCR + 多模态 API + 确定性校验 > 识别结果 |
| 5 | 0.5903 | qwen3-vl-8b-llamacpp | `qwen3-vl-8b-llamacpp/results/phase-9-hybrid-receipt-api.md:5` | Phase 9: 本地 OCR + 多模态 API + 确定性校验 > 目标 |

