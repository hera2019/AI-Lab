# Phase 3：本地 RAG 评测

- 测试：3/4 自动检查通过
- 全部测试墙钟时间：25.093 秒

自动检查只能验证关键事实标记、拒答句式和引用编号；最终语义质量仍需人工阅读。

## RAG-Q01（zh）— PASS

问题：为什么猫眨眼的测试最后只能算部分成功？

回答：

因为猫的双眼能够从睁开逐渐闭合，但闭合后一直保持到最后一帧，没有重新睁开，说明模型只能执行“睁眼 → 闭眼 → 保持闭眼”的单阶段动作，无法可靠完成“闭合 → 短暂停留 → 重新睁开”的多阶段时间顺序，因此该测试结果记为部分成功、完整眨眼失败 [S1][S5]。

来源：

- [S1] `wan2.2-ti2v-5b-stablediffusioncpp/results/phase-5-fastwan.md:105-111` — Phase 5：FastWan 3-step 加速测试 > 画质观察 > 65 帧眨眼单项 I2V（0.7271）
- [S2] `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:59-62` — Phase 4：尺寸、画幅与错误处理 > 画面观察 > 1024 × 768 横图（0.5864）
- [S3] `flux2-klein-4b-stablediffusioncpp/results/phase-4-performance-errors.md:53-55` — Phase 4：尺寸、画幅与错误处理 > 画面观察 > 768 × 768（0.5811）
- [S4] `wan2.2-ti2v-5b-stablediffusioncpp/results/PROJECT-SUMMARY.md:104-111` — Wan2.2 TI2V 5B 本地视频实验总结 > 质量观察 > 正常的 33 帧 I2V（0.5433）
- [S5] `wan2.2-ti2v-5b-stablediffusioncpp/results/PROJECT-SUMMARY.md:68-82` — Wan2.2 TI2V 5B 本地视频实验总结 > FastWan 3-step 结论（0.5332）

检查：

- PASS `citation_syntax`：cited=['S1', 'S5'] unknown=[] uncited_lines=[]
- PASS `did_not_refuse`：因为猫的双眼能够从睁开逐渐闭合，但闭合后一直保持到最后一帧，没有重新睁开，说明模型只能执行“睁眼 → 闭眼 → 保持闭眼”的单阶段动作，无法可靠完成“闭合 → 短暂停留 → 重新睁开”的多阶段时间顺序，因此该测试结果记为部分成功、完整眨眼失败 [S1][S5]。
- PASS `expected_project_retrieved`：retrieved_projects=['flux2-klein-4b-stablediffusioncpp', 'wan2.2-ti2v-5b-stablediffusioncpp']
- PASS `contains_expected_meaning_marker`：accepted=['没有重新睁开', '没能重新睁开', '未能重新睁开', '未重新睁开', '没有再次睁开', '没有再睁开']

时间：检索 0.852 秒；问答模型 5.988 秒；合计 6.858 秒。

## RAG-Q02（ja）— FAIL

问题：レシートの TP は商品名の一部ですか、それとも別の列ですか。

回答：

TP 是另一个列，而不是商品名的组成部分。

在资料中明确提到：
- “TP 1 特セット餃子+3個 165” 表示 TP 是一个独立的标记列，用于标识特定的菜品组合 [S1]。
- 多模态模型和混合方案中也指出，“第三行独立左列标记 TP 被漏掉，尽管 Apple Vision 保留了它与菜品行的独立坐标” [S4]，这说明 TP 是一个独立的列，具有明确的结构位置。

因此，TP 是一个独立的列，用于标识特定商品（如“特セット餃子+3個”），而不是商品名的一部分。

[S4]

来源：

- [S1] `qwen3-vl-8b-llamacpp/results/phase-7-real-japanese-receipt-ocr.md:29-51` — Phase 7：真实日文票据 OCR > 模型原始输出（0.5518）
- [S2] `qwen3-vl-8b-llamacpp/results/phase-7-real-japanese-receipt-ocr.md:55-71` — Phase 7：真实日文票据 OCR > 准确性（0.4744）
- [S3] `qwen3-vl-8b-llamacpp/results/phase-10-gemini-receipt-ab.md:28-51` — Phase 10: 本地 Qwen 与 Gemini 票据 A/B > Gemini 3.6 Flash 结果（0.4627）
- [S4] `qwen3-vl-8b-llamacpp/results/phase-9-hybrid-receipt-api.md:48-69` — Phase 9: 本地 OCR + 多模态 API + 确定性校验 > 识别结果（0.4498）
- [S5] `qwen3-vl-8b-llamacpp/results/phase-8-apple-vision-hybrid-ocr.md:41-43` — Phase 8：Apple Vision 本地 OCR 与混合票据方案 > 表格结构（0.4404）

检查：

- FAIL `citation_syntax`：cited=['S1', 'S4'] unknown=[] uncited_lines=['TP 是另一个列，而不是商品名的组成部分。', '因此，TP 是一个独立的列，用于标识特定商品（如“特セット餃子+3個”），而不是商品名的一部分。']
- PASS `did_not_refuse`：TP 是另一个列，而不是商品名的组成部分。

