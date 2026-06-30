# -*- coding: utf-8 -*-
"""数据库配置加载"""
import os

def _get_db_config():
    """从环境变量获取数据库配置"""
    return {
        "host": os.getenv('MYSQL_HOST', 'localhost'),
        "port": int(os.getenv('MYSQL_PORT', 3306)),
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
        "charset": "utf8mb4"
    }

try:
    from db_config import MYSQL_CONFIG
except ImportError:
    MYSQL_CONFIG = _get_db_config()
