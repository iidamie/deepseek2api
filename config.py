import json
import random
from utils.logger import logger

CONFIG_PATH = "config.json"


def load_config():
    """从 config.json 加载配置，出错则返回空 dict"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[load_config] 无法读取配置文件: {e}")
        return {}


def save_config(cfg):
    """将配置写回 config.json"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[save_config] 写入 config.json 失败: {e}")


def init_account_queue():
    """初始化时从配置加载账号"""
    global account_queue
    account_queue = CONFIG.get("accounts", [])[:]  # 深拷贝
    random.shuffle(account_queue)  # 初始随机排序
    logger.info(f"账号队列初始化完成: {len(account_queue)} 个账号")


def init_claude_api_key_queue():
    """Claude API keys由用户自己的token提供，这里初始化为空"""
    global claude_api_key_queue
    claude_api_key_queue = []
    logger.info("Claude API Key 队列初始化完成")


# 加载配置
CONFIG = load_config()

# 全局账号队列
account_queue = []  # 维护所有可用账号
claude_api_key_queue = []  # 维护所有可用的Claude API keys

# 初始化队列
init_account_queue()
init_claude_api_key_queue()
