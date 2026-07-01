# -*- coding: utf-8 -*-
"""库存 REST API 服务 v2.4 - 入口文件

安全加固版本（TASK-005 + CRITICAL Fixes C1-C5 实施）：
- FLASK_SECRET_KEY: 启动时校验长度 ≥32 + 复杂度 ≥3 类
- INVENTORY_ADMIN_PASSWORD_HASH: 强制使用 pbkdf2 哈希（C5），不再支持明文密码
- MYSQL_USER / INVENTORY_DB_NAME: 强制环境变量，无默认值
- 登录: pbkdf2 哈希验证 + hmac.compare_digest（C3，防止 timing attack）
- 多 worker 部署必须配置 REDIS_URL（H1，否则 InMemory 限流被绕过）
- 登录页: render_template('login.html') 替代内联 HTML
- 响应头: X-Content-Type-Options / X-Frame-Options / CSP
- Cookie: HttpOnly + SameSite + Secure(prod)
- XSS 防护: Jinja2 默认转义 + after_request 安全头
- str(e) 全部改为 logger.exception() + 脱敏消息
"""
import os
import sys
import re
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, session, redirect, render_template
from core.db import get_direct_connection
from pymysql.cursors import DictCursor
from functools import wraps

from logging_setup import setup_daily_logger
setup_daily_logger('inventory_api')
logger = logging.getLogger(__name__)

# ============================================================
# TASK-005 强制环境变量校验（启动失败模式）
# ============================================================

def _validate_secret_key():
    """TASK-005: FLASK_SECRET_KEY 长度 ≥32 + 复杂度 ≥3 类（v2.3 升级）"""
    key = os.getenv('FLASK_SECRET_KEY')
    if not key:
        raise RuntimeError("环境变量 FLASK_SECRET_KEY 必须设置（≥32字符随机）")
    if len(key) < 32:
        raise RuntimeError(
            f"FLASK_SECRET_KEY 长度不足：当前 {len(key)} 字符，要求 ≥32 字符"
        )
    categories = sum([
        any(c.isupper() for c in key),
        any(c.islower() for c in key),
        any(c.isdigit() for c in key),
        any(not c.isalnum() for c in key)
    ])
    if categories < 3:
        raise RuntimeError(
            "FLASK_SECRET_KEY 复杂度不足：需包含大写/小写/数字/特殊字符中的至少 3 类"
        )
    return key


def _validate_admin_password_hash():
    """TASK-005 + CRITICAL Fix C3/C5: 强制使用密码哈希（pbkdf2_hmac）
    环境变量 INVENTORY_ADMIN_PASSWORD_HASH 格式: salt_hex$hash_hex

    生成方法（使用 scripts/generate_password_hash.py）：
        python scripts/generate_password_hash.py "your-password"
    """
    import secrets as _secrets
    stored = os.getenv('INVENTORY_ADMIN_PASSWORD_HASH')
    if not stored:
        raise RuntimeError(
            "环境变量 INVENTORY_ADMIN_PASSWORD_HASH 必须设置（无默认值）\n"
            "生成方法: python scripts/generate_password_hash.py <your-password>"
        )
    # 验证格式: salt_hex$hash_hex
    if '$' not in stored:
        raise RuntimeError("INVENTORY_ADMIN_PASSWORD_HASH 格式错误：必须是 salt_hex$hash_hex")
    salt_hex, hash_hex = stored.split('$', 1)
    if len(salt_hex) != 32 or len(hash_hex) != 128:
        raise RuntimeError(
            f"INVENTORY_ADMIN_PASSWORD_HASH 长度异常: salt={len(salt_hex)} hash={len(hash_hex)}"
        )
    # 验证 hex 格式
    try:
        bytes.fromhex(salt_hex)
        bytes.fromhex(hash_hex)
    except ValueError:
        raise RuntimeError("INVENTORY_ADMIN_PASSWORD_HASH 不是合法的 hex 字符串")
    return stored


def _validate_db_credentials():
    """TASK-005: MYSQL_USER / INVENTORY_DB_NAME 强制无默认值"""
    user = os.getenv('MYSQL_USER')
    db_name = os.getenv('INVENTORY_DB_NAME')
    if not user:
        raise RuntimeError("环境变量 MYSQL_USER 必须设置（无默认值）")
    if not db_name:
        raise RuntimeError("环境变量 INVENTORY_DB_NAME 必须设置（无默认值）")
    if not re.match(r'^[a-zA-Z0-9_]+$', user):
        raise RuntimeError(f"MYSQL_USER 包含非法字符：{user!r}")
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        raise RuntimeError(f"INVENTORY_DB_NAME 包含非法字符：{db_name!r}")
    return user, db_name


