# -*- coding: utf-8 -*-
"""库存管理 — 权限与 CSRF 装饰器

TASK-011 实施：admin_required / require_auth 装饰器
CRITICAL Fix A2: session.regenerate 防护（见 inventory_api_server login）
CRITICAL Fix A3: CSRF 防护（require_csrf 装饰器）

CSRF 防护采用**双 cookie 模式 + 自定义 header**：
1. 登录后生成 csrf_token 写入 session
2. 前端从 meta 标签 / API 读取 token
3. 所有状态变更请求必须携带 X-CSRF-Token header
4. 后端验证：request.header['X-CSRF-Token'] == session['csrf_token']
"""
import secrets
from functools import wraps
from flask import session, jsonify, redirect, request


# ============================================================
# CSRF Token 管理
# ============================================================

def generate_csrf_token() -> str:
    """生成 CSRF token（首次访问时调用）"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


def require_csrf(f):
    """CSRF 防护装饰器：所有 POST/PUT/PATCH/DELETE 必须验证 X-CSRF-Token

    使用方式：
        @bp.route('/inventory/api/product/add', methods=['POST'])
        @admin_required
        @require_csrf
        def product_add():
            ...

    注意：装饰器顺序很重要 — @require_csrf 必须在 @admin_required 之后
    （@admin_required 在上，先执行）
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 安全方法无需 CSRF
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return f(*args, **kwargs)

        # 未登录则由 @admin_required 拦截
        if not session.get('logged_in'):
            return f(*args, **kwargs)

        # 验证 token
        expected = session.get('_csrf_token')
        provided = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')

        if not expected:
            return jsonify({'ok': False, 'msg': 'CSRF token 不存在，请重新登录'}), 403

        if not provided or not secrets.compare_digest(str(expected), str(provided)):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f'[CSRF] 验证失败: IP={request.remote_addr} '
                f'path={request.path} 提供={bool(provided)}'
            )
            return jsonify({
                'ok': False,
                'msg': 'CSRF token 验证失败，请刷新页面重试'
            }), 403

        return f(*args, **kwargs)
    return decorated


# ============================================================
# 权限装饰器
# ============================================================

def require_auth(f):
    """要求登录（页面端点：未登录重定向到 /login）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """要求管理员权限（API 端点：未登录 401 / 非 admin 403）

    使用方式：
        @bp.route('/inventory/api/settings', methods=['POST'])
        @admin_required
        @require_csrf
        def save_settings():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'ok': False, 'msg': '未登录'}), 401
        if not session.get('is_admin'):
            return jsonify({'ok': False, 'msg': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated
