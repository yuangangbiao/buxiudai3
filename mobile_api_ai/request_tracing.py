# -*- coding: utf-8 -*-
"""
请求追踪中间件 - 全链路追踪

功能说明：
- 为每个HTTP请求生成唯一追踪ID
- 记录请求处理时间和性能指标
- 支持分布式追踪上下文传递
- 自动记录异常堆栈信息

使用方式：
    from request_tracing import TracingMiddleware, get_trace_id, add_trace_log

    # 在Flask应用中使用
    app = Flask(__name__)
    app.wsgi_app = TracingMiddleware(app.wsgi_app)

    # 获取当前请求的追踪ID
    trace_id = get_trace_id()

    # 添加追踪日志
    add_trace_log("订单创建完成", order_id=123)
"""
import os
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps
from contextvars import ContextVar

try:
    from flask import Flask, request, g, Response
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

logger = logging.getLogger(__name__)

TRACE_ID_HEADER = "X-Trace-ID"
TRACE_ID_CONTEXT: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
TRACE_LOGS_CONTEXT: ContextVar[List[Dict[str, Any]]] = ContextVar('trace_logs', default=None)


class TraceContext:
    """追踪上下文"""

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.status_code: Optional[int] = None
        self.method: Optional[str] = None
        self.path: Optional[str] = None
        self.remote_addr: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.error: Optional[str] = None
        self.logs: List[Dict[str, Any]] = []

    def finish(self, status_code: int = 200, error: Optional[str] = None):
        """结束追踪"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status_code = status_code
        if error:
            self.error = error

    def add_log(self, message: str, level: str = "info", **kwargs):
        """添加追踪日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level,
            "elapsed": time.time() - self.start_time,
            **kwargs
        }
        self.logs.append(log_entry)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": round(self.duration * 1000, 2) if self.duration else None,
            "remote_addr": self.remote_addr,
            "error": self.error,
            "log_count": len(self.logs)
        }


_trace_store: Dict[str, TraceContext] = {}
_trace_lock = threading.Lock()
_max_traces = 1000


def _cleanup_old_traces():
    """清理旧追踪记录"""
    global _trace_store
    if len(_trace_store) > _max_traces:
        with _trace_lock:
            sorted_traces = sorted(
                _trace_store.items(),
                key=lambda x: x[1].start_time
            )
            for trace_id, _ in sorted_traces[:len(sorted_traces) // 2]:
                del _trace_store[trace_id]


def store_trace(trace: TraceContext):
    """存储追踪上下文"""
    with _trace_lock:
        _trace_store[trace.trace_id] = trace
        _cleanup_old_traces()


def get_trace(trace_id: str) -> Optional[TraceContext]:
    """获取追踪上下文"""
    with _trace_lock:
        return _trace_store.get(trace_id)


class TracingMiddleware:
    """请求追踪中间件"""

    def __init__(self, wsgi_app, app_name: str = "app"):
        self.wsgi_app = wsgi_app
        self.app_name = app_name

    def __call__(self, environ, start_response):
        """处理请求"""
        trace_id = environ.get('HTTP_X_TRACE_ID') or str(uuid.uuid4())
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        remote_addr = environ.get('REMOTE_ADDR', 'unknown')
        user_agent = environ.get('HTTP_USER_AGENT', '')

        context = TraceContext(trace_id)
        context.method = method
        context.path = path
        context.remote_addr = remote_addr
        context.user_agent = user_agent

        TRACE_ID_CONTEXT.set(trace_id)
        TRACE_LOGS_CONTEXT.set(context.logs)

        environ['X-Trace-ID'] = trace_id
        environ['X-Trace-Start'] = context.start_time

        def custom_start_response(status, headers, exc_info=None):
            status_code = int(status.split()[0])
            context.finish(status_code)
            store_trace(context)

            headers.append((TRACE_ID_HEADER, trace_id))

            if context.duration and context.duration > 1.0:
                logger.warning(
                    f"[Trace] 慢请求: {method} {path} "
                    f"耗时 {context.duration:.2f}s trace_id={trace_id}"
                )

            return start_response(status, headers, exc_info)

        try:
            return self.wsgi_app(environ, custom_start_response)
        except Exception as e:
            context.finish(status_code=500, error=str(e))
            store_trace(context)
            logger.error(
                f"[Trace] 请求异常: {method} {path} "
                f"error={e} trace_id={trace_id}"
            )
            raise


def get_trace_id() -> Optional[str]:
    """
    获取当前请求的追踪ID

    返回值说明：
        Optional[str]: 当前请求的追踪ID，如果不在请求上下文中返回None
    """
    return TRACE_ID_CONTEXT.get()


def add_trace_log(message: str, level: str = "info", **kwargs):
    """
    添加追踪日志

    参数说明：
        message (str): 日志消息
        level (str): 日志级别（debug/info/warning/error）
        **kwargs: 额外的上下文数据

    使用示例：
        add_trace_log("订单创建成功", order_id=123, amount=1000)
    """
    trace_id = get_trace_id()
    logs = TRACE_LOGS_CONTEXT.get()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "level": level,
        **kwargs
    }

    if logs is not None:
        logs.append(log_entry)

    if level == "error":
        logger.error(f"[Trace:{trace_id}] {message}")
    elif level == "warning":
        logger.warning(f"[Trace:{trace_id}] {message}")
    elif level == "debug":
        logger.debug(f"[Trace:{trace_id}] {message}")
    else:
        logger.info(f"[Trace:{trace_id}] {message}")