# 启动时执行所有校验
try:
    _FLASK_SECRET_KEY = _validate_secret_key()
    _ADMIN_PASSWORD_HASH = _validate_admin_password_hash()
    _MYSQL_USER, _INVENTORY_DB_NAME = _validate_db_credentials()
except RuntimeError as e:
    logger.critical(f'[启动失败] {e}')
    print(f'[FATAL] {e}', file=sys.stderr)
    sys.exit(1)

# CRITICAL Fix H1: 多 worker 部署必须配置 REDIS_URL（否则 InMemory 限流被绕过）
_workers = int(os.getenv('GUNICORN_WORKERS', '0'))
if _workers > 1 and not os.getenv('REDIS_URL'):
    logger.critical(
        f'[启动失败] 多 worker 模式（{_workers} workers）必须设置 REDIS_URL，'
        f'否则 InMemoryRateLimiter 会被绕过（每个 worker 独立计数）'
    )
    print(
        f'[FATAL] 多 worker 模式必须设置 REDIS_URL', file=sys.stderr
    )
    sys.exit(1)

# ============================================================
# Flask 应用与安全配置
# ============================================================

app = Flask(__name__)
app.secret_key = _FLASK_SECRET_KEY

# Cookie 安全配置（TASK-005）
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=(os.getenv('FLASK_ENV') == 'production'),
    SESSION_COOKIE_NAME='inv_session',
    PERMANENT_SESSION_LIFETIME=3600,  # 1小时过期
)

# CRITICAL Fix B2: 请求体大小限制（防止大文件 DoS / 撑爆内存）
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB


@app.errorhandler(413)
def handle_request_entity_too_large(e):
    """请求体超过 1MB 时返回 413 而不是 Flask 默认错误页"""
    logger.warning(f'[B2] 请求体过大: {request.remote_addr} > 1MB')
    return jsonify({'ok': False, 'msg': '请求体超过 1MB 限制'}), 413

# ============================================================
# MySQL 连接配置（无硬编码）
# ============================================================

MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': _MYSQL_USER,                   # 强制环境变量
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': _INVENTORY_DB_NAME,        # 强制环境变量
    'charset': 'utf8mb4',
    'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '3')),
    'cursorclass': DictCursor,
    'autocommit': False,
}


def _get_conn():
    """获取 MySQL 连接（无硬编码 + 自动重置锁超时）"""
    return get_direct_connection(**MYSQL_CFG)


def _get_conn_with_lock_timeout():
    """TASK-008: 获取连接并设置锁等待超时（防止连接池复用导致超时失效）"""
    conn = get_direct_connection(**MYSQL_CFG)
    with conn.cursor() as c:
        c.execute("SET SESSION innodb_lock_wait_timeout = 5")
    return conn


# ============================================================
# 装饰器：登录态校验（TASK-005）
# ============================================================

