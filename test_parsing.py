#!/usr/bin/env python3
"""
测试 tool_calls 解析逻辑（不依赖模型生成）
"""
import sys
sys.path.insert(0, '/root/deepseek2api')

# 导入解析函数
from app import detect_and_parse_tool_calls
import json

def test_openai_format_parsing():
    """测试 OpenAI 格式的解析"""
    print("🧪 测试 1: OpenAI 格式解析")
    
    # 模拟模型返回的内容（包含 tool_calls）
    content = '''这是一些文本内容
{"tool_calls": [{"id": "call_001", "type": "function", "function": {"name": "get_weather", "arguments": "{\\"location\\": \\"北京\\"}"}}]}
还有一些其他内容'''
    
    tool_calls, remaining = detect_and_parse_tool_calls(content, "openai")
    
    if tool_calls:
        print("✅ 成功解析 OpenAI 格式")
        print(f"Tool calls: {json.dumps(tool_calls, ensure_ascii=False, indent=2)}")
        print(f"剩余内容: {remaining}")
    else:
        print("❌ 解析失败")
    print()


def test_claude_format_parsing():
    """测试 Claude 格式的解析"""
    print("🧪 测试 2: Claude 格式解析")
    
    # 模拟模型返回的内容（包含 tool_use）
    content = '''这是一些文本内容
{"tool_use": [{"type": "tool_use", "id": "toolu_001", "name": "get_weather", "input": {"location": "北京"}}]}
还有一些其他内容'''
    
    tool_calls, remaining = detect_and_parse_tool_calls(content, "claude")
    
    if tool_calls:
        print("✅ 成功解析 Claude 格式")
        print(f"Tool calls: {json.dumps(tool_calls, ensure_ascii=False, indent=2)}")
        print(f"剩余内容: {remaining}")
    else:
        print("❌ 解析失败")
    print()


def test_openai_to_claude_conversion():
    """测试 OpenAI 格式转换为 Claude 格式"""
    print("🧪 测试 3: OpenAI -> Claude 格式转换")
    
    content = '{"tool_calls": [{"id": "call_001", "type": "function", "function": {"name": "search_web", "arguments": "{\\"query\\": \\"AI news\\"}"}}]}'
    
    # 请求 Claude 格式输出
    tool_calls, remaining = detect_and_parse_tool_calls(content, "claude")
    
    if tool_calls:
        print("✅ 成功转换为 Claude 格式")
        print(f"Tool calls: {json.dumps(tool_calls, ensure_ascii=False, indent=2)}")
        
        # 验证格式
        if tool_calls[0].get("type") == "tool_use" and "input" in tool_calls[0]:
            print("✅ 格式正确：包含 type=tool_use 和 input 字段")
        else:
            print("❌ 格式错误")
    else:
        print("❌ 转换失败")
    print()


def test_claude_to_openai_conversion():
    """测试 Claude 格式转换为 OpenAI 格式"""
    print("🧪 测试 4: Claude -> OpenAI 格式转换")
    
    content = '{"tool_use": [{"type": "tool_use", "id": "toolu_001", "name": "search_web", "input": {"query": "AI news"}}]}'
    
    # 请求 OpenAI 格式输出
    tool_calls, remaining = detect_and_parse_tool_calls(content, "openai")
    
    if tool_calls:
        print("✅ 成功转换为 OpenAI 格式")
        print(f"Tool calls: {json.dumps(tool_calls, ensure_ascii=False, indent=2)}")
        
        # 验证格式
        if "function" in tool_calls[0] and "arguments" in tool_calls[0]["function"]:
            print("✅ 格式正确：包含 function 和 arguments 字段")
            # 验证 arguments 是字符串
            if isinstance(tool_calls[0]["function"]["arguments"], str):
                print("✅ arguments 是字符串格式")
            else:
                print("❌ arguments 应该是字符串")
        else:
            print("❌ 格式错误")
    else:
        print("❌ 转换失败")
    print()


def test_multiple_tools():
    """测试多个工具调用"""
    print("🧪 测试 5: 多个工具调用")
    
    content = '{"tool_calls": [{"id": "call_001", "function": {"name": "get_weather", "arguments": "{\\"location\\": \\"北京\\"}"}}, {"id": "call_002", "function": {"name": "get_time", "arguments": "{}"}}]}'
    
    tool_calls, remaining = detect_and_parse_tool_calls(content, "openai")
    
    if tool_calls:
        print(f"✅ 成功解析 {len(tool_calls)} 个工具调用")
        print(f"Tool calls: {json.dumps(tool_calls, ensure_ascii=False, indent=2)}")
    else:
        print("❌ 解析失败")
    print()


if __name__ == "__main__":
    print("=" * 70)
    print("Tool Calls 解析逻辑测试")
    print("=" * 70)
    print()
    
    test_openai_format_parsing()
    test_claude_format_parsing()
    test_openai_to_claude_conversion()
    test_claude_to_openai_conversion()
    test_multiple_tools()
    
    print("=" * 70)
    print("测试完成！")
    print("=" * 70)
