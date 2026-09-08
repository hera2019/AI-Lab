# Phase 4：不依赖模型回答的最小复现

执行日期：2026-08-31

本文件记录实验事实和代码路径，不是用于提交的 GitHub issue、PR 描述或评论。

## Alpha 通道

复现命令：

```bash
scripts/run_mtmd_decode_probe.sh
```

该脚本编译一个只调用 libmtmd 解码 API 的小型本地探针，不加载语言模型，也不使用模型回答作为证据。

结果：

```text
===== fully transparent green 1x1 PNG =====
decoded=1x1 channels=3 bytes=3
first_rgb=0,255,0
pure_red_pixels=0
pure_green_pixels=1

===== PNG containing alpha=0 red text =====
decoded=720x420 channels=3 bytes=907200
first_rgb=0,0,0
pure_red_pixels=4039
pure_green_pixels=0
```

结论：alpha=0 的绿色像素被输出为绿色 RGB；alpha=0 的隐藏红字被输出为 4,039 个纯红像素。透明内容在进入模型之前已经暴露。

直接代码路径：`worktrees/llama.cpp/tools/mtmd/mtmd-helper.cpp` 调用 `stbi_load_from_memory(..., 3)`，强制三通道输出。

尚需由贡献者决定的行为语义：

- 合成到固定白色背景。
- 合成到固定黑色背景。
- 允许调用方选择背景。
- 保留现状，但在 API/文档中明确透明像素的处理方式。

因为预期行为尚未定义，该问题更适合先由人类贡献者讨论设计，不应直接生成修复。

## 无效媒体退出码

复现命令：

```bash
scripts/repro_invalid_media_exit_code.sh
```

脚本在成功复现时故意返回非零状态，方便自动测试捕获问题。

已确认：

```text
BAD-002 exit_code=0
BAD-002 decoder_error=yes
BAD-002 BUG_REPRODUCED: decoder error returned success
BAD-003 exit_code=0
BAD-003 decoder_error=yes
BAD-003 BUG_REPRODUCED: decoder error returned success
BAD-MISSING exit_code=0
BAD-MISSING staging_error=yes
BAD-MISSING BUG_REPRODUCED: staging error returned success
reproduced_cases=3
```

对照：`llama-mtmd-cli` 读取同一 0 字节 PNG 时返回退出码 1，因此问题不是 libmtmd 无法表达失败，而是标准 `llama-cli` 没有把失败传播给进程退出状态。

代码路径：

1. `cli_context::generate_completion()` 在 HTTP/流错误时返回 `false`。
2. `cli_context::run()` 调用它但忽略返回值。
3. `--single-turn` 随后结束循环。
4. `cli_context::run()` 固定返回 0。

另外，命令行指定不存在的媒体文件时，`stage_media_file()` 返回失败，但当前循环也会继续处理没有图片的文字提示。复现脚本包含该对照。

潜在最小行为设计：

- `--single-turn`：媒体暂存、请求或生成失败时返回 1。
- 交互模式：显示错误并保留会话，让用户可以修正输入；不应把一次请求失败当作整个交互进程失败。

在贡献者明确认可该语义前，不修改上游源码、不创建测试、不提交 commit 或 PR。

## 上游规则

llama.cpp 要求贡献者本人理解、审查并长期负责提交内容，禁止 AI 代写 issue、PR 描述和维护者回复，也禁止自动提交。任何后续贡献必须由人类贡献者亲自形成文字、确认设计并执行提交。
