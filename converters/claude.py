import json
from curl_cffi import requests
from utils.logger import logger


def convert_claude_to_deepseek(claude_request):
    """
    将 Claude 请求转换为 DeepSeek 格式
    :param claude_request: Claude 格式的请求
    :return: DeepSeek 格式的请求
    """
    messages = claude_request.get("messages", [])
    system_prompt = claude_request.get("system", "")
    
    # 构造 OpenAI 格式的消息
    openai_messages = []
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        
        # 处理 content 为列表的情况
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "image":
                        # Claude 图片格式
                        source = item.get("source", {})
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            text_parts.append(f"[Image: data:{media_type};base64,{data[:50]}...]")
            content = "\n".join(text_parts)
        
        openai_messages.append({"role": role, "content": content})
    
    return {
        "model": claude_request.get("model", "claude-3-5-sonnet-20241022"),
        "messages": openai_messages,
        "temperature": claude_request.get("temperature", 1.0),
        "max_tokens": claude_request.get("max_tokens", 4096),
        "stream": claude_request.get("stream", False),
    }


def call_claude_via_openai(openai_request, claude_api_key):
    """
    通过 OpenAI 格式调用 Claude API
    :param openai_request: OpenAI 格式的请求
    :param claude_api_key: Claude API Key
    :return: Response 对象
    """
    try:
        headers = {
            "Authorization": f"Bearer {claude_api_key}",
            "Content-Type": "application/json",
        }
        
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=openai_request,
            stream=openai_request.get("stream", False),
            impersonate="safari15_3",
        )
        
        return resp
        
    except Exception as e:
        logger.error(f"[call_claude_via_openai] 请求异常: {e}")
        raise


def claude_to_openai_messages(claude_messages: list, system_prompt: str = None):
    """
    将 Claude 格式的 messages 转换为 OpenAI 格式
    :param claude_messages: Claude 格式的消息列表
    :param system_prompt: 系统提示（可选）
    :return: OpenAI 格式的消息列表
    """
    openai_messages = []
    
    # 添加系统提示
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})
    
    for msg in claude_messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        
        # 处理 content 为列表的情况
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "image":
                        # Claude 图片格式转换
                        source = item.get("source", {})
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            text_parts.append(f"[Image: data:{media_type};base64,{data}]")
            content = "\n".join(text_parts)
        
        openai_messages.append({"role": role, "content": content})
    
    return openai_messages


def openai_to_claude_response(openai_response: dict, model: str = "claude-3-5-sonnet-20241022"):
    """
    将 OpenAI 格式的响应转换为 Claude 格式
    :param openai_response: OpenAI 格式的响应
    :param model: 模型名称
    :return: Claude 格式的响应
    """
    choice = openai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "")
    
    # 处理工具调用
    tool_calls = message.get("tool_calls", [])
    claude_content = []
    
    if content:
        claude_content.append({"type": "text", "text": content})
    
    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        claude_content.append({
            "type": "tool_use",
            "id": tool_call.get("id", ""),
            "name": function.get("name", ""),
            "input": json.loads(function.get("arguments", "{}"))
        })
    
    claude_response = {
        "id": openai_response.get("id", ""),
        "type": "message",
        "role": "assistant",
        "content": claude_content if claude_content else [{"type": "text", "text": content}],
        "model": model,
        "stop_reason": "end_turn" if choice.get("finish_reason") == "stop" else choice.get("finish_reason"),
        "stop_sequence": None,
        "usage": {
            "input_tokens": openai_response.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": openai_response.get("usage", {}).get("completion_tokens", 0)
        }
    }
    
    return claude_response


def openai_stream_to_claude_stream(chunk: dict, model: str = "claude-3-5-sonnet-20241022"):
    """
    将 OpenAI 流式响应转换为 Claude 流式格式
    :param chunk: OpenAI 流式 chunk
    :param model: 模型名称
    :return: Claude 流式事件列表
    """
    events = []
    
    # message_start 事件
    if chunk.get("choices", [{}])[0].get("delta", {}).get("role"):
        events.append({
            "type": "message_start",
            "message": {
                "id": chunk.get("id", ""),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }
        })
        events.append({
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""}
        })
    
    # content_block_delta 事件
    delta = chunk.get("choices", [{}])[0].get("delta", {})
    content = delta.get("content", "")
    if content:
        events.append({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": content}
        })
    
    # message_delta 事件（结束）
    finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
    if finish_reason:
        events.append({
            "type": "content_block_stop",
            "index": 0
        })
        events.append({
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn" if finish_reason == "stop" else finish_reason, "stop_sequence": None},
            "usage": {"output_tokens": 0}
        })
        events.append({"type": "message_stop"})
    
    return events
