# -*- coding: utf-8 -*-
"""
线程生命周期管理模块 - 优雅关闭与资源清理

功能说明：
- 追踪所有后台线程
- 提供优雅关闭机制
- 防止应用退出时线程被强制杀死

使用方式：
    from thread_lifecycle import ThreadManager, register_thread, shutdown_all

    # 注册线程
    register_thread(my_thread, name="worker", cleanup_func=cleanup_handler)

    # 应用关闭时调用
    shutdown_all(timeout=10)
"""
import os
import sys
import time
import atexit
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_thread_registry: Dict[str, Dict[str, Any]] = {}
_registry_lock = threading.Lock()
_shutdown_in_progress = False


class ThreadInfo:
    """线程信息"""

    def __init__(self, thread: threading.Thread, name: str, cleanup_func: Optional[Callable] = None):
        self.thread = thread
        self.name = name
        self.cleanup_func = cleanup_func
        self.start_time = time.time()
        self.stopped = False

    def __repr__(self):
        return f"<ThreadInfo {self.name} daemon={self.thread.daemon} alive={self.thread.is_alive()}>"


def register_thread(
    thread: threading.Thread,
    name: str,
    cleanup_func: Optional[Callable] = None,
    graceful_timeout: float = 5.0
) -> None:
    """
    注册后台线程

    参数说明：
        thread (threading.Thread): 要注册的线程对象
        name (str): 线程名称（唯一标识）
        cleanup_func (Callable): 清理函数，关闭前调用
        graceful_timeout (float): 优雅关闭超时时间（秒）
    """
    with _registry_lock:
        if name in _thread_registry:
            logger.warning(f"[ThreadLifecycle] 线程 {name} 已存在，将被覆盖")

        _thread_registry[name] = ThreadInfo(
            thread=thread,
            name=name,
            cleanup_func=cleanup_func
        )

        logger.info(f"[ThreadLifecycle] 注册线程: {name} (daemon={thread.daemon})")


def unregister_thread(name: str) -> bool:
    """
    注销线程

    参数说明：
        name (str): 线程名称

    返回值：
        bool: 是否成功注销
    """
    with _registry_lock:
        if name in _thread_registry:
            del _thread_registry[name]
            logger.info(f"[ThreadLifecycle] 注销线程: {name}")
            return True
        return False


def get_thread(name: str) -> Optional[ThreadInfo]:
    """获取线程信息"""
    with _registry_lock:
        return _thread_registry.get(name)


def list_threads() -> List[ThreadInfo]:
    """列出所有已注册的线程"""
    with _registry_lock:
        return list(_thread_registry.values())


def stop_thread(name: str, timeout: float = 5.0) -> bool:
    """
    停止指定线程

    参数说明：
        name (str): 线程名称
        timeout (float): 等待超时时间

    返回值：
        bool: 是否成功停止
    """
    thread_info = get_thread(name)
    if not thread_info:
        logger.warning(f"[ThreadLifecycle] 线程 {name} 不存在")
        return False

    if thread_info.stopped:
        logger.info(f"[ThreadLifecycle] 线程 {name} 已停止")
        return True

    logger.info(f"[ThreadLifecycle] 停止线程: {name}")

    if thread_info.cleanup_func:
        try:
            logger.info(f"[ThreadLifecycle] 调用清理函数: {name}")
            thread_info.cleanup_func()
        except Exception as e:
            logger.error(f"[ThreadLifecycle] 清理函数异常: {name}, error={e}")

    if thread_info.thread.is_alive():
        thread_info.thread.join(timeout=timeout)

        if thread_info.thread.is_alive():
            logger.warning(f"[ThreadLifecycle] 线程 {name} 未能在 {timeout}s 内停止")
            return False

    thread_info.stopped = True
    logger.info(f"[ThreadLifecycle] 线程 {name} 已停止")
    return True


