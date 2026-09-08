# Phase 0–1 Setup

本文中的项目内路径均相对于 `qwen3-14b-llamacpp` 项目根目录。

## Metal 在本项目中的含义

Metal 是 Apple 提供的 GPU 计算接口。`llama.cpp` 通过 Metal 把适合并行计算的模型运算交给 M2 Max GPU。

这台 Mac 使用统一内存：CPU 与 GPU 访问同一组物理内存，不需要像独立显卡那样先把完整模型复制到单独显存。

启用 Metal 不表示 CPU 完全不工作。CPU 仍负责程序控制、分词、文件映射和少量输出缓冲；关键判断是模型主要计算层是否分配给 Metal GPU。

本次详细日志确认：

- 设备：`MTL0: Apple M2 Max`
- 模型层：`offloaded 41/41 layers to GPU`
- Metal model buffer：8,579.06 MiB
- Metal KV buffer：640.00 MiB（context 4096）
- Metal compute buffer：126.01 MiB
- Metal fusion、concurrency、graph optimization：启用
- Flash Attention：启用

因此本次不是 CPU-only 推理。

## 源码与构建

隔离源码：

```text
worktrees/llama.cpp
```

Release + Metal 构建：

```text
worktrees/llama.cpp/build-release-metal
```

可执行文件：

```text
worktrees/llama.cpp/build-release-metal/bin/llama-cli
worktrees/llama.cpp/build-release-metal/bin/llama-server
worktrees/llama.cpp/build-release-metal/bin/llama-bench
```

## 模型

只下载：

```text
Repository: Qwen/Qwen3-14B-GGUF
File: Qwen3-14B-Q4_K_M.gguf
Quantization: Q4_K_M
```

模型保存在项目外的统一缓存中：

```text
~/Documents/AI-Models/huggingface
```

没有把模型复制到项目目录，也没有下载 Q5、Q6、Q8 或整个 57.6 GB 仓库。

验证值：

```text
Size: 9001752960 bytes
SHA-256: 500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0
Hugging Face revision: 530227a7d994db8eca5ab5ced2fb692b614357fd
```

## 可重复烟雾测试

直接运行：

```bash
scripts/run_smoke_test.sh
```

脚本强制使用本地缓存和 `--offline`，所以不会重新联网下载。它使用当前 `llama.cpp` 的正式参数 `--reasoning off`，让第一次短测试只验证加载、Metal、中文和基础速度。

## 首次结果

Prompt：

```text
你好。请用三句话解释什么是大型语言模型，每句话不超过30个汉字。
```

模型输出：

```text
大型语言模型是基于大量文本训练的深度学习模型。
它能理解和生成自然语言，完成多种任务。
常用于聊天、写作、翻译等人工智能应用。
```

结果：

```text
Prompt processing: 83.8 tokens/s
Generation: 29.1 tokens/s
Maximum resident set size: 9411379200 bytes (~8.76 GiB)
Swap events reported by /usr/bin/time: 0
System-wide swap after the run: 3296.75 MiB used
```

`/usr/bin/time` 的 0 次 swap 只描述被测进程；系统全局 swap 可能来自此前或同时运行的其他应用。由于本阶段没有采集运行前基线，不能把当前 3296.75 MiB 归因于模型，也不能据此断言模型完全没有触发系统级换页。

首次进程总耗时约 19 分 55 秒，其中绝大部分是一次性下载。模型已经进入缓存后，一次强制离线的加载与单 token 核验约 1.7 秒完成。

下一阶段再单独进行可重复 benchmark、thinking/non-thinking 对照和功能测试，并补充运行前、运行中、运行后的内存与 swap 采样；本阶段没有运行 benchmark 或 slow tests。
