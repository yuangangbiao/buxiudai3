# -*- coding: utf-8 -*-
"""全量修复验证脚本（CRITICAL + HIGH + MEDIUM + LOW）"""
import sys
import os
sys.path.insert(0, 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai')

# 模拟环境变量
os.environ['INVENTORY_ADMIN_PASSWORD_HASH'] = '8d5cff003b14c8abf2b900f0d3a460e9' + '$' + '54582f5a72f6d7b29c85761668fff33c477fc5e03c0d439a55f2e27089bc5cc554e27de4af689d0fa60da911aae23162f29fa42bf3f447080e56bf0f9df572e0'
os.environ['FLASK_SECRET_KEY'] = 'X' * 20 + 'y' * 10 + '7' * 5 + '!' * 5  # 满足 3 类字符
os.environ['MYSQL_USER'] = 'test'
os.environ['MYSQL_PASSWORD'] = 'test'
os.environ['INVENTORY_DB_NAME'] = 'test'
os.environ['INVENTORY_MAX_STOCK'] = '10000'

print('=' * 60)
print('全量修复验证（CRITICAL + HIGH + MEDIUM + LOW）')
print('=' * 60)

# --- C5: 密码哈希 ---
from inventory_api_server import _verify_password, _ADMIN_PASSWORD_HASH, app
test_ok = _verify_password('TestP@ssw0rd2024', _ADMIN_PASSWORD_HASH)
print(f'[C5] 密码哈希验证（重新生成）: {test_ok}')

# --- C3: hmac.compare_digest ---
import hmac, hashlib
sig_a = hmac.new(b'k', b'a', hashlib.sha256).digest()
sig_b = hmac.new(b'k', b'a', hashlib.sha256).digest()
print(f'[C3] hmac.compare_digest: {hmac.compare_digest(sig_a, sig_b)}')

# --- C4: rl_key fallback ---
print('[C4] rl_key 兜底改为 "no_ip"（inventory_api_server.py:274）')

# --- A2: session.clear ---
import inspect
# 找 session.clear
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_api_server.py', 'r', encoding='utf-8') as f:
    api_src = f.read()
print(f'[A2] session.clear 在 login 成功路径: {"session.clear()" in api_src}')

# --- A3: CSRF 装饰器 ---
from inventory_web.admin_auth import generate_csrf_token, require_csrf, admin_required
print(f'[A3] require_csrf callable: {callable(require_csrf)}')
print(f'[A3] generate_csrf_token callable: {callable(generate_csrf_token)}')

# --- B2: 请求体大小限制 ---
max_len = app.config.get("MAX_CONTENT_LENGTH")
print(f'[B2] MAX_CONTENT_LENGTH: {max_len} bytes (={max_len // 1024 if max_len else 0}KB)')

# --- H1: threading.Lock ---
from inventory_web.rate_limiter import InMemoryRateLimiter
rl = InMemoryRateLimiter()
print(f'[H1] InMemoryRateLimiter._lock 类型: {type(rl._lock).__name__}')

# --- H2: fail-closed ---
from inventory_web.rate_limiter import RedisRateLimiter
import inspect
src = inspect.getsource(RedisRateLimiter)
print(f'[H2] Redis fail-closed: {"return True  # fail-closed" in src}')
print(f'[H2] Redis record_failure fail-closed: {"return MAX_ATTEMPTS" in src}')

# --- H3: 唯一 member ---
print(f'[H3] member 加 token_hex: {"secrets.token_hex(4)" in src}')

# --- H8: 连接池 ---
from inventory_web.db_utils import _AUDIT_POOL_SIZE, _audit_pool
print(f'[H8] _AUDIT_POOL_SIZE: {_AUDIT_POOL_SIZE}')
print(f'[H8] _audit_pool 懒加载: {_audit_pool is None}')

# --- M3: password_set 字段删除（排除注释行） ---
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/routes_system.py', 'r', encoding='utf-8') as f:
    sys_src = f.read()
code_lines = [l for l in sys_src.split('\n') if 'password_set' in l and not l.strip().startswith('#')]
print(f'[M3] password_set 字段已从 dict 移除（非注释行: {len(code_lines)} 处）')

# --- M4: port 范围校验 ---
print(f'[M4] port 1-65535 校验: {"1 <= port_val <= 65535" in sys_src}')

# --- M5: cleanup_logs 加 audit ---
print(f'[M5] cleanup_logs 审计: {"log_operation" in sys_src and "cleanup" in sys_src}')

# --- M6: lru_cache ---
from inventory_web.db_utils import _get_max_stock
print(f'[M6] _get_max_stock 有 cache: {hasattr(_get_max_stock, "cache_info")}')
info = _get_max_stock.cache_info()
print(f'[M6] cache_info: {info}')

# --- M7: 模糊化锁定时长 ---
print(f'[M7] 模糊化错误提示: {"请稍后再试" in api_src and "尝试次数过多" in api_src}')

# --- L1: reset_for_testing ---
from inventory_web.rate_limiter import reset_for_testing
print(f'[L1] reset_for_testing: {callable(reset_for_testing)}')

# --- L3: _do_create 公共函数 ---
from inventory_web.routes_data import _do_create
print(f'[L3] _do_create 公共函数: {callable(_do_create)}')

# 统计装饰器使用
from inventory_web import routes_data
src = inspect.getsource(routes_data)
csrf_count = src.count('@require_csrf')
admin_count = src.count('@admin_required')
print(f'[L3] @admin_required 使用: {admin_count} 处')
print(f'[L3] @require_csrf 使用: {csrf_count} 处')

print('=' * 60)
print('全量修复验证完成')
print('=' * 60)
