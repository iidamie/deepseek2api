from fastapi import Request, HTTPException
from utils.logger import logger
from config import CONFIG
from auth.account import choose_new_account, login_deepseek_via_account, get_account_identifier

# 常量
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def determine_mode_and_token(request: Request):
    """
    判断调用模式：
    1. 配置模式：caller 的 key 在 config.keys 中 -> 使用配置的账号池
    2. 用户自带 token 模式：caller 的 key 不在 config.keys 中 -> 直接使用该 key 作为 DeepSeek token
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    caller_key = auth_header.replace("Bearer ", "", 1).strip()
    config_keys = CONFIG.get("keys", [])
    
    if caller_key in config_keys:
        # 配置模式
        request.state.use_config_token = True
        request.state.tried_accounts = []  # 初始化已尝试账号
        selected_account = choose_new_account()
        
        if not selected_account:
            raise HTTPException(
                status_code=429,
                detail="No accounts configured or all accounts are busy.",
            )
        
        if not selected_account.get("token", "").strip():
            try:
                login_deepseek_via_account(selected_account)
            except Exception as e:
                logger.error(
                    f"[determine_mode_and_token] 账号 {get_account_identifier(selected_account)} 登录失败：{e}"
                )
                raise HTTPException(status_code=500, detail="Account login failed.")
        
        request.state.deepseek_token = selected_account.get("token")
        request.state.account = selected_account
    else:
        # 用户自带 token 模式
        request.state.use_config_token = False
        request.state.deepseek_token = caller_key


def get_auth_headers(request: Request):
    """返回 DeepSeek 请求所需的公共请求头"""
    return {**BASE_HEADERS, "authorization": f"Bearer {request.state.deepseek_token}"}


def determine_claude_mode_and_token(request: Request):
    """
    Claude认证：沿用现有的OpenAI接口认证逻辑
    """
    determine_mode_and_token(request)
