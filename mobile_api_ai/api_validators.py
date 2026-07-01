# -*- coding: utf-8 -*-
"""
API校验装饰器模块 - 统一参数校验与幂等性控制

功能说明：
- 统一参数校验装饰器
- 必填参数检查
- 类型检查
- 请求幂等性控制

使用方式：
    from api_validators import validate_json, require_params, rate_limit

    @app.route('/api/order/create', methods=['POST'])
    @validate_json
    @require_params('order_no', 'customer_name')
    def create_order():
        pass
"""
import os
import time
import uuid
import logging
from functools import wraps
from typing import List, Dict, Any, Optional, Callable
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

_idempotency_store: Dict[str, Dict[str, Any]] = {}
_idempotency_lock_timeout = int(os.getenv('IDEMPOTENCY_LOCK_TIMEOUT', '300'))


def _get_cache():
    """获取缓存实例"""
    try:
        from cache import get_cache
        cache = get_cache()
        if cache is None:
            return None
        return cache
    except Exception:
        return None


class ValidationError(Exception):
    """校验异常"""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_json(required_fields: Optional[List[str]] = None,
                  optional_fields: Optional[List[str]] = None,
                  field_types: Optional[Dict[str, type]] = None) -> Callable:
    """
    JSON参数校验装饰器

    参数说明：
        required_fields (List[str]): 必填字段列表
        optional_fields (List[str]): 可选字段列表
        field_types (Dict[str, type]): 字段类型约束

    使用示例：
        @validate_json(required_fields=['name', 'email'])
        def create_user():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({'code': 400, 'message': '请求体必须是JSON'}), 400

                if required_fields:
                    missing = [f for f in required_fields if f not in data or data[f] is None]
                    if missing:
                        return jsonify({
                            'code': 400,
                            'message': f'缺少必填参数: {", ".join(missing)}',
                            'missing_fields': missing
                        }), 400

                if field_types:
                    for field, expected_type in field_types.items():
                        if field in data and data[field] is not None:
                            if not isinstance(data[field], expected_type):
                                return jsonify({
                                    'code': 400,
                                    'message': f'参数 {field} 类型错误，期望 {expected_type.__name__}',
                                    'field': field
                                }), 400

                g.request_data = data
                return func(*args, **kwargs)

            except ValidationError as e:
                return jsonify({'code': 400, 'message': e.message, 'field': e.field}), 400
            except Exception as e:
                logger.error(f"[Validator] 校验异常: {e}")
                return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

        return wrapper
    return decorator


def require_params(*required_params: str) -> Callable:
    """
    必填参数校验装饰器（支持GET/POST）

    参数说明：
        *required_params: 必填参数名

    使用示例：
        @require_params('id', 'name')
        def update_item():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            missing = []
            for param in required_params:
                value = request.args.get(param) or request.form.get(param)
                if value is None:
                    missing.append(param)

            if missing:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必填参数: {", ".join(missing)}',
                    'missing_params': missing
                }), 400

            return func(*args, **kwargs)
        return wrapper
    return decorator


def idempotent(key_prefix: str = 'idempotency', timeout: int = 300) -> Callable:
    """
    幂等性校验装饰器

    参数说明：
        key_prefix (str): 幂等键前缀
        timeout (int): 幂等锁超时时间（秒）

    使用示例：
        @idempotent(key_prefix='order_create')
        def create_order():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            idempotency_key = request.headers.get('X-Idempotency-Key')

            if not idempotency_key:
                idempotency_key = request.args.get('idempotency_key')

            if not idempotency_key:
                return jsonify({
                    'code': 400,
                    'message': '缺少幂等键，请提供 X-Idempotency-Key header'
                }), 400

            full_key = f"{key_prefix}:{idempotency_key}"

            cache = _get_cache()
            if cache:
                cached_result = cache.get(full_key)
                if cached_result:
                    logger.info(f"[Idempotent] 命中缓存: {full_key}")
                    return jsonify(cached_result), 200

            if full_key in _idempotency_store:
                entry = _idempotency_store[full_key]
                if time.time() - entry['timestamp'] < timeout:
                    if entry.get('response'):
                        logger.info(f"[Idempotent] 命中记录: {full_key}")
                        return jsonify(entry['response']), entry['status_code']
                else:
                    del _idempotency_store[full_key]

            g.idempotency_key = idempotency_key
            g.idempotency_full_key = full_key

            result = func(*args, **kwargs)

            if isinstance(result, tuple):
                response_data, status_code = result[0], result[1] if len(result) > 1 else 200
            else:
                response_data, status_code = result, 200

            if hasattr(response_data, 'get_json'):
                response_dict = response_data.get_json()
            else:
                response_dict = response_data

            if cache:
                cache.set(full_key, response_dict, ttl=timeout)

            _idempotency_store[full_key] = {
                'timestamp': time.time(),
                'response': response_dict,
                'status_code': status_code
            }

            return response_data, status_code

        return wrapper
    return decorator


def rate_limit(max_requests: int = 100, window: int = 60) -> Callable:
    """
    请求限流装饰器

    参数说明：
        max_requests (int): 时间窗口内最大请求数
        window (int): 时间窗口（秒）

    使用示例：
        @rate_limit(max_requests=10, window=60)
        def sensitive_api():
            pass
    """
    request_history: Dict[str, List[float]] = {}
    history_lock = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_ip = request.remote_addr or 'unknown'
            endpoint = request.endpoint or 'unknown'

            key = f"{client_ip}:{endpoint}"

            now = time.time()

            if key not in request_history:
                request_history[key] = []
                history_lock[key] = __import__('threading').Lock()

            with history_lock[key]:
                request_history[key] = [
                    t for t in request_history[key]
                    if now - t < window
                ]

                if len(request_history[key]) >= max_requests:
                    logger.warning(f"[RateLimit] 触发限流: {key}")
                    return jsonify({
                        'code': 429,
                        'message': f'请求过于频繁，请{window}秒后重试',
                        'retry_after': window
                    }), 429

                request_history[key].append(now)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(func: Callable) -> Callable:
    """
    简易认证校验装饰器

    使用示例：
        @require_auth
        def protected_api():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'code': 401, 'message': '缺少认证信息'}), 401

        if not auth_header.startswith('Bearer '):
            return jsonify({'code': 401, 'message': '认证格式错误'}), 401

        token = auth_header[7:]

        try:
            from api.auth import verify_token
            payload = verify_token(token)
            if not payload:
                return jsonify({'code': 401, 'message': '无效的token'}), 401

            g.current_user = payload
            return func(*args, **kwargs)

        except ImportError:
            logger.warning("[Auth] auth模块不可用，跳过认证")
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[Auth] 认证异常: {e}")
            return jsonify({'code': 401, 'message': '认证失败'}), 401

    return wrapper


def sanitize_params(*allowed_params: str) -> Callable:
    """
    参数白名单过滤装饰器

    参数说明：
        *allowed_params: 允许的参数列表

    使用示例：
        @sanitize_params('id', 'name', 'status')
        def query_items():
            # g.sanitized_params 只包含白名单参数
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}

            sanitized = {
                k: v for k, v in data.items()
                if k in allowed_params
            }

            g.sanitized_params = sanitized
            return func(*args, **kwargs)
        return wrapper
    return decorator
