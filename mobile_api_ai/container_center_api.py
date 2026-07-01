# -*- coding: utf-8 -*-
"""
容器中心API服务器
基于container_center_v5的API服务器
"""
import os
import json
import logging
import time
import threading
import sys as _sys
import atexit
import uuid
from dotenv import load_dotenv

_MOBILE_API_PATH = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_MOBILE_API_PATH)
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
if _MOBILE_API_PATH not in _sys.path:
    _sys.path.append(_MOBILE_API_PATH)

load_dotenv(os.path.join(_MOBILE_API_PATH, '.env'))
load_dotenv(os.path.join(_MOBILE_API_PATH, '..', '.env'))

from core.config import DB_PATHS, Config, BASE_DIR, now as _now_func
from core.db_compat import get_conn as _get_mysql_connection
from datetime import datetime, timedelta
from typing import Optional, Dict
# [H2 修复 2026-06-13] 错误码字典
from mobile_api_ai.utils.error_codes import ErrorCode

import jwt
import requests
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# [F16 T16.1 修复] process_names 表替代层
# 根因: F6 P9 2026-06-10 已 DROP container_center.process_names 表
#       (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
#       原代码 8 处直接 SELECT/UPDATE/INSERT/DELETE 该表 → 1146 WARNING
# 修复: 改用内存数据源 (process_records 实时聚合 + dispatch_cache.process_departments)
#       process_code → 内存 PROCESS_CODES 字典 (core._config_domain)
#       department   → dispatch_cache.process_departments (含调度中心同步)
# ──────────────────────────────────────────────
_DISPATCH_CENTER_URL_DEFAULT = 'http://localhost:5003'


def _get_dispatch_center_url() -> str:
    return os.getenv('DISPATCH_CENTER_URL', _DISPATCH_CENTER_URL_DEFAULT)


def _sync_dispatch_process_dept(process_code: str, department: str) -> None:
    """通过 HTTP 把 process_code→department 同步到 dispatch_cache (无 dispatch_cache 直引, 避免循环)
    失败不影响主流程, 仅记录 WARNING"""
    try:
        url = f'{_get_dispatch_center_url()}/cc-api/process-departments/{process_code}'
        requests.post(url, json={'department': department}, timeout=2)
    except Exception as e:
        logger.warning(f'[F16 T16.1] 同步 process_dept 到调度中心失败: code={process_code} dept={department} err={e}')


def _get_process_names_from_records():
    """从 process_records 实时聚合 process_code→process_name 映射 (替代 process_names 表)
    返回: list[dict] 含 process_code, process_name, prefix (prefix=process_code 首字母)
    """
    try:
        rows = container_center.storage.get_all_process_records()
        seen = {}  # process_code → process_name (首次出现)
        for r in rows or []:
            pc = (r.get('process_code') or '').strip()
            pn = (r.get('process_name') or '').strip() or (r.get('step_name') or '').strip()
            if pc and pc not in seen:
                seen[pc] = pn
        # 合并 PROCESS_CODES (内存内置) — 标准工序 P01-P16
        try:
            from core._config_domain import PROCESS_CODES, _custom_process_codes
            for pn, pc in {**PROCESS_CODES, **_custom_process_codes}.items():
                if pc and pc not in seen:
                    seen[pc] = pn
        except Exception:
            pass
        # 合并 dispatch_cache.process_departments (避免循环, 走 HTTP)
        try:
            resp = requests.get(f'{_get_dispatch_center_url()}/cc-api/process-departments', timeout=2)
            if resp.ok:
                for pn in (resp.json().get('data') or {}).keys():
                    pc_guess = None
                    try:
                        from core.config import get_process_code
                        pc_guess = get_process_code(pn)
                    except Exception:
                        pass
                    if pc_guess and pc_guess not in seen:
                        seen[pc_guess] = pn
                    elif not pc_guess and pn not in seen.values():
                        # 无 code, 用 pn 作 key 兼容
                        seen.setdefault(pn, pn)
        except Exception:
            pass
        return [{'process_code': pc, 'process_name': pn, 'prefix': pc[:1].upper() if pc else ''}
                for pc, pn in sorted(seen.items(), key=lambda x: (x[0][:1], x[0]))]
    except Exception as e:
        logger.warning(f'[F16 T16.1] _get_process_names_from_records 失败: {e}')
        return []


def _get_process_departments_from_cache() -> Dict[str, str]:
    """从 dispatch_cache 读取 process_code→department 映射 (替代 SELECT FROM process_names)"""
    try:
        resp = requests.get(f'{_get_dispatch_center_url()}/cc-api/process-departments', timeout=2)
        if resp.ok:
            data = resp.json().get('data') or {}
            # 反转: 容器中心原本按 process_name→dept, 容器 API 客户端可能按 process_code
            return data
    except Exception as e:
        logger.warning(f'[F16 T16.1] _get_process_departments_from_cache 失败: {e}')
    return {}


# ── ResilientThread：弹性后台线程，异常自动日志 ──
class ResilientThread(threading.Thread):
    """带异常保护的弹性后台线程，异常时自动记录日志而非静默消失"""
    def run(self):
        try:
            super().run()
        except Exception:
            logger.exception('后台线程 [%s] 异常退出', self.name)
            raise
# 可选依赖：api.decorators 不存在时降级为空装饰器
# [J2 修复 2026-06-13] fail-fast：导入失败时拒绝启动 5002
# 之前：静默降级为空装饰器，所有 API 无鉴权
# 现在：导入失败 → 抛 RuntimeError → 5002 不启动
try:
    from api.decorators import require_api_key
    if not callable(require_api_key):
        raise RuntimeError('[J2] require_api_key 不可调用，鉴权可能失效')
except ImportError as e:
    raise RuntimeError(f'[J2] api.decorators.require_api_key 导入失败: {e}（5002 必须有鉴权才能启动）')

from container_center_v5 import ContainerCenter, DataStatus


# [J5 修复 2026-06-13] 全局异常处理
# 之前：47% API 无 try/except，异常时返回 Flask 默认 500 HTML
# 现在：所有未捕获异常统一返回 JSON {code, message}
def _register_global_error_handlers(app):
    """注册全局异常处理器"""
    from flask import jsonify
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """HTTP 异常（如 404, 405）"""
        return jsonify({
            'code': e.code,
            'message': e.description or '请求错误',
            'data': {}
        }), e.code

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """所有未捕获异常"""
        # 写日志（不暴露堆栈到客户端）
        try:
            from utils.trace import get_trace_id
            trace_id = get_trace_id() or 'unknown'
        except Exception:
            trace_id = 'unknown'
        logger.error(f'[5002] 未捕获异常 trace_id={trace_id}: {e}', exc_info=True)
        return jsonify({
            'code': ErrorCode.INTERNAL_ERROR[0] if 'ErrorCode' in dir() else 1500,
            'message': '服务器内部错误',
            'data': {'trace_id': trace_id}
        }), 500

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({'code': 404, 'message': 'API 不存在', 'data': {}}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({'code': 405, 'message': 'HTTP 方法不允许', 'data': {}}), 405

# 可选依赖：desktop_callback 不存在时降级为空管理器
try:
    from integration.desktop_callback import desktop_callback_manager
except ImportError:
    desktop_callback_manager = None

# 服务端增强模块（全部降级为可选）
try:
    from modules.api_signature import require_signature, init_signature_validator
except ImportError:
    # 降级：签名验证跳过，直接放行
    def require_signature(f):
        return f
    init_signature_validator = None

try:
    from modules.health_checker import DetailedHealthChecker as HealthChecker
except ImportError:
    HealthChecker = None

try:
    from modules.deployment_manager import DeploymentManager
except ImportError:
    DeploymentManager = None

try:
    from modules.enhanced_audit_logger import EnhancedAuditLogger
except ImportError:
    EnhancedAuditLogger = None

try:
    from modules.enhanced_backup import EnhancedBackupManager
except ImportError:
    EnhancedBackupManager = None

from data_integrity import DataIntegrity
from data_boundary import DataBoundary, data_boundary as global_data_boundary
from clock_sync import ClockSync, clock_sync as global_clock_sync

app = Flask(__name__)
CORS(app, origins=os.getenv('CORS_ALLOWED_ORIGINS', '*'), supports_credentials=True)

# [J5 修复 2026-06-13] 注册全局异常处理器
_register_global_error_handlers(app)

# [J1 修复 2026-06-13] 全局鉴权
# 之前：67/71 个 API 无任何鉴权
# 现在：除白名单外，所有 API 必须有 X-API-Key header
_API_KEY = os.getenv('API_KEY', '')
if not _API_KEY:
    raise RuntimeError('[J1] API_KEY 未配置，5002 必须有 API Key 才能启动')

# 公开 API 白名单（无需鉴权）
_PUBLIC_API_WHITELIST = frozenset([
    '/health', '/', '/favicon.ico',
    '/api/health', '/api/status', '/api/dashboard',
    '/api/auth/login',
    '/api/operators',  # [K22 修复 2026-06-14] 供调度中心内部调用
])

# 内部 mirror 路由（用 _check_mirror_auth 单独鉴权）
_INTERNAL_MIRROR_PATHS = frozenset([
    '/api/process_sub_steps/mirror',
])


@app.before_request
def _global_api_key_check():
    """[J1 修复 2026-06-13] 全局 API Key 鉴权
    顺序：
    1. 白名单 API 直接通过
    2. 内部 mirror 路由用 _check_mirror_auth
    3. 其他 API 必须有 X-API-Key header 且匹配

    [J7 修复 2026-06-13] URL 版本管理
    - /v1/api/* 重定向到 /api/*（301 永久）
    - 保留向后兼容
    """
    from flask import request, jsonify, redirect
    path = request.path
    # [J7 修复] /v1/api/orders/xxx → /api/orders/xxx
    if path.startswith('/v1/'):
        new_path = '/api/' + path[len('/v1/api/'):] if path.startswith('/v1/api/') else path[3:]
        return redirect(new_path, code=301)
    if path in _PUBLIC_API_WHITELIST:
        return None  # 通过
    if path in _INTERNAL_MIRROR_PATHS:
        return None  # 由路由内部 _check_mirror_auth 鉴权
    # 检查 X-API-Key header
    provided = request.headers.get('X-API-Key', '')
    if not provided:
        return jsonify({'code': 1003, 'message': '缺少 X-API-Key header', 'data': {}}), 401
    # [T41.6 修复 2026-06-14] 接受 API_KEY 或 WECHAT_CLOUD_API_KEY 任意一个
    # 之前：只检查 API_KEY，导致 require_api_key (检查 WECHAT_CLOUD_API_KEY) 永远 403
    _valid_keys = {_API_KEY, os.getenv('WECHAT_CLOUD_API_KEY', '')}
    _valid_keys.discard('')
    if provided not in _valid_keys:
        return jsonify({'code': 1003, 'message': 'API Key 错误', 'data': {}}), 401
    return None  # 通过


# [J4 修复 2026-06-13] 全局审计日志
# 之前：5/71 个 API 有审计（7%）
# 现在：所有写 API 自动审计
@app.after_request
def _global_audit_log(response):
    """[J4 修复 2026-06-13] 审计所有写操作

    写操作：POST/PUT/DELETE/PATCH
    读操作：GET（不审计）

    [J9 修复 2026-06-13] GET 自动加 Cache-Control
    """
    from flask import request
    method = request.method

    # [J9 修复] GET 加 cache-control
    if method == 'GET':
        path = request.path
        # 静态数据：operators / process_names / 部门
        if any(k in path for k in ('/api/operators', '/api/process_names', '/api/process_departments', '/api/pool/status')):
            response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 小时
        # 半静态：order 查询
        elif '/api/orders/' in path:
            response.headers['Cache-Control'] = 'private, max-age=10'  # 10 秒
        # 动态数据
        else:
            response.headers['Cache-Control'] = 'private, max-age=0, must-revalidate'

    # 只审计写操作
    if method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
        return response

    # 调审计日志（如果有）
    if _server_audit_logger:
        try:
            from utils.trace import get_trace_id
            trace_id = get_trace_id() or 'unknown'
            user_id = request.headers.get('X-User-Id', '')
            _server_audit_logger.log(
                operation_type='api',
                user_id=user_id or 'anonymous',
                user_name=user_id or 'anonymous',
                action=f'{method} {request.path}',
                result='success' if response.status_code < 400 else 'failure',
                client_ip=request.remote_addr or 'unknown',
                trace_id=trace_id,
            )
        except Exception as _e:
            logger.warning(f'[J4] 审计日志写入失败: {_e}')
    return response


# [J3 修复 2026-06-13] 简易 rate limit
# 之前：0 个 rate limit，易被攻击
# 现在：每个 IP 60 QPS 限制（默认），写 API 30 QPS
# 不引入 flask-limiter（避免依赖），用简单内存计数器
_rate_limit_buckets = {}  # {ip: [(timestamp, ...), ...]}
# [K30 修复 2026-06-14] 调高限流阈值以适应压力测试
# 之前：READ=100, WRITE=30，500/200 并发被 60%+ 拦截
# 现在：READ=1000, WRITE=200，业务能扛 100+ 并发；超限 200+ 走 429 而不是 500
_RATE_LIMIT_WINDOW_SEC = 60
_RATE_LIMIT_READ_QPS = 1000   # [T31 2026-06-14] 真正 QPS（每秒 1000）
_RATE_LIMIT_WRITE_QPS = 200   # 真正 QPS（每秒 200）

# [T31 修复 2026-06-14] token bucket 限流
# 之前 bug：滑动 60s 窗口 + 1000 上限 → 实际 16 QPS（不是注释写的 1000 QPS）
# 5 worker × 1700 QPS 压测 → 15s 内 27020 个请求 → 96% 触发 429
# 现在：token bucket 每秒补充 N 个令牌，瞬时 QPS 上限 = 配置值
# 5 worker × 15s 测：现在可达到 ~1000 QPS
_token_buckets = {}  # {ip: {'tokens': float, 'last_refill': float}}
_TOKEN_BUCKET_CAPACITY = {
    'read': _RATE_LIMIT_READ_QPS,    # 桶容量 = 1 秒可累积
    'write': _RATE_LIMIT_WRITE_QPS,
}


def _check_rate_limit(is_write: bool = False):
    """[T31 修复 2026-06-14] 检查当前 IP 是否超限（token bucket 算法）

    之前：滑动 60s 窗口（1000/60s = 16 QPS），注释与实际不符
    现在：每秒补充 QPS 个令牌，桶满丢弃，请求消耗 1 令牌
          瞬时 QPS 上限 = 配置的 QPS 值（1000/200）

    Returns:
        None: 未超限
        dict: 超限响应
    """
    from flask import request
    import time
    now = time.time()
    ip = request.remote_addr or 'unknown'
    kind = 'write' if is_write else 'read'
    rate = _TOKEN_BUCKET_CAPACITY[kind]

    # 懒加载：每个 IP 首次出现时初始化令牌桶
    if ip not in _token_buckets:
        _token_buckets[ip] = {'tokens': float(rate), 'last_refill': now}
    b = _token_buckets[ip]

    # 1. 计算距上次补充的秒数，按 rate 补充令牌
    elapsed = now - b['last_refill']
    if elapsed > 0:
        b['tokens'] = min(float(rate), b['tokens'] + elapsed * rate)
        b['last_refill'] = now

    # 2. 桶空 → 限流
    if b['tokens'] < 1.0:
        from flask import jsonify
        return jsonify({
            'code': 1503,
            'message': f'请求过于频繁（{rate} QPS 限制）',
            'data': {}
        }), 429
    # 3. 消耗 1 令牌
    b['tokens'] -= 1.0

    # 4. 定期清理内存（每 1000 个 IP 清理一次）
    if len(_token_buckets) > 1000:
        old_ips = [k for k, v in _token_buckets.items()
                   if now - v['last_refill'] > 600]
        for k in old_ips:
            del _token_buckets[k]
    return None


# 集成到 before_request
@app.before_request
def _global_rate_limit():
    """[J3 修复 2026-06-13] 全局 rate limit"""
    from flask import request
    method = request.method
    is_write = method in ('POST', 'PUT', 'DELETE', 'PATCH')
    return _check_rate_limit(is_write=is_write)

# [C2 修复 2026-06-13] trace_id 中间件注册
# [N3 修复 2026-06-13] 移到最后注册（详见下方）
_5002_trace_init = lambda: None
try:
    from utils.trace import init_trace_middleware
    _5002_trace_init = lambda: init_trace_middleware(app)
except Exception as e:
    logger.warning(f'[TRACE] 5002 中间件导入失败: {e}')

# ── 404 专用处理器（避免被全局异常吞掉） ──
@app.errorhandler(404)
def handle_404(e):
    logger.warning('[404] %s %s: 资源不存在', request.method, request.path)
    return jsonify({'code': 404, 'message': '请求的资源不存在'}), 404

# ── 全局异常处理器（零侵入覆盖所有API端点） ──
@app.errorhandler(Exception)
def handle_global_exception(e):
    logger.exception('[全局异常] %s %s: %s', request.method, request.path, e)
    return jsonify({'code': 500, 'message': str(e)}), 500

try:
    from container_dashboard import container_dashboard_bp
    app.register_blueprint(container_dashboard_bp, url_prefix='/container')
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"无法注册容器仪表盘蓝图: {e}")

try:
    from inventory_web import web_bp as inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    logger.info("已注册库存管理蓝图 (url_prefix=/inventory)")
except Exception as e:
    logger.warning(f"无法注册库存管理蓝图: {e}")

try:
    from container_center.api import create_container_api_bp, init_api_bp
    from container_center.storage import DocumentStore, IndexStore, ConfigStore, AlertStore

    # v4 stores — 全部走 MySQL (MySQLRouter 默认)
    _v4_doc_store = DocumentStore()
    _v4_idx_store = IndexStore()
    _v4_cfg_store = ConfigStore()
    _v4_alt_store = AlertStore()

    _v4_bp = create_container_api_bp()
    init_api_bp(_v4_bp, _v4_doc_store, _v4_idx_store, _v4_cfg_store, _v4_alt_store)
    app.register_blueprint(_v4_bp)
    logger.info("已注册容器中心v4 API蓝图 (MySQL)")

    # [N3 修复 2026-06-13] 在所有蓝图注册后再注册 trace_id 中间件
    # 确保 before_request 在所有蓝图的 before_request 之前执行
    try:
        _5002_trace_init()
        logger.info('[TRACE] 5002 trace_id 中间件已注册（最后位置）')
    except Exception as e:
        logger.warning(f'[TRACE] 5002 中间件注册失败: {e}')
except Exception as e:
    logger.warning(f"无法注册容器中心v4 API蓝图: {e}")

@app.after_request
def set_charset_and_cors(resp):
    ct = resp.headers.get('Content-Type', '')
    if not ct or 'text/html' in ct:
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

# 加载配置
load_dotenv()
SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# 初始化容器中心
# 优先级：CONTAINER_DB_PATH 环境变量 > 集中配置默认路径
_env_db_path = os.getenv('CONTAINER_DB_PATH', '').strip()
if _env_db_path:
    if os.path.isabs(_env_db_path):
        _container_db_path = _env_db_path
    else:
        _container_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _env_db_path)
    logger.info(f'[容器中心API] 使用环境变量数据库路径: {_container_db_path}')
container_center = ContainerCenter()
logger.info('[容器中心API] 使用 MySQL: container_center 库')

# 启动 MySQL 连接健康巡检
try:
    from storage.mysql_storage import start_connection_monitor
    start_connection_monitor(container_center.storage, interval=60)
except Exception as e:
    logger.warning('[容器中心API] 连接巡检启动失败: %s', e)

# 初始化API签名校验器
api_secret_key = os.getenv('API_SECRET_KEY', '')
if api_secret_key:
    init_signature_validator()
    logger.info("API签名校验器已初始化")
else:
    logger.warning("API_SECRET_KEY 未设置，API签名验证已禁用")

# 报工程序 Webhook URL（用于推送数据到报工程序）
REPORT_SYSTEM_WEBHOOK_URL = os.environ.get('REPORT_SYSTEM_WEBHOOK_URL', '').strip()
if REPORT_SYSTEM_WEBHOOK_URL:
    logger.info(f"报工程序推送地址已配置: {REPORT_SYSTEM_WEBHOOK_URL}")
else:
    logger.warning("REPORT_SYSTEM_WEBHOOK_URL 未设置，报工程序推送已禁用")

# 报工程序人员同步 URL（用于推送企业微信人员到报工程序）
REPORT_SYSTEM_WORKER_SYNC_URL = os.environ.get('REPORT_SYSTEM_WORKER_SYNC_URL', '').strip()
if REPORT_SYSTEM_WORKER_SYNC_URL:
    logger.info(f"报工程序人员同步地址已配置: {REPORT_SYSTEM_WORKER_SYNC_URL}")
else:
    logger.warning("REPORT_SYSTEM_WORKER_SYNC_URL 未设置，人员同步已禁用")

# ──────────────────────────────────────────────
# 服务端增强模块初始化
# ──────────────────────────────────────────────
_server_health_checker = None
_server_deployment_manager = None
_server_audit_logger = None
_server_backup_manager = None
_server_clock_sync = global_clock_sync

try:
    _redis_for_server = None
    _rh = os.getenv('REDIS_HOST', '')
    if _rh:
        import redis as _r
        _redis_for_server = _r.Redis(
            host=_rh, port=int(os.getenv('REDIS_PORT', '6379')),
            decode_responses=True, socket_connect_timeout=int(os.environ.get('SOCKET_CONNECT_TIMEOUT', '5'))
        )
except Exception as e:
            logger.debug(f"Redis 连接失败（可选，不影响核心功能）: {e}")
            _redis_for_server = None

try:
    _es_hosts = os.environ.get('ES_HOSTS', '').strip()
    _server_health_checker = HealthChecker(
        redis_client=_redis_for_server,
        es_hosts=_es_hosts.split(',') if _es_hosts else None
    )
    logger.info("✓ 服务端健康检查器初始化完成")
except Exception as e:
    logger.warning(f"✗ 服务端健康检查器初始化失败: {e}")

try:
    _server_deployment_manager = DeploymentManager(
        backup_dir=os.environ.get('DEPLOY_BACKUP_DIR', '_backup'),
        config_dir=os.environ.get('CONFIG_DIR', '_config'),
        deploy_dir=os.environ.get('DEPLOY_DIR', '_deploy')
    )
    logger.info("✓ 服务端部署管理器初始化完成")
except Exception as e:
    logger.warning(f"✗ 服务端部署管理器初始化失败: {e}")

try:
    _es_hosts_audit = os.environ.get('ES_HOSTS', '').strip()
    _server_audit_logger = EnhancedAuditLogger(
        es_hosts=_es_hosts_audit.split(',') if _es_hosts_audit else None,
        redis_client=_redis_for_server
    )
    logger.info("✓ 服务端审计日志模块初始化完成")
except Exception as e:
    logger.warning(f"✗ 服务端审计日志模块初始化失败: {e}")

try:
    _server_backup_manager = EnhancedBackupManager(
        backup_dir=os.environ.get('ENHANCED_BACKUP_DIR'),
        redis_password=os.environ.get('REDIS_PASSWORD')
    )
    logger.info("✓ 服务端增强备份模块初始化完成")
except Exception as e:
    logger.warning(f"✗ 服务端增强备份模块初始化失败: {e}")

logger.info("✓ 服务端时钟同步已就绪")
logger.info(
    f"  服务端增强模块: "
    f"健康检查={'✓' if _server_health_checker else '✗'}, "
    f"部署管理={'✓' if _server_deployment_manager else '✗'}, "
    f"审计日志={'✓' if _server_audit_logger else '✗'}, "
    f"增强备份={'✓' if _server_backup_manager else '✗'}"
)

def _cleanup_expired_data():
    """启动时清理过期数据"""
    try:
        from core.config import Config
        retention_days = Config.DATA_RETENTION_DAYS
        result = container_center.storage.cleanup_expired_packages(retention_days)
        if isinstance(result, int):
            logger.info(f"[启动清理] 已清理 {result} 个过期包")
        elif isinstance(result, dict) and result.get('success'):
            if result.get('deleted_packages', 0) > 0:
                logger.info(f"[启动清理] 已清理过期数据: 包={result['deleted_packages']}, 截止日期={result['cutoff_date']}")
            else:
                logger.debug(f"[启动清理] 无过期数据需要清理，截止日期={result['cutoff_date']}")
        else:
            logger.warning(f"[启动清理] 清理失败: {result.get('error')}")
    except Exception as e:
        logger.warning(f"[启动清理] 清理任务执行异常: {e}")

cleanup_thread = ResilientThread(target=_cleanup_expired_data, daemon=True, name='cleanup-expired')
cleanup_thread.start()

CONFIG_VERSIONS_DOC_ID = 'global_config_versions'
CONFIG_VERSIONS_DOC_TYPE = 'config_version'
_config_lock = threading.Lock()

def _load_config_versions():
    """从 DocumentStore 加载配置版本数据"""
    try:
        doc = _v4_doc_store.get(CONFIG_VERSIONS_DOC_ID, CONFIG_VERSIONS_DOC_TYPE)
        if doc:
            return doc.get('doc_data', {})
    except Exception as e:
        logger.error(f"加载配置版本数据失败: {e}")
    return {}

def _save_config_versions(data):
    """保存配置版本数据到 DocumentStore"""
    with _config_lock:
        try:
            existing = _v4_doc_store.get(CONFIG_VERSIONS_DOC_ID, CONFIG_VERSIONS_DOC_TYPE)
            if existing:
                _v4_doc_store.update(CONFIG_VERSIONS_DOC_ID, data, CONFIG_VERSIONS_DOC_TYPE)
            else:
                _v4_doc_store.create(CONFIG_VERSIONS_DOC_TYPE, data,
                                     doc_id=CONFIG_VERSIONS_DOC_ID, status='active')
        except Exception as e:
            logger.error(f"保存配置版本数据失败: {e}")


# ──────────────────────────────────────────────
# 企业微信架构缓存（数据库 + 文件双重存储）
# ──────────────────────────────────────────────
ENTERPRISE_STRUCTURE_PATH = DB_PATHS['enterprise_structure']
_enterprise_lock = threading.Lock()

def _init_enterprise_db_table():
    """初始化企业架构数据库表（仅首次创建，绝不覆盖已有数据）"""
    try:
        es = container_center.storage.get_enterprise_structure()
        if es is None or not es.get('users'):
            # 只有表为空时才创建空记录
            users = es.get('users') if es else None
            if not users:
                container_center.storage.save_enterprise_structure({
                    'departments': [], 'users': [], 'updated_at': ''
                })
                logger.info("[企业架构] 数据库表已初始化（空白）")
            else:
                logger.info(f"[企业架构] 已有数据 ({len(users)} 人)，跳过初始化")
        else:
            logger.info(f"[企业架构] 数据库表已就绪 ({len(es.get('users',[]))} 人)")
    except Exception as e:
        logger.error(f"[企业架构] 初始化数据库表失败: {e}")

def _enterprise_db_save(departments, users, updated_at):
    """保存企业架构到数据库（MySQL 迁移版）"""
    try:
        container_center.storage.save_enterprise_structure({
            'departments': departments, 'users': users, 'updated_at': updated_at
        })
        return True
    except Exception as e:
        logger.error(f"[企业架构] 写入数据库失败: {e}")
    return False

def _enterprise_db_load():
    """从数据库加载企业架构（MySQL 迁移版）"""
    try:
        es = container_center.storage.get_enterprise_structure()
        if es:
            dept = es.get('departments', [])
            usr = es.get('users', [])
            upd = es.get('updated_at', '')
            if dept:
                return {
                    'departments': dept if isinstance(dept, list) else json.loads(dept),
                    'users': usr if isinstance(usr, list) else (json.loads(usr) if usr else []),
                    'updated_at': upd or ''
                }
    except Exception as e:
        logger.error(f"[企业架构] 读取数据库失败: {e}")
    return None

