# -*- coding: utf-8 -*-
"""
API通用装饰器 - 统一参数校验和错误处理
"""
import os
from functools import wraps
from flask import request, jsonify
from typing import List, Dict, Any, Callable, Optional


def success(data: Any = None, message: str = '操作成功', **extra) -> Dict:
    """统一成功响应格式"""
    resp = {'code': 0, 'message': message}
    if data is not None:
        resp['data'] = data
    resp.update(extra)
    return jsonify(resp)


def fail(code: int, message: str, data: Any = None) -> jsonify:
    """统一失败响应格式"""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def validate_json_params(*required_fields: str, optional_fields: List[str] = None) -> Callable:
    """
    装饰器：校验JSON请求参数

    用法:
        @bp.route('/submit', methods=['POST'])
        @validate_json_params('order_id', 'worker_id', 'completed_qty')
        def submit_report():
            data = request.validated_data  # 已校验的参数字典
            ...

    Args:
        required_fields: 必填参数名
        optional_fields: 可选参数名列表
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True)
            if data is None or not isinstance(data, dict):
                return fail(400, '请求体必须是有效的JSON对象')

            missing = [f for f in required_fields if f not in data or data[f] is None]
            if missing:
                return fail(400, f"缺少必填参数: {', '.join(missing)}")

            if optional_fields:
                for f in optional_fields:
                    if f not in data:
                        data[f] = None

            request.validated_data = data
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_type(field: str, expected_type: type, message: str = None) -> Callable:
    """
    装饰器：校验参数类型

    用法:
        @bp.route('/update', methods=['POST'])
        @validate_json_params('qty')
        @validate_type('qty', int, 'qty必须是整数')
        def update():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(request, 'validated_data'):
                return fail(500, '装饰器顺序错误：validate_type必须在validate_json_params之后')

            data = request.validated_data
            if field in data and not isinstance(data[field], expected_type):
                msg = message or f"参数'{field}'类型错误，期望{expected_type.__name__}"
                return fail(400, msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(func: Callable) -> Callable:
    """
    装饰器：简单认证检查（从header获取token）

    用法:
        @bp.route('/protected', methods=['GET'])
        @require_auth
        def protected():
            user_id = request.user_id  # 已认证的用户ID
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return fail(401, '缺少认证令牌')
        try:
            import jwt
            from core.config import JWT_SECRET_KEY as SECRET_KEY
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            request.user_role = payload.get('role', 'user')
        except jwt.ExpiredSignatureError:
            return fail(401, '令牌已过期')
        except jwt.InvalidTokenError:
            return fail(401, '无效的令牌')
        except ImportError:
            return fail(500, 'JWT模块未安装')
        return func(*args, **kwargs)
    return wrapper


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """
    装饰器：简易请求频率限制（基于IP）

    用法:
        @bp.route('/send', methods=['POST'])
        @rate_limit(max_requests=10, window_seconds=60)
        def send_message():
            ...

    注意: 生产环境建议使用Redis
    """
    from collections import defaultdict
    from time import time

    request_times = defaultdict(list)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            now = time()

            request_times[ip] = [t for t in request_times[ip] if now - t < window_seconds]

            if len(request_times[ip]) >= max_requests:
                return fail(429, f'请求过于频繁，请在{window_seconds}秒后重试')

            request_times[ip].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable) -> Callable:
    """
    装饰器：管理接口权限认证

    要求请求携带 JWT Bearer Token，并验证 role ∈ {管理员, 操作员}

    用法:
        @bp.route('/admin/update', methods=['POST'])
        @require_admin
        def admin_update():
            # request.current_operator 包含已验证的操作员信息
            ...

    注意: 该装饰器应位于 @limiter 之后、视图函数之前
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return fail(401, '缺少认证令牌，请先登录')

        token = auth_header[7:]
        if not token:
            return fail(401, '令牌为空')

        secret = os.getenv('JWT_SECRET_KEY')
        if not secret:
            return fail(500, '服务器认证未配置')

        try:
            import jwt as _jwt
            payload = _jwt.decode(token, secret, algorithms=['HS256'])
            role = payload.get('role', '')
            operator_id = payload.get('operator_id', '')
            name = payload.get('name', '')
            if role not in ('管理员', '操作员', 'admin', 'operator'):
                return fail(403, f'权限不足：需要管理员或操作员角色，当前为「{role}」')
            request.current_operator = {
                'operator_id': operator_id,
                'name': name,
                'role': role,
            }
        except jwt.ExpiredSignatureError:
            return fail(401, '令牌已过期，请重新登录')
        except jwt.InvalidTokenError:
            return fail(401, '无效的令牌')
        except ImportError:
            return fail(500, 'JWT模块未安装')
        return func(*args, **kwargs)
    return wrapper


def require_api_key(f):
    """API Key验证装饰器（从环境变量 WECHAT_CLOUD_API_KEY 读取）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.environ.get('WECHAT_CLOUD_API_KEY')
        if not expected:
            return jsonify({'code': 500, 'message': 'API key not configured'}), 500
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if key != expected:
            return jsonify({'code': 403, 'message': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated
