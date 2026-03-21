from curl_cffi import requests
from fastapi import Request, HTTPException
from utils.logger import logger
from auth.token import get_auth_headers

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_CREATE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/create"
DEEPSEEK_DELETE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/delete"


def create_session(request: Request) -> str:
    """
    创建 DeepSeek 会话
    :param request: FastAPI Request 对象
    :return: 会话 ID
    """
    try:
        headers = get_auth_headers(request)
        resp = requests.post(
            DEEPSEEK_CREATE_SESSION_URL,
            headers=headers,
            json={},
            impersonate="safari15_3",
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            logger.error(f"[create_session] 创建会话失败: {data}")
            return None
        
        session_id = data["data"]["biz_data"]["id"]
        logger.info(f"[create_session] 会话创建成功: {session_id}")
        
        return session_id
        
    except Exception as e:
        logger.error(f"[create_session] 创建会话异常: {e}")
        return None


def delete_deepseek_session(token: str, session_id: str) -> bool:
    """
    删除 DeepSeek 会话
    :param token: DeepSeek token
    :param session_id: 会话 ID
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
            DEEPSEEK_DELETE_SESSION_URL,
            headers=headers,
            json={"chat_session_id": session_id},
            impersonate="safari15_3",
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") == 0:
            logger.info(f"[delete_deepseek_session] 会话删除成功: {session_id}")
            return True
        else:
            logger.warning(f"[delete_deepseek_session] 会话删除失败: {data}")
            return False
            
    except Exception as e:
        logger.error(f"[delete_deepseek_session] 删除会话异常: {e}")
        return False
