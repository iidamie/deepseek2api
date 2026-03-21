#!/usr/bin/env python3
"""
测试 deepseek2api 的 Claude 格式 tools 支持
"""
import requests
import json

# 配置
API_BASE = "http://localhost:8000"
API_KEY = "sk-test"  # 测试用

def test_claude_format_tools():
    """测试 Claude 格式的 tools 调用"""
    
    # Claude 格式的工具定义
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
    
    # 构建请求
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "北京今天天气怎么样？"
            }
        ],
        "tools": tools,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("🧪 测试 1: Claude 格式 - 非流式 tools 调用")
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
            
            # 检查是否有 tool_calls
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                message = choice.get("message", {})
                
                if "tool_calls" in message:
                    print("✅ 成功检测到 tool_calls!")
                    print(f"Tool calls: {json.dumps(message['tool_calls'], ensure_ascii=False, indent=2)}")
                    
                    # 检查格式
                    first_call = message['tool_calls'][0]
                    if 'type' in first_call and first_call['type'] == 'tool_use':
                        print("✅ 返回格式为 Claude 格式 (tool_use)")
                    elif 'function' in first_call:
                        print("✅ 返回格式为 OpenAI 格式 (function)")
                else:
                    print("⚠️  未检测到 tool_calls，可能模型没有调用工具")
                    print(f"Content: {message.get('content', '')}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")


def test_openai_format_tools():
    """测试 OpenAI 格式的 tools 调用（对比测试）"""
    
    # OpenAI 格式的工具定义
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
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
        }
    ]
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "上海今天天气怎么样？"
            }
        ],
        "tools": tools,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("\n🧪 测试 2: OpenAI 格式 - 非流式 tools 调用（对比测试）")
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}\n")
            
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                message = choice.get("message", {})
                
                if "tool_calls" in message:
                    print("✅ 成功检测到 tool_calls!")
                    print(f"Tool calls: {json.dumps(message['tool_calls'], ensure_ascii=False, indent=2)}")
                    
                    # 检查格式
                    first_call = message['tool_calls'][0]
                    if 'function' in first_call:
                        print("✅ 返回格式为 OpenAI 格式 (function)")
                    elif 'type' in first_call and first_call['type'] == 'tool_use':
                        print("✅ 返回格式为 Claude 格式 (tool_use)")
                else:
                    print("⚠️  未检测到 tool_calls")
                    print(f"Content: {message.get('content', '')}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")


def test_claude_streaming():
    """测试 Claude 格式的流式调用"""
    
    tools = [
        {
            "name": "search_web",
            "description": "搜索网络信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "帮我搜索一下最新的 AI 新闻"
            }
        ],
        "tools": tools,
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("\n🧪 测试 3: Claude 格式 - 流式 tools 调用")
    print(f"请求: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}\n")
        
        if response.status_code == 200:
            print("流式响应:")
            tool_calls_found = False
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            print("\n✅ 流结束")
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", )
                                if "tool_calls" in delta:
                                    tool_calls_found = True
                                    print(f"\n🔧 Tool call: {json.dumps(delta['tool_calls'], ensure_ascii=False, indent=2)}")
                                elif "content" in delta:
                                    print(delta['content'], end='', flush=True)
                        except json.JSONDecodeError:
                            pass
            
            if tool_calls_found:
                print("\n✅ 流式响应中成功检测到 tool_calls")
            else:
                print("\n⚠️  流式响应中未检测到 tool_calls")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("DeepSeek2API Claude 格式 Tools 功能测试")
    print("=" * 70)
    print()
    
    test_claude_format_tools()
    test_openai_format_tools()
    test_claude_streaming()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
