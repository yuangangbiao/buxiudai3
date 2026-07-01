# -*- coding: utf-8 -*-
"""
企业微信应用机器人服务器

Flask服务器，整合bots、commands、services模块
"""

import os
import sys
import re
import base64
import logging
import hashlib
import struct
import random
import time
import shutil
import traceback
import argparse
import threading
import requests
from typing import Optional, Tuple
from dataclasses import dataclass
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import unquote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cache import cache as redis_cache

# 加载环境变量（务必在 config.py 被导入前执行）
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_PROJECT_ROOT)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)
load_dotenv(os.path.join(_PROJECT_ROOT, '.env'))

# 不再注入表格机器人/本地路径 —— 使用本项目 container_center 模块

# 微信机器人模块（可选）
try:
    from bots import BotFactory, MessageHub, BotType
    from bots.factory import get_factory
    from bots.message_hub import get_hub
    from commands.manager import get_command_manager
    from services.notifier import get_notifier
    _BOTS_AVAILABLE = True
except ImportError:
    _BOTS_AVAILABLE = False

    # 定义桩函数确保后续引用不会 NameError
    def get_factory():
        return None
    def get_hub():
        return None
    def get_command_manager():
        return None
    def get_notifier():
        return None
    class BotType:
        GROUP = 'group'
        APP = 'app'
    class BotFactory:
        pass
    class MessageHub:
        pass
from operation_log import log_upstream, log_downstream, get_operation_log_db, set_static_dir
from report_request_manager import get_report_request_manager
from data_boundary import data_boundary
from data_integrity import DataIntegrity, DriftDetector
# 模块引用（可选依赖）
try:
    from modules.circuit_breaker import CircuitBreaker, CircuitState
except ImportError:
    class CircuitBreaker:
        def __init__(self, **kwargs): pass
        def record_failure(self): pass
        def record_success(self): pass
        def allow_request(self): return True
        @property
        def state(self): return 'closed'
        def __repr__(self): return 'CircuitBreaker(stub-disabled)'
    class CircuitState:
        CLOSED = 'closed'
        OPEN = 'open'
        HALF_OPEN = 'half_open'
try:
    from modules.queue_manager import QueueManager, QueueOverflowError
except ImportError:
    class QueueManager:
        def __init__(self, redis_client=None, **kwargs): pass
        def enqueue(self, *a, **kw): return True
        def dequeue(self, *a, **kw): return None
        def get_queue_info(self, *a, **kw): return {'size': 0, 'max_size': 'unlimited', 'dlq_size': 0, 'stats': {}}
        def __repr__(self): return 'QueueManager(stub-disabled)'
    class QueueOverflowError(Exception): pass
try:
    from enhanced_modules import EnhancedModules集成
except ImportError:
    class EnhancedModules集成:
        _instance = None
        @classmethod
        def get_instance(cls):
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
        def initialize_client_side(self, **kwargs): pass
        def __repr__(self): return 'EnhancedModules集成(stub-disabled)'
from container_center_client import ContainerCenterClient
try:
    from container_center.client import ContainerCenterClient as ContainerCenterSDK
except ImportError:
    class ContainerCenterSDK:
        def __init__(self, *a, **kw): pass
        def get_document(self, *a, **kw): return None
        def create_document(self, *a, **kw): return {'id': '', 'success': False}
        def update_document(self, *a, **kw): return {'success': False}
try:
    from container_center.v5_compatible_client import V5CompatibleClient
except ImportError:
    class V5CompatibleClient:
        def __init__(self, *a, **kw): pass
        def get_document(self, *a, **kw): return None
        def create_document(self, *a, **kw): return {'id': '', 'success': False}
        def get_all_process_records(self, *a, **kw): return []
        def search_documents(self, *a, **kw): return []

# 云端轮询模块（混合模式）
try:
    from cloud_poller import init_cloud_poller, get_cloud_poller, start_polling, stop_polling, send_to_cloud
    CLOUD_POLLER_AVAILABLE = True
except ImportError:
    CLOUD_POLLER_AVAILABLE = False

from functools import wraps
from flask import request, jsonify

def _get_cloud_api_key():
    """获取云端API Key（优先环境变量，其次配置文件）"""
    key = os.getenv('WECHAT_CLOUD_API_KEY', '')
    if key:
        return key
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloud_config.json')
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return cfg.get('api_key', '')
        except Exception as e:
            logger.warning(f"读取cloud_config.json失败: {e}")
    return ''

def require_api_key(f):
    """API Key验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        expected_key = _get_cloud_api_key()
        if not expected_key or key != expected_key:
            return jsonify({'code': 403, 'message': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated

from logging_setup import setup_daily_logger, cleanup_old_logs
setup_daily_logger('wechat_server')
logger = logging.getLogger(__name__)

if not CLOUD_POLLER_AVAILABLE:
    logger.warning('[云端] cloud_poller模块不可用，混合模式未启用')

_enhanced_modules = None
_drift_detector = None
_circuit_breaker = None
_queue_manager = None

app = Flask(__name__, static_folder=None)
CORS(app, origins=os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5000,http://localhost:3000').split(','))

app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False


@app.route('/favicon.ico')
def favicon():
    return '', 204

_FACE_STATIC_DIR = os.path.join(os.path.dirname(__file__), 'face_checkin_static')

@app.route('/models/<path:filename>')
def face_models(filename):
    return send_from_directory(os.path.join(_FACE_STATIC_DIR, 'models'), filename)

@app.route('/wasm/<path:filename>')
def face_wasm(filename):
    return send_from_directory(os.path.join(_FACE_STATIC_DIR, 'wasm'), filename)

def get_app_dir():
    """获取应用程序所在目录（兼容打包后的exe）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

_static_dir = get_app_dir()
set_static_dir(_static_dir)

dat_dir = os.path.join(_static_dir, 'DAT')
os.makedirs(dat_dir, exist_ok=True)

