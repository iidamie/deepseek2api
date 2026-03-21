import hashlib
import os
from curl_cffi import requests
from fastapi import Request, HTTPException
from utils.logger import logger
from auth.token import get_auth_headers

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_POW_CHALLENGE_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/create_pow_challenge"

# WASM 相关
try:
    from wasmtime import Store, Module, Instance, Func, FuncType, ValType
    WASM_AVAILABLE = True
except ImportError:
    logger.warning("[PoW] wasmtime 未安装，PoW 功能可能不可用")
    WASM_AVAILABLE = False

WASM_FILE = "sha3_wasm_bg.7b9ca65ddd.wasm"
WASM_INSTANCE = None
WASM_MEMORY = None


def init_wasm():
    """初始化 WASM 模块"""
    global WASM_INSTANCE, WASM_MEMORY
    
    if not WASM_AVAILABLE:
        return False
    
    if not os.path.exists(WASM_FILE):
        logger.error(f"[init_wasm] WASM 文件不存在: {WASM_FILE}")
        return False
    
    try:
        store = Store()
        module = Module.from_file(store.engine, WASM_FILE)
        
        # 定义导入函数
        def wbg_log(a: int, b: int):
            pass
        
        def wbg_error(a: int, b: int):
            pass
        
        log_func = Func(store, FuncType([ValType.i32(), ValType.i32()], []), wbg_log)
        error_func = Func(store, FuncType([ValType.i32(), ValType.i32()], []), wbg_error)
        
        # 创建实例
        instance = Instance(store, module, [log_func, error_func])
        
        # 获取内存
        memory = instance.exports(store)["memory"]
        
        WASM_INSTANCE = instance
        WASM_MEMORY = memory
        
        logger.info("[init_wasm] WASM 模块初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"[init_wasm] WASM 初始化失败: {e}")
        return False


def compute_pow_answer(challenge: str, difficulty: str, salt: str):
    """
    使用 WASM 计算 PoW 答案
    :param challenge: 挑战字符串
    :param difficulty: 难度（目标前缀，如 "0000"）
    :param salt: 盐值
    :return: nonce 或 None
    """
    if not WASM_AVAILABLE or WASM_INSTANCE is None:
        logger.error("[compute_pow_answer] WASM 不可用")
        return None
    
    try:
        store = Store()
        
        # 获取导出函数
        exports = WASM_INSTANCE.exports(store)
        hash_fn = exports["hash"]
        alloc_fn = exports["__wbindgen_malloc"]
        free_fn = exports["__wbindgen_free"]
        
        # 分配内存并写入数据
        challenge_bytes = challenge.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        
        challenge_ptr = alloc_fn(store, len(challenge_bytes), 1)
        salt_ptr = alloc_fn(store, len(salt_bytes), 1)
        
        memory = WASM_MEMORY.data_ptr(store)
        memory[challenge_ptr:challenge_ptr + len(challenge_bytes)] = challenge_bytes
        memory[salt_ptr:salt_ptr + len(salt_bytes)] = salt_bytes
        
        # 尝试不同的 nonce
        max_attempts = 1000000
        for nonce in range(max_attempts):
            nonce_str = str(nonce)
            nonce_bytes = nonce_str.encode("utf-8")
            nonce_ptr = alloc_fn(store, len(nonce_bytes), 1)
            memory[nonce_ptr:nonce_ptr + len(nonce_bytes)] = nonce_bytes
            
            # 调用 hash 函数
            result_ptr = hash_fn(
                store,
                challenge_ptr, len(challenge_bytes),
                nonce_ptr, len(nonce_bytes),
                salt_ptr, len(salt_bytes)
            )
            
            # 读取结果
            result_len = int.from_bytes(memory[result_ptr:result_ptr + 4], "little")
            result_data_ptr = int.from_bytes(memory[result_ptr + 4:result_ptr + 8], "little")
            result_hash = memory[result_data_ptr:result_data_ptr + result_len].decode("utf-8")
            
            # 释放内存
            free_fn(store, nonce_ptr, len(nonce_bytes), 1)
            free_fn(store, result_data_ptr, result_len, 1)
            
            # 检查是否满足难度要求
            if result_hash.startswith(difficulty):
                logger.info(f"[compute_pow_answer] 找到答案: nonce={nonce}, hash={result_hash}")
                free_fn(store, challenge_ptr, len(challenge_bytes), 1)
                free_fn(store, salt_ptr, len(salt_bytes), 1)
                return nonce
        
        logger.error(f"[compute_pow_answer] 超过最大尝试次数: {max_attempts}")
        free_fn(store, challenge_ptr, len(challenge_bytes), 1)
        free_fn(store, salt_ptr, len(salt_bytes), 1)
        return None
        
    except Exception as e:
        logger.error(f"[compute_pow_answer] 计算失败: {e}")
        return None


def solve_pow_challenge(challenge: str, difficulty: str, salt: str):
    """
    解决 PoW 挑战（简化版，使用纯 Python）
    :param challenge: 挑战字符串
    :param difficulty: 难度（目标前缀，如 "0000"）
    :param salt: 盐值
    :return: nonce 或 None
    """
    # 如果 WASM 可用，优先使用 WASM
    if WASM_AVAILABLE and WASM_INSTANCE is not None:
        return compute_pow_answer(challenge, difficulty, salt)
    
    # 否则使用纯 Python 实现
    logger.info("[solve_pow_challenge] 使用纯 Python 实现")
    max_attempts = 1000000
    
    for nonce in range(max_attempts):
        nonce_str = str(nonce)
        combined = challenge + nonce_str + salt
        hash_result = hashlib.sha256(combined.encode()).hexdigest()
        
        if hash_result.startswith(difficulty):
            logger.info(f"[solve_pow_challenge] 找到答案: nonce={nonce}, hash={hash_result}")
            return nonce
    
    logger.error(f"[solve_pow_challenge] 超过最大尝试次数: {max_attempts}")
    return None


def get_pow_response(request: Request):
    """
    获取 PoW 响应（带账号切换逻辑）
    :param request: FastAPI Request 对象
    :return: PoW 响应字符串或 None
    """
    from auth.account import choose_new_account, release_account, login_deepseek_via_account
    
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            token = getattr(request.state, "deepseek_token", "")
            if not token:
                logger.error("[get_pow_response] 缺少 deepseek_token")
                return None
            
            headers = get_auth_headers(request)
            
            # 请求 PoW 挑战
            resp = requests.post(
                DEEPSEEK_POW_CHALLENGE_URL,
                headers=headers,
                json={},
                impersonate="safari15_3",
            )
            
            if resp.status_code != 200:
                logger.warning(f"[get_pow_response] 获取 PoW 挑战失败: {resp.status_code}")
                
                # 如果是配置模式，尝试切换账号
                if hasattr(request.state, "use_config_token") and request.state.use_config_token:
                    old_account = getattr(request.state, "account", None)
                    if old_account:
                        release_account(old_account)
                    
                    # 选择新账号
                    new_account = choose_new_account()
                    if not new_account:
                        logger.error("[get_pow_response] 无可用账号")
                        return None
                    
                    # 登录新账号
                    new_token = login_deepseek_via_account(new_account)
                    if not new_token:
                        logger.error("[get_pow_response] 新账号登录失败")
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
                logger.error(f"[get_pow_response] PoW 挑战返回错误: {data.get('msg')}")
                return None
            
            challenge_data = data.get("data", {})
            challenge = challenge_data.get("challenge", "")
            difficulty = challenge_data.get("difficulty", "0000")
            salt = challenge_data.get("salt", "")
            
            if not challenge or not salt:
                logger.error("[get_pow_response] PoW 挑战数据不完整")
                return None
            
            # 解决 PoW 挑战
            nonce = solve_pow_challenge(challenge, difficulty, salt)
            if nonce is None:
                logger.error("[get_pow_response] PoW 计算失败")
                return None
            
            # 构造响应
            pow_response = f"{challenge}:{nonce}:{salt}"
            return pow_response
            
        except Exception as e:
            logger.error(f"[get_pow_response] 异常: {e}")
            attempts += 1
            continue
    
    logger.error(f"[get_pow_response] 超过最大重试次数: {max_attempts}")
    return None


# 初始化 WASM
init_wasm()
