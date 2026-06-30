"""并发安全与隔离执行"""
import os
import sys
import uuid
import socket
import threading
import time
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class WorkerContext:
    """Worker 隔离上下文 - 每个 pytest-xdist worker 一个"""
    
    def __init__(self):
        self.worker_id = self._get_worker_id()
        self.test_id_prefix = f"TEST_{self.worker_id}_"
        self.browser_port = self._allocate_port(9000, 9999)
        self.log_file = f"tests/reports/logs/worker_{self.worker_id}.log"
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def _get_worker_id(self) -> str:
        """获取 worker ID（pytest-xdist 会设置 PYTEST_XDIST_WORKER）"""
        return os.environ.get('PYTEST_XDIST_WORKER', 'master')
    
    def _allocate_port(self, min_p: int, max_p: int) -> int:
        """分配唯一端口 - 修复 P2-3: 使用真正的可用端口而不是 hash"""
        # 修复 P2-3: 使用 PortAllocator 真正分配可用端口
        from tests.core.parallel import PortAllocator
        try:
            return PortAllocator.allocate(min_p, max_p)
        except RuntimeError:
            # 端口耗尽，回退到 hash 模式
            base = int(self.worker_id.replace('gw', '0') if 'gw' in self.worker_id else '0')
            return min_p + (base * 10) % (max_p - min_p)
    
    def get_test_id(self) -> str:
        """生成测试 ID"""
        ts = int(time.time() * 1000)
        return f"{self.test_id_prefix}{ts}_{uuid.uuid4().hex[:6]}"


# 全局上下文
_context = None
_context_lock = threading.Lock()


def get_worker_context() -> WorkerContext:
    """获取当前 worker 上下文（单例）"""
    global _context
    if _context is None:
        with _context_lock:
            if _context is None:
                _context = WorkerContext()
    return _context


@contextmanager
def isolated_data_context(db, prefix: Optional[str] = None):
    """
    隔离数据上下文 - 测试自动用 prefix 隔离
    用法:
        with isolated_data_context(db) as ctx:
            order_no = ctx.make_test_order(...)
            # 测试代码
    """
    # 修复 P0-4: 使用绝对路径导入，避免路径解析错误
    from tests.core.db_pool import db as global_db
    from tests.fixtures.orders import make_test_order as _make_order
    from tests.fixtures.orders import cleanup_test_orders as _cleanup

    if not prefix:
        prefix = f"TEST_{get_worker_context().worker_id}_"

    class IsolatedContext:
        def __init__(self):
            self.prefix = prefix
            self.created_orders = []

        def make_test_order(self, **kwargs):
            # 用 prefix 隔离
            kwargs.setdefault('prefix', prefix.rstrip('_'))
            order_no = _make_order(**kwargs)
            self.created_orders.append(order_no)
            return order_no

        def cleanup(self):
            if self.created_orders:
                # 软删除本 context 创建的订单
                _cleanup(self.created_orders)

    ctx = IsolatedContext()
    try:
        yield ctx
    finally:
        ctx.cleanup()


class PortAllocator:
    """端口分配器 - 避免多 worker 端口冲突"""
    
    _allocated = set()
    _lock = threading.Lock()
    
    @classmethod
    def allocate(cls, min_port: int = 9100, max_port: int = 9999) -> int:
        """分配一个空闲端口"""
        with cls._lock:
            for port in range(min_port, max_port):
                if port in cls._allocated:
                    continue
                if cls._is_port_free(port):
                    cls._allocated.add(port)
                    return port
            raise RuntimeError("无可用端口")
    
    @classmethod
    def release(cls, port: int):
        with cls._lock:
            cls._allocated.discard(port)
    
    @classmethod
    def _is_port_free(cls, port: int) -> bool:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return False  # 端口已被占用
        except (socket.timeout, ConnectionRefusedError, OSError):
            return True


class TestMutex:
    """测试互斥锁 - 防止并发冲突"""
    
    _locks = {}
    _global_lock = threading.Lock()
    
    @classmethod
    def get(cls, name: str) -> threading.Lock:
        """获取命名锁"""
        with cls._global_lock:
            if name not in cls._locks:
                cls._locks[name] = threading.Lock()
            return cls._locks[name]
    
    @classmethod
    @contextmanager
    def acquire(cls, name: str, timeout: float = 30):
        """获取锁的上下文"""
        lock = cls.get(name)
        acquired = lock.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError(f"获取锁 {name} 超时")
        try:
            yield
        finally:
            lock.release()
