import json
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


# 加载配置
CONFIG = load_config()

# 全局账号队列
account_queue = []  # 维护所有可用账号
claude_api_key_queue = []  # 维护所有可用的Claude API keys
