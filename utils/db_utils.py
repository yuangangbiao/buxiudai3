# -*- coding: utf-8 -*-
"""
数据库连接工具模块 - 统一管理数据库连接

提供安全的数据库连接方式，避免硬编码密码
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_mysql_password() -> str:
    """
    获取MySQL密码，优先从环境变量读取

    Returns:
        MySQL密码字符串

    Raises:
        ValueError: 当密码为空时抛出
    """
    password = os.getenv('MYSQL_PASSWORD', '')
    if not password:
        raise ValueError("MYSQL_PASSWORD 环境变量未设置")
    return password


def get_db_config() -> Dict[str, Any]:
    """
    获取数据库配置

    Returns:
        包含数据库配置的字典
    """
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': get_mysql_password(),
        'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
        'charset': 'utf8mb4'
    }


def create_db_connection(database: Optional[str] = None, **kwargs):
    """
    创建数据库连接

    Args:
        database: 数据库名称，默认从环境变量读取
        **kwargs: 其他连接参数

    Returns:
        pymysql.connect 连接对象
    """
    from core.db import get_direct_connection

    config = get_db_config()
    if database:
        config['database'] = database

    config.update(kwargs)

    try:
        conn = get_direct_connection(**config)
        logger.debug(f"[DB] 连接数据库成功: {config['host']}/{config.get('database', 'unknown')}")
        return conn
    except Exception as e:
        logger.error(f"[DB] 连接数据库失败: {e}")
        raise


def create_remote_db_connection(host: str, port: int = 3306,
                                user: str = 'root',
                                database: Optional[str] = None,
                                password: Optional[str] = None,
                                **kwargs):
    """
    创建远程数据库连接

    Args:
        host: 数据库主机地址
        port: 端口号，默认3306
        user: 用户名，默认root
        database: 数据库名称
        password: 密码，默认从环境变量读取
        **kwargs: 其他连接参数

    Returns:
        pymysql.connect 连接对象
    """
    from core.db import get_direct_connection

    if not password:
        password = get_mysql_password()

    config = {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'charset': 'utf8mb4'
    }

    if database:
        config['database'] = database

    config.update(kwargs)

    try:
        conn = get_direct_connection(**config)
        logger.debug(f"[DB] 连接远程数据库成功: {host}:{port}")
        return conn
    except Exception as e:
        logger.error(f"[DB] 连接远程数据库失败: {host}:{port} - {e}")
        raise


def with_db_connection(func):
    """
    数据库连接装饰器

    用法:
        @with_db_connection
        def query_data(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders")
            return cursor.fetchall()
    """
    def wrapper(*args, **kwargs):
        conn = create_db_connection()
        try:
            result = func(conn, *args, **kwargs)
            return result
        finally:
            if conn:
                conn.close()
    return wrapper


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("数据库连接工具模块")
    print("=" * 60)

    try:
        config = get_db_config()
        print(f"\n[OK] 数据库配置获取成功")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  User: {config['user']}")
        print(f"  Database: {config['database']}")
        print(f"  Password: {'*' * len(config['password'])}")

        conn = create_db_connection()
        print(f"\n[OK] 数据库连接测试成功")
        conn.close()

    except ValueError as e:
        print(f"\n[ERROR] {e}")
        print("请设置 MYSQL_PASSWORD 环境变量")
    except Exception as e:
        print(f"\n[ERROR] {e}")

    print("\n" + "=" * 60)
