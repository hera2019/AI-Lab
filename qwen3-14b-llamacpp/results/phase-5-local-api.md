# Phase 5：本地模型 API

状态：已完成。

## 配置

- 模型：Qwen3-14B Q4_K_M
- 服务：llama-server
- 地址：`http://127.0.0.1:8080`
- 接口：`POST /v1/chat/completions`
- 上下文：8K
- Reasoning：off
- 网络：只访问本机回环地址，不访问互联网

## 测试请求

```text
请用三点说明，把本地大模型作为程序 API 有什么价值。每点不超过二十五个汉字。
```

## 模型回答

```text
1. 提升程序响应速度与效率。
2. 降低对网络连接的依赖。
3. 增强数据处理与隐私安全。
```

## 结果

- `/health` 检查成功。
- JSON 请求成功发送。
- OpenAI Chat Completions 风格响应成功返回。
- 脚本正确提取 `choices[0].message.content`。
- 中文参数与输出正常。

## 复现

Terminal 1：

```bash
scripts/start_chat.sh
```

Terminal 2：

```bash
scripts/ask_local_model.sh "你的问题"
```

当前服务只监听 `127.0.0.1`，其他电脑和手机无法直接访问。
