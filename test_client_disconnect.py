#!/usr/bin/env python3
"""
测试客户端中断时的 stop_stream 功能
"""
import requests
import time
import signal
import sys

BASE_URL = "http://localhost:5001"
API_KEY = "u-lbTc6NOU_ca-IJ23L8mBQO1W3IZKC6cPrIpaEk2BE"

def test_disconnect():
    """发起流式请求，然后主动断开"""
    print("🚀 发起流式对话请求...")
    
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "请写一篇5000字的文章，主题是人工智能的发展历程"}
        ],
        "stream": True
    }
    
    try:
        # 发起流式请求
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=10)
        
        print(f"📡 响应状态码: {resp.status_code}")
        print("📥 开始接收流式数据...\n")
        
        chunk_count = 0
        for line in resp.iter_lines():
            if line:
                chunk_count += 1
                decoded = line.decode('utf-8')
                print(f"[Chunk {chunk_count}] {decoded[:100]}...")
                
                # 接收 3 个 chunk 后主动断开
                if chunk_count >= 3:
                    print("\n⚠️  模拟客户端中断（关闭连接）...")
                    resp.close()  # 主动关闭连接
                    break
        
        print("\n✅ 连接已关闭")
        print("💡 现在检查服务端日志，应该能看到调用 stop_stream 的记录")
        
    except requests.exceptions.Timeout:
        print("⏱️  请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试客户端中断时的 stop_stream 功能")
    print("=" * 60)
    print()
    
    test_disconnect()
    
    print("\n" + "=" * 60)
    print("测试完成！请查看服务端日志:")
    print("  tail -f /root/deepseek2api/logs/*.log")
    print("=" * 60)
