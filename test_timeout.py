#!/usr/bin/env python3
"""
测试客户端中断 - 使用 timeout 模拟真实场景
"""
import requests
import time

BASE_URL = "http://localhost:5001"
API_KEY = "u-lbTc6NOU_ca-IJ23L8mBQO1W3IZKC6cPrIpaEk2BE"

def test_timeout_disconnect():
    """使用短 timeout 模拟客户端中断"""
    print("🚀 发起流式请求（设置 2 秒超时）...")
    
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
        # 设置 2 秒超时，强制中断
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=2)
        
        print(f"📡 响应状态码: {resp.status_code}")
        print("📥 开始接收流式数据...\n")
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                print(f"{decoded[:80]}...")
        
    except requests.exceptions.ReadTimeout:
        print("\n⏱️  读取超时 - 连接被强制中断")
        print("💡 这会触发服务端的 GeneratorExit，应该调用 stop_stream")
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试客户端超时中断")
    print("=" * 60)
    print()
    
    test_timeout_disconnect()
    
    print("\n" + "=" * 60)
    print("等待 2 秒后查看日志...")
    print("=" * 60)
    
    time.sleep(2)
    
    import subprocess
    print("\n📋 服务端日志（最近 30 行）:")
    print("-" * 60)
    subprocess.run(["tail", "-30", "/root/deepseek2api/test_app.log"])
