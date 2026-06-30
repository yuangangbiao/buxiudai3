# -*- coding: utf-8 -*-
"""
统一连接池管理层（Phase 2 - BUG-P0-003 架构修复）

container_center 和 steel_belt 两个数据库，按 autocommit 模式各建一个池，
共 4 个池，消除 29 个 get_direct_connection() 调用方的连接泄漏。
"""
from __future__ import annotations

import threading, os, pymysql
from dbutils.pooled_db import PooledDB
from core.config import CONTAINER_MYSQL_CFG, MYSQL_CFG

_container_center_ac_pool: PooledDB | None = None
_container_center_noac_pool: PooledDB | None = None
_steel_belt_ac_pool: PooledDB | None = None
_steel_belt_noac_pool: PooledDB | None = None
_pools_lock = threading.Lock()


def _make_pymysql_cfg(base_cfg: dict) -> dict:
    return {
        'host': base_cfg.get('host', os.getenv('MYSQL_HOST', 'localhost')),
        'port': int(base_cfg.get('port', os.getenv('MYSQL_PORT', 3306))),
        'user': base_cfg.get('user', os.getenv('MYSQL_USER', 'root')),
        'password': base_cfg.get('password', os.getenv('MYSQL_PASSWORD', '')),
        'database': base_cfg.get('database', 'unknown'),
        'charset': base_cfg.get('charset', 'utf8mb4'),
        'connect_timeout': int(base_cfg.get('connect_timeout', 5)),
        'read_timeout': 30,
        'write_timeout': 30,
    }


def _get_container_center_ac_pool() -> PooledDB:
    global _container_center_ac_pool
    if _container_center_ac_pool is None:
        with _pools_lock:
            if _container_center_ac_pool is None:
                cfg = _make_pymysql_cfg(CONTAINER_MYSQL_CFG)
                cfg['autocommit'] = True
                _container_center_ac_pool = PooledDB(
                    creator=pymysql, maxconnections=20, mincached=3,
                    maxcached=10, blocking=True, ping=1, **cfg)
    return _container_center_ac_pool


def _get_container_center_noac_pool() -> PooledDB:
    global _container_center_noac_pool
    if _container_center_noac_pool is None:
        with _pools_lock:
            if _container_center_noac_pool is None:
                cfg = _make_pymysql_cfg(CONTAINER_MYSQL_CFG)
                cfg['autocommit'] = False
                _container_center_noac_pool = PooledDB(
                    creator=pymysql, maxconnections=20, mincached=3,
                    maxcached=10, blocking=True, ping=1, **cfg)
    return _container_center_noac_pool


def _get_steel_belt_ac_pool() -> PooledDB:
    global _steel_belt_ac_pool
    if _steel_belt_ac_pool is None:
        with _pools_lock:
            if _steel_belt_ac_pool is None:
                cfg = _make_pymysql_cfg(MYSQL_CFG)
                cfg['autocommit'] = True
                _steel_belt_ac_pool = PooledDB(
                    creator=pymysql, maxconnections=20, mincached=3,
                    maxcached=10, blocking=True, ping=1, **cfg)
    return _steel_belt_ac_pool


def _get_steel_belt_noac_pool() -> PooledDB:
    global _steel_belt_noac_pool
    if _steel_belt_noac_pool is None:
        with _pools_lock:
            if _steel_belt_noac_pool is None:
                cfg = _make_pymysql_cfg(MYSQL_CFG)
                cfg['autocommit'] = False
                _steel_belt_noac_pool = PooledDB(
                    creator=pymysql, maxconnections=20, mincached=3,
                    maxcached=10, blocking=True, ping=1, **cfg)
    return _steel_belt_noac_pool


def get_container_connection(autocommit: bool = True, connect_timeout: int = 5):
    if autocommit:
        return _get_container_center_ac_pool().connection(shareable=False)
    else:
        return _get_container_center_noac_pool().connection(shareable=False)


def get_steel_belt_connection(autocommit: bool = True, connect_timeout: int = 5):
    if autocommit:
        return _get_steel_belt_ac_pool().connection(shareable=False)
    else:
        return _get_steel_belt_noac_pool().connection(shareable=False)