def shutdown_all(timeout: float = 10.0, force: bool = False) -> Dict[str, bool]:
    """
    关闭所有已注册的线程

    参数说明：
        timeout (float): 单个线程等待超时时间
        force (bool): 是否强制杀死

    返回值：
        Dict[str, bool]: 每个线程的关闭结果
    """
    global _shutdown_in_progress

    if _shutdown_in_progress:
        logger.warning("[ThreadLifecycle] 关闭流程已在进行中")
        return {}

    _shutdown_in_progress = True
    logger.info(f"[ThreadLifecycle] 开始关闭所有线程 (timeout={timeout}s)")

    results = {}
    threads_to_stop = list_threads()

    for thread_info in threads_to_stop:
        name = thread_info.name
        success = stop_thread(name, timeout)
        results[name] = success

    success_count = sum(1 for v in results.values() if v)
    logger.info(f"[ThreadLifecycle] 关闭完成: {success_count}/{len(results)} 成功")

    return results


@contextmanager
def thread_context(name: str, cleanup_func: Optional[Callable] = None):
    """
    线程上下文管理器

    使用示例：
        with thread_context("worker", cleanup_func=cleanup_handler):
            # 线程运行中
            pass
        # 退出时自动清理
    """
    thread = threading.current_thread()
    register_thread(thread, name, cleanup_func)
    try:
        yield thread
    finally:
        unregister_thread(name)


class GracefulShutdownHandler:
    """优雅关闭处理器"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._registered = False

    def _handle_shutdown(self, signum=None, frame=None):
        """处理关闭信号"""
        sig_name = signal_name(signum) if signum else "unknown"
        logger.info(f"[ThreadLifecycle] 收到关闭信号: {sig_name}")

        shutdown_all(timeout=self.timeout)

        logger.info("[ThreadLifecycle] 关闭处理完成")

    def register(self):
        """注册关闭处理器"""
        if self._registered:
            return

        try:
            import signal

            signal.signal(signal.SIGTERM, self._handle_shutdown)
            signal.signal(signal.SIGINT, self._handle_shutdown)

            atexit.register(shutdown_all, timeout=self.timeout)

            self._registered = True
            logger.info("[ThreadLifecycle] 关闭处理器已注册")

        except (ImportError, ValueError) as e:
            logger.warning(f"[ThreadLifecycle] 无法注册信号处理器: {e}")

    def unregister(self):
        """注销关闭处理器"""
        if not self._registered:
            return

        try:
            import signal
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            atexit.unregister(shutdown_all)
            self._registered = False
            logger.info("[ThreadLifecycle] 关闭处理器已注销")
        except Exception as e:
            logger.warning(f"[ThreadLifecycle] 注销信号处理器失败: {e}")


def signal_name(signum: Optional[int]) -> str:
    """获取信号名称"""
    try:
        import signal
        return signal.Signals(signum).name
    except (ValueError, ImportError):
        return f"SIG{signum}"


_shutdown_handler: Optional[GracefulShutdownHandler] = None


def init_graceful_shutdown(timeout: float = 10.0) -> GracefulShutdownHandler:
    """
    初始化优雅关闭机制

    参数说明：
        timeout (float): 关闭超时时间

    返回值：
        GracefulShutdownHandler: 关闭处理器实例
    """
    global _shutdown_handler

    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(timeout=timeout)
        _shutdown_handler.register()

    return _shutdown_handler


def is_shutting_down() -> bool:
    """检查是否正在关闭"""
    return _shutdown_in_progress


def create_daemon_thread(
    target: Callable,
    name: str,
    args: tuple = (),
    kwargs: dict = None,
    cleanup_func: Optional[Callable] = None,
    graceful_timeout: float = 5.0
) -> threading.Thread:
    """
    创建受管理的守护线程

    参数说明：
        target (Callable): 线程目标函数
        name (str): 线程名称
        args (tuple): 目标函数参数
        kwargs (dict): 目标函数关键字参数
        cleanup_func (Callable): 清理函数
        graceful_timeout (float): 优雅关闭超时

    返回值：
        threading.Thread: 创建的线程对象
    """
    kwargs = kwargs or {}

    def wrapper():
        try:
            target(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ThreadLifecycle] 线程 {name} 异常: {e}")
            raise

    thread = threading.Thread(target=wrapper, name=name, daemon=True)
    register_thread(thread, name, cleanup_func, graceful_timeout)
    thread.start()

    logger.info(f"[ThreadLifecycle] 启动守护线程: {name}")
    return thread