def _load_enterprise_structure():
    """加载企业微信架构缓存（数据库优先，文件兜底）"""
    db_data = _enterprise_db_load()
    if db_data:
        return db_data
    if os.path.exists(ENTERPRISE_STRUCTURE_PATH):
        try:
            with open(ENTERPRISE_STRUCTURE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载企业架构文件失败: {e}")
    return {'departments': [], 'users': [], 'updated_at': ''}

def _save_enterprise_structure(data):
    """保存企业微信架构缓存（数据库 + 文件双重写入）"""
    with _enterprise_lock:
        data['updated_at'] = _now_func().isoformat()
        depts = data.get('departments', [])
        users = data.get('users', [])
        _enterprise_db_save(depts, users, data['updated_at'])
        try:
            with open(ENTERPRISE_STRUCTURE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[企业架构] 已保存 {len(depts)} 个部门, {len(users)} 名用户 (DB+File)")
        except Exception as e:
            logger.error(f"保存企业架构文件失败: {e}")



def _push_enterprise_users_to_report():
    """推送企业微信用户列表到报工程序的人员同步端点"""
    if not REPORT_SYSTEM_WORKER_SYNC_URL:
        return
    try:
        data = _load_enterprise_structure()
        users = data.get('users', [])
        if not users:
            logger.info("[人员推送] 无企业微信用户数据，跳过")
            return
        seen = {}
        for u in users:
            uid = u.get('userid', '')
            if uid and uid not in seen:
                seen[uid] = u
        deduped = list(seen.values())
        payload = {
            'event_type': 'worker_sync',
            'timestamp': _now_func().isoformat(),
            'data': deduped
        }
        resp = requests.post(REPORT_SYSTEM_WORKER_SYNC_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            logger.info(f"[人员推送成功] {len(deduped)} 名用户推送至报工程序: {result.get('message', 'OK')}")
        else:
            logger.warning(f"[人员推送失败] HTTP {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        logger.warning("[人员推送] 报工程序不可达，跳过人员同步")
    except Exception as e:
        logger.warning(f"[人员推送异常] {e}")


# ──────────────────────────────────────────────
# API 端点：企业微信架构缓存
# ──────────────────────────────────────────────
@app.route('/api/enterprise/structure', methods=['POST'])
def save_enterprise_structure():
    """
    保存企业微信架构数据

    由 wechat_cloud.py 调用，保存从企业微信获取的部门/人员数据

    Request Body:
        {"departments": [...], "users": [...]}

    Returns:
        {"code": 0, "message": "企业架构已保存", "data": {"updated_at": "..."}}
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        depts = body.get('departments', [])
        users = body.get('users', [])
        if isinstance(depts, str):
            try: depts = json.loads(depts)
            except Exception: depts = []
        if isinstance(users, str):
            try: users = json.loads(users)
            except Exception: users = []
        if isinstance(depts, dict):
            depts = depts.get('departments', depts.get('data', []))
        if isinstance(users, dict):
            users = users.get('operators', users.get('users', users.get('data', [])))
        if not isinstance(depts, list):
            depts = []
        if not isinstance(users, list):
            users = []
        if not depts and not users:
            return jsonify({'code': 1, 'message': '数据为空'})
        data = {'departments': depts, 'users': users}
        _save_enterprise_structure(data)
        _push_enterprise_users_to_report()
        return jsonify({'code': 0, 'message': '企业架构已保存', 'data': {'updated_at': data['updated_at']}})
    except Exception as e:
        logger.exception(f"[企业架构] 保存异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/enterprise/structure', methods=['GET'])
def get_enterprise_structure():
    """
    获取企业微信架构缓存数据

    由调度中心调用，读取缓存的部门/人员数据

    Returns:
        {"code": 0, "data": {"departments": [...], "users": [...], "updated_at": "..."}}
    """
    try:
        data = _load_enterprise_structure()
        return jsonify({'code': 0, 'data': data})
    except Exception as e:
        logger.exception(f"[企业架构] 读取异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


def _load_operators_from_workers():
    """从 workers 表直接加载操作员列表（统一数据源）"""
    try:
        if not hasattr(container_center, 'storage') or container_center.storage is None:
            logger.warning('[操作员加载] container_center.storage 未初始化')
            return []

        rows = container_center.storage.fetch_all(
            'SELECT id, enterprise_id, name, role, department, status, '
            '       wechat_userid, phone, can_receive_wechat, can_send_wechat, '
            '       max_tasks, created_at, updated_at '
            'FROM workers WHERE status=%s ORDER BY id',
            ('active',)
        )
        if not rows:
            logger.warning('[操作员加载] workers 表为空')
            return []
        result = []
        for row in rows:
            if isinstance(row, dict):
                auto_id = row.get('id', 0) or 0
                enterprise_id = row.get('enterprise_id', '')
                name = row.get('name', '')
                role = row.get('role', '操作员')
                department = row.get('department', '')
                wechat_userid = row.get('wechat_userid', '') or enterprise_id
                phone = row.get('phone', '') or ''
                can_receive_wechat = bool(row.get('can_receive_wechat', 1))
                can_send_wechat = bool(row.get('can_send_wechat', 1))
                max_tasks = int(row.get('max_tasks', 10) or 10)
                created_at = row.get('created_at', '')
                updated_at = row.get('updated_at', '')
            else:
                auto_id = row[0] if len(row) > 0 else 0
                enterprise_id = row[1] if len(row) > 1 else ''
                name = row[2] if len(row) > 2 else ''
                role = row[3] if len(row) > 3 else '操作员'
                department = row[4] if len(row) > 4 else ''
                wechat_userid = row[6] if len(row) > 6 and row[6] else enterprise_id
                phone = row[7] if len(row) > 7 and row[7] else ''
                can_receive_wechat = bool(row[8]) if len(row) > 8 and row[8] is not None else True
                can_send_wechat = bool(row[9]) if len(row) > 9 and row[9] is not None else True
                max_tasks = int(row[10]) if len(row) > 10 and row[10] else 10
                created_at = row[11] if len(row) > 11 and row[11] else ''
                updated_at = row[12] if len(row) > 12 and row[12] else ''
            if not enterprise_id:
                continue
            result.append({
                'auto_id': int(auto_id) if auto_id else 0,
                'id': enterprise_id,
                'enterprise_id': enterprise_id,
                'name': name,
                'role': role,
                'department': department,
                'wechat_userid': wechat_userid,
                'phone': phone,
                'can_receive_wechat': can_receive_wechat,
                'can_send_wechat': can_send_wechat,
                'max_tasks': max_tasks,
                'created_at': str(created_at) if created_at else '',
                'updated_at': str(updated_at) if updated_at else '',
                'enabled': True,
            })
        logger.info(f'[操作员加载] 从 workers 表加载 {len(result)} 名操作员')
        return result
    except Exception as e:
        logger.warning(f'[操作员加载] 从 workers 表读取失败: {e}')
        return []


def _load_operators_from_enterprise():
    """从 workers 表加载真实操作员列表（数据库优先，JSON 兜底）"""
    workers_operators = _load_operators_from_workers()
    if workers_operators:
        return workers_operators

    es = _load_enterprise_structure()
    operators_raw = es.get('operators', {})
    if not operators_raw:
        return []
    if isinstance(operators_raw, dict):
        ops = operators_raw.values()
    else:
        ops = operators_raw
    result = []
    for op in ops:
        if not isinstance(op, dict):
            continue
        dept = op.get('department', '')
        if not dept and isinstance(op.get('team_name'), str):
            dept = op.get('team_name', '')
        result.append({
            'operator_id': op.get('id', op.get('operator_id', '')),
            'name': op.get('name', ''),
            'role': op.get('role', '操作员'),
            'department': dept,
            'team_name': dept,
            'wechat': op.get('wechat_userid', ''),
            'enabled': op.get('enabled', True),
        })
    return result


OPERATORS = _load_operators_from_enterprise()  # 启动时从数据库 workers 表加载

def success(data=None, message='success'):
    """[J6 修复 2026-06-13] 统一成功响应"""
    result = {'code': 0, 'message': message}
    if data is not None:
        result['data'] = data
    return jsonify(result)


def fail(code=1, message='error'):
    """[J6 修复 2026-06-14] 统一失败响应"""
    return jsonify({'code': code, 'message': message}), 400

@app.route('/api/process_sub_steps/<order_no>/<process_code>', methods=['GET'])
def verify_process_sub_step(order_no, process_code):
    """验证工序是否已同步到 container_center"""
    try:
        row = container_center.storage.fetch_one(
            'SELECT id, order_no, process_code, step_name, quantity FROM process_sub_steps '
            'WHERE order_no=%s AND process_code=%s LIMIT 1',
            (order_no, process_code))
        if row:
            return success(data={'received': True, 'detail': dict(row)})
        return success(data={'received': False, 'message': '未找到对应记录'})
    except Exception as e:
        return fail(code=ErrorCode.DB_ERROR[0], message=str(e))

# [J8 修复 2026-06-13] /api/process_names 重复路由 - L836 删掉（保留 L1260 的 get_process_names）
# 之前：L836 api_process_names 和 L1260 get_process_names 完全相同 URL
# 现在：L836 改为 redirect 到 L1260
# 已删除重复的 api_process_names 函数（与 L1260 get_process_names 完全相同）


def fail(code=None, message='操作失败', http_status=200):
    """[J6 修复 2026-06-13] 统一失败响应

    改进：
    1. code 默认从 ErrorCode.INTERNAL_ERROR 取
    2. 支持 HTTP 状态码分离（业务 code 与 HTTP code 解耦）
    3. message 缺失时自动从 ErrorCode 查表

    Args:
        code: 业务错误码（int），None 时用 INTERNAL_ERROR
        message: 中文错误信息，None 时从 ErrorCode 自动查
        http_status: HTTP 状态码（200/400/404/500）
    """
    if code is None:
        code = ErrorCode.INTERNAL_ERROR[0]
    if message == '操作失败' or not message:
        message = ErrorCode.get_message(code)
    resp = jsonify({'code': code, 'message': message})
    resp.status_code = http_status
    return resp

# ──────────────────────────────────────────────
# 报工程序推送
# ──────────────────────────────────────────────

_push_thread_lock = threading.Lock()
_push_active_count = 0
_PUSH_MAX_CONCURRENT = 3


def push_to_report_system(record: dict, event_type: str = 'process_updated'):
    """异步推送流程记录变更到报工程序

    使用后台线程发起HTTP POST请求，不阻塞当前请求。
    最多允许 _PUSH_MAX_CONCURRENT 个推送线程同时运行，超出则丢弃。

    Args:
        record: 流程记录字典
        event_type: 事件类型 (process_created/process_updated/process_deleted)
    """
    if not REPORT_SYSTEM_WEBHOOK_URL:
        return

    global _push_active_count
    with _push_thread_lock:
        if _push_active_count >= _PUSH_MAX_CONCURRENT:
            logger.warning(f"[推送] 推送线程已达上限({_PUSH_MAX_CONCURRENT})，丢弃推送: {event_type}")
            return
        _push_active_count += 1

    def _do_push():
        global _push_active_count
        try:
            payload = {
                'event_type': event_type,
                'timestamp': _now_func().isoformat(),
                'data': record
            }
            resp = requests.post(
                REPORT_SYSTEM_WEBHOOK_URL,
                json=payload,
                timeout=5
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 0:
                    logger.info(f"[推送成功] {event_type}: {record.get('order_no', record.get('id', '?'))}")
                else:
                    logger.warning(f"[推送失败] {event_type}: {result.get('message')}")
            else:
                logger.warning(f"[推送失败] HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            logger.warning(f"[推送超时] {event_type}: {REPORT_SYSTEM_WEBHOOK_URL}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"[推送连接失败] {event_type}: 无法连接到 {REPORT_SYSTEM_WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"[推送异常] {event_type}: {e}")
        finally:
            with _push_thread_lock:
                _push_active_count -= 1

    thread = ResilientThread(target=_do_push, daemon=True, name='push-notify')
    thread.start()


_sync_checker_running = True


def _sync_check_sender():
    """定时校对线程：每小时推送过去1小时内的变更数据到报工程序"""
    while _sync_checker_running:
        try:
            time.sleep(3600)
            if not REPORT_SYSTEM_WEBHOOK_URL:
                continue

            cutoff = (_now_func() - timedelta(hours=1)).isoformat()
            changed = container_center.storage.get_recently_updated_records(cutoff, limit=500)
            if not changed:
                logger.debug("[定时校对] 过去1小时无变更数据")
                continue

            payload = {
                'event_type': 'sync_check',
                'timestamp': _now_func().isoformat(),
                'data': changed
            }
            resp = requests.post(REPORT_SYSTEM_WEBHOOK_URL, json=payload, timeout=30)
            if resp.status_code == 200:
                logger.info(f"[定时校对成功] 推送 {len(changed)} 条记录到报工程序")
            else:
                logger.warning(f"[定时校对失败] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"[定时校对异常] {e}")


def _push_existing_records_on_startup():
    """启动时推送所有已有真实流程记录到报工程序"""
    if not REPORT_SYSTEM_WEBHOOK_URL:
        logger.warning("[启动推送] REPORT_SYSTEM_WEBHOOK_URL 未配置，跳过")
        return

    try:
        all_records = container_center.storage.get_all_process_records(fields='*')
    except Exception as e:
        logger.error(f"[启动推送] 获取流程记录失败: {e}")
        return

    if not all_records:
        logger.info("[启动推送] 无已有流程记录，跳过")
        return

    real_records = [
        r for r in all_records
        if not r.get('order_no', '').startswith('ORD-SCAN-')
           and not r.get('order_no', '').startswith('ORD-TEST-')
    ]

    test_records = len(all_records) - len(real_records)
    logger.info(f"[启动推送] 共 {len(all_records)} 条记录（真实 {len(real_records)} 条，测试 {test_records} 条），开始推送...")

    if not real_records:
        logger.info("[启动推送] 无真实流程记录，跳过")
        return

    # 先批量校对推送（使用 sync-check 端点）
    try:
        sync_check_url = REPORT_SYSTEM_WEBHOOK_URL.replace('/webhook', '/sync-check')
        batch_payload = {
            'event_type': 'sync_check',
            'timestamp': _now_func().isoformat(),
            'data': real_records
        }
        resp = requests.post(sync_check_url, json=batch_payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            logger.info(f"[启动推送成功] 批量推送 {len(real_records)} 条记录: {result.get('message', 'OK')}")
            return
        else:
            logger.warning(f"[启动推送] 批量推送失败 HTTP {resp.status_code}，切换为逐个推送")
    except Exception as e:
        logger.warning(f"[启动推送] 批量推送异常: {e}，切换为逐个推送")

    # 逐个推送兜底
    for record in real_records:
        push_to_report_system(record, 'process_created')
        time.sleep(0.2)


def get_current_operator():
    """从Token获取当前操作员"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT Token验证失败: {e}")
        return None

@app.route('/health')
def health():
    """健康检查（集成服务端健康检查器）"""
    base_info = {
        'service': 'container-center-api',
        'version': '1.0',
        'time': _now_func().isoformat(),
        'server_modules': {
            'signature_validator': bool(api_secret_key),
            'health_checker': _server_health_checker is not None,
            'deployment_manager': _server_deployment_manager is not None,
            'audit_logger': _server_audit_logger is not None,
            'backup_manager': _server_backup_manager is not None,
        }
    }
    if _server_health_checker:
        try:
            report = _server_health_checker.get_health_report(detailed=False)
            base_info['health_report'] = report
        except Exception as e:
            base_info['health_report'] = {'status': 'error', 'message': str(e)}
    return success(base_info)

@app.route('/')
def index():
    return jsonify({'code': 0, 'service': 'container_center', 'status': 'running'})

@app.route('/api/dashboard')
def api_dashboard_compat():
    return jsonify({'code': 0, 'message': 'dashboard not available, use /admin on port 5003'})

# ──────────────────────────────────────────────
# 主软件回调代理（容器中心 → 主软件）
# ──────────────────────────────────────────────
@app.route('/api/callback', methods=['POST'])
def proxy_main_software_callback():
    """
    主软件回调代理：容器中心接收回调请求，转发到主软件
    主软件地址从 MAIN_SOFTWARE_CALLBACK_TARGET 环境变量读取
    """
    target_url = os.environ.get(
        'MAIN_SOFTWARE_CALLBACK_TARGET',
        'http://localhost:5001/api/wechat/schedule/confirm'
    )
    payload = request.get_json(silent=True) or {}
    logger.info(f'[回调代理] 接收回调 → 转发到 {target_url} | 类型: {payload.get("type", "unknown")}')

    try:
        resp = requests.post(
            target_url,
            json=payload,
            timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))
        )
        if resp.status_code == 200:
            logger.info(f'[回调代理] 转发成功 | HTTP {resp.status_code}')
            try:
                return jsonify(resp.json()), resp.status_code
            except Exception:
                return success({'proxy_status': 'forwarded', 'target_status': resp.status_code})
        else:
            logger.warning(f'[回调代理] 转发异常 | HTTP {resp.status_code} | {resp.text[:200]}')
            return jsonify({'error': 'target_error', 'status': resp.status_code, 'detail': resp.text[:500]}), resp.status_code
    except requests.exceptions.ConnectionError:
        logger.error(f'[回调代理] 主软件连接失败: {target_url}')
        return jsonify({'error': 'target_unreachable', 'detail': f'无法连接到主软件: {target_url}'}), 502
    except Exception as e:
        logger.exception(f'[回调代理] 转发异常: {e}')
        return jsonify({'error': 'proxy_error', 'detail': str(e)}), 500

# ──────────────────────────────────────────────
# 3.01版本兼容API端点
# ──────────────────────────────────────────────
# OPERATORS 列表已统一从企业架构加载，见上方 _load_operators_from_enterprise()

@app.route('/api/health')
def api_health():
    """API健康检查（供3.01版本测试连接使用）"""
    return jsonify({
        'code': 0,
        'status': 'running',
        'service': 'container-api',
        'version': '3.0',
        'timestamp': _now_func().isoformat()
    })

@app.route('/api/status')
def api_status():
    """获取容器状态（供3.01版本刷新状态使用）"""
    pool_status = container_center.get_pool_status()
    return jsonify({
        'status': 'running',
        'version': '3.0',
        'service': 'container-api',
        'containers': pool_status.get('total_packages', 0),
        'active_tasks': pool_status.get('total_packages', 0),
        'pool_status': pool_status,
        'timestamp': _now_func().isoformat()
    })

@app.route('/api/operators', methods=['GET'])
def api_get_operators():
    """获取操作员列表（供调度中心调用）
    数据源优先级:
      1. workers 表 (MySQL) - 统一数据源
      2. enterprise_structure.json (operators 字段) - Fallback
    """
    try:
        operators_list = _load_operators_from_workers()
        if operators_list:
            logger.info(f'[/api/operators] 从 workers 表返回 {len(operators_list)} 名操作员')
            return jsonify({'code': 0, 'data': operators_list})

        logger.warning('[/api/operators] workers 表为空，fallback 到 enterprise_structure.json')
        es = container_center.storage.load_enterprise_structure() or {}

        operators_raw = es.get('operators', {})
        operators_list = []
        if isinstance(operators_raw, dict) and operators_raw:
            for op_id, op in operators_raw.items():
                if not isinstance(op, dict):
                    continue
                operators_list.append({
                    'id': op.get('id') or op_id,
                    'name': op.get('name', ''),
                    'department': op.get('department', ''),
                    'role': op.get('role', '操作员'),
                    'wechat_userid': op.get('wechat_userid', ''),
                    'enabled': op.get('enabled', True),
                    'max_tasks': op.get('max_tasks', 10),
                })
        elif isinstance(operators_raw, list) and operators_raw:
            for op in operators_raw:
                if not isinstance(op, dict):
                    continue
                operators_list.append({
                    'id': op.get('id', ''),
                    'name': op.get('name', ''),
                    'department': op.get('department', ''),
                    'role': op.get('role', '操作员'),
                    'wechat_userid': op.get('wechat_userid', ''),
                    'enabled': op.get('enabled', True),
                    'max_tasks': op.get('max_tasks', 10),
                })

        if not operators_list:
            users_raw = es.get('users', [])
            users = users_raw if isinstance(users_raw, list) else []
            if isinstance(users, dict):
                users = users.get('operators', users.get('users', []))
            if not isinstance(users, list):
                users = []
            operators_list = [{
                'id': u.get('userid', u.get('id', '')) if isinstance(u, dict) else str(u),
                'name': u.get('name', '') if isinstance(u, dict) else str(u),
                'department': u.get('department_name', u.get('department', '')) if isinstance(u, dict) else '',
                'role': u.get('role', '操作员') if isinstance(u, dict) else '操作员',
                'wechat_userid': u.get('userid', ''),
                'enabled': True,
                'max_tasks': 10,
            } for u in users]

        return jsonify({'code': 0, 'data': operators_list})
    except Exception as e:
        logger.warning(f'[/api/operators] 失败: {e}', exc_info=True)
        return jsonify({'code': 0, 'data': []})


@app.route('/api/v4/operators', methods=['GET'])
def api_v4_operators():
    """获取操作员列表（/api/v4版本，兼容ContainerCenterClient）"""
    return jsonify({'code': 0, 'data': OPERATORS})

@app.route('/api/v4/work_order', methods=['GET'])
def api_v4_work_orders():
    """获取工单/任务列表（/api/v4版本，兼容ContainerCenterClient）"""
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 50))
    status_filter = request.args.get('status')
    q = request.args.get('q')

    all_packages = container_center.storage.get_packages(limit=5000)
    items = []
    for pkg in all_packages:
        pkg_status = pkg.get('status', 'pending')
        if status_filter and pkg_status != status_filter:
            continue
        items.append({
            'id': pkg.get('id', ''),
            'title': pkg.get('title', ''),
            'status': pkg_status,
            'data_type': pkg.get('data_type', 'report'),
            'priority': pkg.get('priority', 'normal'),
            'target_operator': pkg.get('target_operator', ''),
            'content': pkg.get('content', {}),
            'created_at': pkg.get('created_at', ''),
            'distributed_at': pkg.get('distributed_at', ''),
            'acknowledged_at': pkg.get('acknowledged_at', ''),
            'completed_at': pkg.get('completed_at', ''),
            'related_order': pkg.get('related_order', ''),
            'related_process': pkg.get('related_process', ''),
            'source': pkg.get('source', ''),
        })

    total = len(items)
    start = (page - 1) * size
    paged = items[start:start + size]

    # RE-008 全字典中文化: 翻译 status/data_type/priority(英文原值保存在 *_code)
    try:
        from utils.i18n_zh import translate_payload
        translate_payload({'items': paged})
    except Exception as i18n_e:
        logger.debug(f'work_order 翻译失败,降级: {i18n_e}')

    return jsonify({
        'code': 0,
        'total': total,
        'page': page,
        'size': size,
        'items': paged
    })

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/process_names', methods=['GET'])
def get_process_names():
    """返回工序编码→名称映射表，可选含部门 [F16 T16.1 修复] 改用 process_records 内存聚合 + dispatch_cache 部门"""
    try:
        include_dept = request.args.get('include_dept') == '1'
        rows = _get_process_names_from_records()
        if include_dept:
            depts = _get_process_departments_from_cache()
            data = [{'process_code': r['process_code'],
                     'process_name': r['process_name'],
                     'department': depts.get(r['process_name']) or depts.get(r['process_code'])}
                    for r in rows]
            return jsonify({'code': 0, 'data': data})
        mapping = {r['process_code']: r['process_name'] for r in rows}
        return jsonify({'code': 0, 'data': mapping})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/process_departments', methods=['GET'])
def get_process_departments_api():
    """工序→部门绑定（兼容调度中心旧API） [F16 T16.1 修复] 改用 dispatch_cache"""
    try:
        mapping = _get_process_departments_from_cache()
        return jsonify({'code': 0, 'data': mapping})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/process_departments/<process_code>', methods=['PUT', 'POST'])
