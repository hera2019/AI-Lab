# DeepFilterNet Cleaner

用途：从老 DV 等素材中挑出一小段目标人物语音，做轻量本地降噪，供 VoxStage 声线克隆测试。

## 最简单用法

1. 把一个音频文件放到 `input/`
2. 双击 `Clean-Audio.command`
3. 清理后的文件会出现在 `output/`，文件名为 `原名_clean.wav`

脚本会先用本机 FFmpeg 转为 48 kHz 单声道 WAV，再调用 DeepFilterNet Plus。
不启用额外 post-filter，避免为了“听起来更干净”而过度修改声线。

程序位置：
`/Users/Hera/Documents/AI-Models/DeepFilterNet/deep-filter-macos-arm64`

来源：DeepFilterNet Plus（MIT / Apache-2.0）
https://github.com/ismailivanov/DeepFilterNetPlus
