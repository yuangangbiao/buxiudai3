# -*- coding: utf-8 -*-
"""
调度中心共享数据库工具层 (v3.6.1)

抽取 _get_mysql_connection / _get_container_center / _dispatch_cache 等
共享基础设施到独立模块，避免 _core.py / schedule_routes.py / 未来新模块
重复定义导致的 NameError Bug。

使用方式:
    from ._db import _get_mysql_connection, _get_container_center
    from ._db import _dispatch_cache_get, _dispatch_cache_set
    from ._db import get_storage, send_wechat_message
"""
import os
import logging
import threading
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据库连接
# ═══════════════════════════════════════════════════════════════════════════════

def _get_mysql_connection():
    """获取 container_center MySQL 连接（走连接池）

    [v3.6.1 抽取] 原本分散在 _core.py:125 和 schedule_routes.py
    返回 pymysql 连接，调用方负责关闭

    Returns:
        pymysql.connections.Connection: 数据库连接对象
    """
    from storage.mysql_storage import MySQLStorage
    storage = MySQLStorage()
    return storage._pool.connection()


def _get_storage():
    """获取 MySQLStorage 实例（单例）

    Returns:
        MySQLStorage: 存储对象
    """
    from storage.mysql_storage import MySQLStorage
    if not hasattr(_get_storage, '_instance'):
        _get_storage._instance = MySQLStorage()
    return _get_storage._instance


def _get_container_center():
    """获取 ContainerCenter 实例（单例）

    Returns:
        ContainerCenter: 容器中心对象
    """
    if not hasattr(_get_container_center, '_instance'):
        try:
            from container_center_v5 import ContainerCenter
            _get_container_center._instance = ContainerCenter()
        except Exception as e:
            logger.warning(f'[容器中心] 实例化失败: {e}')
            _get_container_center._instance = None
    return _get_container_center._instance


# ═══════════════════════════════════════════════════════════════════════════════
# 派工缓存（dispatch_cache）
# ═══════════════════════════════════════════════════════════════════════════════

class _DispatchCache:
    """派工缓存（线程安全）

    替代 _core.py 中零散的 _dispatch_cache 全局变量
    提供：
    - get_data() / set_data()
    - update_data(updater_fn) - 原子操作
    - persist() - 持久化
    - TTL 缓存
    """

    def __init__(self, cache_file: str = None, default_ttl: int = 30):
        self._lock = threading.RLock()
        self._data = {}
        self._cache_ts = 0
        self._default_ttl = default_ttl
        self._cache_file = cache_file
        if cache_file is None:
            # 默认缓存文件路径
            self._cache_file = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'dispatch_cache.json'
            )

    def get_data(self, force_reload: bool = False) -> dict:
        """获取派工缓存数据"""
        with self._lock:
            import time
            now = time.time()
            if force_reload or (now - self._cache_ts) > self._default_ttl:
                self._load_from_file()
                self._cache_ts = now
            return self._data

    def set_data(self, data: dict):
        """设置派工缓存数据"""
        with self._lock:
            self._data = data
            self._cache_ts = __import__('time').time()
            self.persist()

    def update_data(self, updater_fn) -> bool:
        """原子更新派工缓存

        Args:
            updater_fn: 接收 data dict 的修改函数
        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            try:
                if not self._data:
                    self._load_from_file()
                updater_fn(self._data)
                self._cache_ts = __import__('time').time()
                self.persist()
                return True
            except Exception as e:
                logger.exception(f'[派工缓存] 更新失败: {e}')
                return False

    def _load_from_file(self):
        """从文件加载缓存"""
        try:
            if os.path.exists(self._cache_file):
                import json
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = {}
        except Exception as e:
            logger.warning(f'[派工缓存] 加载失败: {e}')
            self._data = {}

    def persist(self):
        """持久化到文件"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            import json
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f'[派工缓存] 持久化失败: {e}')


_dispatch_cache = _DispatchCache()


def get_dispatch_cache() -> _DispatchCache:
    """获取派工缓存实例"""
    return _dispatch_cache


