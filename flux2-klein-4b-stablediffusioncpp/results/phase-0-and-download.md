# Phase 0 与模型下载结果

日期：2026-09-03

## 结论

环境、源码、Release + Metal 构建和三份模型权重均已准备完成。尚未运行第一次生图，所以这里确认的是“工具链与文件完整”，图像生成兼容性、速度、内存和质量将在 Phase 1 的固定参数基线中实测。

## 构建

- 新建独立源码目录：`worktrees/stable-diffusion.cpp`
- 上游：`https://github.com/leejet/stable-diffusion.cpp.git`
- commit：`6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- 编译：Release + Metal
- 产物：`worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli`
- 产物：`worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-server`
- Metal 运行自检：`MTL0 / Apple M2 Max`
- 源码与 frontend submodule 均保持 clean

可选网页前端的依赖安装触发了 pnpm 的构建脚本安全限制。本阶段没有放宽安全策略，改为构建无网页资源的 `sd-server`；API 服务能力保留，内嵌网页 UI 暂不包含。失败安装产生的 63 MB 临时依赖已经删除。

## 模型文件

统一模型根目录：`~/Documents/AI-Models/stable-diffusion/flux2-klein-4b`

| 组件 | 文件 | 字节数 | revision |
| --- | --- | ---: | --- |
| 扩散模型 | `diffusion/flux-2-klein-4b-Q4_0.gguf` | 2,460,378,560 | `3b1f5a9dc3abb32238b053aeb3d823c30afdacbd` |
| 文字编码器 | `text-encoder/Qwen3-4B-Q4_K_M.gguf` | 2,497,281,312 | `22c9fc8a8c7700b76a1789366280a6a5a1ad1120` |
| 编码器/小型解码器 | `vae/full_encoder_small_decoder.safetensors` | 249,519,092 | `a3efc24f613ef42d9428af62fdbd6f5fd8856c4a` |

精确合计：5,207,178,964 字节（4.85 GiB）。三份文件均与 Hugging Face 官方文件清单的字节数和 SHA-256 一致，哈希见 `results/model-manifest.sha256`。

## 下一步

Phase 1 使用固定 prompt、seed、1024 × 1024、4 steps 生成首张图片，记录加载、采样、VAE 解码、总耗时、峰值内存与 swap；随后以同一 seed 重复一次检查可复现性。
