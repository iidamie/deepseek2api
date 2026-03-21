from curl_cffi import requests
import threading
from fastapi import HTTPException
from utils.logger import logger
from config import CONFIG, account_queue, save_config

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_LOGIN_URL = f"https://{DEEPSEEK_HOST}/api/v0/users/login"
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 线程锁
account_lock = threading.Lock()


def get_account_identifier(account):
    """获取账号标识符（邮箱或手机号）"""
    return account.get("email") or account.get("phone", "unknown")


def login_deepseek_via_account(account):
    """使用账号登录 DeepSeek 并更新 token"""
    email = account.get("email")
    phone = account.get("phone")
    password = account.get("password")
    
    if not password:
        raise ValueError("账号缺少密码")
    
    payload = {
        "password": password,
        "device_id": "deepseek2api",
        "os": "android"
    }
    if email:
        payload["email"] = email
    elif phone:
        payload["phone"] = phone
    else:
        raise ValueError("账号缺少 email 或 phone")
    
    try:
        resp = requests.post(
            DEEPSEEK_LOGIN_URL,
            json=payload,
            headers=BASE_HEADERS,
            impersonate="safari15_3",
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            raise Exception(f"登录失败: {data.get('msg', 'Unknown error')}")
        
        token = data["data"]["biz_data"]["user"]["token"]
        account["token"] = token
        
        # 更新配置文件
        save_config(CONFIG)
        
        logger.info(f"[login_deepseek_via_account] 账号 {get_account_identifier(account)} 登录成功")
        return token
        
    except Exception as e:
        logger.error(f"[login_deepseek_via_account] 账号 {get_account_identifier(account)} 登录失败: {e}")
        raise


def choose_new_account():
    """从配置中选择一个可用账号"""
    with account_lock:
        accounts = CONFIG.get("accounts", [])
        if not accounts:
            return None
        
        # 如果队列为空，重新填充
        if not account_queue:
            account_queue.extend(accounts)
        
        # 从队列中取出一个账号
        if account_queue:
            return account_queue.pop(0)
        
        return None


def release_account(account):
    """释放账号，放回队列"""
    if account:
        with account_lock:
            account_queue.append(account)
        logger.info(f"[release_account] 账号 {get_account_identifier(account)} 已释放")


def choose_claude_api_key():
    """从配置中选择一个可用的Claude API key"""
    from config import claude_api_key_queue
    with account_lock:
        keys = CONFIG.get("keys", [])
        if not keys:
            return None
        
        # 如果队列为空，重新填充
        if not claude_api_key_queue:
            claude_api_key_queue.extend(keys)
        
        # 从队列中取出一个key
        if claude_api_key_queue:
            return claude_api_key_queue.pop(0)
        
        return None


def release_claude_api_key(api_key):
    """释放Claude API key - 现在无需操作"""
    pass
