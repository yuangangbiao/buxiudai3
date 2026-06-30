# -*- coding: utf-8 -*-
"""
不锈钢网带跟单系统 - 版本管理配置
"""

# 当前版本号
VERSION = "3.1.0"
BUILD_DATE = "2026-05-05"

# 升级包相关配置
UPGRADE_DIR = "升级包"
UPGRADE_FILES = [
    # 核心模型文件
    "models/production.py",
    "models/order.py",
    "models/database.py",
    "models/process_calc_rule.py",
    
    # 工具模块
    "utils/op_logger.py",
    
    # 常量配置
    "constants.py",
    "config.py",
    
    # 视图文件
    "views/production_view.py",
    "views/order_view.py",
]

# 升级包排除文件
EXCLUDE_FILES = [
    "__pycache__",
    ".pyc",
    ".pyo",
    ".log",
    ".bak",
]

# 数据库升级SQL脚本目录
DB_UPGRADE_DIR = "db_upgrades"
