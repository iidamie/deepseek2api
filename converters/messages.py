import re
import json
from utils.logger import logger


def messages_prepare(messages: list) -> str:
    """
    将 OpenAI 格式的 messages 转换为 DeepSeek 的 prompt 格式
    :param messages: OpenAI 格式的消息列表
    :return: DeepSeek 格式的 prompt 字符串
    """
    prompt_parts = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # 处理 content 为列表的情况（多模态）
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "image_url":
                        # 图片会在外部处理，这里只保留文本
                        pass
            content = "\n".join(text_parts)
        
        if role == "system":
            prompt_parts.append(f"System: {content}")
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
    
    return "\n\n".join(prompt_parts)


def parse_tool_calls_from_text(text: str):
    """
    从文本中解析工具调用
    支持格式：<tool_call>{"name": "...", "arguments": {...}}</tool_call>
    :param text: 文本内容
    :return: (纯文本, 工具调用列表)
    """
    tool_calls = []
    
    # 匹配 <tool_call>...</tool_call>
    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            tool_data = json.loads(match.strip())
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": tool_data.get("name", ""),
                    "arguments": json.dumps(tool_data.get("arguments", {}))
                }
            })
        except json.JSONDecodeError as e:
            logger.warning(f"[parse_tool_calls] JSON 解析失败: {e}")
    
    # 移除工具调用标签，保留纯文本
    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    
    return clean_text, tool_calls