在资料中明确提到：
- “TP 1 特セット餃子+3個 165” 表示 TP 是一个独立的标记列，用于标识特定的菜品组合 [S1]。
- 多模态模型和混合方案中也指出，“第三行独立左列标记 TP 被漏掉，尽管 Apple Vision 保留了它与菜品行的独立坐标” [S4]
- PASS `expected_project_retrieved`：retrieved_projects=['qwen3-vl-8b-llamacpp']
- PASS `contains:TP`：TP 是另一个列，而不是商品名的组成部分。

在资料中明确提到：
- “TP 1 特セット餃子+3個 165” 表示 TP 是一个独立的标记列，用于标识特定的菜品组合 [S1]。
- 多模态模型和混合方案中也指出，“第三行独立左列标记 TP 被漏掉，尽管 Apple Vision 保留了它与菜品行的独立坐标” [S4]，这说明 TP 是一个独立的列，具有明确的结构位置。

因此，TP 是一个独立的
- FAIL `contains_expected_meaning_marker`：accepted=['別の列', '別列', '独立した列', '別のカラム', '独立した', '商品名の一部ではない']

时间：检索 0.871 秒；问答模型 6.438 秒；合计 7.326 秒。

## RAG-Q03（en）— PASS

问题：Did four concurrent multimodal requests substantially improve throughput, and what happened to average latency?

回答：

Four concurrent multimodal requests did not substantially improve throughput. The throughput increased only from 0.220 req/s to 0.238 req/s, a rise of about 8.2% [S1]. 

The average single request latency increased significantly, from 4.55 seconds to 16.79 seconds, approximately 3.69 times higher [S1]. 

Thus, concurrency did not lead to meaningful throughput gains and instead caused a substantial increase in latency. [S2]

来源：

- [S1] `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:44-59` — Phase 14: llama-server 多模态并发与内存 > 结果（0.7293）
- [S2] `qwen3-vl-8b-llamacpp/results/phase-14-concurrency-scaling.md:63-69` — Phase 14: llama-server 多模态并发与内存 > 怎么理解（0.7013）
- [S3] `README.md:22-24` — AI Lab > Projects > qwen3-vl-8b-llamacpp（0.5308）
- [S4] `flux2-klein-4b-stablediffusioncpp/results/final-project-summary.md:52-56` — FLUX.2 klein 4B 本地实验最终总结 > 各阶段结论 > Phase 4：性能与工程可靠性（0.5250）
- [S5] `flux2-klein-4b-stablediffusioncpp/results/phase-2-instruction-isolation.md:67-74` — Phase 2：提示遵循拆分测试 > 性能（0.5059）

检查：

- PASS `citation_syntax`：cited=['S1', 'S2'] unknown=[] uncited_lines=[]
- PASS `did_not_refuse`：Four concurrent multimodal requests did not substantially improve throughput. The throughput increased only from 0.220 req/s to 0.238 req/s, a rise of about 8.2
- PASS `expected_project_retrieved`：retrieved_projects=['AI-Lab', 'flux2-klein-4b-stablediffusioncpp', 'qwen3-vl-8b-llamacpp']
- PASS `contains:8.2`：Four concurrent multimodal requests did not substantially improve throughput. The throughput increased only from 0.220 req/s to 0.238 req/s, a rise of about 8.2% [S1]. 

The average single request lat
- PASS `contains:16.79`：Four concurrent multimodal requests did not substantially improve throughput. The throughput increased only from 0.220 req/s to 0.238 req/s, a rise of about 8.2% [S1]. 

The average single request lat

时间：检索 0.880 秒；问答模型 5.752 秒；合计 6.650 秒。

## RAG-Q04（zh）— PASS

问题：Hera 的 Mac Studio 是在哪家商店购买的，当时准确价格是多少？

回答：

资料中没有足够信息，无法回答。

来源：

- [S1] `README.md:7-10` — AI Lab > Hardware（0.5217）
- [S2] `flux2-klein-4b-stablediffusioncpp/results/phase-3-assisted-compositing.md:144-146` — Phase 3：辅助工具精确合成与像素锁定 > Hera 人工复核：初版杯子比例过大（0.4931）
- [S3] `wan2.2-ti2v-5b-stablediffusioncpp/results/PROJECT-SUMMARY.md:23-31` — Wan2.2 TI2V 5B 本地视频实验总结 > 环境（0.4609）
- [S4] `flux2-klein-4b-stablediffusioncpp/results/phase-3-assisted-compositing.md:222-224` — Phase 3：辅助工具精确合成与像素锁定 > 比例修正版 > Hera 人工复核结果（0.4498）
- [S5] `flux2-klein-4b-stablediffusioncpp/results/final-project-summary.md:7` — FLUX.2 klein 4B 本地实验最终总结 > 一句话结论（0.4307）

检查：

- PASS `citation_syntax`：cited=[] unknown=[] uncited_lines=[]
- PASS `exact_refusal`：资料中没有足够信息，无法回答。

时间：检索 0.943 秒；问答模型 3.298 秒；合计 4.259 秒。

