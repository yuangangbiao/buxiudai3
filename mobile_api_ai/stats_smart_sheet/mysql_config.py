# -*- coding: utf-8 -*-
"""
MySQL 三库连接配置
- STEEL_BELT_CFG: 业务主库 (production_orders, process_sub_steps)
- CONTAINER_CENTER_CFG: 容器中心库 (process_records 完整字段, data_packages, report_queue)
- INVENTORY_CFG: 库存管理库 (products, inventory, inventory_transactions)

所有密码/用户名强制从环境变量读取，无任何默认值。
"""
import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv('.env', override=True)


def _require_env(key: str) -> str:
    """强制环境变量存在，无默认值（符合 jgs7 安全规范）"""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"环境变量 {key} 必须设置（无默认值）")
    return val


# 基础配置（host/port/user/password 共享）
def _base_cfg(user_env: str, password_env: str) -> dict:
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': _require_env(user_env),
        'password': _require_env(password_env),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'connect_timeout': 10,
        'autocommit': True,
    }


# 库 1: 业务主库 steel_belt
STEEL_BELT_CFG = {
    **_base_cfg('MYSQL_USER', 'MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
}

# 库 2: 容器中心库 container_center（可独立部署，独立账号）
CONTAINER_CENTER_CFG = {
    **_base_cfg('CONTAINER_MYSQL_USER', 'CONTAINER_MYSQL_PASSWORD'),
    'database': os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center'),
}

# 库 3: 库存管理库 inventory_db
INVENTORY_CFG = {
    **_base_cfg('INVENTORY_MYSQL_USER', 'INVENTORY_MYSQL_PASSWORD'),
    'database': os.getenv('INVENTORY_DB_NAME', ''),
}


# 池化连接（避免每次查询创建新连接）
_pools = {}


def get_pool(cfg_key: str):
    """获取连接池（懒加载）"""
    if cfg_key in _pools:
        return _pools[cfg_key]
    from dbutils.pooled_db import PooledDB
    cfg_map = {
        'steel_belt': STEEL_BELT_CFG,
        'container_center': CONTAINER_CENTER_CFG,
        'inventory': INVENTORY_CFG,
    }
    if cfg_key not in cfg_map:
        raise ValueError(f"未知数据库: {cfg_key}")
    cfg = cfg_map[cfg_key]
    pool = PooledDB(
        creator=pymysql,
        maxconnections=10, mincached=2, maxcached=5,
        blocking=True, ping=1,
        **cfg,
    )
    _pools[cfg_key] = pool
    return pool


def get_conn(cfg_key: str):
    """获取一个连接（用完记得 close）"""
    return get_pool(cfg_key).connection()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    for name in ('steel_belt', 'container_center', 'inventory'):
        try:
            conn = get_conn(name)
            with conn.cursor() as c:
                c.execute("SELECT 1 AS ok")
                result = c.fetchone()
            conn.close()
            logger.info(f"  ✅ {name}: {result}")
        except Exception:
            logger.exception(f"  ❌ {name}")