# ═══════════════════════════════════════════════════════════════════════════════
# SSOT 缓存（统一订单状态缓存，v3.6.1）
# ═══════════════════════════════════════════════════════════════════════════════

_SSOT_CACHE = {}
_SSOT_CACHE_TS = {}
_SSOT_CACHE_LOCK = threading.RLock()
SSOT_CACHE_TTL = 10  # 秒
SSOT_CACHE_MAX = 100  # 最大缓存项数


def _ssot_cache_get(key: str) -> Optional[Any]:
    """从 SSOT 缓存获取"""
    import time
    with _SSOT_CACHE_LOCK:
        ts = _SSOT_CACHE_TS.get(key, 0)
        if time.time() - ts < SSOT_CACHE_TTL:
            return _SSOT_CACHE.get(key)
        return None


def _ssot_cache_set(key: str, value: Any, ttl: int = SSOT_CACHE_TTL):
    """设置 SSOT 缓存"""
    import time
    with _SSOT_CACHE_LOCK:
        _SSOT_CACHE[key] = value
        _SSOT_CACHE_TS[key] = time.time()
        # 超过最大项数时清理过期
        if len(_SSOT_CACHE) > SSOT_CACHE_MAX:
            now = time.time()
            expired = [k for k, t in _SSOT_CACHE_TS.items() if now - t >= ttl]
            for k in expired:
                _SSOT_CACHE.pop(k, None)
                _SSOT_CACHE_TS.pop(k, None)


def _ssot_cache_clear():
    """清空 SSOT 缓存"""
    with _SSOT_CACHE_LOCK:
        _SSOT_CACHE.clear()
        _SSOT_CACHE_TS.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 容器中心代理（统一封装 v3.6.1）
# ═══════════════════════════════════════════════════════════════════════════════

def _proxy_to_container_ssot(path: str, retries: int = 2, timeout: int = 5):
    """统一代理到容器中心 SSOT 端点

    Args:
        path: 容器中心路径，如 /api/orders/full-status/ORD001
        retries: 重试次数
        timeout: 超时秒数

    Returns:
        dict: 容器中心返回的 JSON 数据
    """
    import requests as _req
    from core.config import CONTAINER_CENTER_URL
    url = f'{CONTAINER_CENTER_URL}{path}'

    # 先查缓存
    cache_key = f'ssot:{url}'
    cached = _ssot_cache_get(cache_key)
    if cached is not None:
        return cached

    # 重试
    result = None
    for attempt in range(retries):
        try:
            resp = _req.get(url, timeout=timeout)
            if resp.status_code == 200:
                result = resp.json()
                break
            logger.error(f'容器中心返回非200: {url} -> {resp.status_code} {resp.text[:200]}')
            result = {'code': resp.status_code, 'message': f'容器中心返回 {resp.status_code}: {resp.text[:100]}'}
        except _req.exceptions.Timeout:
            logger.error(f'容器中心超时(尝试{attempt+1}/{retries}): {url}')
            result = {'code': 504, 'message': '容器中心响应超时'}
        except _req.exceptions.ConnectionError:
            logger.error(f'容器中心连接失败(尝试{attempt+1}/{retries}): {url}')
            result = {'code': 503, 'message': '容器中心连接失败（端口可能未启动）'}
        except Exception as e:
            logger.exception(f'代理到容器中心异常: {url}')
            result = {'code': 503, 'message': f'容器中心不可用: {str(e)}'}
            break
        if attempt < retries - 1:
            import time
            time.sleep(0.5)

    if result and result.get('code') == 0:
        _ssot_cache_set(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 兼容性别名（保持向后兼容）
# ═══════════════════════════════════════════════════════════════════════════════

# 旧代码可能用 _dispatch_cache 这种全局变量名访问
# 通过 __getattr__ 模拟模块级变量
_old_dispatch_cache = _dispatch_cache


def __getattr__(name):
    """兼容旧代码中的 _dispatch_cache 全局变量访问"""
    if name == '_dispatch_cache':
        return _old_dispatch_cache
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')