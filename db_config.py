# -*- coding: utf-8 -*-
"""
数据库配置文件 - 独立管理数据库连接配置
所有敏感信息必须从环境变量读取，不提供硬编码默认值
"""
import os
import logging

logger = logging.getLogger(__name__)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"[DB] 已加载环境变量文件: {env_path}")
except ImportError:
    pass

def _get_required_env(key: str, default: str = None) -> str:
    """获取必需的环境变量，如果未设置则记录警告"""
    value = os.getenv(key, default or "")
    if not value:
        logger.warning(f"环境变量 {key} 未设置，请检查配置")
    return value

MYSQL_CONFIG = {
    "host": os.getenv('MYSQL_HOST', 'localhost'),
    "port": int(os.getenv('MYSQL_PORT', 3306)),
    "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
    "user": os.getenv('MYSQL_USER', 'root'),
    "password": os.getenv('MYSQL_PASSWORD', ''),
    "charset": "utf8mb4",
    "cursorclass": "dict"
}

INVENTORY_SYSTEM_CONFIG = {
    "enabled": True,
    "host": os.getenv('INVENTORY_HOST', 'localhost'),
    "port": int(os.getenv('INVENTORY_PORT', 8080)),
    "api_key": os.getenv('INVENTORY_API_KEY', ''),
    "timeout": int(os.getenv('INVENTORY_TIMEOUT', 10))
}
