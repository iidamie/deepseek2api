import struct
import ctypes
from curl_cffi import requests
from fastapi import Request
from utils.logger import logger
from auth.token import get_auth_headers

# 常量
DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_POW_CHALLENGE_URL = f"https://{DEEPSEEK_HOST}/api/v0/chat/create_pow_challenge"
WASM_FILE = "sha3_wasm_bg.7b9ca65ddd.wasm"

# WASM 相关
try:
    from wasmtime import Store, Module, Linker
    WASM_AVAILABLE = True
except ImportError:
    logger.warning("[PoW] wasmtime 未安装，PoW 功能可能不可用")
    WASM_AVAILABLE = False


def compute_pow_answer(
    algorithm: str,
    challenge_str: str,
    salt: str,
    difficulty: int,
    expire_at: int,
    signature: str,
    target_path: str,
    wasm_path: str,
) -> int:
    """
    使用 WASM 模块计算 DeepSeekHash 答案（answer）。
    根据 JS 逻辑：
      - 拼接前缀： "{salt}_{expire_at}_"
      - 将 challenge 与前缀写入 wasm 内存后调用 wasm_solve 进行求解，
      - 从 wasm 内存中读取状态与求解结果，
      - 若状态非 0，则返回整数形式的答案，否则返回 None。
    """
    if not WASM_AVAILABLE:
        logger.error("[compute_pow_answer] wasmtime 不可用")
        return None
    
    if algorithm != "DeepSeekHashV1":
        raise ValueError(f"不支持的算法：{algorithm}")
    
    prefix = f"{salt}_{expire_at}_"
    
    # --- 加载 wasm 模块 ---
    store = Store()
    linker = Linker(store.engine)
    
    try:
        with open(wasm_path, "rb") as f:
            wasm_bytes = f.read()
    except Exception as e:
        raise RuntimeError(f"加载 wasm 文件失败: {wasm_path}, 错误: {e}")
    
    module = Module(store.engine, wasm_bytes)
    instance = linker.instantiate(store, module)
    exports = instance.exports(store)
    
    try:
        memory = exports["memory"]
        add_to_stack = exports["__wbindgen_add_to_stack_pointer"]
        alloc = exports["__wbindgen_export_0"]
        wasm_solve = exports["wasm_solve"]
    except KeyError as e:
        raise RuntimeError(f"缺少 wasm 导出函数: {e}")

    def write_memory(offset: int, data: bytes):
        size = len(data)
        base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
        ctypes.memmove(base_addr + offset, data, size)

    def read_memory(offset: int, size: int) -> bytes:
        base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
        return ctypes.string_at(base_addr + offset, size)

    def encode_string(text: str):
        data = text.encode("utf-8")
        length = len(data)
        ptr_val = alloc(store, length, 1)
        ptr = int(ptr_val.value) if hasattr(ptr_val, "value") else int(ptr_val)
        write_memory(ptr, data)
        return ptr, length

    # 1. 申请 16 字节栈空间
    retptr = add_to_stack(store, -16)
    # 2. 编码 challenge 与 prefix 到 wasm 内存中
    ptr_challenge, len_challenge = encode_string(challenge_str)
    ptr_prefix, len_prefix = encode_string(prefix)
    # 3. 调用 wasm_solve（注意：difficulty 以 float 形式传入）
    wasm_solve(
        store,
        retptr,
        ptr_challenge,
        len_challenge,
        ptr_prefix,
        len_prefix,
        float(difficulty),
    )
    # 4. 从 retptr 处读取 4 字节状态和 8 字节求解结果
    status_bytes = read_memory(retptr, 4)
    if len(status_bytes) != 4:
        add_to_stack(store, 16)
        raise RuntimeError("读取状态字节失败")
    status = struct.unpack("<i", status_bytes)[0]
    value_bytes = read_memory(retptr + 8, 8)
    if len(value_bytes) != 8:
        add_to_stack(store, 16)
        raise RuntimeError("读取结果字节失败")
    value = struct.unpack("<d", value_bytes)[0]
    # 5. 恢复栈指针
    add_to_stack(store, 16)
    
    if status == 0:
        return None
    return int(value)


def get_pow_response(request: Request, max_attempts=3):
    """
    获取 PoW 响应（带账号切换逻辑）
    :param request: FastAPI Request 对象
    :param max_attempts: 最大重试次数
    :return: PoW 响应字符串或 None
    """
    from auth.account import choose_new_account, release_account, login_deepseek_via_account
    
    attempts = 0
    
    while attempts < max_attempts:
        headers = get_auth_headers(request)
        
        try:
            resp = requests.post(
                DEEPSEEK_POW_CHALLENGE_URL,
                headers=headers,
                json={"target_path": "/api/v0/chat/completion"},
                timeout=30,
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
            
            challenge_data = data["data"]["biz_data"]["challenge"]
            challenge = challenge_data.get("challenge", "")
            difficulty = challenge_data.get("difficulty", 144000)
            salt = challenge_data.get("salt", "")
            algorithm = challenge_data.get("algorithm", "")
            signature = challenge_data.get("signature", "")
            target_path = challenge_data.get("target_path", "")
            expire_at = challenge_data.get("expire_at", 1680000000)
            
            if not challenge or not salt:
                logger.error("[get_pow_response] PoW 挑战数据不完整")
                return None
            
            # 计算 PoW 答案
            answer = compute_pow_answer(
                algorithm=algorithm,
                challenge_str=challenge,
                salt=salt,
                difficulty=difficulty,
                expire_at=expire_at,
                signature=signature,
                target_path=target_path,
                wasm_path=WASM_FILE,
            )
            
            if answer is None:
                logger.error("[get_pow_response] PoW 计算失败")
                return None
            
            logger.info(f"[get_pow_response] PoW 计算成功: answer={answer}")
            return str(answer)
            
        except Exception as e:
            logger.error(f"[get_pow_response] 异常: {e}")
            attempts += 1
            continue
    
    logger.error(f"[get_pow_response] 超过最大重试次数: {max_attempts}")
    return None
