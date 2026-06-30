# -*- coding: utf-8 -*-
"""
测试配置中心 - 解决循环导入

所有 conftest.py / health.py / parallel.py 等核心模块都必须从此处导入配置。
严禁反向依赖 tests.conftest 或其他上层模块。
"""
import os
from pathlib import Path


# ==================== 服务地址 ====================
# 5 个核心服务的 URL 配置（从环境变量读取，提供默认值）
SERVICES = {
    'desktop_web': os.getenv('DESKTOP_WEB_URL', 'http://localhost:5001'),
    'container': os.getenv('CONTAINER_URL', 'http://localhost:5002'),
    'dispatch': os.getenv('DISPATCH_URL', 'http://localhost:5003'),
    'mobile': os.getenv('MOBILE_URL', 'http://localhost:5008'),
    'sync_bridge': os.getenv('SYNC_BRIDGE_URL', 'http://localhost:8008'),
}


# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': os.getenv('TEST_DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('TEST_DB_PORT', '3306')),
    'user': os.getenv('TEST_DB_USER', 'root'),
    'password': os.getenv('TEST_DB_PASSWORD', '123456'),
    'database': os.getenv('TEST_DB_NAME', 'steel_belt'),
    'charset': 'utf8mb4',
    'connect_timeout': int(os.getenv('TEST_DB_TIMEOUT', '10')),
}


# ==================== Redis 配置 ====================
REDIS_CONFIG = {
    'host': os.getenv('TEST_REDIS_HOST', '127.0.0.1'),
    'port': int(os.getenv('TEST_REDIS_PORT', '6379')),
    'db': int(os.getenv('TEST_REDIS_DB', '0')),
    'password': os.getenv('TEST_REDIS_PASSWORD', None),
}


# ==================== 路径配置 ====================
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = TESTS_ROOT / 'reports'
SCREENSHOTS_DIR = REPORTS_DIR / 'screenshots'
LOGS_DIR = REPORTS_DIR / 'logs'

# 确保目录存在
for _dir in (REPORTS_DIR, SCREENSHOTS_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ==================== 测试数据清理配置 ====================
# 测试数据识别 + 软删除白名单
TEST_DATA_TABLES = [
    'orders',          # 订单
    'order_logs',      # 订单日志
    'process_records', # 工序记录
    'production_orders',  # 生产单
    'data_packages',   # 数据包
    'quality_records', # 质检记录
    'material_records',  # 物料记录
    'material_requests',  # 物料申请
    'outsource_records',  # 外协记录
    'shipment_records',   # 发货记录
    'repair_records',     # 报修记录
]


# ==================== Worker 端口范围 ====================
WORKER_PORT_RANGE = (9100, 9999)


__all__ = [
    'SERVICES',
    'DB_CONFIG',
    'REDIS_CONFIG',
    'PROJECT_ROOT',
    'TESTS_ROOT',
    'REPORTS_DIR',
    'SCREENSHOTS_DIR',
    'LOGS_DIR',
    'TEST_DATA_TABLES',
    'WORKER_PORT_RANGE',
]
