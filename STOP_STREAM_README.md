# Stop Stream 功能说明

## 功能概述

当用户主动中断正在进行的流式对话时，可以调用 `stop_stream` 端点来停止服务器端的响应生成。

## API 端点

### 1. OpenAI 格式

**端点**: `POST /v1/chat/stop_stream`

**请求头**:
```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**请求体**:
```json
{
  "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
  "message_id": 2
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "已停止流式响应"
}
```

### 2. Claude 格式

**端点**: `POST /anthropic/v1/messages/stop_stream`

**请求头**:
```
x-api-key: YOUR_API_KEY
Content-Type: application/json
anthropic-version: 2023-06-01
```

**请求体**:
```json
{
  "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
  "message_id": 2
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "已停止流式响应"
}
```

## 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `chat_session_id` | string | 是 | 对话会话 ID，从对话响应中获取 |
| `message_id` | integer | 否 | 消息 ID，用于标识具体要停止的消息 |

## 使用场景

1. **用户主动中断**: 用户点击"停止生成"按钮时
2. **超时保护**: 响应时间过长，客户端主动中断
3. **切换对话**: 用户在响应未完成时发起新的对话

## cURL 示例

### OpenAI 格式
```bash
curl -X POST 'http://localhost:5001/v1/chat/stop_stream' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
    "message_id": 2
  }'
```

### Claude 格式
```bash
curl -X POST 'http://localhost:5001/anthropic/v1/messages/stop_stream' \
  -H 'x-api-key: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{
    "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
    "message_id": 2
  }'
```

## Python 示例

```python
import requests

# OpenAI 格式
def stop_stream_openai(session_id, message_id=None):
    url = "http://localhost:5001/v1/chat/stop_stream"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    }
    payload = {
        "chat_session_id": session_id,
        "message_id": message_id
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()

# Claude 格式
def stop_stream_claude(session_id, message_id=None):
    url = "http://localhost:5001/anthropic/v1/messages/stop_stream"
    headers = {
        "x-api-key": "YOUR_API_KEY",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "chat_session_id": session_id,
        "message_id": message_id
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()

# 使用示例
result = stop_stream_openai("85437c2a-acf8-436a-a2ba-a4a110907fe7", 2)
print(result)
```

## 测试工具

项目提供了测试脚本 `test_stop_stream.py`，使用方法：

```bash
# 编辑脚本，配置 API_KEY 和参数
vim test_stop_stream.py

# 运行测试
python test_stop_stream.py
```

## 注意事项

1. **session_id 获取**: 需要从对话响应中提取 `chat_session_id`
2. **认证方式**: 
   - OpenAI 格式使用 `Authorization: Bearer TOKEN`
   - Claude 格式使用 `x-api-key: TOKEN`
3. **幂等性**: 多次调用同一个 session_id 的 stop 请求是安全的
4. **响应时机**: 调用后服务器会尽快停止生成，但已发送的内容无法撤回

## 错误处理

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 200 | 成功停止 | 正常处理 |
| 400 | 参数错误 | 检查 `chat_session_id` 是否提供 |
| 401 | 认证失败 | 检查 API Key 是否正确 |
| 500 | 服务器错误 | 查看日志，重试或联系管理员 |

## 实现细节

- 底层调用 DeepSeek 官方的 `/api/v0/chat/stop_stream` 接口
- 自动处理认证和请求头转换
- 支持 OpenAI 和 Claude 两种认证方式
- 完整的错误日志记录

## 更新日志

- **2026-03-21**: 初始版本，支持 OpenAI 和 Claude 格式的 stop_stream