def save_process_department(process_code):
    """保存工序编码→部门绑定 [F16 T16.1 修复] 写到 dispatch_cache (不再 UPDATE process_names)"""
    try:
        body = request.get_json(force=True, silent=True) or {}
        dept = body.get('department', '')
        _sync_dispatch_process_dept(process_code, dept)
        return jsonify({'code': 0, 'message': f'{process_code} -> {dept}'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/process_departments/<process_code>', methods=['DELETE'])
def delete_process_department(process_code):
    """删除工序编码→部门绑定 [F16 T16.1 修复] 从 dispatch_cache 移除"""
    try:
        _sync_dispatch_process_dept(process_code, '')
        return jsonify({'code': 0, 'message': 'deleted'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/process_names/<process_name>', methods=['DELETE'])
def delete_process_name(process_name):
    """删除工序名称记录 [F16 T16.1 修复] 仅清 dispatch_cache 中对应映射 (process_records 真实数据保留)"""
    try:
        _sync_dispatch_process_dept(process_name, '')
        _sync_dispatch_process_dept(process_name, '')  # 双触发确保按 process_name 同步
        return jsonify({'code': 0, 'message': 'deleted'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/dispatch', methods=['POST'])
@app.route('/api/wechat/dispatch', methods=['POST'])
def dispatch_task():
    """发布任务到指定操作员（供3.01版本调用，兼容桌面端和微信端）"""
    raw_data = request.get_json(force=True, silent=True) or {}
    logger.info(f'[dispatch_task] 来源IP={request.remote_addr} 调用者={raw_data.get("operator_id","?")} 订单={raw_data.get("order_no","?")} 工序={raw_data.get("process","?")}')
    import os
    _log_file = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\logs\dispatch_callers.log'
    with open(_log_file, 'a', encoding='utf-8') as _f:
        from datetime import datetime
        _f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] IP={request.remote_addr} order={raw_data.get("order_no","?")} process={raw_data.get("process","?")} operator={raw_data.get("operator_id","?")}\n')

    outer_operator_id = None
    if 'task_data' in raw_data:
        outer_operator_id = raw_data.get('operator_id')
        data = raw_data['task_data']
        if outer_operator_id and not data.get('operator_id'):
            data['operator_id'] = outer_operator_id
    else:
        data = raw_data

    # [R13 T9] process_code SSOT 校验
    order_no = data.get('order_no')
    process = data.get('process', data.get('process_name', ''))
    process_code_input = data.get('process_code', '')
    from mobile_api_ai.process_code_validator import validate_process_code
    ok, resolved_code, err_msg = validate_process_code(
        scenario='dispatch_task',
        process_code=process_code_input,
        process_name=process,
        order_no=order_no,
    )
    if not ok:
        return fail(code=1002, message=err_msg)
    if resolved_code and not process_code_input:
        data['process_code'] = resolved_code
        process_code_input = resolved_code

    operator_id = data.get('operator_id')
    order_no = data.get('order_no')
    process = data.get('process', data.get('process_name', ''))
    quantity = data.get('quantity', 0)
    priority = data.get('priority', 'normal')
    source = data.get('source', 'main_software')
    flow_type = data.get('flow_type', '')

    # 去重：同订单+同工序 已有未完成工序则跳过 (v3.6.1: 改用 process_sub_steps 表)
    if order_no and process:
        try:
            existing = container_center.storage.fetch_one(
                'SELECT id FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND status NOT IN (%s, %s) LIMIT 1',
                (order_no, process, 'completed', 'withdrawn'))
            if existing:
                logger.info(f'[派工] 跳过重复: order={order_no} process={process}')
                return success(data={'duplicate': True, 'message': '该工序已派工，跳过'})
        except Exception:
            existing = None
        # 同时检查 data_packages（兼容保护）
        try:
            existing_dp = container_center.storage.fetch_one(
                'SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s AND status!=%s LIMIT 1',
                (order_no, process, 'completed'))
            if existing_dp and not existing:
                logger.info(f'[派工] data_packages 兼容跳过: order={order_no} process={process}')
                return success(data={'duplicate': True, 'message': '该工序已派工，跳过'})
        except Exception:
            pass

    # [Bug 1 Fix 2026-06-19] is_public=True 时允许空 operator_id（全员派工场景）
    if not operator_id and not data.get('is_public'):
        return fail(code=1001, message='缺少operator_id参数')

    operator = {
        'operator_id': operator_id, 'name': operator_id,
        'department': '', 'role': '操作员', 'wechat_userid': operator_id
    }
    # 尝试从 OPERATORS 查找真实姓名
    real_op = next((o for o in OPERATORS if o.get('id') == operator_id), None)
    if real_op:
        operator.update({'name': real_op.get('name', operator_id),
                         'department': real_op.get('department', ''),
                         'wechat_userid': real_op.get('wechat_userid', operator_id)})

    # 使用容器中心发布任务
    try:
        process_code = data.get('process_code', '')
        # 自动注册 P 开头 process_code 到映射表（含 flow_type）
        # [F16 T16.1 修复] 改用 register_process() 内存注册, 替代 INSERT IGNORE INTO process_names
        if process_code and process_code.upper().startswith('P') and process:
            try:
                base_code = process_code.split('-')[0].upper()
                from core.config import register_process
                register_process(process, process_code=base_code, category='process')
                logger.info(f'[工序映射] 自动注册: {base_code} → {process} ({flow_type})')
            except Exception:
                pass
        pkg = container_center.collect_report(
            order_no=order_no,
            process_name=process,
            record_id=0,
            operator_id=operator_id,
            planned_qty=quantity,
            process_code=process_code,
        )
        pkg.content['process_code'] = process_code
        pkg.content.update({
            'order_no': data.get('order_no', order_no),
            'quantity': quantity,
            'priority': priority,
            'source': source,
            'flow_type': flow_type or 'production',
            'is_broadcast': data.get('is_broadcast', 0),
            'remark': data.get('remark', ''),
            'unit': data.get('unit', ''),
        })
        if process_code:
            container_center.storage.execute(
                'UPDATE data_packages SET process_code=%s WHERE id=%s',
                (process_code, pkg.id))
            container_center.storage.execute(
                "UPDATE data_packages SET content=JSON_SET(content, '$.process_code', %s) "
                "WHERE related_order=%s AND related_process=%s AND data_type='process_task' AND content->>'$.source'='collect_report'",
                (process_code, order_no, process))
        if data.get('is_public'):
            pkg_dict = pkg.to_dict()
            pkg_dict['is_public'] = 1
            # [M2 广播标记 2026-06-19] 1=M2 全员广播（工序配置触发，仅部门群发 1 遍通知）
            pkg_dict['is_broadcast'] = 1 if data.get('is_broadcast') else 0
            container_center.storage.save_package(pkg_dict)
        else:
            pkg_dict = pkg.to_dict()
            pkg_dict['is_broadcast'] = 0
            container_center.storage.save_package(pkg_dict)

        # [M2 广播标记 2026-06-19] 同步 process_task 子任务（collect_report 内部创建）的 is_public/is_broadcast
        # 原因：collect_report 内部创建 process_task 时没传这两个字段，需 SQL 显式更新
        try:
            is_pub_val = 1 if data.get('is_public') else 0
            is_bc_val = 1 if data.get('is_broadcast') else 0
            container_center.storage.execute(
                "UPDATE data_packages SET is_public=%s, is_broadcast=%s "
                "WHERE related_order=%s AND related_process=%s AND data_type='process_task'",
                (is_pub_val, is_bc_val, order_no, process)
            )
        except Exception as e:
            logger.warning(f'[M2 广播] 同步 process_task.is_public/is_broadcast 失败: {e}')

        # 修补 T4 (F4.2): 同步写入 data_packages.flow_type 列 (T1 DDL 加的列)
        # 原因: content JSON 字段无法走 idx_pkg_flow 索引, T2 回填白跑
        effective_flow_type = flow_type or 'production'
        try:
            container_center.storage.execute(
                'UPDATE data_packages SET flow_type=%s WHERE id=%s',
                (effective_flow_type, pkg.id)
            )
        except Exception as e:
            logger.warning(f'[T4] 写 data_packages.flow_type 列失败: {e}')


        if operator_id:
            try:
                container_center.distributor.distribute(pkg.id, operator_id)
            except Exception as e:
                logger.warning(f'[3.01对接] 任务分配时警告: {e}')

        logger.info(f"[3.01对接] 派工成功: 订单{order_no}, 工序{process}, 操作员{operator['name']}")

        # 根据 process_code 前缀自动创建对应工作流
        if process_code:
            try:
                import uuid as _uuid
                rec_id = str(_uuid.uuid4())[:8]

                # 修补 T4 (F4.1): 推断逻辑与请求体入参解耦, 请求体优先
                # 优先级: data.flow_type (L976) > process_code 前缀推断 > 默认 'production'
                inferred_flow_type = None
                if process_code.startswith('P'):
                    flow_name = '生产工序'
                    prefix = 'SC'
                    flow_steps = [
                        {'name': '工单发布', 'role': '计划部', 'status_key': 'published'},
                        {'name': '排产制定', 'role': '生产部', 'status_key': 'scheduled'},
                        {'name': '生产执行', 'role': '生产部', 'status_key': 'in_production'},
                        {'name': '报工完成', 'role': '生产部', 'status_key': 'reported'},
                        {'name': '质量检验', 'role': '质检部', 'status_key': 'qc_passed'},
                        {'name': '完工入库', 'role': '仓库', 'status_key': 'completed'},
                    ]
                    inferred_flow_type = 'production'
                elif process_code.startswith('M'):
                    flow_name = '物料采购'
                    prefix = 'WL'
                    flow_steps = [
                        {'name': '物料申请', 'role': '采购部', 'status_key': 'material_requested'},
                        {'name': '任务确认', 'role': '采购部', 'status_key': 'material_confirmed'},
                        {'name': '回复采购期限', 'role': '采购部', 'status_key': 'material_deadline'},
                        {'name': '入库通知', 'role': '采购部', 'status_key': 'material_arrived'},
                        {'name': '物料出库', 'role': '生产部', 'status_key': 'material_delivered'},
                    ]
                    inferred_flow_type = 'material_purchase'
                elif process_code.startswith('X'):
                    flow_name = '外协任务'
                    prefix = 'WX'
                    flow_steps = [
                        {'name': '外协发单', 'role': '计划部', 'status_key': 'outsource_created'},
                        {'name': '外协确认', 'role': '外协厂', 'status_key': 'outsource_confirmed'},
                        {'name': '外协生产', 'role': '外协厂', 'status_key': 'outsource_production'},
                        {'name': '外协质检', 'role': '质检部', 'status_key': 'outsource_qc'},
                        {'name': '外协回厂', 'role': '仓库', 'status_key': 'outsource_returned'},
                        {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed'},
                        {'name': '入库', 'role': '仓库', 'status_key': 'completed'},
                    ]
                    inferred_flow_type = 'outsource'
                else:
                    flow_name, prefix, flow_steps = None, None, None

                # 请求体入参优先, 推断兜底, 默认 'production'
                flow_type = flow_type or inferred_flow_type or 'production'

                if flow_type:
                    container_center.storage.insert('process_records', {
                        'id': rec_id,
                        'process_type': flow_type,
                        'work_order_no': f'{prefix}-{order_no}',
                        'order_no': order_no,
                        'product_name': data.get('product_type', process),
                        'quantity': quantity,
                        'unit': data.get('unit', '件'),
                        'priority': priority,
                        'status': 'created',
                        'current_step': 0,
                        'steps': json.dumps(flow_steps, ensure_ascii=False),
                        'task_count': len(flow_steps),
                        'completed_task_count': 0,
                        'source': source,
                        'flow_type': flow_type,
                        'created_at': _now_func().isoformat(),
                    })
                    logger.info(f"[3.01对接] {flow_name}流程已创建: rec_id={rec_id} order={order_no}")
            except Exception as e:
                logger.warning(f"[3.01对接] 流程创建失败: {e}")

        try:
            dispatch_center_url = os.getenv('DISPATCH_CENTER_URL', 'http://localhost:5003')
            notify_url = f'{dispatch_center_url}/api/dispatch-center/task-notify'
            notify_payload = {
                'event_type': 'task_published',
                'order_no': data.get('order_no', order_no),
                'task_id': pkg.id,
                'process': process,
                'operator_id': operator_id,
                'operator_name': operator['name'],
                'quantity': quantity,
                'source': source,
                'timestamp': _now_func().isoformat()
            }
            import threading
            def notify_async():
                try:
                    resp = requests.post(notify_url, json=notify_payload, timeout=15)
                    logger.info(f"[3.01对接] 通知调度中心: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[3.01对接] 异步通知失败: {e}")
            t = threading.Thread(target=notify_async)
            t.start()
            # 完全异步，不 join 阻塞，避免请求线程被长时间占用
        except Exception as notify_err:
            logger.warning(f"[3.01对接] 通知调度中心失败: {notify_err}")

        return success(data={
            'task_id': pkg.id,
            'operator_id': operator_id,
            'operator_name': operator['name'],
            'order_no': order_no,
            'process': process
        })
    except Exception as e:
        logger.error(f"[3.01对接] 派工失败: {e}")
        return fail(code=500, message=f'派工失败: {str(e)}')

@app.route('/api/schedule/publish', methods=['POST'])
def schedule_publish():
    """
    排产发布接口（供3.01主软件调用）
    
    接收主软件发布的排产数据，通过容器中心存储为流程记录，
    供调度中心编排流转。
    """
    data = request.get_json(force=True, silent=True) or {}

    order_no = data.get('order_no', '')

    if not order_no:
        return jsonify({'code': 1001, 'success': False, 'message': '缺少order_no参数'})

    import uuid
    record_id = str(uuid.uuid4())[:8]
    
    # [F6 P9 2026-06-10] 确定流程类型: 优先读请求体 flow_type, 默认 production
    # 原"查 product_flow_map 映射表"逻辑已删除 (表 2026-06-10 DROP, 引用为 dangling ref)
    # 业务影响: 不再支持 product_type_id 隐式决定 flow_type, 调用方必须显式传 flow_type
    flow_type = data.get('flow_type') or 'production'

    # ─── 流程步骤定义 ───
    if flow_type == 'material_purchase':
        steps = [
            {'name': '物料申请', 'role': '采购部', 'status_key': 'material_requested'},
            {'name': '供应商确认', 'role': '采购部', 'status_key': 'material_confirmed'},
            {'name': '物料采购', 'role': '采购部', 'status_key': 'material_purchasing'},
            {'name': '物料到货', 'role': '仓库', 'status_key': 'material_arrived'},
            {'name': '质检入库', 'role': '质检部', 'status_key': 'material_qc'},
            {'name': '物料出库', 'role': '生产部', 'status_key': 'material_delivered'},
        ]
    elif flow_type == 'quality':
        steps = [
            {'name': '接收质检', 'role': '质检部', 'status_key': 'quality_received'},
            {'name': '外观检验', 'role': '质检部', 'status_key': 'quality_appearance'},
            {'name': '尺寸检验', 'role': '质检部', 'status_key': 'quality_dimension'},
            {'name': '性能检验', 'role': '质检部', 'status_key': 'quality_performance'},
            {'name': '判定结果', 'role': '质检部', 'status_key': 'quality_judged'},
            {'name': '质检放行', 'role': '质检部', 'status_key': 'quality_approved'},
        ]
    elif flow_type == 'repair':
        steps = [
            {'name': '故障报修', 'role': '维修部', 'status_key': 'repair_reported'},
            {'name': '维修接单', 'role': '维修部', 'status_key': 'repair_confirmed'},
            {'name': '故障诊断', 'role': '维修部', 'status_key': 'repair_diagnosed'},
            {'name': '维修执行', 'role': '维修部', 'status_key': 'repair_in_progress'},
            {'name': '功能测试', 'role': '维修部', 'status_key': 'repair_tested'},
            {'name': '验收确认', 'role': '维修部', 'status_key': 'repair_verified'},
            {'name': '维修完成', 'role': '维修部', 'status_key': 'completed'},
        ]
    elif flow_type == 'outsource':
        steps = [
            {'name': '外协发单', 'role': '计划部', 'status_key': 'outsource_created'},
            {'name': '外协确认', 'role': '外协厂', 'status_key': 'outsource_confirmed'},
            {'name': '外协生产', 'role': '外协厂', 'status_key': 'outsource_production'},
            {'name': '外协质检', 'role': '质检部', 'status_key': 'outsource_qc'},
            {'name': '外协回厂', 'role': '仓库', 'status_key': 'outsource_returned'},
            {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed'},
            {'name': '入库登记', 'role': '仓库', 'status_key': 'completed'},
            {'name': '发货', 'role': '仓库', 'status_key': 'shipped'},
        ]
    else:
        steps = [
            {'name': '工单发布', 'role': '计划部', 'status_key': 'published'},
            {'name': '排产制定', 'role': '生产部', 'status_key': 'scheduled'},
            {'name': '排产确认', 'role': '计划部', 'status_key': 'confirmed'},
            {'name': '生产执行', 'role': '生产部', 'status_key': 'in_production'},
            {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed', 'parallel': True},
            {'name': '报工完成', 'role': '生产部', 'status_key': 'reported'},
            {'name': '完工入库', 'role': '仓库', 'status_key': 'completed'},
            {'name': '发货', 'role': '仓库', 'status_key': 'shipped'},
        ]

    # ─── 工序代码前缀映射 ───
    SUB_STEP_CODE_PREFIX = {
        'material_purchase': 'M',
        'quality': 'Q',
        'repair': 'R',
        'outsource': 'O',
        'production': 'P',
    }
    step_code_prefix = SUB_STEP_CODE_PREFIX.get(flow_type, 'X')

    record = {
        'id': record_id,
        'process_type': flow_type,
        'order_no': order_no,
        'record_type': 'workflow',
        'prod_id': data.get('prod_id', 0),
        'product_name': data.get('product_type', '') or data.get('material', ''),
        'quantity': data.get('quantity', 0),
        'unit': data.get('unit', '米'),
        'customer_name': data.get('customer_name', ''),
        'delivery_date': data.get('delivery_date', ''),
        'priority': data.get('priority', 'high'),
        'status': 'created',
        'current_step': 0,
        'steps': steps,
        'task_count': 0,
        'completed_task_count': 0,
        'source': data.get('source', 'main_software'),
        'flow_type': flow_type,
        'template_id': data.get('template_id'),
        'content': {
            'customer_group': data.get('customer_group', ''),
            'product_type': data.get('product_type', ''),
            'material': data.get('material', ''),
            'mesh_size': data.get('mesh_size', ''),
            'wire_diameter': data.get('wire_diameter', ''),
            'width': data.get('width', ''),
            'length': data.get('length', ''),
            'surface_treatment': data.get('surface_treatment', ''),
            'special_requirements': data.get('special_requirements', ''),
            'remark': data.get('remark', ''),
            'plan_start': data.get('plan_start', ''),
            'plan_end': data.get('plan_end', ''),
            'extra_params': data.get('extra_params', {}),
        },
        'created_at': _now_func().isoformat(),
        'updated_at': _now_func().isoformat(),
    }

    try:
        # 去重：同 order_no 的 process_record 只创建一次（后续步骤只写 data_packages）
        exists_pr = container_center.storage.fetch_one(
            'SELECT id FROM process_records WHERE order_no=%s LIMIT 1', (order_no,))
        exists_pkg = container_center.storage.fetch_one(
            'SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s LIMIT 1',
            (order_no, data.get('process', '')))
        if exists_pkg:
            logger.info(f'[排产发布] 工序任务已存在: order={order_no} process={data.get("process","")}')
            return jsonify({
                'code': 0, 'success': True,
                'data': {'duplicate': True, 'message': '该工序任务已存在'},
            })

        # [P2 修复 2026-06-19] 不论 exists_pr 是 True/False，都确保 process_records 存在
        # 根因：之前 exists_pr=True 时跳过 save_process_record
        #       → 容器中心 process_records 表里没这条订单
        #       → 桌面端 publish_schedule verify `/api/processes/by-order/{order_no}` 返回 data=None
        #       → 12:30:00 触发 DELETE schedule_queue + 重新发布
        # 修复：save_process_record 已是 upsert 语义（存在则 update，不存在则 insert）
        #       → 不论 exists_pr 是什么状态，都执行一次 save_process_record 保持存在性
        try:
            container_center.storage.save_process_record(record)
            if exists_pr:
                logger.info(f'[排产发布] 工单已存在，刷新 process_records: order={order_no}, id={exists_pr["id"]}')
            else:
                logger.info(f'[排产发布] 新建工单: order_no={order_no}, record_id={record_id}')

            # ─── 同步写入 process_sub_steps ───
            try:
                for idx, step in enumerate(steps):
                    step_name = step.get('name', '')
                    if not step_name:
                        continue
                    step_code = f'{step_code_prefix}{str(idx + 1).zfill(2)}'
                    sub_step_id = f'{record_id[:4]}-{step_code}'
                    container_center.storage.insert('process_sub_steps', {
                        'id': sub_step_id,
                        'order_no': order_no,
                        'process_code': step_code,
                        'step_name': step_name,
                        'quantity': data.get('quantity', 0),
                        'completed_qty': 0,
                        'status': '待开始',
                        'operator': '',
                    })
                logger.info(f'[排产发布] process_sub_steps 已写入: order={order_no}, {len(steps)} 个工序')
            except Exception as _sub_e:
                logger.warning(f'[排产发布] process_sub_steps 写入失败(非致命): {_sub_e}')

        except Exception as _pr_e:
            logger.error(f'[排产发布] process_records 写入失败(非致命): {_pr_e}')
            # 不阻塞后续 data_package / dispatch_center register

        # 同步创建任务记录（新表，按 flow_type 写入独立表）
        try:
            pkg_id = str(uuid.uuid4())[:8]
            title = f"{order_no} - {data.get('process', data.get('product_type', ''))}"
            target_operator = data.get('operator_id', '')
            quantity = data.get('quantity', 0)
            priority = data.get('priority', 'normal')

            # 根据 flow_type 写入对应的新表
            if flow_type == 'material_purchase':
                container_center.storage.insert('material_records', {
                    'id': pkg_id,
                    'title': title,
                    'order_no': order_no,
                    'related_order': order_no,
                    'target_operator': target_operator,
                    'status': 'pending',
                    'quantity': quantity,
                    'priority': priority,
                    'source': 'schedule_publish',
                })
                logger.info(f'[排产发布] material_record 已创建: id={pkg_id}')
            elif flow_type == 'repair':
                container_center.storage.insert('repair_records', {
                    'id': pkg_id,
                    'title': title,
                    'order_no': order_no,
                    'target_operator': target_operator,
                    'status': 'reported',
                    'quantity': quantity,
                    'priority': priority,
                    'source': 'schedule_publish',
                })
                logger.info(f'[排产发布] repair_record 已创建: id={pkg_id}')
            elif flow_type == 'outsource':
                container_center.storage.insert('outsource_records', {
                    'id': pkg_id,
                    'title': title,
                    'order_no': order_no,
                    'target_operator': target_operator,
                    'status': 'pending',
                    'quantity': quantity,
                    'priority': priority,
                    'source': 'schedule_publish',
                })
                logger.info(f'[排产发布] outsource_record 已创建: id={pkg_id}')
            elif flow_type == 'production':
                container_center.storage.insert('schedule_records', {
                    'id': pkg_id,
                    'title': title,
                    'order_no': order_no,
                    'target_operator': target_operator,
                    'status': 'pending',
                    'quantity': quantity,
                    'priority': priority,
                    'source': 'schedule_publish',
                })
                logger.info(f'[排产发布] schedule_record 已创建: id={pkg_id}')
            else:
                # 兼容旧逻辑，写入 data_packages
                container_center.storage.insert('data_packages', {
                    'id': pkg_id,
                    'data_type': flow_type,
                    'title': title,
                    'related_order': order_no,
                    'related_process': data.get('process', ''),
                    'target_operator': target_operator,
                    'status': 'pending',
                    'content': json.dumps({
                        'order_no': order_no, 'flow_type': flow_type,
                        'product_name': data.get('product_type', '') or data.get('material', ''),
                        'quantity': quantity, 'unit': data.get('unit', '米'),
                        'customer_name': data.get('customer_name', ''),
                        'delivery_date': data.get('delivery_date', ''),
                        'completed_qty': 0,
                    }, ensure_ascii=False),
                    'source': 'schedule_publish',
                    'priority': priority,
                    'status': 'created',
                })
                logger.info(f'[排产发布] data_package 已创建: id={pkg_id}')
        except Exception as e:
            logger.warning(f'[排产发布] 任务记录创建失败(非致命): {e}')

        # 同步通知调度中心注册工单
        try:
            dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://localhost:5003')
            register_data = {
                'order_no': order_no,
                'flow_type': flow_type,
                'product_name': data.get('product_type', '') or data.get('material', ''),
                'quantity': data.get('quantity', 0),
                'unit': data.get('unit', '米'),
                'customer_name': data.get('customer_name', ''),
                'delivery_date': data.get('delivery_date', ''),
                'priority': data.get('priority', 'high'),
            }
            resp = requests.post(
                f'{dispatch_url}/api/dispatch-center/workorder/register',
                json=register_data,
                timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))
            )
            if resp.status_code == 200:
                logger.info(f"[排产发布] 已同步注册到调度中心: {order_no}")
            else:
                logger.warning(f"[排产发布] 调度中心注册返回非200: HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError:
            logger.warning("[排产发布] 调度中心不可达，跳过注册")
        except Exception as e:
            logger.warning(f"[排产发布] 通知调度中心异常: {e}")

        return jsonify({
            'code': 0,
            'success': True,
            'message': f'排产任务已发布: {order_no}',
            'data': {
                'record_id': record_id,
                'order_no': order_no
            }
        })
    except Exception as e:
        logger.error(f"[排产发布] 存储失败: {e}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': f'排产存储失败: {str(e)}'
        })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    operator_id = data.get('operator_id') or data.get('name') or ''

    operator = next((op for op in OPERATORS if op['id'] == operator_id), None)
    if not operator:
        operator = next((op for op in OPERATORS if op['name'] == operator_id), None)
    if not operator:
        return fail(code=1002, message='操作员不存在')

    token_payload = {
        'operator_id': operator_id,
        'name': operator['name'],
        'role': operator['role'],
        'team_name': operator.get('department', '默认组'),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')

    return success(data={
        'token': token,
        'operator': {
            'id': operator['id'],
            'name': operator['name'],
            'role': operator['role'],
            'team_name': operator.get('department', '默认组')
        }
    })

@app.route('/api/auth/verify', methods=['GET'])
def verify():
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='无效的Token')
    return success(data={'valid': True, 'operator': operator})

@app.route('/api/pool/status', methods=['GET'])
def get_pool_status():
    """获取容器池状态"""
    status = container_center.get_pool_status()
    return success(data=status)

@app.route('/api/processes', methods=['GET'])
def get_processes():
    """获取流程记录列表"""
    status = request.args.get('status')
    process_type = request.args.get('type')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))
    records = container_center.storage.get_process_records(
        status=status, process_type=process_type, search=search, limit=limit
    )
    return success(data=records)

@app.route('/api/processes/<record_id>', methods=['GET'])
def get_process(record_id):
    """获取单个流程记录"""
    record = container_center.storage.get_process_record(record_id)
    if not record:
        return fail(code=ErrorCode.PARAM_MISSING[0], message='流程记录不存在')
    return success(data=record)

@app.route('/api/processes', methods=['POST'])
def create_process():
    """创建流程记录"""
    data = request.get_json(force=True, silent=True) or {}
    if not data.get('order_no'):
        return fail(code=1001, message='缺少order_no')
    import uuid
    record = {
        'id': data.get('id') or str(uuid.uuid4())[:8],
        'process_type': data.get('process_type', 'production'),
        'order_no': data.get('order_no'),
        'product_name': data.get('product_name'),
        'quantity': data.get('quantity', 0),
        'unit': data.get('unit', '件'),
        'customer_name': data.get('customer_name'),
        'delivery_date': data.get('delivery_date'),
        'priority': data.get('priority', 'normal'),
        'status': data.get('status', 'created'),
        'current_step': data.get('current_step', 0),
        'steps': data.get('steps', []),
        'task_count': data.get('task_count', 0),
        'completed_task_count': data.get('completed_task_count', 0),
        'source': data.get('source'),
        'flow_type': data.get('flow_type'),
        'template_id': data.get('template_id'),
        'created_at': data.get('created_at') or _now_func().isoformat(),
        'updated_at': _now_func().isoformat(),
    }
    container_center.storage.save_process_record(record)
    push_to_report_system(record, 'process_created')
    return success(data=record)


@app.route('/api/processes/<record_id>', methods=['PUT'])
def update_process(record_id):
    """更新流程记录"""
    data = request.get_json(force=True, silent=True) or {}
    record = container_center.storage.get_process_record(record_id)
    if not record:
        return fail(code=404, message='流程记录不存在')
    for key in ['order_no', 'product_name', 'quantity', 'unit', 'customer_name',
                'delivery_date', 'priority', 'status', 'current_step', 'steps',
                'task_count', 'completed_task_count', 'flow_type', 'template_id']:
        if key in data:
            record[key] = data[key]
    record['updated_at'] = _now_func().isoformat()
    container_center.storage.save_process_record(record)
    push_to_report_system(record, 'process_updated')
    return success(data=record)

@app.route('/api/processes/<record_id>/status', methods=['PUT'])
def update_process_status(record_id):
    """更新流程状态"""
    data = request.get_json(force=True, silent=True) or {}
    status = data.get('status')
    if not status:
        return fail(code=1001, message='缺少status')
    completed_at = data.get('completed_at')
    completed_by = data.get('completed_by')
    container_center.storage.update_process_record_status(
        record_id, status, completed_at, completed_by
    )
    record = container_center.storage.get_process_record(record_id)
    if record:
        push_to_report_system(record, 'process_updated')
    return success(data={'id': record_id, 'status': status})


@app.route('/api/processes/<record_id>/template', methods=['PUT'])
def assign_process_template(record_id):
    """为流程指定消息模板"""
    data = request.get_json(force=True, silent=True) or {}
    template_id = data.get('template_id')
    if template_id is None:
        return fail(code=1001, message='缺少template_id')
    record = container_center.storage.get_process_record(record_id)
    if not record:
        return fail(code=404, message='流程记录不存在')
    container_center.storage.assign_template_to_process(record_id, template_id)
    record['template_id'] = template_id
    record['updated_at'] = _now_func().isoformat()
    push_to_report_system(record, 'process_updated')
    return success(data={'id': record_id, 'template_id': template_id})


@app.route('/api/processes/<record_id>/step', methods=['PUT'])
def update_process_step(record_id):
    """更新流程当前步骤"""
    data = request.get_json(force=True, silent=True) or {}
    step = data.get('current_step')
    if step is None:
        return fail(code=1001, message='缺少current_step')
    container_center.storage.update_process_record_step(record_id, int(step))
    record = container_center.storage.get_process_record(record_id)
    if record:
        push_to_report_system(record, 'process_updated')
    return success(data={'id': record_id, 'current_step': step})


@app.route('/api/processes/<record_id>/tasks', methods=['PUT'])
def update_process_tasks(record_id):
    """更新流程任务计数"""
    data = request.get_json(force=True, silent=True) or {}
    task_count = data.get('task_count', 0)
    completed_task_count = data.get('completed_task_count', 0)
    container_center.storage.update_process_record_task_count(
        record_id, task_count, completed_task_count
    )
    record = container_center.storage.get_process_record(record_id)
    if record:
        push_to_report_system(record, 'process_updated')
    return success(data={'id': record_id, 'task_count': task_count, 'completed_task_count': completed_task_count})

@app.route('/api/processes/<record_id>', methods=['DELETE'])
def delete_process(record_id):
    """删除流程记录"""
    record = container_center.storage.get_process_record(record_id)
    container_center.storage.delete_process_record(record_id)
    if record:
        push_to_report_system(record, 'process_deleted')
    return success(message='流程记录已删除')

@app.route('/api/processes/by-order/<order_no>', methods=['GET'])
def get_process_by_order(order_no):
    """根据订单号或工单编号获取流程记录"""
    record = container_center.storage.get_process_record_by_order(order_no)
    if not record:
        all_records = container_center.storage.get_all_process_records(fields='*')
        record = next((r for r in all_records if r.get('order_no') == order_no), None)
    if not record:
        return fail(code=404, message='流程记录不存在')
    return success(data=record)

# ═══════════════════════════════════════════════════════════════════════════════
# SSOT 端点：统一订单全流程状态查询 (v3.6.1)
# 用途：手机报工5008 和 调度中心5003 都通过此端点获取订单状态
# 桌面端直接读数据库（不走 API）
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/orders/full-status/<order_no>', methods=['GET'])
def api_orders_full_status(order_no):
    """统一订单全流程状态查询（SSOT 端点）

    数据源：
    - 订单主表: process_records
    - 生产工序: process_sub_steps
    - 质检: quality_records
    - 物料: material_records
    - 维修: repair_records
    - 外协: outsource_records
    - 排产: schedule_records

    返回各流程状态统计、整体进度、阻塞判定
    """
    import pymysql
    from core.config import CONTAINER_MYSQL_CFG
    try:
        conn = get_conn()
        cur = conn.cursor()
        result = {
            'order_no': order_no,
            'order_status': 'unknown',
            'order_status_label': '未知',
            'order_basic': {},
            'processes': {'total': 0, 'completed': 0, 'in_progress': 0, 'distributed': 0, 'pending': 0, 'withdrawn': 0},
            'quality': {'total': 0, 'passed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0},
            'material': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'withdrawn': 0},
            'repair': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0},
            'outsource': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'sent': 0},
            'schedule': {'total': 0, 'in_progress': 0, 'scheduled': 0, 'completed': 0},
            'source': 'container_center_ssot',
        }

        # 1. 订单主表
        cur.execute(
            "SELECT id, order_no, product_name, customer_name, quantity, unit, "
            "status, priority, delivery_date, created_at, updated_at "
            "FROM process_records WHERE order_no=%s LIMIT 1",
            (order_no,))
        order_row = cur.fetchone()
        if order_row:
            cols = [d[0] for d in cur.description]
            order_dict = dict(zip(cols, order_row))
            for k in ['created_at', 'updated_at', 'delivery_date']:
                if order_dict.get(k) and hasattr(order_dict[k], 'isoformat'):
                    order_dict[k] = order_dict[k].isoformat()
            result['order_basic'] = order_dict
            status = order_dict.get('status', 'unknown')
            result['order_status'] = status
            STATUS_LABELS = {
                'created': '已创建', 'planning': '排产中', 'processing': '进行中',
                'in_progress': '进行中', 'partial_completed': '部分完成',
                'completed': '已完成', 'cancelled': '已取消', 'withdrawn': '已撤回'
            }
            result['order_status_label'] = STATUS_LABELS.get(status, status)

        # 2. 生产工序
        total_qty = 0
        done_qty = 0
        cur.execute(
            "SELECT status, COUNT(*) as cnt, SUM(completed_qty) as done, SUM(quantity) as total "
            "FROM process_sub_steps WHERE order_no=%s AND status NOT IN ('withdrawn') "
            "GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['processes']['total'] += cnt
            if status in result['processes']:
                result['processes'][status] = cnt
            total_qty += float(row[3] or 0)
            done_qty += float(row[2] or 0)

        # 3. 质检
        cur.execute(
            "SELECT status, result, COUNT(*) as cnt FROM quality_records "
            "WHERE order_no=%s GROUP BY status, result",
            (order_no,))
        for row in cur.fetchall():
            status, res, cnt = row[0], row[1], row[2]
            result['quality']['total'] += cnt
            if status == 'completed':
                if res in ('pass', 'qualified'):
                    result['quality']['passed'] += cnt
                elif res in ('fail', 'unqualified'):
                    result['quality']['failed'] += cnt
            elif status in ('pending', 'distributed'):
                result['quality']['pending'] += cnt
            elif status == 'in_progress':
                result['quality']['in_progress'] += cnt

        # 4. 物料
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM material_records "
            "WHERE order_no=%s GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['material']['total'] += cnt
            if status in result['material']:
                result['material'][status] = cnt

        # 5. 维修
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM repair_records "
            "WHERE order_no=%s GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['repair']['total'] += cnt
            if status in result['repair']:
                result['repair'][status] = cnt

        # 6. 外协
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM outsource_records "
            "WHERE order_no=%s GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['outsource']['total'] += cnt
            if status in result['outsource']:
                result['outsource'][status] = cnt

        # 7. 排产
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM schedule_records WHERE order_no=%s "
            "AND (is_deleted = 0 OR is_deleted IS NULL) GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['schedule']['total'] += cnt
            if status in result['schedule']:
                result['schedule'][status] = cnt

        # 8. 整体进度
        result['overall_progress'] = round(min(1.0, done_qty / total_qty), 2) if total_qty > 0 else 0

        # 9. 阻塞判定
        is_blocked = False
        block_reasons = []
        if result['material']['total'] > 0 and result['material']['completed'] < result['material']['total']:
            mp = result['material']['pending'] + result['material']['in_progress']
            if mp > 0:
                is_blocked = True
                block_reasons.append(f"物料待办 {mp} 个")
        if result['quality']['failed'] > 0:
            is_blocked = True
            block_reasons.append(f"质检不合格 {result['quality']['failed']} 个")
        if result['outsource']['total'] > 0 and result['outsource']['completed'] < result['outsource']['total']:
            op = result['outsource']['pending'] + result['outsource']['sent']
            if op > 0:
                is_blocked = True
                block_reasons.append(f"外协待办 {op} 个")
        result['is_blocked'] = is_blocked
        result['block_reasons'] = block_reasons

        # 10. 兜底
        if not order_row:
            if result['processes']['total'] == 0:
                result['order_status'] = 'unknown'
                result['order_status_label'] = '订单不存在或无工序'
            elif result['processes']['completed'] == result['processes']['total']:
                result['order_status'] = 'completed'
                result['order_status_label'] = '已完成'
            elif result['processes']['in_progress'] > 0 or result['processes']['distributed'] > 0:
                result['order_status'] = 'processing'
                result['order_status_label'] = '进行中'

        conn.close()
        return success(data=result)
    except Exception as e:
        logger.exception('SSOT 订单状态查询失败')
        return fail(500, message=str(e))


@app.route('/api/orders/full-status-list', methods=['GET'])
def api_orders_full_status_list():
    """批量查询订单状态（SSOT 端点）

    参数:
      - limit: 限制条数，默认 50
      - status_filter: blocked/processing/completed/all
    """
    import pymysql
    from core.config import CONTAINER_MYSQL_CFG
    try:
        conn = get_conn()
        cur = conn.cursor()
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status_filter', 'all')

        cur.execute(
            "SELECT order_no, product_name, customer_name, status, quantity, delivery_date "
            "FROM process_records WHERE is_archived = 0 "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,))
        cols = [d[0] for d in cur.description]
        orders = [dict(zip(cols, r)) for r in cur.fetchall()]

        result_orders = []
        for o in orders:
            ono = o.get('order_no')
            if not ono:
                continue
            if o.get('delivery_date') and hasattr(o['delivery_date'], 'isoformat'):
                o['delivery_date'] = o['delivery_date'].isoformat()

            cur.execute(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed, "
                "SUM(quantity) as qty_total, SUM(completed_qty) as qty_done "
                "FROM process_sub_steps WHERE order_no=%s AND status != 'withdrawn'",
                (ono,))
            ps = cur.fetchone()
            proc_total = int(ps[0] or 0)
            proc_done = int(ps[1] or 0)
            qty_total = float(ps[2] or 0)
            qty_done = float(ps[3] or 0)

            cur.execute(
                "SELECT COUNT(*) FROM quality_records WHERE order_no=%s "
                "AND status='completed' AND result IN ('fail', 'unqualified')",
                (ono,))
            q_failed = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM material_records WHERE order_no=%s "
                "AND status NOT IN ('completed', 'withdrawn')",
                (ono,))
            m_pending = cur.fetchone()[0]

            is_blocked = q_failed > 0 or m_pending > 0
            progress = round(qty_done / qty_total, 2) if qty_total > 0 else 0

            result_orders.append({
                'order_no': ono,
                'product_name': o.get('product_name', ''),
                'customer_name': o.get('customer_name', ''),
                'order_status': o.get('status', 'unknown'),
                'quantity': qty_total,
                'completed_qty': qty_done,
                'progress': progress,
                'proc_total': proc_total,
                'proc_completed': proc_done,
                'quality_failed': q_failed,
                'material_pending': m_pending,
                'is_blocked': is_blocked,
                'delivery_date': o.get('delivery_date', ''),
            })

        if status_filter == 'blocked':
            result_orders = [x for x in result_orders if x['is_blocked']]
        elif status_filter == 'processing':
            result_orders = [x for x in result_orders if x['order_status'] in ('processing', 'in_progress') and not x['is_blocked']]
        elif status_filter == 'completed':
            result_orders = [x for x in result_orders if x['order_status'] == 'completed']

        conn.close()
        return success(data={'orders': result_orders, 'total': len(result_orders), 'source': 'container_center_ssot'})
    except Exception as e:
        logger.exception('SSOT 订单状态列表查询失败')
        return fail(500, message=str(e))


# [C6 修复 2026-06-13] 添加 /api/orders/<order_no> 路由
# 用途：app.py 的 C5 修复（订单校验）依赖此接口
# 数据源：本地表 orders_local（如果不存在则读 orders 兜底）
@app.route('/api/orders/<order_no>', methods=['GET'])
def api_get_order(order_no):
    """查询订单信息（消除跨库直查的读路径）"""
    import pymysql
    from core.config import CONTAINER_MYSQL_CFG
    try:
        conn = get_conn()  # [T5b 2026-06-14] 走连接池
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as c:
                # 优先读本地表（镜像表），兜底读原表
                try:
                    c.execute("SELECT * FROM orders_local WHERE order_no=%s LIMIT 1", (order_no,))
                    row = c.fetchone()
                    if row:
                        return success(data=row)
                except pymysql.OperationalError:
                    pass  # 表不存在，回退

                # 兜底：直接读 orders 表
                c.execute("SELECT * FROM orders WHERE order_no=%s LIMIT 1", (order_no,))
                row = c.fetchone()
                if row:
                    return success(data=row)
                return fail(message='订单不存在', code=ErrorCode.ORDER_NOT_FOUND[0], http_status=404)
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[ORDERS_QUERY] {order_no} 失败: {e}')
        return fail(message=f'查询失败: {e}', code=500), 500


# [同步冲突修复 2026-06-13] 8008 写 steel_belt 后回写此路由
# 用途：把 process_sub_steps 数据写入 container_center.process_sub_steps_local
#      避免 ETL 与 8008 双写冲突
# [Q3 修复 2026-06-13] 添加 IP 白名单 + 内部共享密钥
# [T17 修复 2026-06-14] 生产环境禁用白名单
# 之前：永远允许 localhost，攻击者只需伪装 localhost 来源即可绕过白名单
# 现在：仅开发环境允许 localhost，生产环境白名单为空（必须用共享密钥）
import os
if os.getenv('FLASK_ENV') == 'production' or os.getenv('PRODUCTION_MODE') == '1':
    _MIRROR_WHITELIST_IPS = frozenset()  # 生产：禁用 IP 白名单
else:
    _MIRROR_WHITELIST_IPS = frozenset(['127.0.0.1', '::1', 'localhost'])  # 开发：允许本机
# [P3 修复 2026-06-13] 强制要求环境变量配置密钥
# [K19 修复 2026-06-14] 使用与 sync_bridge.py 相同的默认值
_MIRROR_SHARED_SECRET = os.getenv('MIRROR_SHARED_SECRET', 'yuan-mirror-2026')
if _MIRROR_SHARED_SECRET == 'yuan-mirror-2026':
    logger.warning('[MIRROR] 使用默认密钥（生产环境应配置 MIRROR_SHARED_SECRET）')

# [RATE-LIMIT FIX 2026-06-14] 防止外部 IP 刷屏 WARNING 日志
_mirror_auth_warn_cache = {}
_mirror_auth_warn_lock = threading.Lock()
_MIRROR_WARN_INTERVAL = 300  # 同一 IP 同一原因，5分钟最多告警1次


def _check_mirror_auth():
    """检查 mirror 调用方是否在白名单中

    [Q12 修复 2026-06-13] 严格鉴权
    之前 BUG：
    - 优先用 X-Forwarded-For（攻击者可伪造）
    - 空密钥 == 空字符串（未配环境变量时鉴权通过！）

    [K19 修复 2026-06-14] 使用与 sync_bridge.py 相同的默认密钥
    - 默认密钥为 'yuan-mirror-2026'
    - 外部 IP 仍需严格密钥校验
    """
    from flask import request
    use_xff = os.getenv('TRUSTED_PROXY', '0') == '1'
    if use_xff:
        remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    else:
        remote_ip = request.remote_addr or ''

    # [K19 调试] 显示所有 headers
    logger.debug(f'[MIRROR] 请求 headers: {dict(request.headers)}')

    if not _MIRROR_SHARED_SECRET:
        return False, f'MIRROR_SHARED_SECRET 未配置，拒绝外部 IP'
    provided = request.headers.get('X-Mirror-Secret', '')
    logger.debug(f'[MIRROR] 配置密钥={_MIRROR_SHARED_SECRET}, 请求密钥={provided}')
    if not provided:
        return False, f'缺少 X-Mirror-Secret header'
    if provided != _MIRROR_SHARED_SECRET:
        return False, f'密钥错误'
    return True, 'ok'


@app.route('/api/process_sub_steps/mirror', methods=['POST'])
def api_process_sub_steps_mirror():
    """8008 → 5002 镜像写入 process_sub_steps_local"""
    # [Q3 修复 2026-06-13] 鉴权检查
    from flask import request
    auth_ok, auth_msg = _check_mirror_auth()
    if not auth_ok:
        use_xff = os.getenv('TRUSTED_PROXY', '0') == '1'
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip() if use_xff else (request.remote_addr or '')
        reason = f'[MIRROR] 鉴权失败: {auth_msg} (IP={ip})'
        now = time.time()
        with _mirror_auth_warn_lock:
            last = _mirror_auth_warn_cache.get(ip, 0)
            if now - last > _MIRROR_WARN_INTERVAL:
                _mirror_auth_warn_cache[ip] = now
                if len(_mirror_auth_warn_cache) > 1000:
                    expired = [k for k, v in _mirror_auth_warn_cache.items() if now - v > _MIRROR_WARN_INTERVAL]
                    for k in expired:
                        del _mirror_auth_warn_cache[k]
                logger.warning(reason)
        return fail(message=f'鉴权失败: {auth_msg}', code=403, http_status=403)

    import pymysql
    from core.config import CONTAINER_MYSQL_CFG
    try:
        data = request.get_json(silent=True) or {}
        # [D3 修复 2026-06-13] 字段名严格匹配源表
        if not data.get('uuid') or not data.get('order_no'):
            return fail(message='缺少必填字段 uuid/order_no', code=400)
        conn = _get_mysql_connection()  # [T5b 2026-06-14] 走连接池
        try:
            with conn.cursor() as c:
                # 使用 REPLACE INTO 幂等
                # [D2 修复] 字段补全到 13 个（匹配 8008 写入）
                c.execute("""
                    REPLACE INTO process_sub_steps_local
                    (uuid, process_id, process_record_id, order_no, step_name, batch_no,
                     quantity, qualified_qty, operator, operator_id, wechat_userid,
                     equipment_name, remark, record_date, source, overtime_hours,
                     synced, synced_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data.get('uuid'),
                    data.get('process_id', ''),
                    data.get('process_record_id', ''),
                    data.get('order_no'),
                    data.get('step_name', ''),
                    data.get('batch_no', ''),
                    data.get('quantity', 0),
                    data.get('qualified_qty', 0),
                    data.get('operator', ''),
                    data.get('operator_id', ''),
                    data.get('wechat_userid', ''),
                    data.get('equipment_name', ''),
                    data.get('remark', ''),
                    data.get('record_date', _now_func().strftime('%Y-%m-%d')),
                    data.get('source', 'sync_bridge'),
                    data.get('overtime_hours', 0),
                    data.get('synced', 1),
                    data.get('synced_at', _now_func().strftime('%Y-%m-%d %H:%M:%S')),
                    data.get('created_at', _now_func().strftime('%Y-%m-%d %H:%M:%S')),
                ))
            conn.commit()
            logger.info(f'[MIRROR] process_sub_steps_local 写入: uuid={data.get("uuid")[:8]}... order={data.get("order_no")}')
            return success(data={'mirror_uuid': data.get('uuid')})
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[MIRROR] 写入失败: {e}')
        return fail(message=f'写入失败: {e}', code=500), 500


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取当前员工的任务列表"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    # 支持 page_route 分流参数
    page_route = request.args.get('page_route', None)
    PAGE_TO_TYPES = {
        'scan_report': ['report', 'production'],
        'quality':     ['quality'],
        'material':    ['material', 'material_purchase'],
        'outsource':   ['outsource'],
    }

    status_filter = request.args.get('status', None)
    kwargs = {'limit': 100}
    if operator:
        kwargs['operator'] = operator['operator_id']
    if status_filter:
        kwargs['status'] = status_filter

    if page_route:
        data_types = PAGE_TO_TYPES.get(page_route, [])
        if not data_types:
            return fail(code=1004, message=f'未知的 page_route: {page_route}')
        # 多类型查询：合并每种类型的查询结果
        all_tasks = []
        for dt in data_types:
            all_tasks.extend(container_center.storage.get_packages(data_type=dt, **kwargs))
    else:
        all_tasks = container_center.storage.get_packages(**kwargs)

    # 修: DB data_type -> API type 映射 + 加工序编码
    DB_TO_API = {
        'process_report':   'report',
        'process_task':     'process',
        'quality_task':     'quality',
        'material_request': 'material',
        'material_pickup':  'material',
        'material_buy':     'material',
        'outsource_task':   'outsource',
        'approval':         'approval',
    }
    for t in all_tasks:
        raw = t.get('data_type', '')
        t['type'] = DB_TO_API.get(raw, raw)
        # process_code: 优先顶层, 没有则从 content 拿
        if not t.get('process_code'):
            t['process_code'] = (t.get('content') or {}).get('process_code', '')

    return success(data={
        'tasks': all_tasks,
        'total': len(all_tasks)
    })

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    pkg = container_center.storage.get_package(task_id)
    if not pkg:
        return fail(code=404, message='任务不存在')
    return success(data=pkg)

@app.route('/api/tasks/<task_id>/acknowledge', methods=['POST'])
def acknowledge_task(task_id):
    """确认任务接收"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    result = container_center.acknowledge_task(task_id, operator['operator_id'])
    if result.get('success'):
        return success(data=result, message='任务已确认')
    else:
        return fail(code=400, message=result.get('message', '确认失败'))

@app.route('/api/tasks/unacknowledged', methods=['GET'])
def get_unacknowledged_tasks():
    """获取未确认的任务"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    tasks = container_center.get_unacknowledged_tasks(operator['operator_id'])
    return success(data={
        'tasks': tasks,
        'total': len(tasks)
    })

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """完成任务"""
    operator = get_current_operator()
    if not operator:
        return fail(code=1002, message='请先登录')

    data = request.get_json(force=True, silent=True) or {}
    return_data = data.get('return_data', {})

    # 数据边界校验（服务端权威校验）
    quantity = return_data.get('quantity', 0)
    is_valid, error_msg = global_data_boundary.validate_report_request(
        order_no=return_data.get('order_no', ''),
        process=return_data.get('process', ''),
        quantity=quantity,
        user_id=operator['operator_id']
    )
    if not is_valid:
        logger.warning(f"完成任务数据校验失败: {error_msg}")
        return fail(code=400, message=error_msg)

    result = container_center.receive_return(task_id, return_data)

    if result.get('success') and _server_audit_logger:
        try:
            _server_audit_logger.log(
                operation_type='task',
                user_id=operator['operator_id'],
                user_name=operator.get('name', operator['operator_id']),
                action='task_complete',
                result='success',
                details={'task_id': task_id, 'return_data': return_data}
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败 (task_complete): {e}")

    return success(data=result)

def _validate_api_key():
    """验证API Key（用于主软件等简单集成）"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return False, "缺少 X-API-Key"
    # [BUG 修复 2026-06-19] HTTP 401 根因：服务端也读错环境变量
    # 兼容 3 种环境变量名（按优先级）
    expected_key = (
        os.getenv('CONTAINER_CENTER_API_KEY')
        or os.getenv('API_KEY')
        or os.getenv('CONTAINER_API_KEY')
        or os.getenv('API_SECRET_KEY')
    )
    if not expected_key:
        logger.warning("服务器未配置 API Key")
        return False, "服务器未配置 API Key"
    if api_key != expected_key:
        logger.warning(
            "API Key 验证失败: IP=%s, Path=%s, Method=%s",
            request.remote_addr, request.path, request.method
        )
        return False, "API Key 不匹配"
    return True, None

@app.route('/api/internal/publish', methods=['POST'])
def publish_task():
    """发布任务（内部接口 - 支持签名认证或API Key认证）

    v3.6.1 增强：幂等键机制 + 应用层去重 + 数据库约束 三层防护
    """
    api_key = request.headers.get('X-API-Key')
    if api_key:
        is_valid, error_msg = _validate_api_key()
        if not is_valid:
            return fail(code=401, message=error_msg)

    data = request.get_json(force=True, silent=True) or {}

    # 数据完整性校验（_checksum）
    input_checksum = data.pop('_checksum', None)
    if input_checksum:
        actual_checksum = DataIntegrity.calculate_hash(data)
        if actual_checksum != input_checksum:
            logger.warning(f"数据完整性校验失败: 期望{input_checksum[:8]}, 实际{actual_checksum[:8]}")
            return fail(code=401, message='数据完整性校验失败（数据可能被篡改）')

    task_type = data.get('task_type', 'report')
    title = data.get('title', '任务')
    content = data.get('content', {})
    operator_id = data.get('operator_id')
    priority = data.get('priority', 'normal')
    related_order = data.get('related_order')
    related_process = data.get('related_process')
    source = data.get('source', '')

    # ── v3.6.1: L1 接口层去重检查 ──
    if related_order and related_process:
        try:
            existing = container_center.storage.fetch_one(
                'SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s '
                "AND status NOT IN ('completed', 'withdrawn') LIMIT 1",
                (related_order, related_process))
            if existing:
                logger.info(f'[publish-去重] 跳过重复: order={related_order} process={related_process} existing_id={existing["id"]}')
                return success(data={
                    'task_id': existing['id'],
                    'duplicate': True,
                    'message': '该工序已发布，跳过重复'
                })
        except Exception as e:
            logger.warning(f'[publish-去重] 校验异常: {e}')

    # 数据边界校验（服务端权威校验）
    is_valid, error_msg = global_data_boundary.validate_report_request(
        order_no=related_order or '',
        process=related_process or '',
        quantity=content.get('quantity', 0) if isinstance(content, dict) else 0,
        user_id=operator_id or ''
    )
    if not is_valid:
        logger.warning(f"发布任务数据校验失败: {error_msg}")
        return fail(code=400, message=error_msg)

    # 如果来自主软件订单管理，使用默认操作员进行分发
    if source == '主软件_订单管理' and not operator_id:
        logger.warning('订单任务来自主软件_订单管理但未指定操作员，跳过分发')

    try:
        # 兜底：content 缺少 quantity 时从订单查询
        if isinstance(content, dict) and not content.get('quantity'):
            if related_order:
                try:
                    recs = container_center.storage.get_process_records_by_work_order(related_order)
                    if recs:
                        content['quantity'] = recs[0].get('quantity', 0)
                        content['planned_qty'] = content['quantity']
                except Exception:
                    pass
        if isinstance(content, dict) and not content.get('quantity'):
            content['quantity'] = 1  # 最终兜底

        pkg = container_center.collector.collect(
            data_type=task_type,
            title=title,
            content=content,
            operator_id=operator_id,
            priority=priority,
            related_order=related_order,
            related_process=related_process
        )

        # 如果是物料任务，同时写入 material_records 表
        if task_type == 'material':
            try:
                import uuid
                material_id = uuid.uuid4().hex[:8].upper()
                material_data = {
                    'id': material_id,
                    'title': title,
                    'content': content,
                    'source': source,
                    'priority': priority,
                    'status': 'pending',
                    'order_no': related_order or '',
                    'related_order': related_order or '',
                    'material_name': content.get('material', content.get('material_name', '')) if isinstance(content, dict) else '',
                    'material_spec': content.get('spec', '') if isinstance(content, dict) else '',
                    'unit': content.get('unit', '件') if isinstance(content, dict) else '件',
                    'warehouse': content.get('warehouse', '主仓库') if isinstance(content, dict) else '主仓库',
                    'planned_qty': content.get('quantity', 0) if isinstance(content, dict) else 0,
                    'completed_qty': 0,
                    'target_operator': operator_id or '',
                    'operator_id': operator_id or '',
                    'flow_type': 'material_purchase',
                }
                container_center.storage.insert('material_records', material_data)
                logger.info(f'[物料发布] material_record 已创建: id={material_id}, order_no={related_order}')
            except Exception as e:
                logger.warning(f'[物料发布] material_record 创建失败: {e}')

        # 如果没有指定负责人（来自主软件订单管理），不自动派单，等待调度中心手动派单
        if operator_id:
            container_center.distributor.distribute(pkg.id)

        if _server_audit_logger:
            try:
                _server_audit_logger.log(
                    operation_type='task',
                    user_id=operator_id or 'system',
                    user_name=operator_id or 'system',
                    action='task_publish',
                    result='success',
                    details={'task_id': pkg.id, 'task_type': task_type, 'title': title}
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败 (task_publish): {e}")

        return success(data={
            'task_id': pkg.id,
            'message': '任务已发布并分发'
        })
    except Exception as e:
        logger.exception(f"发布任务失败: {e}")
        return fail(code=500, message=f'发布失败: {str(e)}')


# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# 配置版本管理API
# ──────────────────────────────────────────────

@app.route('/api/internal/config/deploy', methods=['POST'])
@require_signature
def deploy_config():
    """
    部署配置（内部接口 - 需要API签名认证）

    请求体:
        config_name: 配置名称
        config_data: 配置数据
    """
    data = request.get_json(force=True, silent=True) or {}
    config_name = data.get('config_name')
    config_data = data.get('config_data')
    timestamp = data.get('timestamp', time.strftime('%Y-%m-%dT%H:%M:%S'))

    if not config_name or config_data is None:
        return fail(code=400, message='缺少 config_name 或 config_data')

    version = _now_func().strftime('%Y%m%d%H%M%S')

    entry = {
        'version': version,
        'config_name': config_name,
        'config_data': config_data,
        'deployed_at': timestamp,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    versions = _load_config_versions()
    if config_name not in versions:
        versions[config_name] = []
    versions[config_name].append(entry)

    max_versions = int(os.getenv('CONFIG_MAX_VERSIONS', '20'))
    if len(versions[config_name]) > max_versions:
        versions[config_name] = versions[config_name][-max_versions:]

    _save_config_versions(versions)

    logger.info(f"配置已部署: {config_name} (版本: {version})")
    return success(data={'config_name': config_name, 'version': version})


@app.route('/api/internal/config/versions/<config_name>', methods=['GET'])
def get_config_versions(config_name):
    """
    获取配置版本列表

    Args:
        config_name: 配置名称
    """
    versions = _load_config_versions()
    config_versions = versions.get(config_name, [])

    return success(data={
        'config_name': config_name,
        'versions': config_versions,
        'total': len(config_versions)
    })


@app.route('/api/internal/config/rollback', methods=['POST'])
@require_signature
def rollback_config():
    """
    回滚配置（内部接口 - 需要API签名认证）

    请求体:
        config_name: 配置名称
        version: 目标版本号
    """
    data = request.get_json(force=True, silent=True) or {}
    config_name = data.get('config_name')
    target_version = data.get('version')

    if not config_name or not target_version:
        return fail(code=400, message='缺少 config_name 或 version')

    versions = _load_config_versions()
    config_versions = versions.get(config_name, [])

    target = next((v for v in config_versions if v['version'] == target_version), None)
    if not target:
        return fail(code=404, message=f'版本 {target_version} 不存在')

    logger.info(f"配置已回滚: {config_name} -> 版本 {target_version}")
    return success(data={
        'config_name': config_name,
        'version': target_version,
        'config_data': target.get('config_data')
    })


# ──────────────────────────────────────────────
# 外协管理 API
# ──────────────────────────────────────────────

OUTSOURCE_QUERY_LIMIT = int(os.getenv('OUTSOURCE_QUERY_LIMIT', '2000'))
_OUTSOURCE_CACHE = threading.local()

def _get_outsource_records(status: str = None) -> list:
    """获取外协记录列表（单次请求内缓存结果）"""
    cache_key = f'outsource_{status or "all"}'
    cached = getattr(_OUTSOURCE_CACHE, cache_key, None)
    if cached is not None:
        return cached
    records = container_center.storage.get_packages(
        data_type='outsource_task', status=status, limit=OUTSOURCE_QUERY_LIMIT
    ) or []
    setattr(_OUTSOURCE_CACHE, cache_key, records)
    return records


def _update_outsource_extra(record_id: str, status: str, **extra) -> Optional[Dict]:
    """更新外协记录额外字段"""
    target = container_center.storage.get_package(record_id)
    if not target or target.get('data_type') != 'outsource':
        return None
    content = target.get('content', {})
    if isinstance(content, str):
        import json as _json
        content = _json.loads(content)
    content.update(extra)
    container_center.storage.update_package(record_id, {'content': content, 'status': status})
    return target


@app.route('/api/outsource/records', methods=['GET'])
def list_outsource_records():
    """获取外协记录列表"""
    try:
        status = request.args.get('status')
        records = _get_outsource_records(status)
        records.sort(key=lambda r: str(r.get('created_at') or ''), reverse=True)
        return success(data=records)
    except Exception as e:
        logger.exception('获取外协记录列表异常')
        return fail(code=500, message=str(e))


@app.route('/api/outsource/records/<record_id>', methods=['GET'])
def get_outsource_record(record_id):
    """获取单条外协记录"""
    try:
        target = container_center.storage.get_package(record_id)
        if not target or target.get('data_type') != 'outsource':
            return fail(code=404, message='记录不存在')
        return success(data=target)
    except Exception as e:
        logger.exception('获取外协记录异常')
        return fail(code=500, message=str(e))


@app.route('/api/internal/outsource/publish', methods=['POST'])
@require_signature
def publish_outsource_task():
    """发布外协任务（内部接口 - 需要API签名认证）"""
    data = request.get_json(force=True, silent=True) or {}

    input_checksum = data.pop('_checksum', None)
    if input_checksum:
        actual_checksum = DataIntegrity.calculate_hash(data)
        if actual_checksum != input_checksum:
            logger.warning(f"外协数据完整性校验失败: 期望{input_checksum[:8]}, 实际{actual_checksum[:8]}")
            return fail(code=401, message='数据完整性校验失败')

    order_no = data.get('order_no', '').strip()
    process_name = data.get('process_name', '').strip()
    process_seq = data.get('process_seq', 1)
    planned_qty = data.get('planned_qty', 0)
    outsource_remark = data.get('outsource_remark', '').strip()
    operator_id = data.get('operator_id', '').strip()

    if not order_no or not process_name:
        return fail(code=400, message='订单号和工序名不能为空')

    is_valid, error_msg = global_data_boundary.validate_report_request(
        order_no=order_no,
        process=process_name,
        quantity=planned_qty,
        user_id=operator_id
    )
    if not is_valid:
        logger.warning(f"外协任务数据校验失败: {error_msg}")
        return fail(code=400, message=error_msg)

    try:
        pkg = container_center.collect_outsource(
            order_no=order_no,
            process_name=process_name,
            process_seq=process_seq,
            planned_qty=planned_qty,
            outsource_remark=outsource_remark,
            operator_id=operator_id
        )
        container_center.distributor.distribute(pkg.id)

        if _server_audit_logger:
            try:
                _server_audit_logger.log(
                    operation_type='outsource',
                    user_id=operator_id or 'system',
                    user_name=operator_id or 'system',
                    action='outsource_publish',
                    result='success',
                    details={'outsource_id': pkg.id, 'order_no': order_no, 'process': process_name, 'qty': planned_qty}
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败 (outsource_publish): {e}")

        return success(data={'id': pkg.id, 'message': '外协任务已发布并分发'})
    except Exception as e:
        logger.exception(f"发布外协任务失败: {e}")
        return fail(code=500, message=f'发布失败: {str(e)}')


@app.route('/api/outsource/records/<record_id>/feedback', methods=['POST'])
def feedback_outsource_record(record_id):
    """外协反馈（承诺天数）"""
    body = request.get_json(force=True, silent=True) or {}
    promised_days = body.get('promised_days')
    if promised_days is None:
        return fail(code=400, message='承诺天数不能为空')
    promised_days = int(promised_days)
    promised_date = (_now_func() + timedelta(days=promised_days)).strftime('%Y-%m-%d %H:%M:%S')
    result = _update_outsource_extra(record_id, 'processing',
        promised_days=promised_days,
        promised_date=promised_date,
        feedback_at=_now_func().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return fail(code=404, message='记录不存在')
    return success(message=f'已反馈：承诺 {promised_days} 天后完成')


@app.route('/api/outsource/records/<record_id>/complete', methods=['POST'])
def complete_outsource_record(record_id):
    """完成外协任务"""
    result = _update_outsource_extra(record_id, 'completed',
        completed_at=_now_func().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return fail(code=404, message='记录不存在')

    if _server_audit_logger:
        try:
            _server_audit_logger.log(
                operation_type='outsource',
                user_id='system',
                user_name='system',
                action='outsource_complete',
                result='success',
                details={'outsource_id': record_id, 'status': 'completed'}
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败 (outsource_complete): {e}")

    return success(message='外协任务已完成')


@app.route('/api/outsource/records/<record_id>/receive', methods=['POST'])
def receive_outsource_record(record_id):
    """外协收货确认"""
    result = _update_outsource_extra(record_id, 'received',
        received_at=_now_func().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return fail(code=404, message='记录不存在')

    if _server_audit_logger:
        try:
            _server_audit_logger.log(
                operation_type='outsource',
                user_id='system',
                user_name='system',
                action='outsource_receive',
                result='success',
                details={'outsource_id': record_id, 'status': 'received'}
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败 (outsource_receive): {e}")

    return success(message='已确认收货入库')


@app.route('/api/outsource/config', methods=['GET'])
def get_outsource_config():
    """获取外协配置"""
    from container_config import container_config as cc_cfg
    cfg = cc_cfg.get_outsourc_config()
    return success(data={
        'enabled': cfg.enabled,
        'default_operator_id': cfg.default_operator_id,
        'remind_days': cfg.remind_days,
        'overdue_remind_times': cfg.overdue_remind_times,
    })


@app.route('/api/outsource/config', methods=['POST'])
def update_outsource_config():
    """更新外协配置"""
    body = request.get_json(force=True, silent=True) or {}
    from container_config import container_config as cc_cfg
    cc_cfg.update_outsourc_config(**body)
    return success(message='配置已更新')


@app.route('/api/wechat/get_access_token', methods=['GET'])
def wechat_get_access_token():
    """
    获取企业微信 access_token（通过容器中心配置）

    容器中心所在服务器配置了 WECHAT_CORP_ID / WECHAT_AGENT_ID / WECHAT_SECRET，
    wechat_cloud.py 通过此端点获取 token，替代本地环境变量。

    Returns:
        {"code": 0, "data": {"access_token": "xxx"}}
    """
    try:
        from wechat_app_bot import WeChatAppBot
        corp_id = os.environ.get('WECHAT_CORP_ID', '')
        agent_id = os.environ.get('WECHAT_AGENT_ID', '')
        secret = os.environ.get('WECHAT_SECRET', '')
        if not corp_id or not agent_id or not secret:
            return jsonify({'code': 500, 'message': '容器中心未配置企业微信参数'}), 500
        bot = WeChatAppBot(corp_id, agent_id, secret)
        token = bot.get_access_token()
        if not token:
            return jsonify({'code': 500, 'message': '获取access_token失败'}), 500
        return jsonify({'code': 0, 'data': {'access_token': token}})
    except Exception as e:
        logger.error(f"[容器中心] 获取access_token异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


def _shutdown_all():
    """容器中心API服务器完整关闭：停止线程 + 关闭数据库 + 释放资源"""
    logger.info('开始容器中心API服务器关闭流程...')

    if desktop_callback_manager:
        try:
            desktop_callback_manager.stop()
            logger.info('桌面端回调管理器已停止')
        except Exception as e:
            logger.warning(f'停止桌面端回调管理器时异常: {e}')

    global _sync_checker_running
    _sync_checker_running = False
    logger.info('定时校对线程已标记停止')

    try:
        if hasattr(container_center, 'storage') and container_center.storage:
            container_center.storage.disconnect()
            logger.info('容器中心数据库连接已关闭')
    except Exception as e:
        logger.warning(f'关闭容器中心数据库连接时异常: {e}')

    logger.info('容器中心API服务器关闭完成')


# ════════════════════════════════════════
# [T41.6 修复 2026-06-14] api_create_sub_step 移到 if-main 之前
# 之前：函数在 if-main 块内，exec(serve) 阻塞 → serve() 前 add_url_rule 找不到函数定义
# 现在：函数在模块级定义，装饰器正常执行
# ════════════════════════════════════════
@app.route('/api/process_sub_step', methods=['POST'])
@require_api_key
def api_create_sub_step():
    """创建子步骤（分批入库/发货）"""
    try:
        data = request.get_json(force=True)
        if not data:
            return fail('请求数据为空')
        order_no = data.get('order_no', '')
        step_name = data.get('step_name', '')
        operator = data.get('operator', '')
        remark = data.get('remark', '')
        qty_valid, qty_result = _validate_quantity(data.get('quantity'))
        if not qty_valid:
            return fail(message=qty_result, code=400)
        quantity = qty_result
        if step_name not in ALLOWED_STEP_NAMES:
            return fail(message=f'step_name 不合法，允许值: {sorted(ALLOWED_STEP_NAMES)}', code=400)
        order_ok, order_err = _check_order_exists(order_no)
        if not order_ok:
            return fail(message=order_err, code=400)
        import uuid
        today = _now_func().strftime('%Y%m%d')
        prefix = 'STK' if '入库' in step_name else 'SHP'
        batch_no = f'{prefix}-{today}-{uuid.uuid4().hex[:6].upper()}'
        record = {
            'id': str(uuid.uuid4()), 'order_no': order_no, 'step_name': step_name,
            'batch_no': batch_no, 'quantity': quantity, 'operator': operator,
            'remark': remark, 'created_at': _now_func().isoformat()
        }
        ok = container_center.add_sub_step(record)
        if not ok:
            return fail('保存子步骤失败')
        logger.info('报工审核: %s %s 数量=%s 操作人=%s', step_name, batch_no, quantity, operator or 'system')
        try:
            from core.db_compat import get_conn
            _cc_conn = get_conn()
            try:
                with _cc_conn.cursor() as _cc_cur:
                    _cc_cur.execute("""
                        REPLACE INTO process_sub_steps_local
                        (uuid, process_id, process_record_id, order_no, step_name, batch_no,
                         quantity, qualified_qty, operator, operator_id, wechat_userid,
                         equipment_name, remark, record_date, source, overtime_hours,
                         synced, synced_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        record['id'], data.get('process_id', ''), data.get('process_record_id', ''),
                        record['order_no'], record['step_name'], record['batch_no'],
                        record['quantity'], data.get('qualified_qty', record['quantity']),
                        record['operator'], data.get('operator_id', ''),
                        data.get('wechat_userid', ''), data.get('equipment_name', ''),
                        data.get('remark', ''), data.get('record_date', _now_func().strftime('%Y-%m-%d')),
                        data.get('source', 'mobile'), data.get('overtime_hours', 0),
                        data.get('synced', 0), data.get('synced_at', None), record['created_at'],
                    ))
                _cc_conn.commit()
                logger.info(f'[Q2] 5002→process_sub_steps_local: uuid={record["id"][:8]}...')
            finally:
                _cc_conn.close()
        except Exception as _e:
            logger.warning(f'[Q2] 镜像失败: {_e}')
        try:
            import threading
            def _notify():
                from utils.trace import traced_request
                _url = os.getenv('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008') + '/api/sync/sub-step-report'
                try:
                    traced_request('POST', _url, json={
                        'order_no': order_no, 'step_name': step_name,
                        'quantity': quantity, 'operator': operator,
                    }, timeout=5)
                except Exception:
                    pass
            threading.Thread(target=_notify, daemon=True).start()
        except Exception:
            pass
        advanced = False
        try:
            cur_find = conn.cursor()
            cur_find.execute(
                "SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s LIMIT 1",
                (order_no, step_name))
            found = cur_find.fetchone()
            cur_find.close()
            if found:
                process_id = found[0] if isinstance(found, tuple) else found.get('id')
                proc = container_center.storage.get_process_record(process_id)
            if proc:
                steps_raw = proc.get('steps', [])
                if isinstance(steps_raw, str):
                    try:
                        steps_raw = json.loads(steps_raw)
                    except (json.JSONDecodeError, TypeError):
                        steps_raw = []
                cur = int(proc.get('current_step', 0))
                if steps_raw and cur < len(steps_raw):
                    cur_step_name = steps_raw[cur].get('name', '') if isinstance(steps_raw[cur], dict) else ''
                    if cur_step_name and step_name == cur_step_name:
                        next_step = cur + 1
                        container_center.storage.update_process_record_step(process_id, next_step)
                        proc['current_step'] = next_step
                        proc['updated_at'] = _now_func().isoformat()
                        if next_step >= len(steps_raw):
                            container_center.storage.update_process_record_status(process_id, 'completed')
                            proc['status'] = 'completed'
                        advanced = True
                        logger.info('步骤自动推进: %s %s→%s (index %d→%d)', order_no, cur_step_name,
                                     steps_raw[next_step].get('name', '完成') if next_step < len(steps_raw) else '流程结束',
                                     cur, next_step)
                        push_to_report_system(proc, 'process_updated')
        except Exception as e:
            logger.warning('报工后自动推进步骤异常(非致命): %s', e)
        summary = container_center.get_sub_step_summary(order_no)
        if advanced:
            summary['step_advanced'] = True
        return success({'record': record, 'summary': summary}, '报工成功')
    except Exception as e:
        logger.exception(f'创建子步骤异常: {e}')
        return fail(message=f'创建子步骤失败: {e}')


@app.route('/api/process_sub_steps/<order_no>', methods=['GET'])
@require_api_key
def api_get_sub_steps(order_no):
    """获取流程的所有子步骤"""
    try:
        steps = container_center.get_sub_steps(order_no)
        return success(steps)
    except Exception as e:
        logger.exception(f'获取子步骤列表异常: {e}')
        return fail(message=f'获取子步骤列表失败: {e}')


@app.route('/api/process_sub_step_summary/<order_no>', methods=['GET'])
@require_api_key
def api_get_sub_step_summary(order_no):
    """获取子步骤汇总"""
    try:
        summary = container_center.get_sub_step_summary(order_no)
        return success(summary)
    except Exception as e:
        logger.exception(f'获取子步骤汇总异常: {e}')
        return fail(message=f'获取子步骤汇总失败: {e}')


# ════════════════════════════════════════
# [T41.6 修复 2026-06-14] api_create_sub_step 已移到模块级（上面）
# if-main 块内的旧函数定义保留（永不执行，仅作注释占位）
# ════════════════════════════════════════


# [T41.6 修复 2026-06-14] 移到 if-main 之前（api_create_sub_step 在模块级引用）
def _validate_quantity(value) -> tuple:
    """[F12 修复 2026-06-13] 严格 quantity 类型校验"""
    from decimal import Decimal, InvalidOperation
    from mobile_api_ai.utils.error_codes import ErrorCode
    if value is None or value == '':
        return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 不能为空'
    try:
        q = Decimal(str(value))
        if q.is_nan():
            return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 不能为 NaN'
        if q.is_infinite():
            return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 不能为 Inf'
    except (InvalidOperation, TypeError, ValueError):
        return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 必须为数字'
    if q < 0:
        return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 不能为负数'
    if q >= Decimal('10000000'):
        return False, ErrorCode.get_message(ErrorCode.SUBSTEP_QUANTITY_INVALID[0]) + ': 不能超过 10,000,000'
    return True, q


def _check_order_exists(order_no: str) -> tuple:
    """[F4 修复 2026-06-13] 校验订单存在性"""
    from mobile_api_ai.utils.error_codes import ErrorCode
    if not order_no or not isinstance(order_no, str):
        return False, ErrorCode.get_message(ErrorCode.PARAM_INVALID[0])
    if len(order_no) > 50:
        return False, ErrorCode.get_message(ErrorCode.PARAM_INVALID[0]) + ': 长度超过 50'
    import pymysql
    try:
        conn = _get_mysql_connection()
        try:
            with conn.cursor() as c:
                c.execute("SELECT 1 FROM orders_local WHERE order_no=%s AND is_deleted=0 LIMIT 1", (order_no,))
                if not c.fetchone():
                    return False, f'{ErrorCode.get_message(ErrorCode.ORDER_NOT_FOUND[0])} 或已删除: {order_no}'
        finally:
            conn.close()
    except Exception as e:
        return False, f'订单存在性校验失败: {e}'
    return True, None

# [F5 修复 2026-06-13] step_name 白名单
# 业务合法值：常见工序名称（中英文混合）
ALLOWED_STEP_NAMES = frozenset([
    '入库', '发货', '分切', '焊接', '包装', '质检', '备料', '清洗',
    'stock_in', 'stock_out', 'cut', 'weld', 'pack', 'inspect', 'prep', 'wash',
    '入库登记', '发货登记', '出库', '入库审核', '完成',
])

if __name__ == '__main__':
    # ── 初始化日志系统（优先执行，确保所有日志可见） ──
    from logging.handlers import RotatingFileHandler
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    _log_file = os.path.join(Config.LOG_DIR, 'container_center.log')
    _file_handler = RotatingFileHandler(
        _log_file, maxBytes=Config.LOG_MAX_BYTES, backupCount=10, encoding='utf-8'
    )
    _file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT, Config.LOG_DATE_FORMAT))
    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT, Config.LOG_DATE_FORMAT))
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        handlers=[_file_handler, _console_handler]
    )
    logger.info('日志系统已初始化: 级别=%s, 文件=%s, 最大=%sMB',
                Config.LOG_LEVEL, _log_file, Config.LOG_MAX_BYTES // (1024 * 1024))

    # ── 注册 atexit 清理钩子 ──
    atexit.register(_shutdown_all)

    # ── 注册优雅关闭信号处理器 ──
    import signal
    def _signal_handler(sig, frame):
        sig_name = signal.Signals(sig).name
        logger.info('收到 %s 信号，开始优雅关闭...', sig_name)
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    logger.info('信号处理器已注册: SIGINT/SIGTERM → atexit')

    # 启动桌面端回调管理器
    if desktop_callback_manager:
        desktop_callback_manager.start()

    # [C1 修复 2026-06-13] 启动本地表镜像 ETL Worker
    try:
        from etl_local_mirror import start_etl_worker
        start_etl_worker(interval_sec=60)
        logger.info('[ETL] 5002 启动本地表镜像同步')
    except Exception as e:
        logger.warning(f'[ETL] 5002 启动失败: {e}')

    # [E2 修复 2026-06-13] 启动 outbox worker
    # [P4 修复 2026-06-13] 启动失败时 ERROR 日志 + 微信告警
    try:
        from outbox_worker import start_outbox_worker
        start_outbox_worker(interval_sec=30)
        logger.info('[OUTBOX] 5002 启动 outbox worker')
    except Exception as e:
        logger.error(f'[OUTBOX] 5002 启动失败（重要）: {e}', exc_info=True)
        # 调 5003 微信通知（不阻塞 5002 启动）
        try:
            import requests as _req_alert
            _req_alert.post(
                f'{os.getenv("DISPATCH_CENTER_URL", "http://127.0.0.1:5003")}/api/notify/wechat',
                json={
                    'message': f'🚨 [5002] outbox worker 启动失败\n{e}',
                    'level': 'error',
                },
                timeout=2,
            )
        except Exception:
            pass

    # 启动定时校对线程
    if REPORT_SYSTEM_WEBHOOK_URL:
        _sync_thread = ResilientThread(target=_sync_check_sender, daemon=True, name='sync-checker')
        _sync_thread.start()
        logger.info("报工程序定时校对线程已启动（每小时一次）")

        # 启动时推送已有真实数据到报工程序
        _push_existing_records_on_startup()

    # 初始化企业架构数据库表
    _init_enterprise_db_table()

    logger.info('=' * 60)
    logger.info('  容器中心API服务器启动')
    logger.info('=' * 60)
    logger.info('  服务地址: http://localhost:5002')
    api_status = '已启用' if api_secret_key else '未启用（危险）'
    logger.info(f'  API签名验证: {api_status}')
    logger.info('  健康检查器: %s', '[OK]' if _server_health_checker else '[--]')
    logger.info('  部署管理器: %s', '[OK]' if _server_deployment_manager else '[--]')
    logger.info('  审计日志: %s', '[OK]' if _server_audit_logger else '[--]')
    logger.info('  增强备份: %s', '[OK]' if _server_backup_manager else '[--]')
    logger.info('  数据边界校验: [OK]')
    logger.info('  外协管理: [OK]')

    # ── Waitress WSGI 生产级服务器 ──
    from waitress import serve
    _host = Config.FLASK_HOST
    _port = Config.CONTAINER_CENTER_PORT
    _threads = int(os.getenv('WAITRESS_THREADS', '8'))
    # [T27 修复 2026-06-14] connection_limit 100→200 + outbuf_size 调大
    # 之前：connection_limit=100 高 QPS 时触顶 → ConnectTimeoutError
    # 现在：200 连接上限 + 1MB outbuf，减少 TIME_WAIT 阻塞
    _conn_limit = int(os.getenv('WAITRESS_CONN_LIMIT', '200'))
    logger.info('启动 Waitress WSGI 服务器: %s:%s (线程池=%d, 连接上限=%d)',
                _host, _port, _threads, _conn_limit)
    serve(
        app,
        host=_host,
        port=_port,
        threads=_threads,
        connection_limit=_conn_limit,
        channel_timeout=int(os.getenv('WAITRESS_CHANNEL_TIMEOUT', '60')),
        cleanup_interval=30,
        outbuf_overflow=1048576,  # 1MB outbuf（T27: 减少分包）
        outbuf_high_watermark=1048576,
    )

# [F5 修复 2026-06-13] step_name 白名单
# 业务合法值：常见工序名称（中英文混合）
ALLOWED_STEP_NAMES = frozenset([
    '入库', '发货', '分切', '焊接', '包装', '质检', '备料', '清洗',
    'stock_in', 'stock_out', 'cut', 'weld', 'pack', 'inspect', 'prep', 'wash',
    '入库登记', '发货登记', '出库', '入库审核', '完成',
])


# [T41.6 修复 2026-06-14] _validate_quantity + _check_order_exists 已移到模块级
# （此处旧定义已删除，避免重复）


# [T41.6 修复 2026-06-14] _validate_quantity + _check_order_exists 已移到模块级
# （此处旧定义已删除，避免重复）


# [T41.6 修复 2026-06-14] api_create_sub_step + api_get_sub_steps + api_get_sub_step_summary
# 已移到模块级（第 2766-2916 行）。此处旧定义已删除（永不执行）。


@app.route('/api/process_sub_step/summary_by_order/<order_no>', methods=['GET'])
@require_api_key
def api_get_sub_step_summary_by_order(order_no):
    """根据订单号获取子步骤汇总（主软件调用）"""
    try:
        record = container_center.storage.get_process_record_by_order(order_no)
        if not record:
            return success({'order_no': order_no, 'total_qty': 0, 'completed_qty': 0, 'steps': []})
        summary = container_center.get_sub_step_summary(record["order_no"])
        return success({
            **summary,
            "order_no": record["order_no"],
            "order_no": order_no
        })
    except Exception as e:
        logger.exception(f'按订单查询子步骤汇总异常: {e}')
        return fail(message=f'查询失败: {e}')


@app.route('/api/scan-info', methods=['GET'])
def api_scan_info():
    code = request.args.get('code', '').strip()
    if not code:
        return fail('缺少参数: code')

    try:
        records = container_center.storage.get_process_records(search=code, limit=50)
        if not records:
            return fail(code=404, message=f'未找到工单 [{code}] 的工序记录')

        main_rec = None
        for rec in records:
            steps = rec.get('steps', []) or []
            if isinstance(steps, str):
                try:
                    steps = json.loads(steps)
                except (json.JSONDecodeError, TypeError):
                    steps = []
            if steps:
                main_rec = rec
                break
        if not main_rec:
            main_rec = records[0]

        steps_list = main_rec.get('steps', []) or []
        if isinstance(steps_list, str):
            try:
                steps_list = json.loads(steps_list)
            except (json.JSONDecodeError, TypeError):
                steps_list = []

        # 直接查询子步骤汇总（按 order_no，不再用 process_id）
        # [分类 2026-06-15] 过滤非生产类工序（物料/质检/入库）
        from mobile_api_ai.core.process_code_classifier import is_production_code, infer_flow_type_from_code
        sub_step_qty_map = {}
        sub_step_latest_map = {}
        for ss in container_center.storage.get_sub_steps_by_process(order_no=code):
            pc = ss.get('process_code', '') or ''
            if not is_production_code(pc):
                continue  # 过滤物料/质检/入库等非生产类工序
            sn = ss.get('step_name', '')
            qty = ss.get('quantity', 0) or 0
            sub_step_qty_map[sn] = sub_step_qty_map.get(sn, 0) + qty
            sub_step_latest_map[sn] = ss

        step_idx = int(main_rec.get('current_step', 0))
        required_qty = main_rec.get('quantity', 0) or 0

        # total_sub_qty: 从 data_packages 汇总真实完成量
        from core.config import get_process_code
        pkg_qty_map = {}
        for pkg in container_center.storage.get_packages(
            limit=500, extra_filters={'related_order': code}
        ):
            pn = pkg.get('related_process', '')
            pc = pkg.get('process_code', '') or get_process_code(pn) or pn
            if pc:
                pkg_qty_map[pc] = max(pkg_qty_map.get(pc, 0), pkg.get('completed_qty', 0) or 0)

        # 总体进度 = 所有已报工步骤的平均完成百分比 × 需求总数
        if pkg_qty_map and required_qty > 0:
            pcts = [min(1.0, q / required_qty) for q in pkg_qty_map.values()]
            total_sub_qty = round((sum(pcts) / len(pcts)) * required_qty)
        else:
            total_sub_qty = 0
        processes = []

        # 修复说明：
        # 1) processes 改用 sub_step_qty_map（实际报工工序）构建，
        #    不再用 workflow 节点（工单发布/排产/.../发货）—— 与 app.py /api/all-process-tasks 同源
        # 2) 状态判定统一走 api.step_status_helper.compute_sub_step_statuses，
        #    避免今后与 /api/all-process-tasks / dispatch_center 出现三端漂移
        non_zero_sub_steps = {k: v for k, v in sub_step_qty_map.items() if v > 0}
        from api.step_status_helper import compute_sub_step_statuses
        statuses = compute_sub_step_statuses(
            sub_step_qty_map=non_zero_sub_steps,
            required_qty=required_qty,
            sub_step_latest_map=sub_step_latest_map,
        )
        items = list(non_zero_sub_steps.items())
        for i, ((step_name, _), st) in enumerate(zip(items, statuses)):
            pc = sub_step_latest_map.get(step_name, {}).get('process_code', '') or ''
            processes.append({
                'process_id': main_rec['order_no'],
                'process_name': step_name,
                'step_name': step_name,
                'process_code': pc,
                'role': '',
                'status_key': '',
                'step_index': i,
                'is_current': st['is_current'],
                'is_completed': st['is_completed'],
                'required_qty': required_qty,
                'completed_qty': st['completed_qty'],
                'remaining_qty': st['remaining_qty'],
                'unit': main_rec.get('unit', ''),
                'status': st['status'],
                'last_report_operator': st['last_report_operator'],
                'last_report_time': st['last_report_time'],
                'last_report_qty': st['last_report_qty'],
            })

        # [2026-06-15] 按 process_code 编号升序排序（P01 → P02 → ... → P16）
        def _scan_process_code_sort_key(p):
            code = p.get('process_code', '') or ''
            import re as _re
            m = _re.match(r'^([A-Za-z]+)(\d+)?$', code)
            if m:
                return (m.group(1), int(m.group(2)) if m.group(2) else 0)
            return ('Z', 0)

        processes.sort(key=_scan_process_code_sort_key)

        return success({
            'code': code,
            'order_no': main_rec.get('order_no', ''),
            'customer_name': main_rec.get('customer_name', ''),
            'product_name': main_rec.get('product_name', ''),
            'quantity': required_qty,
            'unit': main_rec.get('unit', ''),
            'delivery_date': main_rec.get('delivery_date', ''),
            'priority': main_rec.get('priority', ''),
            'current_step_index': step_idx,
            'total_completed_qty': round(float(total_sub_qty)),
            'total_remaining_qty': max(0, required_qty - round(float(total_sub_qty))),
            'processes': processes
        })
    except Exception as e:
        logger.exception(f'扫码查询异常: {e}')
        return fail(message=f'查询异常: {e}')


@app.route('/api/flow-type/<product_type_id>', methods=['GET'])
def api_get_flow_type(product_type_id):
    """查询产品类型对应的流程类型"""
    return jsonify({'code': 0, 'flow_type': 'production'})


@app.route('/api/flow-map/sync', methods=['POST'])
def api_sync_flow_map():
    """接收桌面端产品-流程映射同步"""
    data = request.get_json(force=True, silent=True) or {}
    mappings = data.get('mappings', [])
    if not mappings:
        return fail('缺少 mappings')
    return success(data={'count': len(mappings), 'msg': 'product_flow_map 已废弃'})


@app.route('/api/sub-step/rollback', methods=['POST'])
def api_rollback_sub_step():
    """回退一条报工记录（管理员操作，记录审计日志，SQLite+MySQL双写）"""
    data = request.get_json(force=True, silent=True) or {}
    sub_step_id = data.get('sub_step_id', '')
    reason = data.get('reason', '手动回退')
    action_by = data.get('action_by', 'admin')
    
    if not sub_step_id:
        return fail('缺少 sub_step_id')
    
    conn = container_center.storage._conn
    cur = conn.cursor()
    t_sal = container_center.storage._table('sub_step_audit_log')
    t_pss = container_center.storage._table('process_sub_steps')
    t_dp = container_center.storage._table('data_packages')
    
    # 幂等检查
    cur.execute(f"SELECT id FROM {t_sal} WHERE sub_step_id=%s AND action='rollback' LIMIT 1", (sub_step_id,))
    if cur.fetchone():
        return fail('该记录已回退，不能重复操作')
    
    try:
        # 1. 查出记录信息
        cur.execute(f'SELECT id, order_no, process_code, step_name, quantity, operator FROM {t_pss} WHERE id=%s', (sub_step_id,))
        row = cur.fetchone()
        if not row:
            return fail('记录不存在')
        if isinstance(row, dict):
            sub_id = row.get('id'); order_no = row.get('order_no'); process_code = row.get('process_code')
            step_name = row.get('step_name'); qty = row.get('quantity'); operator = row.get('operator')
        else:
            sub_id, order_no, process_code, step_name, qty, operator = row
        
        # 写入审计 + 删除 + 重算（MySQL）
        cur.execute(f'INSERT INTO {t_sal} (sub_step_id, order_no, process_code, step_name, quantity, operator, action, action_by, reason) VALUES (%s,%s,%s,%s,%s,%s,"rollback",%s,%s)',
            (sub_id, order_no, process_code, step_name, qty, operator, action_by, reason))
        cur.execute(f'DELETE FROM {t_pss} WHERE id=%s', (sub_step_id,))
        cur.execute(f'SELECT COALESCE(SUM(quantity),0) FROM {t_pss} WHERE order_no=%s AND step_name=%s', (order_no, step_name))
        remaining_qty = cur.fetchone()[0]
        cur.execute(f'UPDATE {t_dp} SET completed_qty=%s WHERE related_order=%s AND related_process=%s', (remaining_qty, order_no, step_name))
        conn.commit()
        logger.info(f'回退完成: id={sub_step_id} order={order_no} step={step_name}')

        return success(data={
            'order_no': order_no, 'step_name': step_name,
            'remaining_qty': remaining_qty
        })
    except Exception as e:
        return fail(message=f'回退失败: {e}')


@app.route('/api/sub-step/audit/<order_no>', methods=['GET'])
def api_get_audit_log(order_no):
    """查询报工审计记录"""
    rows = container_center.storage.fetch_all(
        'SELECT id, sub_step_id, step_name, quantity, operator, action, action_by, reason, created_at '
        'FROM sub_step_audit_log WHERE order_no=%s ORDER BY created_at DESC LIMIT 100', (order_no,))
    return jsonify({'code': 0, 'data': rows})


@app.route('/api/sub-step/repair-mysql', methods=['POST'])
def api_repair_mysql():
    """手动修复MySQL（从SQLite重新同步回退结果）"""
    conn = container_center.storage._conn
    cur = conn.cursor()
    try:
        cur.execute("SELECT order_no, step_name, action, payload FROM sync_retry_queue WHERE action='rollback'")
        fixed = 0
        for row in cur.fetchall():
            ono, step, _, payload = row
            try:
                import json
                from core.db import get_direct_connection
                pd = json.loads(payload or '{}')
                mysql_conn = get_direct_connection(
                    host=os.environ.get('MYSQL_HOST','localhost'), port=int(os.environ.get('MYSQL_PORT','3306')),
                    user=os.environ.get('MYSQL_USER','root'), password=os.environ.get('MYSQL_PASSWORD',''),
                    database=os.environ.get('CONTAINER_MYSQL_DATABASE','container_center'), charset='utf8mb4')
                mcur = mysql_conn.cursor()
                mcur.execute('DELETE FROM process_sub_steps WHERE id=%s', (pd.get('sub_step_id'),))
                mr = mcur.execute('SELECT COALESCE(SUM(quantity),0) FROM process_sub_steps WHERE order_no=%s AND step_name=%s', (ono, step))
                mq = mcur.fetchall()[0][0] if hasattr(mcur,'fetchall') else mcur.fetchone()[0]
                mysql_conn.commit()
                mysql_conn.close()
                fixed += 1
                logger.info(f'MySQL修复: order={ono} step={step} remaining={mq}')
            except Exception as e:
                logger.warning(f'MySQL修复失败: order={ono} {e}')
        cur.execute("DELETE FROM sync_retry_queue WHERE action='rollback'")
        conn.commit()
        return success(data={'repaired': fixed})
    except Exception as e:
        return fail(message=f'修复失败: {e}')


# ══════════════════════════════════════════════════════
# 物料任务 API（四端协同：桌面→调度→手机→库存）
# ══════════════════════════════════════════════════════
import uuid as _uuid_m

MATERIAL_FLOW = [
    {'name': '物料申请', 'key': 'material_requested',  'role': '采购部', 'source': '调度中心自动'},
    {'name': '任务确认', 'key': 'material_confirmed',   'role': '采购部', 'source': '手机端'},
    {'name': '入库通知', 'key': 'material_arrived',     'role': '采购部', 'source': '库存自动'},
    {'name': '物料出库', 'key': 'material_delivered',   'role': '生产部', 'source': '库存自动'},
]


@app.route('/api/material/create', methods=['POST'])
def api_material_create():
    """调度中心 / 桌面端：创建物料申请任务"""
    data = request.get_json(silent=True) or {}
    material_name = data.get('material_name', '').strip()
    order_no = data.get('order_no', '')
    if not material_name:
        return fail('material_name 不能为空')

    pkg_id = str(_uuid_m.uuid4())[:8]
    content = {
        'material_name': material_name,
        'spec': data.get('spec', ''),
        'quantity': data.get('quantity', 0),
        'unit': data.get('unit', '件'),
        'order_no': order_no,
        'ordered_by': data.get('ordered_by', ''),
    }
    container_center.storage.insert('data_packages', {
        'id': pkg_id,
        'data_type': 'material_purchase',
        'title': f'{order_no} - {material_name}',
        'related_order': order_no,
        'related_process': material_name,
        'target_operator': data.get('assignee', ''),
        'status': 'material_requested',
        'content': json.dumps(content, ensure_ascii=False),
        'source': 'material_schedule',
        'priority': data.get('priority', 'normal'),
    })
    logger.info(f'[物料] 物料申请已创建: {pkg_id} {order_no} - {material_name}')
    return success(data={'id': pkg_id, 'status': 'material_requested'})


@app.route('/api/material/list', methods=['GET'])
def api_material_list():
    """获取物料任务列表"""
    status_filter = request.args.get('status', None)
    kwargs = {'data_type': 'material_purchase', 'limit': 200}
    if status_filter:
        kwargs['status'] = status_filter
    pkgs = container_center.storage.get_packages(**kwargs)
    for p in pkgs:
        if isinstance(p.get('content'), str):
            try: p['content'] = json.loads(p['content'])
            except Exception: pass
    return success(data={'tasks': pkgs, 'total': len(pkgs)})


@app.route('/api/material/confirm', methods=['POST'])
def api_material_confirm():
    """手机端：确认物料任务 + 填报采购期限和到货日期"""
    data = request.get_json(silent=True) or {}
    pkg_id = data.get('id', '')
    if not pkg_id:
        return fail('id 不能为空')

    pkg = container_center.storage.get_package(pkg_id)
    if not pkg:
        return fail('物料任务不存在')
    if pkg.get('status') != 'material_requested':
        return fail('当前状态不可确认')

    content = json.loads(pkg.get('content', '{}')) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
    content['deadline'] = data.get('deadline', '')
    content['arrival_date'] = data.get('arrival_date', '')
    content['confirmed_by'] = data.get('operator', '')
    content['confirmed_at'] = _now_func().isoformat()

    container_center.storage.update_package(pkg_id, {
        'status': 'material_confirmed',
        'content': json.dumps(content, ensure_ascii=False),
    })
    logger.info(f'[物料] 任务已确认: {pkg_id} deadline={data.get("deadline")} arrival={data.get("arrival_date")}')
    return success(data={'id': pkg_id, 'status': 'material_confirmed'})


def _find_material_package(data):
    """按 ID 或物料名+工单号 查找物料任务
    物料名匹配：去除'备料-'前缀后的纯物料名，双向模糊匹配"""
    pkg_id = data.get('id', '')
    if pkg_id:
        return container_center.storage.get_package(pkg_id)

    material_name = data.get('material_name', '').strip()
    if not material_name:
        return None

    # 去除备料-前缀得到纯物料名
    clean_name = material_name.replace('备料-', '').strip()

    pkgs = container_center.storage.get_packages(
        data_type='material_purchase', limit=100)
    for p in pkgs:
        rp = p.get('related_process', '')
        rp_clean = rp.replace('备料-', '').strip()
        # 双向匹配：完整名 或 去除前缀后匹配
        if rp == material_name or rp_clean == clean_name:
            order_no = data.get('order_no', '')
            if order_no and p.get('related_order', '') != order_no:
                continue
            return p
    return None


@app.route('/api/material/arrived', methods=['POST'])
def api_material_arrived():
    """库存管理：物料入库后自动触发到货确认
    支持传 id 或 material_name（物料名）进行匹配"""
    data = request.get_json(silent=True) or {}
    pkg = _find_material_package(data)
    if not pkg:
        return fail('物料任务不存在，请提供 id 或 material_name')

    pkg_id = pkg['id']
    content = json.loads(pkg.get('content', '{}')) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
    content['actual_qty'] = data.get('actual_qty', content.get('quantity', 0))
    content['spec'] = data.get('spec', content.get('spec', ''))
    content['arrived_at'] = _now_func().isoformat()

    container_center.storage.update_package(pkg_id, {
        'status': 'material_arrived',
        'content': json.dumps(content, ensure_ascii=False),
    })
    logger.info(f'[物料] 物料已到货: {pkg_id} qty={content["actual_qty"]} material={pkg.get("related_process")}')
    return success(data={'id': pkg_id, 'status': 'material_arrived', 'material_name': pkg.get('related_process')})


@app.route('/api/material/delivered', methods=['POST'])
def api_material_delivered():
    """库存管理：物料出库后自动触发出库确认
    支持传 id 或 material_name（物料名）进行匹配"""
    data = request.get_json(silent=True) or {}
    pkg = _find_material_package(data)
    if not pkg:
        return fail('物料任务不存在，请提供 id 或 material_name')

    pkg_id = pkg['id']
    content = json.loads(pkg.get('content', '{}')) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
    content['delivered_qty'] = data.get('actual_qty', content.get('actual_qty', content.get('quantity', 0)))
    content['spec'] = data.get('spec', content.get('spec', ''))
    content['receiver'] = data.get('receiver', '')
    content['delivered_at'] = _now_func().isoformat()

    container_center.storage.update_package(pkg_id, {
        'status': 'material_delivered',
        'content': json.dumps(content, ensure_ascii=False),
    })
    logger.info(f'[物料] 物料已出库: {pkg_id} receiver={content["receiver"]} material={pkg.get("related_process")}')
    return success(data={'id': pkg_id, 'status': 'material_delivered', 'material_name': pkg.get('related_process')})


@app.route('/api/material/<pkg_id>', methods=['GET'])
def api_material_detail(pkg_id):
    """获取单个物料任务详情"""
    pkg = container_center.storage.get_package(pkg_id)
    if not pkg:
        return fail('物料任务不存在')
    if isinstance(pkg.get('content'), str):
        try: pkg['content'] = json.loads(pkg['content'])
        except Exception: pass
    # 附加工艺流程定义
    current_status = pkg.get('status', '')
    pkg['flow'] = []
    for step in MATERIAL_FLOW:
        step_status = 'completed' if MATERIAL_FLOW.index(step) < next(
            (i for i, s in enumerate(MATERIAL_FLOW) if s['key'] == current_status), 0
        ) else ('active' if step['key'] == current_status else 'pending')
        pkg['flow'].append({**step, 'status': step_status})
    return success(data=pkg)