env_file = os.path.join(dat_dir, '.env')
if not os.path.exists(env_file):
    env_example = os.path.join(dat_dir, '.env.example')
    if os.path.exists(env_example):
        shutil.copy2(env_example, env_file)
        logger.info(f"[Server] 从 .env.example 创建 .env 文件")
    else:
        default_env = """# 企业微信配置（请修改以下值）
WECHAT_TOKEN=
WECHAT_AES_KEY=
WECHAT_APP_ID=
WECHAT_APP_SECRET=
MAIN_SOFTWARE_CALLBACK_URL=http://127.0.0.1:5000/api/callback
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(default_env)

_container_center = None
_container_client = None
_cc_client = None
_message_hub = None
_command_manager = None
_notifier = None
_app_bot = None

_callback_url = None
_callback_sender = None
_report_history = []
_pending_help_requests = {}  # 求助待补全缓存 {user_id: {'content': str, 'timestamp': str}}

# 重构后的消息处理组件
_wechat_decryptor = None
_wechat_parser = None
_wechat_handler = None
_wechat_token = ''
_wechat_aes_key = ''


class WeChatContext:
    """微信服务器全局状态单例"""
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._container_center = None
        self._container_client = None
        self._cc_client = None
        self._message_hub = None
        self._command_manager = None
        self._notifier = None
        self._app_bot = None
        self._callback_url = None
        self._callback_sender = None
        self._report_history = []
        self._pending_help_requests = {}
        self._wechat_decryptor = None
        self._wechat_parser = None
        self._wechat_handler = None
        self._wechat_token = ''
        self._wechat_aes_key = ''
        self._enhanced_modules = None
        self._drift_detector = None
        self._circuit_breaker = None
        self._queue_manager = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = WeChatContext()
        return cls._instance


def _get_client():
    ctx = WeChatContext.get_instance()
    if ctx._cc_client is None:
        cc = ctx._container_center
        if cc is None:
            from container_center_v5 import ContainerCenter
            cc = ContainerCenter()
            ctx._container_center = cc
        http_client = None
        try:
            url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
            secret = os.environ.get('CONTAINER_CENTER_SECRET', '')
            http_client = ContainerCenterSDK(base_url=url, secret=secret)
        except Exception:
            pass
        ctx._cc_client = V5CompatibleClient(container_center=cc, http_client=http_client)
    return ctx._cc_client


def init_services():
    """初始化服务"""
    ctx = WeChatContext.get_instance()
    global container_center, wechat_app_bot, message_hub

    if _BOTS_AVAILABLE:
        ctx._message_hub = get_hub()
        ctx._command_manager = get_command_manager()
        ctx._notifier = get_notifier()

        factory = get_factory()
        factory.create_group_bot()
        factory.create_app_bot()

        group_bot = factory.get_group_bot()
        if group_bot:
            ctx._message_hub.register_bot(BotType.GROUP, group_bot)
            logger.info("[Server] 群机器人已注册")

        app_bot = factory.get_app_bot()
        if app_bot:
            ctx._message_hub.register_bot(BotType.APP, app_bot)
            ctx._app_bot = app_bot
            logger.info("[Server] 应用机器人已注册")
    else:
        logger.info("[Server] 机器人模块不可用，跳过初始化")
        class _StubNotifier:
            def initialize(self, *a, **kw): pass
            def send_notification(self, *a, **kw): pass
            def __getattr__(self, name): return lambda *a, **kw: None
        ctx._notifier = _StubNotifier()

    try:
        from container_center_v5 import ContainerCenter
        ctx._container_center = ContainerCenter()
        container_center = ctx._container_center
        logger.info(f"[Server] 容器中心初始化成功，数据库: {db_path}")
    except Exception as e:
        logger.warning(f"[Server] 容器中心初始化失败: {e}")

    ctx._notifier.initialize(ctx._message_hub, ctx._container_center)

    ctx._callback_url = os.environ.get('MAIN_SOFTWARE_CALLBACK_URL', '')
    if ctx._callback_url:
        logger.info(f"[Server] 主软件回调地址: {ctx._callback_url}")
    else:
        logger.info("[Server] 未配置主软件回调地址")

    ctx._drift_detector = DriftDetector(tolerance_seconds=float(os.environ.get('DRIFT_TOLERANCE_SECONDS', '5.0')))
    logger.info("[Server] 漂移检测器初始化成功")

    try:
        ctx._circuit_breaker = CircuitBreaker(
            name='wechat_bot_main',
            failure_threshold=int(os.environ.get('CB_FAILURE_THRESHOLD', '50')),
            success_threshold=int(os.environ.get('CB_SUCCESS_THRESHOLD', '3')),
            failure_rate_threshold=float(os.environ.get('CB_FAILURE_RATE_THRESHOLD', '0.5')),
            half_open_max_requests=int(os.environ.get('CB_HALF_OPEN_REQUESTS', '3')),
            open_timeout=float(os.environ.get('CB_OPEN_TIMEOUT', '30.0')),
            recovery_timeout=float(os.environ.get('CB_RECOVERY_TIMEOUT', '60.0'))
        )
        logger.info("[Server] 熔断器初始化成功")
    except Exception as e:
        logger.warning(f"[Server] 熔断器初始化失败: {e}")
        ctx._circuit_breaker = None

    try:
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        import redis
        _redis_timeout = int(os.environ.get('SOCKET_CONNECT_TIMEOUT', '5'))
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, socket_connect_timeout=_redis_timeout, socket_timeout=_redis_timeout)
        redis_client.ping()
        ctx._queue_manager = QueueManager(redis_client=redis_client)
        logger.info(f"[Server] 队列管理器初始化成功 (Redis: {redis_host}:{redis_port})")
    except Exception as e:
        logger.warning(f"[Server] 队列管理器初始化失败 (Redis未连接): {e}")
        ctx._queue_manager = None

    ctx._callback_sender = QueuedCallbackSender(ctx._callback_url, ctx._circuit_breaker, ctx._queue_manager)

    # ──────────────────────────────────────────────────
    # 增强模块集成初始化（主软件侧：仅加载客户端保护模块）
    # ──────────────────────────────────────────────────
    try:
        ctx._enhanced_modules = EnhancedModules集成.get_instance()
        ctx._enhanced_modules.initialize_client_side(
            redis_client=redis_client if ctx._queue_manager is not None else None,
            config={
                'CB_FAILURE_THRESHOLD': int(os.environ.get('CB_FAILURE_THRESHOLD', '50')),
                'QUEUE_MAX_SIZE': int(os.environ.get('QUEUE_MAX_SIZE', '1000')),
            }
        )
        logger.info("[Server] 客户端增强模块初始化完成")
    except Exception as e:
        logger.warning(f"[Server] 客户端增强模块初始化失败: {e}")
        ctx._enhanced_modules = None

    # ──────────────────────────────────────────────────
    # 容器中心 API 客户端初始化（HTTP接口交互，集成全部保护能力）
    # ──────────────────────────────────────────────────
    _api_url = os.environ.get('CONTAINER_CENTER_API_URL', '')
    if _api_url:
        try:
            ctx._container_client = ContainerCenterClient(
                base_url=_api_url,
                api_secret_key=os.environ.get('API_SECRET_KEY', ''),
                redis_host=os.environ.get('REDIS_HOST', ''),
                redis_port=int(os.environ.get('REDIS_PORT', '6379')),
            )
            login_result = ctx._container_client.login(operator_id='system')
            if login_result:
                logger.info("[Server] 容器中心 API 客户端初始化成功（已登录）")
            else:
                logger.info("[Server] 容器中心 API 客户端初始化完成（暂未登录）")
        except Exception as e:
            logger.warning(f"[Server] 容器中心 API 客户端初始化失败: {e}")
            ctx._container_client = None
    else:
        logger.info("[Server] 容器中心 API 客户端未配置（跳过）")
        ctx._container_client = None

    logger.info("[Server] 服务初始化完成")

    # 同步兼容导出
    container_center = ctx._container_center
    wechat_app_bot = ctx._app_bot
    message_hub = ctx._message_hub


def init_wechat_services():
    """初始化企业微信消息处理组件"""
    ctx = WeChatContext.get_instance()

    load_dotenv(os.path.join(_static_dir, 'DAT', '.env'))
    ctx._wechat_aes_key = os.environ.get('WECHAT_AES_KEY', '')
    ctx._wechat_token = os.environ.get('WECHAT_TOKEN', '')

    ctx._wechat_parser = WechatMessageParser()
    ctx._wechat_decryptor = WechatMessageDecryptor(ctx._wechat_token, ctx._wechat_aes_key)
    ctx._wechat_handler = WechatMessageHandler(ctx._command_manager, ctx._app_bot)

    logger.info("[Server] 企业微信消息处理组件初始化完成")


# 云端默认禁用人脸考勤（人脸签到仅限本地端使用）
os.environ.setdefault('FACE_ATTENDANCE_ENABLED', 'false')

from blueprint_registry import register_all_blueprints
register_all_blueprints(app)

@app.route('/')
def serve_root():
    """根路径重定向到容器中心统一页面"""
    from flask import redirect
    return redirect('/container/')


@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件和静态资源访问"""
    from flask import send_from_directory

    # 企业微信校验文件
    if filename.startswith('WW_verify_') and filename.endswith('.txt'):
        file_path = os.path.join(_static_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            logger.info(f"[Server] 提供校验文件: {filename}")
            return content, 200, {'Content-Type': 'text/plain'}
        logger.warning(f"[Server] 文件不存在: {filename}")
        return "File not found", 404

    # 静态资源文件（CSS/JS等）
    if filename.startswith('static/'):
        static_dir = os.path.join(_static_dir, 'static')
        rel_path = filename[len('static/'):]
        file_path = os.path.join(static_dir, rel_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(static_dir, rel_path)
    return "File not found", 404


def _extract_sync_request() -> Tuple[Optional[dict], Optional[Tuple]]:
    """提取并验证同步请求的基础字段，返回 (fields_dict, error_response)"""
    data = request.get_json()
    if not data:
        return None, (jsonify({'code': 400, 'message': '无效的JSON数据'}), 400)

    order_no = data.get('order_no')
    order_no = data.get('order_no', '')
    process = data.get('process', '')
    operator = data.get('operator', '')
    force = data.get('force', False)
    if not order_no:
        return None, (jsonify({'code': 400, 'message': '缺少order_no字段'}), 400)

    return {
        'order_no': order_no,
        'order_no': order_no,
        'process': process,
        'operator': operator,
        'force': force,
        'data': data
    }, None


def _check_confirmation(operator: str, force: bool, confirm_type: str) -> bool:
    """检查用户是否已确认操作"""
    if force or not operator:
        return False

    user_confirm = redis_cache.get(f'confirm:{operator}', {})
    if (user_confirm.get('type') == confirm_type and
        time.time() < user_confirm.get('valid_until', 0)):
        logger.info(f"[Sync] 用户 {operator} 已确认{confirm_type}操作")
        return True
    return False


def _send_notification(message: str, operator: str, operation_type: str,
                       order_no: str = '', process: str = '', quantity: int = 0,
                       details: dict = None) -> bool:
    """发送微信通知并记录下游日志"""
    ctx = WeChatContext.get_instance()
    if not ctx._app_bot or not operator:
        return False

    try:
        ctx._app_bot.send_text(message, user_id=operator)
        logger.info(f"[Sync] 已发送{operation_type}给 {operator}")

        log_downstream(
            source='微信',
            operation_type=operation_type,
            content=f'推送{operation_type}给 {operator}',
            details=details or {'message': message},
            result='成功',
            user_id=operator,
            order_no=order_no,
            process=process,
            quantity=quantity,
            status='成功'
        )
        return True
    except Exception as e:
        logger.warning(f"[Sync] 发送{operation_type}失败: {e}")

        log_downstream(
            source='微信',
            operation_type=operation_type,
            content=f'推送{operation_type}给 {operator}',
            details=details or {'message': message},
            result=f'失败: {str(e)}',
            user_id=operator,
            order_no=order_no,
            process=process,
            quantity=quantity,
            status='失败',
            error_message=str(e)
        )
        return False


@app.route('/api/sync/task', methods=['POST'])
def sync_task():
    """
    接收本地系统推送的任务数据

    请求体:
    {
        "order_no": "WO0001",
        "customer": "上海机械厂",
        "process": "编织",
        "quantity": 200,
        "operator": "YuanGangBiao",
        "planned_qty": 500,
        "tech_params": "目数40 Mesh",
        "force": false,
        "timestamp": "2026-05-06T09:30:00"
    }
    """
    try:
        fields, err = _extract_sync_request()
        if err:
            return err
        order_no = fields['order_no']
        process = fields['process']
        operator = fields['operator']
        force = fields['force']
        data = fields['data']

        order_result = data_boundary.validate_order_no(order_no)
        if not order_result.is_valid:
            logger.warning(f"[Sync] 订单号验证失败: {order_result.error_message}")
            return jsonify({'code': 400, 'message': f"订单号验证失败: {order_result.error_message}"}), 400

        process_result = data_boundary.validate_process(process)
        if not process_result.is_valid:
            logger.warning(f"[Sync] 工序验证失败: {process_result.error_message}")
            return jsonify({'code': 400, 'message': f"工序验证失败: {process_result.error_message}"}), 400

        quantity = data.get('quantity', 0)
        quantity_result = data_boundary.validate_quantity(quantity)
        if not quantity_result.is_valid:
            logger.warning(f"[Sync] 数量验证失败: {quantity_result.error_message}")
            return jsonify({'code': 400, 'message': f"数量验证失败: {quantity_result.error_message}"}), 400

        ctx_sync = WeChatContext.get_instance()
        if ctx_sync._drift_detector:
            client_timestamp = data.get('timestamp')
            if client_timestamp:
                has_drift, offset = ctx_sync._drift_detector.detect_time_drift(client_timestamp)
                if has_drift:
                    logger.warning(f"[Sync] 检测到时间漂移: {offset}秒")

        logger.info(f"[Sync] 数据验证通过: 订单={order_result.sanitized_value}, 工序={process_result.sanitized_value}, 数量={quantity_result.sanitized_value}")

        confirmed = _check_confirmation(operator, force, 'task')

        # 检查是否已存在相同的订单和工序（数据库层面）
        existing_tasks = _get_client().get_packages(limit=5000)
        for task in existing_tasks:
            if (task.get('related_order') == order_no or task.get('order_no') == order_no) and \
               (task.get('process_name') == process or task.get('content', {}).get('process_name') == process):
                if not force or not confirmed:
                    logger.warning(f"[Sync] 任务已存在: {order_no} - {process}")
                    return jsonify({
                        'code': 409,
                        'message': f'任务已存在: 订单 {order_no} 工序 {process} 不可重复下达'
                    }), 409

        # 收集任务信息
        planned_qty = data.get('planned_qty', 0) or data.get('quantity', 0)
        order_no = fields.get('order_no') or data.get('order_no', '')
        # 根据任务类型分发到不同的 collector，确保调度中心正确分类展示
        task_type = data.get('task_type', 'process')
        pkg_data = {
            'related_order': order_no,
            'order_no': order_no,
            'order_no': order_no,
            'process_name': process,
            'operator_id': operator,
            'planned_qty': planned_qty,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        if task_type == 'material':
            pkg_data['task_type'] = 'material'
            pkg_data['material_name'] = process
            pkg_data['quantity'] = int(planned_qty) if planned_qty else 0
            pkg_data['unit'] = data.get('unit', '件')
            pkg_data['spec'] = data.get('spec', '')
            pkg = _get_client().save_package(doc_type='material', data=pkg_data)
        elif task_type == 'quality':
            pkg_data['task_type'] = 'quality'
            pkg_data['inspector_id'] = operator
            pkg_data['inspection_type'] = process
            pkg = _get_client().save_package(doc_type='quality', data=pkg_data)
        else:
            pkg_data['task_type'] = 'process'
            pkg_data['record_id'] = 0
            pkg = _get_client().save_package(doc_type='report', data=pkg_data)

        logger.info(f"[Sync] 接收任务: {order_no} - {process}")

        # 记录上游日志
        log_upstream(
            source='主软件',
            operation_type='下达任务',
            content=f'下达任务: {order_no} - {process}',
            details=data,
            result='成功',
            user_id=operator,
            order_no=order_no,
            process=process,
            quantity=planned_qty,
            status='成功'
        )

        # 如果有操作员，发送微信通知
        if operator and ctx_sync._app_bot:
            customer = data.get('customer', '')
            tech_params = data.get('tech_params', '')
            message = f"📋 **新任务分配**\n\n"
            display_no = order_no
            message += f"订单号: {display_no}\n"
            if customer:
                message += f"客户: {customer}\n"
            message += f"工序: {process}\n"
            message += f"数量: {planned_qty}\n"
            if tech_params:
                message += f"技术参数: {tech_params}\n"
            message += f"\n请及时处理！"

            _send_notification(message, operator, '任务通知', order_no, process, planned_qty, {'message': message})

        # 通知调度中心更新工单任务计数
        try:
            requests.post(
                'http://127.0.0.1:5000/api/dispatch-center/workorder/update-task-count',
                json={
                    'order_no': order_no,
                    'action': 'add',
                    'task_type': 'process'
                },
                timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '2'))
            )
        except Exception as e:
            logger.warning(f"[Sync] 通知调度中心任务计数失败: {e}")

        return jsonify({
            'code': 200,
            'message': '任务同步成功',
            'task_id': pkg.id if pkg else None
        })

    except Exception as e:
        logger.error(f"[Sync] 任务同步异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/report', methods=['POST'])
def sync_report():
    """
    接收本地系统推送的报工数据（主软件直接报工）

    请求体:
    {
        "order_no": "WO0001",
        "process": "编织",
        "quantity": 100,
        "operator": "YuanGangBiao",
        "completed": false,
        "force": false,
        "timestamp": "2026-05-06T09:30:00"
    }
    """
    try:
        fields, err = _extract_sync_request()
        if err:
            return err
        order_no = fields['order_no']
        process = fields['process']
        operator = fields['operator']
        force = fields['force']
        data = fields['data']

        confirmed = _check_confirmation(operator, force, 'report')

        # 查询日志，检查当天是否有相同订单的报工（简化检测：不区分工序）
        if not force and not confirmed:
            today = datetime.now().strftime('%Y-%m-%d')
            log_db = get_operation_log_db()
            today_logs = log_db.get_logs(
                direction='上游',
                operation_type='报工回调',
                order_no=order_no,
                start_date=today + ' 00:00:00',
                end_date=today + ' 23:59:59',
                limit=10
            )
            # 发现当天有相同订单的报工，需要确认
            if today_logs:
                logger.warning(f"[Sync] 发现重复报工: {order_no}")

                # 发送微信确认消息给用户
                ctx_sr = WeChatContext.get_instance()
                if operator and ctx_sr._app_bot:
                    confirm_msg = f"⚠️ **重复报工确认**\n\n检测到您今天已对工单 {order_no} 报过工\n\n如需再次报工，请回复：确认报工\n\n（仅对本次生效）"
                    try:
                        ctx_sr._app_bot.send_text(confirm_msg, user_id=operator)
                    except Exception as e:
                        logger.warning(f"[Sync] 发送确认消息失败: {e}")

                return jsonify({
                    'code': 409,
                    'message': f'检测到今天已有报工记录，请确认是否继续',
                    'need_confirm': True,
                    'order_no': order_no
                }), 409

        all_tasks = _get_client().get_packages(limit=5000)
        task = next((t for t in all_tasks if (t.get('related_order') == order_no or t.get('order_no') == order_no) and (t.get('process_name') == process or t.get('content', {}).get('process_name') == process)), None)
        if task:
            task_id = task.get('id')
            task_wo_no = task.get('related_order', '')
            quantity = data.get('quantity', 0)
            is_completed = data.get('completed', False)

            # 获取当前已完成数量（从数据库最新状态）
            current_task = _get_client().get_package(pkg_id=task_id)
            current_completed = current_task.get('completed_qty', 0) if current_task else 0
            planned_qty = current_task.get('content', {}).get('planned_qty', 0) if current_task else 0

            # 计算新的完成数量（本次报工后）
            new_completed = current_completed + quantity
            remaining = max(0, planned_qty - new_completed)

            display_no = task_wo_no or order_no

            if is_completed:
                _get_client().update_document('work_order', task_id, {
                    'completed_qty': new_completed,
                    'actual_qty': new_completed,
                    'target_operator': operator,
                    'operator_id': operator,
                    'status': 'completed'
                })
                message = f"✅ 报工完成！\n\n订单: {display_no}\n工序: {process}\n本次报工: {quantity}\n累计完成: {new_completed}\n计划数量: {planned_qty}\n剩余: {remaining}"

                logger.info(f"[Sync] 报工同步: {order_no} - {quantity}, 累计: {new_completed}, 剩余: {remaining}")

                log_upstream(
                    source='主软件',
                    operation_type='报工回调',
                    content=f'主软件推送报工: {order_no} - {process} - 操作员: {operator}',
                    details={'order_no': order_no, 'process': process, 'quantity': quantity, 'completed_qty': new_completed, 'remaining': remaining, 'operator': operator},
                    result='成功',
                    user_id=operator,
                    order_no=order_no,
                    process=process,
                    quantity=quantity,
                    status='成功'
                )

                if operator and WeChatContext.get_instance()._app_bot:
                    _send_notification(message, operator, '报工回复', order_no, process, quantity, {'message': message})

                return jsonify({
                    'code': 200,
                    'message': '报工同步成功',
                    'data': {
                        'order_no': order_no,
                        'process': process,
                        'quantity': quantity,
                        'total_completed': new_completed,
                        'planned_qty': planned_qty,
                        'remaining': remaining
                    }
                })
            else:
                _get_client().update_document('work_order', task_id, {
                    'progress_qty': quantity,
                    'completed_qty': new_completed,
                    'target_operator': operator,
                    'operator_id': operator
                })

                # 检测是否刚好达到100%（本次报工从<计划量变为>=计划量）
                just_reached_100 = (new_completed >= planned_qty) and (current_completed < planned_qty)

                if just_reached_100:
                    message = f"⚠️ 工单 {display_no} 工序 {process} 累计报工已达计划量({planned_qty})，请输入该工序的实际完成量"
                    if operator and WeChatContext.get_instance()._app_bot:
                        _send_notification(message, operator, '报工回复', order_no, process, quantity, {'message': message})

                    logger.info(f"[Sync] 报工达100%，等待actual_qty: {order_no} - {process}, 累计: {new_completed}")

                    return jsonify({
                        'code': 200,
                        'message': '报工已达计划量，需要填报实际完成量',
                        'need_actual_qty': True,
                        'data': {
                            'order_no': order_no,
                            'process': process,
                            'quantity': quantity,
                            'total_completed': new_completed,
                            'planned_qty': planned_qty,
                            'remaining': remaining,
                            'task_id': task_id
                        }
                    })

                message = f"📝 报工成功！\n\n订单: {display_no}\n工序: {process}\n本次报工: {quantity}\n累计完成: {new_completed}\n计划数量: {planned_qty}\n剩余: {remaining}"

                logger.info(f"[Sync] 报工同步: {order_no} - {quantity}, 累计: {new_completed}, 剩余: {remaining}")

                log_upstream(
                    source='主软件',
                    operation_type='报工回调',
                    content=f'主软件推送报工: {order_no} - {process} - 操作员: {operator}',
                    details={'order_no': order_no, 'process': process, 'quantity': quantity, 'completed_qty': new_completed, 'remaining': remaining, 'operator': operator},
                    result='成功',
                    user_id=operator,
                    order_no=order_no,
                    process=process,
                    quantity=quantity,
                    status='成功'
                )

                if operator and WeChatContext.get_instance()._app_bot:
                    _send_notification(message, operator, '报工回复', order_no, process, quantity, {'message': message})

                return jsonify({
                    'code': 200,
                    'message': '报工同步成功',
                    'data': {
                        'order_no': order_no,
                        'process': process,
                        'quantity': quantity,
                        'total_completed': new_completed,
                        'planned_qty': planned_qty,
                        'remaining': remaining
                    }
                })
        else:
            return jsonify({'code': 404, 'message': f'未找到工单{order_no}的任务'}), 404

    except Exception as e:
        logger.error(f"[Sync] 报工同步异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/report/actual', methods=['POST'])
def sync_report_actual():
    """主软件推送实际完成量"""
    try:
        data = request.get_json(force=True) if request.is_json else request.form
        task_id = data.get('task_id')
        order_no = data.get('order_no', '')
        process = data.get('process', '')
        actual_qty = data.get('actual_qty')
        operator = data.get('operator', '')

        if actual_qty is None:
            return jsonify({'code': 400, 'message': 'actual_qty为必填'}), 400

        actual_qty = int(actual_qty)

        if task_id:
            task = _get_client().get_package(pkg_id=task_id)
        elif order_no:
            all_tasks = _get_client().get_packages(limit=5000)
            task = next((t for t in all_tasks
                        if (t.get('related_order') == order_no or t.get('order_no') == order_no)
                        and (t.get('process_name') == process or t.get('content', {}).get('process_name') == process)), None)
            if task:
                task_id = task.get('id')
        else:
            return jsonify({'code': 400, 'message': 'task_id或order_no+process为必填'}), 400

        if not task:
            return jsonify({'code': 404, 'message': f'未找到任务'}), 404

        order_no = order_no or task.get('related_order', '')
        process = process or task.get('content', {}).get('process_name', '')

        _get_client().update_document('work_order', task_id, {
            'actual_qty': actual_qty,
            'status': 'completed'
        })

        message = f"✅ 实际完成量已填报！\n\n订单: {order_no}\n工序: {process}\n实际完成量: {actual_qty}"
        if operator and WeChatContext.get_instance()._app_bot:
            _send_notification(message, operator, '报工回复', order_no, process, actual_qty, {'message': message})

        logger.info(f"[Sync] 实际完成量填报: {order_no} - {process}, actual_qty: {actual_qty}")

        log_upstream(
            source='主软件',
            operation_type='实际完成量填报',
            content=f'实际完成量填报: {order_no} - {process} - 实际量: {actual_qty}',
            details={'order_no': order_no, 'process': process, 'actual_qty': actual_qty, 'task_id': task_id, 'operator': operator},
            result='成功',
            user_id=operator,
            order_no=order_no,
            process=process,
            quantity=actual_qty,
            status='成功'
        )

        return jsonify({
            'code': 200,
            'message': '实际完成量填报成功',
            'data': {
                'task_id': task_id,
                'order_no': order_no,
                'process': process,
                'actual_qty': actual_qty
            }
        })

    except Exception as e:
        logger.error(f"[Sync] 实际完成量填报异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/status', methods=['GET'])
def get_sync_status():
    """获取同步服务状态"""
    ctx = WeChatContext.get_instance()
    return jsonify({
        'code': 200,
        'message': '服务正常',
        'container_center': 'available' if ctx._container_center else 'unavailable'
    })


@app.route('/api/sync/health/detailed', methods=['GET'])
def get_detailed_health():
    """获取详细健康状态"""
    ctx = WeChatContext.get_instance()
    health_report = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'container_center': 'ok' if ctx._container_center else 'unavailable',
            'message_hub': 'ok' if ctx._message_hub else 'unavailable',
            'command_manager': 'ok' if ctx._command_manager else 'unavailable',
            'app_bot': 'ok' if ctx._app_bot else 'unavailable',
            'notifier': 'ok' if ctx._notifier else 'unavailable'
        }
    }

    if ctx._drift_detector:
        drift_stats = ctx._drift_detector.get_statistics()
        health_report['drift_detector'] = drift_stats

    return jsonify({
        'code': 200,
        'data': health_report
    })


@app.route('/api/sync/validate/input', methods=['POST'])
def validate_input():
    """验证输入数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '无效的JSON数据'}), 400

        order_no = data.get('order_no', '')
        process = data.get('process', '')
        quantity = data.get('quantity', 0)
        user_id = data.get('user_id', '')

        order_result = data_boundary.validate_order_no(order_no)
        if not order_result.is_valid:
            return jsonify({'code': 400, 'message': order_result.error_message}), 400

        process_result = data_boundary.validate_process(process)
        if not process_result.is_valid:
            return jsonify({'code': 400, 'message': process_result.error_message}), 400

        quantity_result = data_boundary.validate_quantity(quantity)
        if not quantity_result.is_valid:
            return jsonify({'code': 400, 'message': quantity_result.error_message}), 400

        user_result = data_boundary.validate_user_id(user_id)
        if not user_result.is_valid:
            return jsonify({'code': 400, 'message': user_result.error_message}), 400

        sanitized = {
            'order_no': order_result.sanitized_value,
            'process': process_result.sanitized_value,
            'quantity': quantity_result.sanitized_value,
            'user_id': user_result.sanitized_value
        }

        return jsonify({
            'code': 200,
            'message': '验证通过',
            'data': sanitized
        })
    except Exception as e:
        logger.error(f"[Validate] 验证异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/delivery-date-change', methods=['POST'])
def sync_delivery_date_change():
    """
    主软件通知交货日期变更

    请求体:
    {
        "order_no": "WO001",
        "old_delivery_date": "2026-05-20",
        "new_delivery_date": "2026-06-10",
        "change_reason": "客户要求延期",
        "operator": "张三"
    }

    流程:
    1. 接收主软件交货日期变更请求
    2. 转发到调度中心更新流程记录并发送通知
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = data.get('order_no', '')
        new_delivery = data.get('new_delivery_date', '')
        if not order_no or not new_delivery:
            return jsonify({'code': 400, 'message': 'order_no 和 new_delivery_date 必填'}), 400

        logger.info(f"[Sync] 交货日期变更: {order_no} → {new_delivery}")

        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5000')
        resp = requests.post(
            f'{dispatch_url}/api/dispatch-center/workorder/change-delivery-date',
            json=data,
            timeout=10
        )
        if resp.status_code != 200:
            logger.warning(f"[Sync] 调度中心返回异常: {resp.status_code} {resp.text}")
            return jsonify({'code': 502, 'message': '调度中心处理失败'}), 502

        result = resp.json()
        logger.info(f"[Sync] 交货日期变更完成: {order_no}, 新日期: {new_delivery}")
        return jsonify({
            'code': 200,
            'message': '交货日期变更已通知',
            'data': result.get('data', {})
        })

    except requests.exceptions.Timeout:
        logger.error(f"[Sync] 调度中心超时: {order_no}")
        return jsonify({'code': 504, 'message': '调度中心超时'}), 504
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[Sync] 调度中心连接失败: {e}")
        return jsonify({'code': 502, 'message': '调度中心连接失败'}), 502
    except Exception as e:
        logger.error(f"[Sync] 交货日期变更异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/drift/check', methods=['POST'])
def check_drift():
    """检测数据漂移"""
    ctx = WeChatContext.get_instance()
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '无效的JSON数据'}), 400

        client_timestamp = data.get('client_timestamp', 0)
        original_quantity = data.get('original_quantity', 0)
        reported_quantity = data.get('reported_quantity', 0)

        if not ctx._drift_detector:
            return jsonify({'code': 500, 'message': '漂移检测器未初始化'}), 500

        has_time_drift, time_offset = ctx._drift_detector.detect_time_drift(client_timestamp)
        has_qty_drift, qty_drift_percent = ctx._drift_detector.detect_quantity_drift(
            original_quantity, reported_quantity
        )

        return jsonify({
            'code': 200,
            'data': {
                'has_time_drift': has_time_drift,
                'time_offset_seconds': time_offset,
                'has_quantity_drift': has_qty_drift,
                'quantity_drift_percent': round(qty_drift_percent, 2),
                'tolerance_seconds': ctx._drift_detector.tolerance_seconds
            }
        })
    except Exception as e:
        logger.error(f"[Drift] 漂移检测异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/data/fingerprint', methods=['POST'])
def create_fingerprint():
    """创建数据指纹"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '无效的JSON数据'}), 400

        order_no = data.get('order_no', '')
        process = data.get('process', '')
        quantity = data.get('quantity', 0)
        timestamp = data.get('timestamp')

        fingerprint = DataIntegrity.create_data_fingerprint(
            order_no, process, quantity, timestamp
        )

        return jsonify({
            'code': 200,
            'data': {
                'fingerprint': fingerprint,
                'order_no': order_no,
                'process': process,
                'quantity': quantity
            }
        })
    except Exception as e:
        logger.error(f"[Fingerprint] 创建指纹异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/circuit/status', methods=['GET'])
def get_circuit_breaker_status():
    """获取熔断器状态"""
    ctx = WeChatContext.get_instance()
    if not ctx._circuit_breaker:
        return jsonify({
            'code': 200,
            'data': {
                'enabled': False,
                'message': '熔断器未初始化'
            }
        })

    state = ctx._circuit_breaker.get_state()
    metrics = ctx._circuit_breaker.get_metrics()

    return jsonify({
        'code': 200,
        'data': {
            'enabled': True,
            'name': ctx._circuit_breaker.name,
            'state': state.value,
            'metrics': {
                'total_calls': metrics.total_calls,
                'successful_calls': metrics.successful_calls,
                'failed_calls': metrics.failed_calls,
                'rejected_calls': metrics.rejected_calls,
                'success_rate': round(metrics.success_rate * 100, 2),
                'failure_rate': round(metrics.failure_rate * 100, 2),
                'avg_response_time_ms': round(metrics.avg_response_time * 1000, 2) if metrics.avg_response_time else 0
            },
            'config': {
                'failure_threshold': ctx._circuit_breaker.failure_threshold,
                'success_threshold': ctx._circuit_breaker.success_threshold,
                'failure_rate_threshold': ctx._circuit_breaker.failure_rate_threshold,
                'open_timeout': ctx._circuit_breaker.open_timeout
            }
        }
    })


@app.route('/api/sync/circuit/reset', methods=['POST'])
def reset_circuit_breaker():
    """重置熔断器"""
    ctx = WeChatContext.get_instance()
    if not ctx._circuit_breaker:
        return jsonify({'code': 400, 'message': '熔断器未初始化'}), 400

    try:
        ctx._circuit_breaker.reset()
        return jsonify({
            'code': 200,
            'message': '熔断器已重置',
            'data': {'state': ctx._circuit_breaker.get_state().value}
        })
    except Exception as e:
        logger.error(f"[Circuit] 重置熔断器异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/queue/status', methods=['GET'])
def get_queue_status():
    """获取队列管理器状态"""
    ctx = WeChatContext.get_instance()
    if not ctx._queue_manager:
        return jsonify({
            'code': 200,
            'data': {
                'enabled': False,
                'message': '队列管理器未初始化'
            }
        })

    try:
        queue_info = ctx._queue_manager.get_queue_info('wechat_report_callbacks')
        return jsonify({
            'code': 200,
            'data': {
                'enabled': True,
                'queue_name': 'wechat_report_callbacks',
                'size': queue_info.get('size', 0),
                'max_size': queue_info.get('max_size', 'unlimited'),
                'dlq_size': queue_info.get('dlq_size', 0),
                'stats': queue_info.get('stats', {}),
                'last_enqueue': queue_info.get('last_enqueue'),
                'last_dequeue': queue_info.get('last_dequeue')
            }
        })
    except Exception as e:
        logger.error(f"[Queue] 获取队列状态异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/queue/stats', methods=['GET'])
def get_queue_stats():
    """获取队列统计信息"""
    ctx = WeChatContext.get_instance()
    if not ctx._queue_manager:
        return jsonify({
            'code': 200,
            'data': {
                'enabled': False,
                'message': '队列管理器未初始化'
            }
        })

    try:
        stats = ctx._queue_manager.get_queue_info('wechat_report_callbacks').get('stats', {})
        return jsonify({
            'code': 200,
            'data': {
                'enqueued_total': stats.get('enqueued_total', 0),
                'dequeued_total': stats.get('dequeued_total', 0),
                'failed_total': stats.get('failed_total', 0),
                'overflow_rejected_total': stats.get('overflow_rejected_total', 0),
                'avg_latency_ms': stats.get('avg_latency_ms', 0),
                'max_latency_ms': stats.get('max_latency_ms', 0)
            }
        })
    except Exception as e:
        logger.error(f"[Queue] 获取队列统计异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/tasks', methods=['GET'])
def get_sync_tasks():
    """
    获取同步的任务列表

    参数:
    - operator: 操作员ID（可选）
    - status: 任务状态（可选）
    - limit: 返回数量（默认100）
    """
    try:
        operator = request.args.get('operator')
        status = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)

        all_tasks = _get_client().get_packages(limit=limit)

        if operator:
            tasks = [t for t in all_tasks if t.get('target_operator') == operator or t.get('operator_id') == operator]
            if status:
                tasks = [t for t in tasks if t.get('status') == status]
        else:
            tasks = all_tasks
            if status:
                tasks = [t for t in tasks if t.get('status') == status]

        return jsonify({
            'code': 200,
            'data': tasks,
            'count': len(tasks)
        })
    except Exception as e:
        logger.error(f"[Sync] 获取任务列表异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/tasks/<task_id>', methods=['GET'])
def get_sync_task(task_id):
    """获取指定任务的详细信息"""
    try:
        task = _get_client().get_package(pkg_id=task_id)
        if task:
            return jsonify({
                'code': 200,
                'data': task
            })
        else:
            return jsonify({'code': 404, 'message': f'未找到任务 {task_id}'}), 404
    except Exception as e:
        logger.error(f"[Sync] 获取任务异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/task/<order_no>/status', methods=['GET'])
def get_task_status(order_no):
    """
    根据订单号查询任务状态

    Returns:
        任务状态信息，包括完成进度
    """
    try:
        # 获取工单对应的所有任务
        all_tasks = _get_client().get_packages(limit=5000)
        tasks = [t for t in all_tasks if t.get('related_order') == order_no or t.get('order_no') == order_no]

        if not tasks:
            return jsonify({'code': 404, 'message': f'未找到工单 {order_no}'}), 404

        # 获取该工单的所有报工记录
        log_db = get_operation_log_db()
        reports = log_db.get_logs(
            direction='上游',
            operation_type='报工回调',
            order_no=order_no,
            limit=100
        )

        # 构建状态信息
        task_info = tasks[0] if tasks else {}
        planned_qty = task_info.get('planned_qty', 0) or task_info.get('content', {}).get('planned_qty', 0)
        completed_qty = task_info.get('completed_qty', 0)

        total_reported = sum(r.get('quantity', 0) for r in reports)
        remaining = max(0, planned_qty - completed_qty) if completed_qty else (planned_qty - total_reported if total_reported else 0)

        status = '已完成' if remaining <= 0 else '进行中'

        return jsonify({
            'code': 200,
            'data': {
                'order_no': order_no,
                'process': task_info.get('process_name') or task_info.get('content', {}).get('process_name', ''),
                'planned_qty': planned_qty,
                'completed_qty': completed_qty or total_reported,
                'remaining': remaining if remaining > 0 else 0,
                'status': status,
                'report_count': len(reports),
                'reports': reports[:10]  # 最近10条报工记录
            }
        })
    except Exception as e:
        logger.error(f"[Sync] 获取任务状态异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/outsource/publish', methods=['POST'])
def publish_outsource():
    """
    发布外协任务到容器中心

    请求体:
        order_no: 订单号（必填）
        process_name: 工序名称（必填）
        planned_qty: 计划数量（必填）
        process_seq: 工序序号（默认1）
        outsource_remark: 外协备注
        operator_id: 操作员ID
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = data.get('order_no', '').strip()
        process_name = data.get('process_name', '').strip()
        planned_qty = data.get('planned_qty', 0)
        process_seq = data.get('process_seq', 1)
        outsource_remark = data.get('outsource_remark', '').strip()
        operator_id = data.get('operator_id', '').strip()

        if not order_no or not process_name or not planned_qty:
            return jsonify({'code': 400, 'message': '订单号、工序名和数量不能为空'}), 400

        ctx = WeChatContext.get_instance()
        if ctx._container_client and ctx._container_client.is_authenticated():
            result = ctx._container_client.publish_outsource_task(
                order_no=order_no,
                process_name=process_name,
                planned_qty=planned_qty,
                process_seq=process_seq,
                outsource_remark=outsource_remark,
                operator_id=operator_id
            )
            if result:
                logger.info(f"[Outsource] 通过API发布外协任务: {order_no} - {process_name}")
                return jsonify({'code': 200, 'data': result, 'message': '外协任务已发布'})
            logger.warning(f"[Outsource] API发布外协任务失败，回退到直接调用")

        pkg = _get_client().create_document(doc_type='outsource', data={
            'order_no': order_no,
            'process_name': process_name,
            'process_seq': process_seq,
            'planned_qty': planned_qty,
            'outsource_remark': outsource_remark,
            'operator_id': operator_id,
            'status': 'pending',
        })
        _get_client().distribute(task_id=pkg.get('id'), operator_id=operator_id)
        logger.info(f"[Outsource] 直接发布外协任务: {order_no} - {process_name}")
        return jsonify({'code': 200, 'data': {'id': pkg.get('id')}, 'message': '外协任务已发布'})

        return jsonify({'code': 500, 'message': '容器中心未初始化'}), 500
    except Exception as e:
        logger.error(f"[Outsource] 发布外协任务异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/hook', methods=['GET', 'POST'])
def wechat_hook():
    """
    企业微信回调接口

    GET: URL验证
    POST: 接收消息
    """
    if request.method == 'GET':
        return verify_url()
    else:
        return receive_message()


def verify_url():
    """URL验证（企业微信签名验证）"""
    logger.info("[Server] 收到URL验证请求")

    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    echostr = request.args.get('echostr', '')

    logger.info(f"[Server] URL验证参数 - msg_signature: {msg_signature}, timestamp: {timestamp}, nonce: {nonce}")

    if not echostr:
        logger.warning("[Server] URL验证失败：缺少echostr")
        return "verification failed", 400

    ctx = WeChatContext.get_instance()
    if not verify_signature(msg_signature, timestamp, nonce, ctx._wechat_token, ctx._wechat_aes_key, echostr):
        logger.warning("[Server] URL验证失败：签名验证不通过")
        return "signature verification failed", 403

    try:
        decrypted_str = decrypt_echostr(echostr, ctx._wechat_aes_key)
        logger.info(f"[Server] URL验证成功，返回解密后的echostr")
        return decrypted_str, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        logger.error(f"[Server] 解密echostr失败: {e}")
        return "decryption failed", 500


def verify_signature(msg_signature, timestamp, nonce, token, aes_key, echostr):
    """验证企业微信签名"""
    try:
        # 将token、timestamp、nonce、echostr四个参数进行字典序排序
        params = [token, timestamp, nonce, echostr]
        params.sort()

        # 拼接成字符串
        params_str = ''.join(params)

        # 进行sha1加密
        sha1 = hashlib.sha1()
        sha1.update(params_str.encode('utf-8'))
        computed_signature = sha1.hexdigest()

        logger.info(f"[Server] 计算签名: {computed_signature}, 传入签名: {msg_signature}")

        # 比较签名
        return computed_signature == msg_signature
    except Exception as e:
        logger.error(f"[Server] 签名验证异常: {e}")
        return False


def decrypt_echostr(encrypted_str, aes_key):
    """解密企业微信的echostr"""
    try:
        # URL解码
        encrypted_str = unquote(encrypted_str)

        # AESKey需要Base64解码（43字符的key需要补齐为44字符）
        aes_key_bytes = base64.b64decode(aes_key + '=')

        # 解码加密字符串
        encrypted_data = base64.b64decode(encrypted_str)

        # 使用AES CBC模式解密，IV为密文的前16字节
        iv = encrypted_data[:16]
        cipher = Cipher(algorithms.AES(aes_key_bytes), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_data[16:]) + decryptor.finalize()

        # 去除PKCS7填充
        pad_len = decrypted[-1]
        if pad_len > 16:
            raise ValueError(f"Invalid padding: {pad_len}")
        decrypted = decrypted[:-pad_len]

        # 解析消息格式: msg_len(4) + msg + from_appid
        msg_len = struct.unpack('>I', decrypted[:4])[0]
        msg = decrypted[4:4 + msg_len].decode('utf-8')

        logger.info(f"[Server] AES解密成功，明文echostr: {msg}")
        return msg
    except Exception as e:
        logger.error(f"[Server] AES解密异常: {e}")
        raise


@dataclass
class WechatMessage:
    """企业微信消息"""
    msg_type: str
    content: str
    user_id: str
    raw_xml: str


class WechatMessageParser:
    """企业微信消息解析器"""

    @staticmethod
    def parse_encrypt(xml_data: str) -> Optional[str]:
        """从XML中提取加密内容"""
        encrypt_match = re.search(r'<Encrypt><!\[CDATA\[(.*?)\]\]></Encrypt>', xml_data)
        return encrypt_match.group(1) if encrypt_match else None

    @staticmethod
    def parse_message(xml_str: str) -> WechatMessage:
        """解析解密后的XML消息"""
        content_match = re.search(r'<Content><!\[CDATA\[(.*?)\]\]></Content>', xml_str)
        user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', xml_str)
        msg_type_match = re.search(r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>', xml_str)

        return WechatMessage(
            msg_type=msg_type_match.group(1) if msg_type_match else 'text',
            content=content_match.group(1) if content_match else '',
            user_id=user_match.group(1) if user_match else '',
            raw_xml=xml_str
        )


class WechatMessageDecryptor:
    """企业微信消息解密器"""

    def __init__(self, token: str, aes_key: str):
        self.token = token
        self.aes_key_bytes = base64.b64decode(aes_key + '=')

    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
        """验证消息签名"""
        params = [self.token, timestamp, nonce, encrypt]
        params.sort()
        params_str = ''.join(params)
        sha1 = hashlib.sha1()
        sha1.update(params_str.encode('utf-8'))
        computed_signature = sha1.hexdigest()
        return computed_signature == msg_signature

    def decrypt(self, encrypt: str) -> str:
        """解密消息"""
        encrypt = unquote(encrypt)

        enc = base64.b64decode(encrypt)

        iv = enc[:16]
        cipher = Cipher(algorithms.AES(self.aes_key_bytes), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(enc[16:]) + decryptor.finalize()

        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]

        return decrypted.decode('utf-8')

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """解密并验证消息"""
        if not self.verify_signature(msg_signature, timestamp, nonce, encrypt):
            raise ValueError("消息签名验证失败")
        return self.decrypt(encrypt)


class WechatMessageHandler:
    """企业微信消息处理器"""

    def __init__(self, command_manager, app_bot):
        self.command_manager = command_manager
        self.app_bot = app_bot

    def _get_wechat_name(self, user_id: str) -> str:
        """
        根据user_id获取微信名称，带缓存

        优先从云端API获取，云端不可用时使用本地app_bot

        Args:
            user_id: 企业微信UserID

        Returns:
            微信名称，如果获取失败则返回user_id
        """
        if not user_id:
            return ''

        name = redis_cache.get(f'wxname:{user_id}')
        if name:
            return name

        name = self._fetch_wechat_name_from_cloud(user_id)
        if name and name != user_id:
            redis_cache.set(f'wxname:{user_id}', name, ex=3600)
            return name

        if self.app_bot and hasattr(self.app_bot, 'get_user_info'):
            try:
                user_info = self.app_bot.get_user_info(user_id)
                if user_info and user_info.get('name'):
                    name = user_info['name']
                    redis_cache.set(f'wxname:{user_id}', name, ex=3600)
                    return name
            except Exception as e:
                logger.warning(f"[WechatHandler] 本地获取用户 {user_id} 信息失败: {e}")

        redis_cache.set(f'wxname:{user_id}', user_id, ex=3600)
        return user_id

    def _fetch_wechat_name_from_cloud(self, user_id: str) -> str:
        """
        从云端API获取微信用户名称

        Args:
            user_id: 企业微信UserID

        Returns:
            用户名称，获取失败返回原始user_id
        """
        import requests

        cloud_host = os.getenv('WECHAT_CLOUD_HOST', '')
        cloud_api_key = _get_cloud_api_key()

        if not cloud_host or not cloud_api_key:
            return user_id

        try:
            url = f"{cloud_host}/api/wechat/user/{user_id}/name"
            headers = {'X-API-Key': cloud_api_key}
            resp = requests.get(url, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    return data.get('name', user_id)
        except Exception as e:
            logger.debug(f"[WechatHandler] 云端获取用户 {user_id} 失败: {e}")

        return user_id

    def _handle_process_confirmation(self, user_id: str, content: str) -> bool:
        """处理流程确认（通过dispatch_center API）"""
        try:
            from flask import current_app
            with current_app.app_context():
                try:
                    from dispatch_center import _dispatch_cache
                    data = _dispatch_cache.get_data()
                    processes = data.get('processes', [])
                    awaiting_process = None
                    for p in processes:
                        if p.get('awaiting_confirmation'):
                            awaiting_operator = p.get('awaiting_operator', '')
                            if not awaiting_operator or awaiting_operator == user_id or awaiting_operator == 'system':
                                awaiting_process = p
                                break

                    if not awaiting_process:
                        return False

                    process_id = awaiting_process.get('id')
                    confirm_url = f'http://localhost:{os.environ.get("PORT", "5003")}/api/dispatch-center/processes/confirm-by-reply'
                    resp = requests.post(confirm_url, json={
                        'process_id': process_id,
                        'user_id': user_id,
                        'user_name': self._get_wechat_name(user_id),
                        'content': content
                    }, timeout=10)
                    if resp.status_code == 200:
                        result = resp.json()
                        if result.get('code') == 0:
                            self.app_bot.send_text(f"✅ 流程已确认推进", user_id=user_id)
                            return True
                        else:
                            self.app_bot.send_text(f"⚠️ {result.get('message', '确认失败')}", user_id=user_id)
                            return True
                except ImportError:
                    logger.warning('[WechatHandler] 无法导入 dispatch_center 模块')
        except Exception as e:
            logger.error(f'[WechatHandler] 流程确认处理失败: {e}')
        return False

    def handle_confirmation(self, user_id: str, content: str) -> bool:
        """处理确认指令，返回是否已处理"""
        if self._handle_process_confirmation(user_id, content):
            return True

        if not ('报工' in content or '任务' in content):
            return False

        confirm_type = 'report' if '报工' in content else 'task'
        wechat_name = self._get_wechat_name(user_id)

        redis_cache.set(f'confirm:{user_id}', {
            'type': confirm_type,
            'valid_until': time.time() + 300
        }, ex=300)

        msg = f"✅ 已确认{'报工' if confirm_type == 'report' else '任务'}操作，5分钟内主软件可重试执行"
        self.app_bot.send_text(msg, user_id=user_id)

        log_downstream(
            source='微信',
            operation_type='确认指令',
            content=f'用户 {wechat_name}({user_id}) 确认了{"报工" if confirm_type == "report" else "任务"}重复操作',
            result='成功',
            user_id=user_id,
            wechat_name=wechat_name,
            status='成功'
        )

        return True

    def handle_command(self, user_id: str, content: str, container_center, xml_str: str):
        """处理命令执行"""
        wechat_name = self._get_wechat_name(user_id)
        ctx = {
            'user_id': user_id,
            'wechat_name': wechat_name,
            'container_center': container_center
        }
        result = self.command_manager.process(content, ctx)
        logger.info(f"[Server] 指令执行结果: {result}")

        log_downstream(
            source='微信',
            operation_type='接收消息',
            content=f'收到用户 {wechat_name}({user_id}) 消息: {content}',
            details={'xml_content': xml_str, 'command_result': str(result)},
            result='成功' if result.success else '失败',
            user_id=user_id,
            status='成功' if result.success else '失败'
        )

        if result.message:
            self.app_bot.send_text(result.message, user_id=user_id)

            log_downstream(
                source='微信',
                operation_type='发送回复',
                content=f'回复用户 {wechat_name}({user_id})',
                details={'reply': result.message},
                result='成功' if result.success else '失败',
                user_id=user_id,
                status='成功' if result.success else '失败'
            )

        if result.success and content.strip().startswith('报'):
            self._handle_report_callback(user_id, wechat_name, result)

    def _handle_report_callback(self, user_id: str, wechat_name: str, result):
        """处理报工回调"""
        ctx = WeChatContext.get_instance()
        order_no = result.data.get('order_no') if result.data else ''
        process = result.data.get('process') if result.data else ''
        quantity = result.data.get('quantity') if result.data else 0
        request_id = result.data.get('request_id') if result.data else ''
        callback_data = result.data.get('callback_data') if result.data else {}

        report_info = {
            'request_id': request_id,
            'order_no': order_no,
            'process': process,
            'quantity': quantity,
            'operator': user_id,
            'operator_name': wechat_name,
            'completed': result.data.get('completed') if result.data else False,
            'timestamp': datetime.now().isoformat(),
            'callback_data': callback_data
        }
        ctx._report_history.append(report_info)
        logger.info(f"[Callback] 记录报工请求: {report_info}")

        ctx._callback_sender.send(report_info, order_no=order_no, request_id=request_id)

        log_upstream(
            source='微信',
            operation_type='报工请求',
            content=f'微信用户 {wechat_name}({user_id}) 发起报工请求: {order_no} - {process}',
            details=report_info,
            result='待确认',
            user_id=user_id,
            wechat_name=wechat_name,
            order_no=order_no,
            process=process,
            quantity=quantity,
            status='待确认'
        )

    def handle(self, message: WechatMessage, container_center):
        """处理消息"""
        if message.msg_type != 'text' or not message.content:
            return

        content = message.content.strip()

        if content.startswith('确认'):
            if self.handle_confirmation(message.user_id, content):
                return

        self.handle_command(message.user_id, content, container_center, message.raw_xml)


def receive_message():
    """接收消息（企业微信POST加密消息）"""
    try:
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')

        xml_data = request.get_data(as_text=True)

        logger.info(f"[Server] 收到POST消息 - msg_signature: {msg_signature}, xml_data: {xml_data[:200] if xml_data else 'None'}")

        if not xml_data:
            return "success", 200

        ctx = WeChatContext.get_instance()
        encrypt = ctx._wechat_parser.parse_encrypt(xml_data)
        if not encrypt:
            return "success", 200

        try:
            xml_str = ctx._wechat_decryptor.decrypt_message(msg_signature, timestamp, nonce, encrypt)
            logger.info(f"[Server] 解密后XML: {xml_str}")
        except ValueError as e:
            logger.warning(f"[Server] {e}")
            return "signature verification failed", 403
        except Exception as e:
            logger.error(f"[Server] 解密消息异常: {e}")
            return "success", 200

        message = ctx._wechat_parser.parse_message(xml_str)
        logger.info(f"[Server] 解析消息 - msg_type: {message.msg_type}, content: {message.content}, user_id: {message.user_id}")

        content = message.content.strip() if message.content else ''
        to_user_id = message.user_id

        if message.msg_type == 'event' or not content:
            return "success", 200

        from cloud_matching import get_matcher
        matcher = get_matcher()
        normalized_content = matcher.normalize_content(content)
        match_result = matcher.match(normalized_content)

        logger.info(f"[Server] 匹配结果: type={match_result.command_type.value}, confidence={match_result.confidence:.2f}")

        from cloud_matching import CommandType as CmdType

        if match_result.command_type == CmdType.HELP_REQUEST:
            content_text = match_result.params.get('content', '') if match_result.params else ''
            if not content_text:
                reply = "请输入求助内容，格式: 求助+您的问题描述\n示例: 求助+编织物料不足需要补充钢筋"
                logger.info(f"[Server] 求助内容为空，返回格式提示")
                try:
                    factory = get_factory()
                    app_bot = factory.get_app_bot()
                    if app_bot:
                        app_bot.send_text(reply, user_id=to_user_id)
                except Exception as e:
                    logger.error(f"[Server] 发送求助格式提示失败: {e}")
                return "success", 200

            ctx._pending_help_requests[to_user_id] = {
                'content': content_text,
                'original_content': content,
                'user_id': message.user_id,
                'msg_id': f"{message.user_id}_{int(time.time())}",
                'msg_type': message.msg_type,
                'params': match_result.params,
                'confidence': match_result.confidence,
                'match_method': match_result.match_method.value,
                'matched_keyword': match_result.matched_keyword,
                'timestamp': datetime.now().isoformat()
            }
            reply = f"请输入订单号+物料名称\n示例: WO001+钢筋\n（您的问题: {content_text}）"
            logger.info(f"[Server] 已记录求助待补全: user={to_user_id}, content={content_text[:50]}")
            try:
                factory = get_factory()
                app_bot = factory.get_app_bot()
                if app_bot:
                    app_bot.send_text(reply, user_id=to_user_id)
            except Exception as e:
                logger.error(f"[Server] 发送物料信息提示失败: {e}")
            return "success", 200

        if match_result.command_type == CmdType.UNKNOWN:
            pending = ctx._pending_help_requests.pop(to_user_id, None)
            if pending:
                combined = f"{pending['content']}\n单号/物料: {content}"
                logger.info(f"[Server] 求助补全: user={to_user_id}, combined={combined[:80]}")
                try:
                    import requests
                    forward_data = {
                        'type': 'wechat_message',
                        'msg_id': pending['msg_id'],
                        'content': combined,
                        'original_content': pending['original_content'],
                        'msg_type': pending['msg_type'],
                        'user_id': pending['user_id'],
                        'to_user_id': to_user_id,
                        'timestamp': datetime.now().isoformat(),
                        'command_type': 'help_request',
                        'params': {
                            'content': combined,
                            'original_content': pending['original_content'],
                            'follow_up': content,
                            'material_info': content
                        },
                        'confidence': pending.get('confidence', 1.0),
                        'match_method': 'follow_up_help',
                        'matched_keyword': pending.get('matched_keyword', '')
                    }
                    resp = requests.post(f'{os.getenv("WECHAT_CLOUD_HOST", "http://127.0.0.1:5006")}/api/forward', json=forward_data, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
                    logger.info(f"[Server] 求助补全消息已转发到5006: {resp.status_code}")
                except Exception as fe:
                    logger.error(f"[Server] 求助补全消息转发失败: {fe}")
                return "success", 200

            help_text = f"未识别的指令\n\n{matcher.get_command_list()}\n\n输入求助+内容 可获取人工帮助"
            logger.info(f"[Server] 未识别指令，返回帮助信息")
            try:
                factory = get_factory()
                app_bot = factory.get_app_bot()
                if app_bot:
                    app_bot.send_text(help_text, user_id=to_user_id)
            except Exception as e:
                logger.error(f"[Server] 发送帮助信息失败: {e}")
            return "success", 200

        if match_result.error_message:
            logger.info(f"[Server] 格式错误，返回格式提示")
            try:
                factory = get_factory()
                app_bot = factory.get_app_bot()
                if app_bot:
                    app_bot.send_text(match_result.error_message, user_id=to_user_id)
            except Exception as e:
                logger.error(f"[Server] 发送格式提示失败: {e}")
            return "success", 200

        ctx._pending_help_requests.pop(to_user_id, None)

        try:
            import requests
            forward_data = {
                'type': 'wechat_message',
                'msg_id': f"{message.user_id}_{int(time.time())}",
                'content': normalized_content,
                'original_content': content,
                'msg_type': message.msg_type,
                'user_id': message.user_id,
                'to_user_id': to_user_id,
                'timestamp': datetime.now().isoformat(),
                'command_type': match_result.command_type.value,
                'params': match_result.params,
                'confidence': match_result.confidence,
                'match_method': match_result.match_method.value,
                'matched_keyword': match_result.matched_keyword
            }
            resp = requests.post(f'{os.getenv("WECHAT_CLOUD_HOST", "http://127.0.0.1:5006")}/api/forward', json=forward_data, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
            logger.info(f"[Server] 消息已转发到5006: {resp.status_code}")
        except Exception as fe:
            logger.error(f"[Server] 转发失败: {fe}")

        ctx._wechat_handler.handle(message, ctx._container_center)

        return "success", 200

    except Exception as e:
        logger.error(f"[Server] 处理消息异常: {e}", exc_info=True)
        return "success", 200


@app.route('/api/sync/reports', methods=['GET'])
def get_report_history():
    """
    获取报工历史记录

    参数:
    - operator: 操作员ID（可选）
    - order_no: 订单号（可选）
    - limit: 返回数量（默认50）
    """
    try:
        operator = request.args.get('operator')
        order_no = request.args.get('order_no')
        limit = request.args.get('limit', 50, type=int)

        if operator or order_no:
            log_db = get_operation_log_db()
            logs = log_db.get_logs(
                direction='上游',
                operation_type='报工回调',
                order_no=order_no,
                limit=limit * 2
            )
            reports = []
            for log in logs:
                if operator and log.get('user_id') != operator:
                    continue
                reports.append({
                    'order_no': log.get('order_no'),
                    'process': log.get('process'),
                    'quantity': log.get('quantity'),
                    'operator': log.get('user_id'),
                    'status': log.get('status'),
                    'created_at': log.get('created_at')
                })
                if len(reports) >= limit:
                    break
        else:
            ctx = WeChatContext.get_instance()
            reports = ctx._report_history[-limit:]

        return jsonify({
            'code': 200,
            'data': reports,
            'count': len(reports)
        })
    except Exception as e:
        logger.error(f"[Sync] 获取报工记录异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/logs/operations', methods=['GET'])
@app.route('/api/sync/logs', methods=['GET'])
def get_operation_logs():
    """
    获取操作日志

    参数:
    - direction: 方向 (上游/下游)
    - source: 来源 (微信/主软件/系统)
    - operation_type: 操作类型
    - order_no: 订单号
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - limit: 返回数量 (默认100)
    - offset: 偏移量 (默认0)
    """
    try:
        direction = request.args.get('direction')
        source = request.args.get('source')
        operation_type = request.args.get('operation_type')
        order_no = request.args.get('order_no')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        log_db = get_operation_log_db()
        logs = log_db.get_logs(
            direction=direction,
            source=source,
            operation_type=operation_type,
            order_no=order_no,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'code': 200,
            'data': logs,
            'count': len(logs)
        })
    except Exception as e:
        logger.error(f"[Log] 获取操作日志异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/logs/stats', methods=['GET'])
def get_log_stats():
    """获取操作日志统计"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        log_db = get_operation_log_db()
        stats = log_db.get_stats(start_date=start_date, end_date=end_date)

        return jsonify({
            'code': 200,
            'data': stats
        })
    except Exception as e:
        logger.error(f"[Log] 获取日志统计异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/departments', methods=['GET'])
def get_departments():
    """
    获取企业微信部门列表

    Returns:
        部门列表
    """
    try:
        if not _app_bot:
            return jsonify({'code': 500, 'message': '应用机器人未初始化'}), 500

        departments = _app_bot.get_department_list()
        return jsonify({
            'code': 200,
            'data': departments,
            'count': len(departments)
        })
    except Exception as e:
        logger.error(f"[WeChat] 获取部门列表异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/users', methods=['GET'])
def get_users():
    """
    获取企业微信用户列表

    参数:
    - department_id: 部门ID（可选，不传则获取所有用户）

    Returns:
        用户列表
    """
    try:
        ctx = WeChatContext.get_instance()
        if not ctx._app_bot:
            return jsonify({'code': 500, 'message': '应用机器人未初始化'}), 500

        department_id = request.args.get('department_id', type=int)

        if department_id:
            users = ctx._app_bot.get_department_users(department_id, fetch_child=True)
        else:
            users = ctx._app_bot.get_all_users()

        return jsonify({
            'code': 200,
            'data': users,
            'count': len(users)
        })
    except Exception as e:
        logger.error(f"[WeChat] 获取用户列表异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/user/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """
    获取单个用户详细信息

    Args:
        user_id: 用户ID

    Returns:
        用户信息
    """
    try:
        ctx = WeChatContext.get_instance()
        if not ctx._app_bot:
            return jsonify({'code': 500, 'message': '应用机器人未初始化'}), 500

        user_info = ctx._app_bot.get_user_info(user_id)
        if user_info:
            return jsonify({
                'code': 200,
                'data': user_info
            })
        else:
            return jsonify({'code': 404, 'message': f'未找到用户 {user_id}'}), 404
    except Exception as e:
        logger.error(f"[WeChat] 获取用户信息异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/poll', methods=['GET'])
@require_api_key
def poll_messages():
    """代理到wechat_cloud的轮询接口"""
    try:
        import requests
        cloud_host = os.getenv('WECHAT_CLOUD_HOST', 'http://127.0.0.1:5006')
        cloud_api_key = _get_cloud_api_key()
        resp = requests.get(
            f'{cloud_host}/api/queue/poll',
            headers={'X-API-Key': cloud_api_key},
            timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))
        )
        return resp.content, resp.status_code, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f'[poll代理] 失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/cloud/status')
def cloud_status():
    """获取云端连接状态（混合模式）"""
    try:
        from cloud_poller import get_cloud_poller, CLOUD_POLLER_AVAILABLE

        cloud_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloud_config.json')
        cloud_host = ''
        cloud_enabled = False

        if os.path.exists(cloud_config_file):
            try:
                import json
                with open(cloud_config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    cloud_host = cfg.get('cloud_host', '')
                    cloud_enabled = cfg.get('enabled', False)
            except Exception as e:
                logger.warning(f"加载云端配置文件失败: {e}")

        status = {
            'cloud_enabled': CLOUD_POLLER_AVAILABLE,
            'cloud_configured': bool(cloud_host),
            'cloud_host': cloud_host,
            'cloud_active': cloud_enabled,
            'poller_status': None
        }

        if CLOUD_POLLER_AVAILABLE:
            poller = get_cloud_poller()
            if poller:
                status['poller_status'] = poller.get_status()
            else:
                status['poller_status'] = {'running': False, 'error': '轮询器未初始化'}

        return jsonify({
            'code': 0,
            'data': status
        })
    except Exception as e:
        logger.error(f'[云端] 获取状态异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/cloud/send', methods=['POST'])
def cloud_send():
    """主动发送消息到微信（通过云端，降级到本地群机器人）"""
    try:
        data = request.get_json() or {}
        content = data.get('content', '')
        to_user = data.get('to_user', '@all')
        msg_type = data.get('msg_type', 'text')
        bot_type = data.get('bot_type', 'group')

        if not content:
            return jsonify({'code': 400, 'message': '内容不能为空'}), 400

        try:
            from cloud_poller import get_cloud_poller
            poller = get_cloud_poller()
            if poller:
                success = poller.send_message(content, to_user, msg_type, bot_type)
                if success:
                    return jsonify({'code': 0, 'success': True})
                logger.warning('[云端] cloud_poller.send_message 返回失败，降级到本地发送')
            else:
                logger.warning('[云端] 轮询器未初始化，降级到本地发送')
        except ImportError:
            logger.info('[云端] cloud_poller模块不可用，使用本地群机器人发送')

        factory = get_factory()
        group_bot = factory.get_group_bot()
        if not group_bot:
            logger.error('[云端] 群机器人未初始化')
            return jsonify({'code': 500, 'message': '群机器人未初始化'}), 500

        if msg_type == 'markdown':
            ok = group_bot.send_markdown(content)
        else:
            ok = group_bot.send_text(content)

        if ok:
            logger.info(f'[云端] 通过本地群机器人发送消息成功: {content[:50]}')
            return jsonify({'code': 0, 'success': True})
        else:
            logger.error(f'[云端] 群机器人发送失败')
            return jsonify({'code': 500, 'success': False, 'message': '群机器人发送失败'}), 500

    except Exception as e:
        logger.error(f'[云端] 发送消息异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/proxy_send', methods=['POST'])
def proxy_send():
    """
    云端代理转发接口

    接收本地 GroupBot 的代理请求，将消息转发到企业微信 Webhook。
    验证 API Key 确保只有授权的本地实例可以使用。

    请求体:
    {
        "_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
        "_api_key": "<从环境变量 WECHAT_CLOUD_API_KEY 获取>",
        "msgtype": "text",
        "text": {"content": "hello"}
    }

    Returns:
        企业微信 Webhook 的原始响应
    """
    try:
        data = request.get_json(silent=True) or {}
        webhook_url = data.pop('_webhook_url', '')
        api_key = data.pop('_api_key', '')

        if not webhook_url:
            return jsonify({'errcode': 400, 'errmsg': '缺少 _webhook_url'}), 400

        expected_key = os.environ.get('WECHAT_CLOUD_API_KEY', '')
        if not api_key or api_key != expected_key:
            logger.warning(f"[Proxy] API Key 验证失败: {api_key[:4]}...")
            return jsonify({'errcode': 403, 'errmsg': 'API Key 无效'}), 403

        if 'msgtype' not in data:
            return jsonify({'errcode': 400, 'errmsg': '缺少 msgtype 字段'}), 400

        logger.info(f"[Proxy] 转发消息到企业微信: msgtype={data.get('msgtype')}")

        resp = requests.post(
            webhook_url,
            json=data,
            timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')),
            headers={'Content-Type': 'application/json'}
        )

        result = resp.json()
        logger.info(f"[Proxy] 企业微信响应: errcode={result.get('errcode')}")

        return jsonify(result)

    except requests.exceptions.Timeout:
        logger.error("[Proxy] 转发请求超时")
        return jsonify({'errcode': 408, 'errmsg': '请求超时'}), 408
    except requests.exceptions.RequestException as e:
        logger.error(f"[Proxy] 转发请求异常: {e}")
        return jsonify({'errcode': 502, 'errmsg': f'转发失败: {str(e)}'}), 502
    except Exception as e:
        logger.error(f"[Proxy] 代理转发异常: {e}")
        return jsonify({'errcode': 500, 'errmsg': str(e)}), 500


@app.route('/api/wechat/send', methods=['POST'])
def wechat_send():
    """发送微信消息（供本地poll_monitor调用）- 发送后回调云端5006"""
    try:
        data = request.get_json() or {}
        to_user = data.get('to_user')
        content = data.get('content')
        msg_type = data.get('msg_type', 'text')
        msg_id = data.get('msg_id', '')

        if not to_user or not content:
            return jsonify({'code': 400, 'message': 'Missing params'}), 400

        factory = get_factory()
        app_bot = factory.get_app_bot()
        if app_bot:
            try:
                if to_user == '@all':
                    result = app_bot.send_text(content, to_all=True)
                else:
                    result = app_bot.send_text(content, user_id=to_user)
                logger.info(f'[Wechat] 发送消息给 {to_user}: {content[:50]}')
                success = True
                error_msg = ''
            except Exception as send_err:
                logger.error(f'[Wechat] 发送失败: {send_err}')
                success = False
                error_msg = str(send_err)
                result = None

            if msg_id:
                try:
                    cloud_host = os.getenv('WECHAT_CLOUD_HOST', 'http://localhost:5006')
                    requests.post(f'{cloud_host}/api/response/callback', json={
                        'msg_id': msg_id,
                        'success': success,
                        'error': error_msg
                    }, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
                except Exception as cb_err:
                    logger.warning(f'[Wechat] 回调云端失败: {cb_err}')

            return jsonify({'code': 0, 'result': result, 'success': success})
        else:
            return jsonify({'code': 500, 'message': 'App Bot未初始化'}), 500
    except Exception as e:
        logger.error(f'[Wechat] 发送消息异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/wechat/status')
def status():
    """获取服务状态"""
    try:
        factory = get_factory()
        app_bot = factory.get_app_bot()

        status_info = {
            'services': {
                'commands': []
            }
        }

        if _command_manager:
            for cmd in _command_manager.get_all_commands():
                status_info['services']['commands'].append({
                    'aliases': cmd['aliases'],
                    'help': cmd['help']
                })

        return jsonify(status_info)
    except Exception as e:
        logger.error(f"[Server] 获取状态异常: {e}")
        return jsonify({'error': str(e)}), 500


class QueuedCallbackSender:
    """
    带队列和熔断器保护的回调发送器

    封装了三层发送策略：队列投递 → 熔断器保护 → 直接发送
    """

    def __init__(self, callback_url: str, circuit_breaker, queue_manager):
        """
        Args:
            callback_url: 主软件回调地址
            circuit_breaker: CircuitBreaker 实例（可选）
            queue_manager: QueueManager 实例（可选）
        """
        self._callback_url = callback_url
        self._circuit_breaker = circuit_breaker
        self._queue_manager = queue_manager

    def send(
        self,
        callback_data: dict,
        queue_name: str = 'wechat_report_callbacks',
        order_no: str = '',
        request_id: str = '',
        timeout: int = 30
    ) -> bool:
        """
        发送回调数据

        按优先级尝试: 队列投递 → 熔断器保护 → 直接发送

        Args:
            callback_data: 要发送的回调数据
            queue_name: 队列名称
            order_no: 订单号（用于日志）
            request_id: 请求ID（用于日志）
            timeout: HTTP请求超时时间

        Returns:
            是否成功发送
        """
        if not self._callback_url:
            logger.info("[Callback] 未配置回调地址，跳过回调")
            return False

        def _do_send() -> bool:
            response = requests.post(self._callback_url, json=callback_data, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"[Callback] 回调已发送到主软件: {order_no}")
                return True
            logger.warning(f"[Callback] 发送回调失败: {response.status_code}")
            raise Exception(f"HTTP {response.status_code}")

        if self._queue_manager:
            try:
                queued = self._queue_manager.enqueue(
                    queue_name=queue_name,
                    data=callback_data,
                    max_size=int(os.environ.get('QUEUE_MAX_SIZE', '1000')),
                    priority=1,
                    metadata={'request_id': request_id, 'order_no': order_no}
                )
                if queued:
                    logger.info(f"[Queue] 回调已加入队列: {order_no}")
                    return True
                logger.warning(f"[Queue] 队列已满，直接发送: {order_no}")
            except Exception as e:
                logger.error(f"[Queue] 入队失败，直接发送: {e}")

        if self._circuit_breaker:
            try:
                return self._circuit_breaker.call(_do_send)
            except Exception as e:
                logger.error(f"[Callback] 熔断器保护发送回调: {e}")
                return False

        try:
            return _do_send()
        except Exception as e:
            logger.error(f"[Callback] 发送回调异常: {e}")
            return False


@app.route('/api/sync/report/wechat', methods=['POST'])
def wechat_report():
    """
    微信报工接口 - 异步模式
    
    微信端发起报工请求，云服务器记录请求后返回待确认，
    然后通知主软件处理，主软件处理完成后回调确认接口。
    
    请求体:
    {
        "order_no": "WO0001",
        "process": "编织",
        "quantity": 100,
        "operator": "YuanGangBiao"
    }
    
    返回:
    {
        "code": 200,
        "message": "报工请求已提交，等待主软件确认",
        "data": {
            "request_id": "abc123",
            "order_no": "WO0001",
            "process": "编织",
            "quantity": 100,
            "status": "pending"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '无效的JSON数据'}), 400

        order_no = data.get('order_no')
        process = data.get('process', '')
        quantity = data.get('quantity', 0)
        operator = data.get('operator', '')

        if not order_no:
            return jsonify({'code': 400, 'message': '缺少order_no字段'}), 400

        all_tasks = _get_client().get_packages(limit=5000)
        task = next((t for t in all_tasks if (t.get('order_no') == order_no or t.get('related_order') == order_no) and (t.get('process_name') == process or t.get('content', {}).get('process_name') == process)), None)
        if not task:
            return jsonify({'code': 404, 'message': f'未找到订单 {order_no} 的任务'}), 404

        order_no = task.get('related_order', '') or order_no
        task_id = task.get('id')
        planned_qty = task.get('content', {}).get('planned_qty', 0)
        current_completed = task.get('completed_qty', 0)
        new_completed = current_completed + quantity
        remaining = max(0, planned_qty - new_completed)

        req_manager = get_report_request_manager()
        report_req = req_manager.create_request(
            order_no=order_no,
            process=process,
            quantity=quantity,
            operator=operator,
            task_id=task_id,
            current_completed=current_completed,
            planned_qty=planned_qty,
            new_completed=new_completed,
            remaining=remaining
        )

        log_upstream(
            source='微信',
            operation_type='报工请求',
            content=f'微信报工请求: {order_no} - {process} - 操作员: {operator}',
            details={
                'request_id': report_req.id,
                'order_no': order_no,
                'process': process,
                'quantity': quantity,
                'planned_qty': planned_qty,
                'current_completed': current_completed,
                'new_completed': new_completed,
                'remaining': remaining,
                'operator': operator
            },
            result='待确认',
            user_id=operator,
            order_no=order_no,
            process=process,
            quantity=quantity,
            status='待确认'
        )

        ctx = WeChatContext.get_instance()
        if ctx._callback_sender:
            callback_data = {
                'request_id': report_req.id,
                'order_no': task.get('order_no') or task.get('content', {}).get('order_no', order_no),
                'order_no': order_no,
                'process': process,
                'quantity': quantity,
                'operator': operator,
                'task_id': task_id,
                'current_completed': current_completed,
                'planned_qty': planned_qty,
                'new_completed': new_completed,
                'remaining': remaining,
                'timestamp': datetime.now().isoformat()
            }
            ctx._callback_sender.send(
                callback_data=callback_data,
                order_no=order_no,
                request_id=report_req.id
            )

            # 通知调度中心更新工单完成计数
            try:
                requests.post(
                    'http://127.0.0.1:5000/api/dispatch-center/workorder/update-task-count',
                    json={
                        'order_no': order_no,
                        'action': 'complete',
                        'task_type': 'process'
                    },
                    timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '2'))
                )
            except Exception as e:
                logger.warning(f"[Sync] 通知调度中心完成计数失败: {e}")

        return jsonify({
            'code': 200,
            'message': '报工请求已提交，等待主软件确认',
            'data': {
                'request_id': report_req.id,
                'order_no': order_no,
                'process': process,
                'quantity': quantity,
                'planned_qty': planned_qty,
                'current_completed': current_completed,
                'new_completed': new_completed,
                'remaining': remaining,
                'status': 'pending'
            }
        })

    except Exception as e:
        logger.error(f"[Sync] 微信报工异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


def _notify_operator(
    success: bool,
    order_no: str,
    process: str,
    quantity: int,
    operator: str,
    message: str = '',
    completed_qty: int = 0,
    remaining: int = 0,
    request_id: str = '',
):
    """
    发送微信通知并记录下游日志

    Args:
        success: 是否成功
        order_no: 订单号
        process: 工序名称
        quantity: 报工数量
        operator: 操作员ID
        message: 失败原因（失败时使用）
        completed_qty: 累计完成数量（成功时使用）
        remaining: 剩余数量（成功时使用）
        request_id: 报工请求ID
        order_no: 订单号(WO-xxx)，优先显示
    """
    if not _app_bot or not operator:
        return

    display_no = order_no
    if success:
        reply_msg = f"✅ 报工成功！\n\n订单号: {display_no}\n工序: {process}\n本次报工: {quantity}\n累计完成: {completed_qty}\n剩余: {remaining}"
    else:
        reply_msg = f"❌ 报工失败！\n\n订单号: {display_no}\n工序: {process}\n原因: {message}"

    try:
        _app_bot.send_text(reply_msg, user_id=operator)
        status_text = '成功' if success else '失败'
        logger.info(f"[Callback] 已通知用户 {operator} 报工{status_text}")

        if success:
            log_downstream(
                source='微信',
                operation_type='报工确认',
                content=f'通知用户 {operator} 报工成功',
                details={
                    'request_id': request_id,
                    'order_no': order_no,
                    'process': process,
                    'quantity': quantity,
                    'completed_qty': completed_qty,
                    'remaining': remaining
                },
                result='成功',
                user_id=operator,
                order_no=order_no,
                process=process,
                quantity=quantity,
                status='成功'
            )
    except Exception as e:
        logger.error(f"[Callback] 发送微信通知失败: {e}")


@app.route('/api/sync/report/confirm', methods=['POST'])
def confirm_report():
    """
    主软件回调接口 - 确认报工结果
    
    请求参数:
    - request_id: 报工请求ID
    - success: 是否成功 (true/false)
    - message: 回复消息
    - completed_qty: 完成数量（成功时）
    - remaining: 剩余数量（成功时）
    - operator: 操作员ID（用于发送微信通知）
    
    返回:
    - code: 状态码
    - message: 消息
    """
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        success = data.get('success', False)
        message = data.get('message', '')
        completed_qty = data.get('completed_qty', 0)
        remaining = data.get('remaining', 0)
        operator = data.get('operator', '')

        logger.info(f"[Callback] 收到主软件报工确认 - request_id: {request_id}, success: {success}")

        req_manager = get_report_request_manager()
        report_req = req_manager.get_request(request_id)

        if not report_req:
            logger.warning(f"[Callback] 未找到报工请求: {request_id}")
            return jsonify({'code': 404, 'message': '未找到报工请求'}), 404

        order_no = ''
        if report_req.task_id:
            task_doc = _get_client().get_package(report_req.task_id)
            if task_doc:
                order_no = task_doc.get('related_order', '') or report_req.order_no
        if not order_no:
            work_
        if success:
            req_manager.confirm_request(request_id, message)

            if report_req.task_id:
                _get_client().update_document('work_order', report_req.task_id, {
                    'progress_qty': report_req.quantity,
                    'operator_id': report_req.operator,
                })

            _notify_operator(
                success=True,
                order_no=report_req.order_no,
                process=report_req.process,
                quantity=report_req.quantity,
                operator=operator,
                completed_qty=completed_qty,
                remaining=remaining,
                request_id=request_id,
            )

            log_upstream(
                source='主软件',
                operation_type='报工确认',
                content=f'报工确认成功: {report_req.order_no} - {report_req.process} - 操作员: {operator}',
                details=data,
                result='成功',
                user_id=operator,
                order_no=report_req.order_no,
                process=report_req.process,
                quantity=report_req.quantity,
                status='成功'
            )

            return jsonify({
                'code': 200,
                'message': '报工确认成功',
                'data': {
                    'request_id': request_id,
                    'order_no': report_req.order_no,
                    'process': report_req.process,
                    'quantity': report_req.quantity
                }
            })

        req_manager.reject_request(request_id, message)

        _notify_operator(
            success=False,
            order_no=report_req.order_no,
            process=report_req.process,
            quantity=report_req.quantity,
            operator=operator,
            message=message,
            request_id=request_id,
        )

        log_upstream(
            source='主软件',
            operation_type='报工确认',
            content=f'报工确认失败: {report_req.order_no} - {report_req.process} - 操作员: {operator}',
            details=data,
            result=f'失败: {message}',
            user_id=operator,
            order_no=report_req.order_no,
            process=report_req.process,
            quantity=report_req.quantity,
            status='失败',
            error_message=message
        )

        return jsonify({
            'code': 200,
            'message': '报工确认失败',
            'data': {
                'request_id': request_id,
                'order_no': report_req.order_no,
                'error': message
            }
        })

    except Exception as e:
        logger.error(f"[Callback] 处理报工确认异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/sync/report/requests', methods=['GET'])
def get_pending_requests():
    """
    获取待确认的报工请求列表
    """
    try:
        req_manager = get_report_request_manager()
        requests = req_manager.get_pending_requests()
        
        return jsonify({
            'code': 200,
            'data': requests,
            'count': len(requests)
        })
    except Exception as e:
        logger.error(f"[Callback] 获取待确认请求异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500


# ============== 兼容导出 ==============
# 供其他模块通过 `from wechat_server import ...` 引用
container_center = None
wechat_app_bot = None
message_hub = None

if __name__ == '__main__':
    import sys as _sys
    _sys.stderr.write(f"[DEBUG] __name__ == '__main__' reached at line 2730\n")
    _sys.stderr.flush()
    try:
        init_services()
        init_wechat_services()
        cleaned = cleanup_old_logs()
        if cleaned > 0:
            logger.info(f'[Server] 已清理 {cleaned} 个过期日志文件')
    except Exception as e:
        error_log = os.path.join(_static_dir, 'startup_error.log')
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write(f"启动错误: {e}\n")
            f.write(traceback.format_exc())
        logger.error(f"启动失败，请查看错误日志: {error_log}")
        time.sleep(30)
        sys.exit(1)

    _sys.stderr.write("[DEBUG] After init_services, before cloud_config\n")
    _sys.stderr.flush()

    # 启动调度中心后台调度器
    try:
        from dispatch_center import start_background_scheduler
        start_background_scheduler()
        logger.info('[Server] 调度中心后台调度器已启动')
    except Exception as e:
        logger.warning(f'[Server] 调度中心后台调度器启动失败: {e}')
    cloud_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloud_config.json')
    cloud_host = None
    cloud_api_key = None

    if os.path.exists(cloud_config_file):
        try:
            import json
            with open(cloud_config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if cfg.get('enabled') and cfg.get('cloud_host'):
                    cloud_host = cfg['cloud_host']
                    cloud_api_key = cfg.get('api_key', os.getenv('WECHAT_CLOUD_API_KEY'))
        except Exception as e:
            logger.warning(f"读取云端配置异常: {e}")

    _sys.stderr.write(f"[DEBUG] cloud_host={cloud_host}, CLOUD_POLLER_AVAILABLE={CLOUD_POLLER_AVAILABLE}\n")
    _sys.stderr.flush()
    if cloud_host and CLOUD_POLLER_AVAILABLE:
        try:
            from wechat_server_handlers import handle_cloud_message, set_wechat_handler
            init_cloud_poller(
                message_handler=handle_cloud_message,
                cloud_host=cloud_host,
                api_key=cloud_api_key
            )
            ctx = WeChatContext.get_instance()
            set_wechat_handler(ctx._wechat_handler, ctx._container_center)
            start_polling()
            logger.info(f'[云端] 混合模式已启用，轮询: {cloud_host}')
        except Exception as e:
            logger.error(f'[云端] 混合模式初始化失败: {e}')
    else:
        logger.info('[云端] 云端模式运行，禁用本地轮询（本地客户端应连接本云端）')

    _sys.stderr.write("[DEBUG] Before app.run()\n")
    _sys.stderr.flush()
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5003, help='监听端口')
    args = parser.parse_args()

    logger.info(f"[Server] 启动服务器: {args.host}:{args.port}")
    try:
        app.run(host=args.host, port=args.port, threaded=True)
    except Exception as e:
        logger.error(f"[Server] app.run异常: {e}")
        raise
