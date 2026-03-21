from curl_cffi import requests
from utils.logger import logger

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_COMPLETION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/completion"
DEEPSEEK_STOP_STREAM_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/stop_stream"


def call_deepseek_completion(headers: dict, payload: dict, stream: bool = False):
    """
    调用 DeepSeek 对话补全接口
    :param headers: 请求头
    :param payload: 请求体
    :param stream: 是否流式
    :return: Response 对象
    """
    try:
        resp = requests.post(
            DEEPSEEK_COMPLETION_URL,
            headers=headers,
            json=payload,
            stream=stream,
            impersonate="safari15_3",
        )
        return resp
        
    except Exception as e:
        logger.error(f"[call_deepseek_completion] 请求异常: {e}")
        raise


def stop_deepseek_stream(token: str, session_id: str, request_id: str) -> bool:
    """
    停止 DeepSeek 流式响应
    :param token: DeepSeek token
    :param session_id: 会话 ID
    :param request_id: 请求 ID
    :return: 是否成功
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "authorization": f"Bearer {token}",
        }
        
        resp = requests.post(
            DEEPSEEK_STOP_STREAM_URL,
            headers=headers,
            json={
                "chat_session_id": session_id,
                "request_id": request_id,
            },
            impersonate="safari15_3",
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") == 0:
            logger.info(f"[stop_deepseek_stream] 流式响应已停止: {request_id}")
            return True
        else:
            logger.warning(f"[stop_deepseek_stream] 停止失败: {data}")
            return False
            
    except Exception as e:
        logger.error(f"[stop_deepseek_stream] 停止流式响应异常: {e}")
        return False
