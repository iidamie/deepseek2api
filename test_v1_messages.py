#!/usr/bin/env python3
"""
测试 /v1/messages 端点（Claude 格式）
"""
import requests
import json

API_BASE = "http://localhost:8000"
API_KEY = "sk-test"

def test_basic_message():
    """测试基本的消息对话"""
    print("🧪 测试 1: 基本消息对话")
    
    payload = {
        "model": "deepseek-chat",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": "你好，请介绍一下你自己"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
            
            if result.get("type") == "message":
                print("✅ 返回格式正确（Claude message 格式）")
                
                content = result.get("content", [])
                if content and len(content) > 0:
                    print(f"✅ 内容: {content[0].get('text', '')[:100]}...")
            else:
                print("❌ 返回格式错误")
        else:
            print(f"❌ 请求失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    print()


def test_with_system():
    """测试带 system prompt 的对话"""
    print("🧪 测试 2: 带 system prompt 的对话")
    
    payload = {
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
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
            print("✅ 带 system prompt 的请求成功")
        else:
            print(f"❌ 请求失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    print()


def test_with_tools():
    """测试带 tools 的对话"""
    print("🧪 测试 3: 带 tools 的对话")
    
    tools = [
        {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位"
                    }
                },
                "required": ["location"]
            }
        }
    ]
    
    payload = {
        "model": "deepseek-chat",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": "北京今天天气怎么样？"
            }
        ],
        "tools": tools
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
            
            # 检查是否有 tool_use
            content = result.get("content", [])
            has_tool_use = any(block.get("type") == "tool_use" for block in content)
            
            if has_tool_use:
                print("✅ 成功检测到 tool_use!")
                for block in content:
                    if block.get("type") == "tool_use":
                        print(f"Tool: {block.get('name')}")
                        print(f"Input: {json.dumps(block.get('input', {}), ensure_ascii=False)}")
            else:
                print("⚠️  未检测到 tool_use，模型返回了普通文本")
                for block in content:
                    if block.get("type") == "text":
                        print(f"Text: {block.get('text', '')[:200]}")
        else:
            print(f"❌ 请求失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    print()


def test_streaming():
    """测试流式响应"""
    print("🧪 测试 4: 流式响应")
    
    payload = {
        "model": "deepseek-chat",
        "max_tokens": 1024,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "用一句话介绍 Python 编程语言"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/messages",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}\n")
        
        if response.status_code == 200:
            print("流式响应:")
            event_count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('event: '):
                        event_type = line_str[7:]
                        print(f"\n📨 Event: {event_type}")
                        event_count += 1
                    elif line_str.startswith('data: '):
                        data_str = line_str[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if "text" in delta:
                                    print(delta["text"], end='', flush=True)
                        except json.JSONDecodeError:
                            pass
            
            print(f"\n\n✅ 流式响应完成，收到 {event_count} 个事件")
        else:
            print(f"❌ 请求失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    print()


if __name__ == "__main__":
    print("=" * 70)
    print("/v1/messages 端点测试（Claude 格式）")
    print("=" * 70)
    print()
    
    test_basic_message()
    test_with_system()
    test_with_tools()
    test_streaming()
    
    print("=" * 70)
    print("测试完成！")
    print("=" * 70)
