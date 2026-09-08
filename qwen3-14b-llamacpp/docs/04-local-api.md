# Phase 5：调用本地模型 API

`llama-server` 不仅提供网页聊天，也提供与 OpenAI Chat Completions 风格兼容的本地 HTTP 接口。

数据只在本机流动：

```text
Terminal / App -> http://127.0.0.1:8080 -> Qwen3-14B -> JSON response
```

## 使用方法

先在一个 Terminal 窗口启动服务：

```bash
scripts/start_chat.sh
```

保持该窗口打开，在另一个 Terminal 窗口运行：

```bash
scripts/ask_local_model.sh "请用三点说明本地模型的优点"
```

脚本会完成：

1. 检查本地服务是否可用。
2. 把 System Prompt 和问题组成 JSON 请求。
3. 请求 `/v1/chat/completions`。
4. 从 JSON 中提取模型回答并显示在 Terminal。

## 接入其他程序

以后 Flutter、Python、Swift 或快捷指令都可以调用同一个地址。当前服务只监听 `127.0.0.1`，局域网中的其他设备无法访问。
