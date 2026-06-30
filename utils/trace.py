# -*- coding: utf-8 -*-
"""
[架构审计 P0-2 实施 2026-06-13] 统一 trace_id 追踪

功能：
1. 在请求入口生成或继承 trace_id
2. 提供跨函数、跨服务的统一追踪 ID
3. 支持透传到下游 HTTP 调用
4. 提供上下文感知的日志记录器

用法：

```python
from utils.trace import init_trace_middleware, get_trace_id, trace_headers, traced_request

# 1. 在 Flask 入口注册
init_trace_middleware(app)

# 2. 业务函数中获取
logger.info(f'[{get_trace_id()}] 处理订单 {order_no}')

# 3. 跨服务调用透传
resp = traced_request('GET', f'{OTHER_SERVICE}/api/...')

# 4. 上下文日志（自动携带 trace_id）
from utils.trace import traced_logger
log = traced_logger(__name__)
log.info('开始处理')
# 输出: [trace_id=abc-123] 开始处理
```
"""
import uuid
import logging
import threading
from typing import Optional

try:
    from flask import g, request, has_request_context
    _FLASK_AVAILABLE = True
except ImportError:
    _FLASK_AVAILABLE = False


# ============= 上下文存储 =============
# 使用 threading.local 兼容非 Flask 场景
_context = threading.local()


def _get_context() -> dict:
    """获取当前线程的 trace 上下文"""
    if not hasattr(_context, 'data'):
        _context.data = {'trace_id': 'no-trace', 'span_id': 0}
    return _context.data


def get_trace_id() -> str:
    """获取当前 trace_id"""
    if _FLASK_AVAILABLE and has_request_context():
        return getattr(g, 'trace_id', None) or _get_context()['trace_id']
    return _get_context()['trace_id']


def get_span_id() -> int:
    """获取当前 span_id（用于分布式追踪）"""
    if _FLASK_AVAILABLE and has_request_context():
        return getattr(g, 'span_id', None) or 0
    return _get_context().get('span_id', 0)


def set_trace_id(trace_id: str):
    """手动设置 trace_id（用于内部调用）"""
    _get_context()['trace_id'] = trace_id


def new_span() -> int:
    """开启新的 span（自增 span_id）"""
    ctx = _get_context()
    ctx['span_id'] = ctx.get('span_id', 0) + 1
    return ctx['span_id']


# ============= Flask 中间件 =============
def init_trace_middleware(app):
    """注册 Flask trace_id 中间件

    [P0-2 实施 2026-06-13] before_request + after_request
    """
    if not _FLASK_AVAILABLE:
        raise RuntimeError('Flask 未安装，无法注册 trace 中间件')

    @app.before_request
    def _trace_before():
        # 优先从请求头获取（链路追踪关键）
        incoming = request.headers.get('X-Trace-Id')
        if incoming:
            g.trace_id = incoming
        else:
            g.trace_id = str(uuid.uuid4())
        g.span_id = 0
        g.start_time = __import__('time').time()

    @app.after_request
    def _trace_after(response):
        # [N7 修复 2026-06-13] 避免覆盖已有的 X-Trace-Id
        # 5 个代理透传 trace 时，after_request 会再设置一次（重复）
        # 现在只在该响应头未设置时才设置
        if hasattr(g, 'trace_id') and 'X-Trace-Id' not in response.headers:
            response.headers['X-Trace-Id'] = g.trace_id
        return response


# ============= 跨服务调用 =============
def trace_headers(extra: Optional[dict] = None) -> dict:
    """生成携带 trace_id 的请求头（用于透传到下游）

    用法:
    ```python
    resp = requests.get(url, headers=trace_headers({'Authorization': token}))
    ```
    """
    headers = {'X-Trace-Id': get_trace_id()}
    if extra:
        headers.update(extra)
    return headers


def traced_request(method: str, url: str, **kwargs):
    """自动携带 trace_id 的 HTTP 请求

    用法:
    ```python
    resp = traced_request('GET', f'{CC_URL}/api/orders/{order_no}', timeout=3)
    resp = traced_request('POST', f'{CC_URL}/api/process_sub_step', json=data, timeout=5)
    ```
    """
    import requests
    headers = trace_headers(kwargs.pop('headers', None))
    new_span()
    return requests.request(method, url, headers=headers, **kwargs)


# ============= 上下文日志 =============
class TraceFilter(logging.Filter):
    """自动注入 trace_id 到日志记录"""

    def filter(self, record):
        record.trace_id = get_trace_id()
        record.span_id = get_span_id()
        return True


def traced_logger(name: str) -> logging.Logger:
    """获取自动携带 trace_id 的 logger

    用法:
    ```python
    from utils.trace import traced_logger
    log = traced_logger(__name__)
    log.info('开始处理订单')
    # 输出: [trace_id=abc-123] [span=1] 开始处理订单
    ```
    """
    logger = logging.getLogger(name)
    # 避免重复添加 filter
    if not any(isinstance(f, TraceFilter) for f in logger.filters):
        logger.addFilter(TraceFilter())
    return logger


# ============= 上下文管理器 =============
class trace_span:
    """手动管理 span（用于复杂业务流）

    用法:
    ```python
    with trace_span('validate_order'):
        validate(order_no)
    # 自动记录进入/退出 + trace_id
    ```
    """
    def __init__(self, name: str):
        self.name = name
        self.span_id = 0
        self.start_time = 0

    def __enter__(self):
        import time
        self.span_id = new_span()
        self.start_time = time.time()
        log = traced_logger('trace')
        log.info(f'进入 span [{self.name}]')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed_ms = (time.time() - self.start_time) * 1000
        log = traced_logger('trace')
        if exc_type:
            log.error(f'span [{self.name}] 异常退出: {exc_val} 耗时={elapsed_ms:.2f}ms')
        else:
            log.info(f'span [{self.name}] 完成 耗时={elapsed_ms:.2f}ms')
        return False


# ============= 便捷函数 =============
def with_trace(func):
    """装饰器：自动设置 trace_id 上下文

    用法:
    ```python
    @with_trace
    def process_order(order_no):
        # 内部所有日志自动携带 trace_id
        log = traced_logger(__name__)
        log.info('处理中')
    ```
    """
    def wrapper(*args, **kwargs):
        if not get_trace_id() or get_trace_id() == 'no-trace':
            set_trace_id(str(uuid.uuid4()))
        return func(*args, **kwargs)
    return wrapper


__all__ = [
    'init_trace_middleware',
    'get_trace_id',
    'get_span_id',
    'set_trace_id',
    'new_span',
    'trace_headers',
    'traced_request',
    'TraceFilter',
    'traced_logger',
    'trace_span',
    'with_trace',
]
