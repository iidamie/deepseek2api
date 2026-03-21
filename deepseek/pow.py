import hashlib
from curl_cffi import requests
from fastapi import Request, HTTPException
from utils.logger import logger
from auth.token import get_auth_headers

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_CREATE_POW_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/create_pow_challenge"
WASM_PATH = "sha3_wasm_bg.7b9ca65ddd.wasm"

# 加载 WASM 文件
try:
    with open(WASM_PATH, "rb") as f:
        WASM_BYTES = f.read()
except Exception as e:
    logger.warning(f"[load_wasm] 无法加载 WASM 文件: {e}")
    WASM_BYTES = None


def solve_pow_challenge(challenge: str, target_path: str) -> str:
    """
    解决 PoW 挑战
    :param challenge: 挑战字符串
    :param target_path: 目标路径
    :return: PoW 响应字符串
    """
    if not WASM_BYTES:
        raise Exception("WASM 文件未加载")
    
    nonce = 0
    prefix = f"{challenge}{target_path}"
    
    while True:
        candidate = f"{prefix}{nonce}"
        hash_result = hashlib.sha3_256(candidate.encode()).hexdigest()
        
        if hash_result.startswith("0000"):
            return f"{challenge}:{nonce}"
        
        nonce += 1
        
        if nonce > 1000000:
            raise Exception("PoW 计算超时")


def get_pow_response(request: Request, target_path: str = "/api/v0/chat/completion") -> str:
    """
    获取 PoW 响应
    :param request: FastAPI Request 对象
    :param target_path: 目标路径
    :return: PoW 响应字符串
    """
    try:
        headers = get_auth_headers(request)
        resp = requests.post(
            DEEPSEEK_CREATE_POW_URL,
            headers=headers,
            json={"target_path": target_path},
            impersonate="safari15_3",
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            logger.error(f"[get_pow_response] PoW 请求失败: {data}")
            return None
        
        challenge = data["data"]["biz_data"]["challenge"]
        pow_response = solve_pow_challenge(challenge, target_path)
        
        return pow_response
        
    except Exception as e:
        logger.error(f"[get_pow_response] 获取 PoW 失败: {e}")
        return None
