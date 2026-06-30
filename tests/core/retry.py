"""智能重试机制"""
import time
import functools
import logging
from typing import Callable, Tuple, Type, Optional

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """重试耗尽异常"""
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


def smart_retry(
    max_attempts: int = 3,
    backoff: str = 'exponential',  # exponential / linear / fixed
    initial_delay: float = 0.5,
    max_delay: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    blacklist_modules: Tuple[str, ...] = (),  # P0 模块失败不重试
):
    """
    智能重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        backoff: 退避策略
        initial_delay: 初始延迟(秒)
        max_delay: 最大延迟
        exceptions: 触发重试的异常类型
        on_retry: 重试时的回调
        blacklist_modules: 黑名单模块（这些模块失败不重试）
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 检查是否在黑名单
            test_name = func.__name__
            if any(bl in test_name.lower() for bl in blacklist_modules):
                return func(*args, **kwargs)
            
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt >= max_attempts:
                        break
                    
                    # 计算延迟
                    if backoff == 'exponential':
                        delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
                    elif backoff == 'linear':
                        delay = min(initial_delay * attempt, max_delay)
                    else:  # fixed
                        delay = initial_delay
                    
                    # 回调
                    if on_retry:
                        on_retry(attempt, e, delay)
                    else:
                        logger.warning(
                            f"⚠️ {test_name} 第{attempt}次失败: {e}, "
                            f"{delay:.1f}秒后重试"
                        )
                    
                    time.sleep(delay)
            
            raise RetryError(
                f"{test_name} 重试{max_attempts}次后仍失败",
                last_exception, max_attempts
            )
        return wrapper
    return decorator


class NetworkResilientClient:
    """网络弹性客户端"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.session_stats = {'success': 0, 'retry': 0, 'failed': 0}
    
    def request(self, method: str, url: str, **kwargs) -> dict:
        """带重试的请求"""
        import requests
        
        timeout = kwargs.pop('timeout', 15)
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                r = requests.request(method, url, timeout=timeout, **kwargs)
                
                # 网络抖动判断
                if self._is_network_glitch(r):
                    self.session_stats['retry'] += 1
                    time.sleep(0.5 * attempt)
                    last_error = f"HTTP {r.status_code}"
                    continue
                
                self.session_stats['success'] += 1
                return {
                    'status_code': r.status_code,
                    'data': r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text,
                    'headers': dict(r.headers),
                }
            except (requests.Timeout, requests.ConnectionError) as e:
                self.session_stats['retry'] += 1
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(0.5 * attempt)
                    continue
            except Exception as e:
                self.session_stats['failed'] += 1
                raise
        
        self.session_stats['failed'] += 1
        raise RetryError(
            f"请求失败（重试{self.max_retries}次）",
            Exception(last_error),
            self.max_retries
        )
    
    def _is_network_glitch(self, response) -> bool:
        """判断是否为网络抖动"""
        # 5xx 或特定 4xx 视为可重试
        return response.status_code in [502, 503, 504, 408, 429]
    
    def get_stats(self) -> dict:
        """获取统计"""
        total = sum(self.session_stats.values())
        if total == 0:
            return self.session_stats
        return {
            **self.session_stats,
            'success_rate': f"{self.session_stats['success'] / total * 100:.1f}%"
        }