def traced(span_name: Optional[str] = None):
    """
    函数追踪装饰器

    参数说明：
        span_name (str): 追踪跨度名称，默认使用函数名

    使用示例：
        @traced("order_creation")
        def create_order(data):
            # 函数逻辑
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__
            trace_id = get_trace_id()
            start_time = time.time()

            add_trace_log(f"{name} 开始", level="debug")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                add_trace_log(
                    f"{name} 完成",
                    level="debug",
                    duration_ms=round(duration * 1000, 2)
                )

                if duration > 0.5:
                    logger.warning(
                        f"[Trace:{trace_id}] 慢操作: {name} "
                        f"耗时 {duration:.2f}s"
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                add_trace_log(
                    f"{name} 异常",
                    level="error",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=round(duration * 1000, 2)
                )
                raise

        return wrapper
    return decorator


def get_trace_history(trace_id: str) -> Optional[Dict[str, Any]]:
    """
    获取追踪历史记录

    参数说明：
        trace_id (str): 追踪ID

    返回值说明：
        Optional[Dict]: 追踪详情，如果不存在返回None
    """
    trace = get_trace(trace_id)
    if trace:
        return trace.to_dict()
    return None


def list_recent_traces(limit: int = 10) -> List[Dict[str, Any]]:
    """
    列出最近的追踪记录

    参数说明：
        limit (int): 返回数量限制

    返回值说明：
        List[Dict]: 追踪记录列表
    """
    with _trace_lock:
        traces = sorted(
            _trace_store.values(),
            key=lambda x: x.start_time,
            reverse=True
        )[:limit]
        return [t.to_dict() for t in traces]


def init_tracing(app: Optional["Flask"] = None):
    """
    初始化追踪系统

    参数说明：
        app (Flask): Flask应用实例（可选）
    """
    if app and FLASK_AVAILABLE:
        app.wsgi_app = TracingMiddleware(app.wsgi_app)
        logger.info("[Tracing] 请求追踪中间件已初始化")

        @app.after_request
        def add_trace_header(response: Response):
            trace_id = get_trace_id()
            if trace_id:
                response.headers[TRACE_ID_HEADER] = trace_id
            return response

    logger.info("[Tracing] 追踪系统已初始化")
