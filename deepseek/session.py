from curl_cffi import requests
from fastapi import Request, HTTPException
from utils.logger import logger
from auth.token import get_auth_headers

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_CREATE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/create"
DEEPSEEK_DELETE_SESSION_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat_session/delete"


def create_session(request: Request):
    """
    创建 DeepSeek 会话（带账号切换逻辑）
    :param request: FastAPI Request 对象
    :return: session_id 或 None
    """
    from auth.account import choose_new_account, release_account, login_deepseek_via_account
    
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            token = getattr(request.state, "deepseek_token", "")
            if not token:
                logger.error("[create_session] 缺少 deepseek_token")
                return None
            
            headers = get_auth_headers(request)
            
            resp = requests.post(
                DEEPSEEK_CREATE_SESSION_URL,
                headers=headers,
                json={},
                impersonate="safari15_3",
            )
            
            if resp.status_code != 200:
                logger.warning(f"[create_session] 创建会话失败: {resp.status_code}")
                
                # 如果是配置模式，尝试切换账号
                if hasattr(request.state, "use_config_token") and request.state.use_config_token:
                    old_account = getattr(request.state, "account", None)
                    if old_account:
                        release_account(old_account)
                    
                    # 选择新账号
                    new_account = choose_new_account()
                    if not new_account:
                        logger.error("[create_session] 无可用账号")
                        return None
                    
                    # 登录新账号
                    new_token = login_deepseek_via_account(new_account)
                    if not new_token:
                        logger.error("[create_session] 新账号登录失败")
                        return None
                    
                    # 更新 request.state
                    request.state.account = new_account
                    request.state.deepseek_token = new_token
                    
                    attempts += 1
                    continue
                else:
                    return None
            
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"[create_session] 创建会话返回错误: {data.get('msg')}")
                return None
            
            session_id = data["data"]["biz_data"]["id"]
            if not session_id:
                logger.error("[create_session] 响应中缺少 session_id")
                return None
            
            logger.info(f"[create_session] 会话创建成功: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"[create_session] 创建会话异常: {e}")
            attempts += 1
            continue
    
    logger.error(f"[create_session] 超过最大重试次数: {max_attempts}")
    return None


def delete_deepseek_session(token: str, session_id: str):
    """
    删除 DeepSeek 会话
    :param token: DeepSeek token
    :param session_id: 会话 ID
    :return: 是否成功
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        resp = requests.post(
            DEEPSEEK_DELETE_SESSION_URL,
            headers=headers,
            json={"chat_session_id": session_id},
            impersonate="safari15_3",
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0:
                logger.info(f"[delete_deepseek_session] 会话删除成功: {session_id}")
                return True
            else:
                logger.warning(f"[delete_deepseek_session] 删除失败: {data.get('msg')}")
                return False
        else:
            logger.warning(f"[delete_deepseek_session] 删除失败: {resp.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"[delete_deepseek_session] 删除会话异常: {e}")
        return False
