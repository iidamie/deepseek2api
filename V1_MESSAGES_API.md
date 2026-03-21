# /v1/messages 端点说明

## 概述

新增的 `/v1/messages` 端点完全兼容 **Anthropic Claude API** 格式，可以直接替代 Claude API 使用。

## 端点信息

- **路径**: `/v1/messages`
- **方法**: `POST`
- **格式**: Claude/Anthropic Messages API

## 与其他端点的区别

| 端点 | 格式 | 用途 |
|------|------|------|
| `/v1/chat/completions` | OpenAI | OpenAI 兼容客户端 |
| `/v1/messages` | Claude | Claude 兼容客户端 |
| `/anthropic/v1/messages` | Claude | Anthropic 官方格式（带前缀） |

## 请求格式

### 基本请求

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/messages",
    headers={
        "Content-Type": "application/json",
        "x-api-key": "your-api-key",
        "anthropic-version": "2023-06-01"
    },
    json={
        "model": "deepseek-chat",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": "你好，请介绍一下你自己"
            }
        ]
    }
)

result = response.json()
print(result)
```

### 带 System Prompt

```python
{
    "model": "deepseek-chat",
    "max_tokens": 1024,
    "system": "你是一个友好的助手，总是用简短的语言回答。",
    "messages": [
        {
            "role": "user",
            "content": "什么是人工智能？"
        }
    ]
}
```

### 带 Tools

```python
{
    "model": "deepseek-chat",
    "max_tokens": 1024,
    "messages": [
        {
            "role": "user",
            "content": "北京今天天气怎么样？"
        }
    ],
    "tools": [
        {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["location"]
            }
        }
    ]
}
```

### 流式响应

```python
response = requests.post(
    "http://localhost:8000/v1/messages",
    headers={
        "Content-Type": "application/json",
        "x-api-key": "your-api-key",
        "anthropic-version": "2023-06-01"
    },
    json={
        "model": "deepseek-chat",
        "max_tokens": 1024,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "介绍一下 Python"
            }
        ]
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('event: '):
            print(f"Event: {line_str[7:]}")
        elif line_str.startswith('data: '):
            print(f"Data: {line_str[6:]}")
```

## 响应格式

### 非流式响应

```json
{
    "id": "msg_xxx",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "你好！我是一个 AI 助手..."
        }
    ],
    "model": "deepseek-chat",
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 50
    }
}
```

### 带 Tool Use 的响应

```json
{
    "id": "msg_xxx",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": ""
        },
        {
            "type": "tool_use",
            "id": "toolu_001",
            "name": "get_weather",
            "input": {
                "location": "北京"
            }
        }
    ],
    "model": "deepseek-chat",
    "stop_reason": "tool_use",
    "stop_sequence": null,
    "usage": {
        "input_tokens": 100,
        "output_tokens": 20
    }
}
```

### 流式响应事件

流式响应使用 Server-Sent Events (SSE) 格式：

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你好"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"！"}}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":50}}

event: message_stop
data: {"type":"message_stop"}
```

## 使用 Anthropic SDK

可以直接使用 Anthropic 官方 SDK，只需修改 base_url：

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

message = client.messages.create(
    model="deepseek-chat",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "你好"
        }
    ]
)

print(message.content)
```

## 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型名称（如 deepseek-chat） |
| `messages` | array | 是 | 对话消息数组 |
| `max_tokens` | integer | 是 | 最大生成 token 数 |
| `system` | string | 否 | 系统提示词 |
| `temperature` | number | 否 | 温度参数（0-2，默认 1.0） |
| `top_p` | number | 否 | Top-p 采样（0-1，默认 1.0） |
| `stream` | boolean | 否 | 是否流式返回（默认 false） |
| `tools` | array | 否 | 可用工具列表 |

## 支持的模型

- `deepseek-chat`
- `deepseek-v3`
- `deepseek-r1`
- `deepseek-reasoner`
- 以及它们的 `-search` 变体

## 注意事项

1. **模型能力限制**：DeepSeek 模型不原生支持 function calling，tool_use 功能依赖 prompt engineering
2. **兼容性**：完全兼容 Anthropic Claude API 格式
3. **认证**：支持 `x-api-key` 和 `Authorization` 两种认证方式
4. **版本**：建议在请求头中包含 `anthropic-version: 2023-06-01`

## 测试

运行测试脚本：

```bash
python3 test_v1_messages.py
```

测试包括：
- ✅ 基本消息对话
- ✅ 带 system prompt 的对话
- ✅ 带 tools 的对话
- ✅ 流式响应

## 与 OpenClaw 集成

OpenClaw 可以通过配置使用此端点：

```json
{
  "provider": "anthropic",
  "baseURL": "http://localhost:8000",
  "apiKey": "your-api-key",
  "model": "deepseek-chat"
}
```

## 更新日志

- 2026-03-21: 新增 `/v1/messages` 端点，完全兼容 Claude API 格式
