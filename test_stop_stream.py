#!/usr/bin/env python3
"""
测试 stop_stream 端点
用法: python test_stop_stream.py
"""

import requests
import json
import time

# 配置
BASE_URL = "http://localhost:5001"
API_KEY = "your-api-key-here"  # 替换为你的 API key

def test_openai_stop_stream():
    """测试 OpenAI 格式的 stop_stream"""
    print("=" * 60)
    print("测试 OpenAI 格式 stop_stream")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/chat/stop_stream"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 替换为实际的 session_id 和 message_id
    payload = {
        "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
        "message_id": 2
    }
    
    print(f"\n请求 URL: {url}")
    print(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"\n响应状态码: {resp.status_code}")
        print(f"响应内容: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")


def test_claude_stop_stream():
    """测试 Claude 格式的 stop_stream"""
    print("\n" + "=" * 60)
    print("测试 Claude 格式 stop_stream")
    print("=" * 60)
    
    url = f"{BASE_URL}/anthropic/v1/messages/stop_stream"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    # 替换为实际的 session_id 和 message_id
    payload = {
        "chat_session_id": "85437c2a-acf8-436a-a2ba-a4a110907fe7",
        "message_id": 2
    }
    
    print(f"\n请求 URL: {url}")
    print(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"\n响应状态码: {resp.status_code}")
        print(f"响应内容: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")


def test_with_real_conversation():
    """
    完整测试流程：
    1. 发起一个对话请求
    2. 立即调用 stop_stream 中断
    """
    print("\n" + "=" * 60)
    print("完整测试：发起对话 -> 中断")
    print("=" * 60)
    
    # 1. 发起对话
    chat_url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    chat_payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "请写一篇5000字的文章，主题是人工智能的发展历程"}
        ],
        "stream": True
    }
    
    print("\n📤 发起流式对话请求...")
    print(f"请求体: {json.dumps(chat_payload, indent=2, ensure_ascii=False)}")
    
    try:
        # 发起流式请求（不等待完成）
        resp = requests.post(chat_url, headers=headers, json=chat_payload, stream=True, timeout=5)
        
        # 从响应中提取 session_id（需要根据实际响应格式调整）
        print("\n⏳ 等待 2 秒后中断...")
        time.sleep(2)
        
        # 这里需要从实际响应中获取 session_id 和 message_id
        # 由于是流式响应，可能需要解析第一个 chunk
        print("\n⚠️  注意：需要从实际对话响应中获取 chat_session_id 和 message_id")
        print("请手动替换 test_openai_stop_stream() 中的参数后再测试")
        
    except requests.exceptions.Timeout:
        print("✅ 请求超时（预期行为）")
    except Exception as e:
        print(f"❌ 请求失败: {e}")


if __name__ == "__main__":
    print("\n🧪 DeepSeek2API Stop Stream 测试工具\n")
    
    print("⚠️  使用前请先配置:")
    print(f"   1. API_KEY = '{API_KEY}'")
    print(f"   2. BASE_URL = '{BASE_URL}'")
    print(f"   3. 替换 payload 中的 chat_session_id 和 message_id\n")
    
    choice = input("选择测试:\n1. OpenAI 格式\n2. Claude 格式\n3. 完整流程测试\n请输入 (1/2/3): ").strip()
    
    if choice == "1":
        test_openai_stop_stream()
    elif choice == "2":
        test_claude_stop_stream()
    elif choice == "3":
        test_with_real_conversation()
    else:
        print("❌ 无效选择")
