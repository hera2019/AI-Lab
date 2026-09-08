# Qwen3-VL 模型缓存清理

清理日期：2026-09-01

## 删除目标

实际使用的缓存根目录由项目脚本中的 `LLAMA_CACHE` 默认值核对为：

```text
~/Documents/AI-Models/huggingface
```

只删除了与本项目模型仓库一一对应的目录：

```text
~/Documents/AI-Models/huggingface/models--Qwen--Qwen3-VL-8B-Instruct-GGUF
```

其中主要文件为：

- `Qwen3VL-8B-Instruct-Q4_K_M.gguf` 对应 blob：5,027,784,800 bytes
- `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` 对应 blob：752,289,728 bytes
- 该仓库的 snapshot 软链接和 `refs/main`

没有删除 Hugging Face 缓存根目录、其他模型缓存、项目目录或 llama.cpp worktree。

## 磁盘空间

```text
before_available=32,451,260 KiB  (约 30.95 GiB)
after_available=38,095,964 KiB   (约 36.33 GiB)
released=5,644,704 KiB           (约 5.38 GiB)
```

删除后再次搜索，没有发现 `Qwen3-VL-8B` 同名缓存残留。项目目录仍约 378 MB，README、PROJECT-SUMMARY、docs、scripts、tests、results、原始响应和 llama.cpp worktree 均保留。

以后重新运行带 `-hf Qwen/Qwen3-VL-8B-Instruct-GGUF:Q4_K_M` 的脚本时，llama.cpp 会重新下载主模型和 projector；因此在不准备重跑实验时保持清理状态即可。