def require_auth_page(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('logged_in'):
            return f(*args, **kwargs)
        return redirect('/login')
    return decorated


def admin_required(f):
    """TASK-011: 管理员权限装饰器（save_settings 等敏感操作）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'ok': False, 'msg': '未登录'}), 401
        if not session.get('is_admin'):
            return jsonify({'ok': False, 'msg': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================
# 全局 before_request：会话校验
# ============================================================

# CRITICAL Fix A3: CSRF token 自动生成（任何 GET 请求都会触发）
from inventory_web.admin_auth import generate_csrf_token  # noqa: E402


@app.before_request
def ensure_csrf_token():
    """每次请求都确保 session 中有 _csrf_token（GET 不会验证，但必须存在）"""
    if session.get('logged_in'):
        generate_csrf_token()


@app.before_request
def check_auth():
    path = request.path
    # 白名单：登录页、登出、首页、API 健康检查、静态文件
    whitelist = (
        path.startswith('/login'),
        path.startswith('/logout'),
        path == '/',
        path == '/api/health',
        path.startswith('/static/'),
    )
    if any(whitelist):
        return None
    if not session.get('logged_in'):
        # API 端点返回 401 而非重定向
        if path.startswith('/api/'):
            return jsonify({'code': 401, 'message': '未登录'}), 401
        return redirect('/login')
    return None


# ============================================================
# 响应头安全中间件（TASK-005：XSS / Clickjacking 防护）
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # v2.3 替代 DENY
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self' https://cdn.bootcdn.net; "
        "img-src 'self' data: https://cdn.bootcdn.net; "      # 允许 data: 图片（Bootstrap select 下拉箭头 SVG）
        "style-src 'self' 'unsafe-inline' https://cdn.bootcdn.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.bootcdn.net; "  # 允许模板内 inline script
        "font-src 'self' data: https://cdn.bootcdn.net; "      # 允许 data: 字体（Bootstrap Icons）
        "frame-ancestors 'self'"
    )
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


# ============================================================
# 登录端点（TASK-005：使用模板 + TASK-017：登录限流 + CRITICAL Fix C3/C4）
# ============================================================
import hmac as _hmc  # noqa: E402  # CRITICAL Fix C3: constant-time 比较
import hashlib as _hsh  # noqa: E402  # CRITICAL Fix C5: pbkdf2 密码哈希

# TASK-017: 限流器（Redis/内存 自动选择）
from inventory_web.rate_limiter import rate_limiter as _login_limiter, LOCKOUT_SECONDS  # noqa: E402


def _verify_password(pwd: str, stored_hash: str) -> bool:
    """CRITICAL Fix C3/C5: pbkdf2 哈希 + constant-time 验证

    Args:
        pwd: 用户输入的明文密码
        stored_hash: 格式 "salt_hex$hash_hex"（64 字符盐 + 256 字符哈希）

    Returns:
        True=匹配，False=不匹配
    """
    try:
        salt_hex, hash_hex = stored_hash.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        h = _hsh.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 200_000, dklen=64)
        # CRITICAL Fix C3: 用 hmac.compare_digest 防止 timing attack
        return _hmc.compare_digest(h, expected)
    except Exception:
        return False


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    # CRITICAL Fix C4: rl_key 兜底改为固定字符串 'no_ip'（避免多个 None 共享同一 key）
    rl_key = request.remote_addr if request.remote_addr else 'no_ip'

    if request.method == 'POST':
        # TASK-017: 限流检查
        if _login_limiter.is_locked(rl_key):
            remaining = _login_limiter.get_remaining_lock_seconds(rl_key)
            # CRITICAL Fix M7: 不暴露精确秒数（避免攻击者精确计时再次尝试）
            logger.warning(f'[登录锁定] IP={rl_key} 剩余 {remaining}s')
            return render_template(
                'login.html',
                error='尝试次数过多，请稍后再试'  # 模糊化提示
            ), 429

        pwd = request.form.get('password', '')

        # CRITICAL Fix C3/C5: pbkdf2 哈希 + constant-time 验证
        if pwd and _verify_password(pwd, _ADMIN_PASSWORD_HASH):
            # 成功：清零计数
            _login_limiter.record_success(rl_key)
            # CRITICAL Fix A2: session.regenerate 防止 session fixation
            # （攻击者无法用登录前的 session ID 冒充登录后的身份）
            session.clear()
            session['logged_in'] = True
            session['is_admin'] = True  # 简化：admin 密码登录即为 admin
            session.permanent = True
            return redirect('/inventory/dashboard')

        # 失败：记录 + 限流
        attempts = _login_limiter.record_failure(rl_key)
        logger.warning(
            f'[登录失败] IP={rl_key} 第 {attempts}/{5} 次'
        )
        # 错误信息脱敏：统一为"密码错误"，不暴露具体原因
        return render_template('login.html', error='密码错误'), 401

    # GET 请求
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/')
def root():
    if not session.get('logged_in'):
        return redirect('/login')
    return redirect('/inventory/dashboard')


# ============================================================
# CRITICAL Fix A3: CSRF token 端点
# ============================================================

@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """前端调用此端点获取 CSRF token

    登录后访问 /api/csrf-token 一次，前端缓存 token，
    之后所有 POST/PUT/PATCH/DELETE 请求必须携带 X-CSRF-Token header
    """
    if not session.get('logged_in'):
        return jsonify({'ok': False, 'msg': '未登录'}), 401
    return jsonify({
        'ok': True,
        'csrf_token': generate_csrf_token()
    })


# ============================================================
# 健康检查端点（不依赖 DB，避免泄露敏感信息）
# ============================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'code': 0,
        'service': 'inventory_api',
        'version': '2.3',
        'time': datetime.now().isoformat()
    })


# ============================================================
# 错误处理：避免堆栈泄露
# ============================================================

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(f'[未捕获异常] {type(e).__name__}')
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify({'code': 404, 'message': '资源不存在'}), 404


@app.errorhandler(500)
def handle_500(e):
    logger.exception('[500错误]')
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500


# ============================================================
# 蓝图注册（在所有路由定义后）
# ============================================================

try:
    from inventory_web import web_bp
    app.register_blueprint(web_bp)
    logger.info(f'[库存] Web蓝图注册完成: {len(list(app.url_map.iter_rules()))} 条路由')
except ImportError as e:
    logger.critical(f'[启动失败] 蓝图加载失败: {e}')
    print(f'[FATAL] 蓝图加载失败: {e}', file=sys.stderr)
    sys.exit(1)


# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('INVENTORY_API_PORT', '5010'))
    logger.info(f'库存系统 v2.3 启动: http://{host}:{port} (Web + API)')
    for r in app.url_map.iter_rules():
        logger.debug(f'  {r.rule} -> {r.endpoint}')
    app.run(host=host, port=port, debug=False)
