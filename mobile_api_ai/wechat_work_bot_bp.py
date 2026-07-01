# -*- coding: utf-8 -*-
"""企业微信机器人蓝图 — 从 wechat_work_bot_v2.py 分离

提供:
  POST /api/wechat/hook         群机器人 Webhook
  POST /api/wechat/app/hook     应用机器人回调
  GET  /api/wechat/app/hook     URL 验证
  POST /api/wechat/proxy_send   代理发送消息
  GET  /api/wechat/status       企微连接状态
  GET  /api/wechat/test         测试接口

后台能力:
  企业微信群通知（任务分配/确认/报工推送）
  应用机器人主动推送+回调对话
  物料输入解析（parse_material_input）
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

import re
import time
import json
import random
import threading
import logging
from datetime import datetime

import requests
from flask import Blueprint, request, jsonify

from core.config import (
    DB_PATHS, SERVICE_URLS, DB_CONNECT_TIMEOUT,
    REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL,
    WECHAT_BOT_HOST, WECHAT_BOT_PORT,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════════
WECHAT_WORK_BOT_URL = None
WECHAT_CORP_ID = None
WECHAT_AGENT_ID = None
WECHAT_SECRET = None
WECHAT_TOKEN = None
OPERATORS = {}
MAIN_SOFTWARE_CALLBACK_URL = os.environ.get('MAIN_SOFTWARE_CALLBACK_URL')

# ═══════════════════════════════════════════════
# 容器中心代理（与 wechat_work_bot_v2 共用实例）
# ═══════════════════════════════════════════════
class ContainerCenterHolder:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def initialize(cls, config):
        with cls._lock:
            if cls._instance is not None:
                return
            cls._instance = _ContainerCenterProxy()
            cls._instance.initialize(config)

    @classmethod
    def get(cls):
        return cls._instance


class _ContainerCenterProxy:
    def __init__(self):
        self._cc = None

    def initialize(self, config):
        try:
            from container_center_v5 import ContainerCenter
            self._cc = ContainerCenter(config=config)
        except Exception:
            self._cc = None

    @property
    def storage(self):
        return self._cc.storage if self._cc else None

    def get_all_tasks(self):
        return self._cc.get_all_tasks() if self._cc else []

    def receive_return(self, task_id, return_data):
        if self._cc:
            return self._cc.receive_return(task_id, return_data)


container_center = ContainerCenterHolder.get()


def _refresh_process_names():
    global PROCESS_NAMES
    try:
        if container_center and hasattr(container_center, 'storage'):
            packages = container_center.storage.get_packages(limit=1000)
            processes = set()
            for pkg in packages:
                raw_c = pkg.get('content', {})
                c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                pn = pkg.get('related_process') or c.get('process_name', '')
                if pn:
                    processes.add(pn)
            PROCESS_NAMES = sorted(processes) if processes else []
    except Exception as e:
        logger.warning(f'刷新工序名称列表异常: {e}')


def _get_operator_name_from_container(operator_id):
    if not operator_id:
        return operator_id or '未知'
    try:
        if container_center and hasattr(container_center, 'storage'):
            packages = container_center.storage.get_packages(limit=1000)
            for pkg in packages:
                if pkg.get('target_operator') == operator_id:
                    raw_c = pkg.get('content', {})
                    c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                    name = c.get('operator_name', '')
                    if name:
                        return name
                    name = pkg.get('operator_name', '')
                    if name:
                        return name
    except Exception as e:
        logger.warning(f'从容器获取操作员名称异常: {e}')
    return operator_id


def _refresh_operators():
    global OPERATORS
    try:
        ops = {}
        if container_center and hasattr(container_center, 'storage'):
            packages = container_center.storage.get_packages(limit=1000)
            for pkg in packages:
                op_id = pkg.get('target_operator')
                if not op_id:
                    op_id = pkg.get('operator_id', '')
                if op_id and op_id not in ops:
                    raw_c = pkg.get('content', {})
                    c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                    ops[op_id] = {
                        'name': c.get('operator_name', op_id),
                        'department': c.get('department', ''),
                        'role': c.get('operator_role', '操作员'),
                    }
        else:
            import pymysql
            from core.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD
            conn = pymysql.connect(
                host=MYSQL_HOST, port=MYSQL_PORT,
                user=MYSQL_USER, password=MYSQL_PASSWORD,
                database='container_center', charset='utf8mb4')
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(
                "SELECT DISTINCT target_operator FROM data_packages "
                "WHERE target_operator IS NOT NULL AND target_operator != '' LIMIT 200")
            for row in cur.fetchall():
                op_id = row['target_operator']
                if op_id and op_id not in ops:
                    ops[op_id] = {'name': op_id, 'department': '', 'role': '操作员'}
            cur.close()
            conn.close()
        OPERATORS = ops
    except Exception as e:
        logger.warning(f'刷新操作员列表异常: {e}')


# ═══════════════════════════════════════════════
# 物料解析
# ═══════════════════════════════════════════════
def parse_material_input(text):
    """解析物料输入: '材料名 数量 单位'"""
    text = text.strip()
    if not text:
        return {'material_name': '', 'quantity': 0, 'unit': '件'}
    parts = text.split()
    if len(parts) >= 3 and parts[-2].isdigit():
        return {
            'material_name': ' '.join(parts[:-2]),
            'quantity': int(parts[-2]),
            'unit': parts[-1]
        }
    elif len(parts) >= 2 and parts[-1].isdigit():
        return {
            'material_name': ' '.join(parts[:-1]),
            'quantity': int(parts[-1]),
            'unit': '件'
        }
    return {'material_name': text, 'quantity': 0, 'unit': '件'}


def parse_material_requisition_command(text):
    """解析领料指令"""
    result = parse_material_input(text)
    return result


# ═══════════════════════════════════════════════
# 企业微信配置与 Bot 类
# ═══════════════════════════════════════════════
class WeChatConfig:
    _instance = None
    _lock = threading.Lock()
    _config = {
        'webhook_url': None, 'corp_id': None,
        'agent_id': None, 'secret': None, 'token': None,
    }
    _initialized = False

    @classmethod
    def load(cls):
        with cls._lock:
            if cls._initialized:
                return
            cls._config['webhook_url'] = os.getenv('WECHAT_WORK_BOT_URL')
            cls._config['corp_id'] = os.getenv('WECHAT_CORP_ID')
            cls._config['agent_id'] = os.getenv('WECHAT_AGENT_ID')
            cls._config['secret'] = os.getenv('WECHAT_SECRET')
            cls._config['token'] = os.getenv('WECHAT_TOKEN')

            global WECHAT_WORK_BOT_URL
            WECHAT_WORK_BOT_URL = cls._config['webhook_url']

            if cls._config['corp_id'] and cls._config['agent_id'] and cls._config['secret']:
                try:
                    from wechat_app_bot import init_app_bot
                    init_app_bot(cls._config['corp_id'], cls._config['agent_id'], cls._config['secret'])
                    logger.info('[WeChat] 企业微信应用机器人已初始化')
                except Exception as e:
                    logger.error(f'[WeChat] 应用机器人初始化失败: {e}')
            cls._initialized = True

    @classmethod
    def get(cls, key):
        with cls._lock:
            return cls._config.get(key)

    @classmethod
    def get_all(cls):
        with cls._lock:
            return cls._config.copy()


def load_config():
    WeChatConfig.load()


class WeChatWorkBot:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def _request_with_retry(self, payload, max_retries=3):
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    self.webhook_url, json=payload, timeout=REQUEST_TIMEOUT_FAST
                )
                if resp.json().get('errcode') == 0:
                    return True
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + random.uniform(0, 0.5))
            except Exception as e:
                logger.warning(f'[WeChatBot] 请求失败(第{attempt+1}次): {e}')
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + random.uniform(0, 0.5))
        return False

    def send_text(self, content):
        _violation_forbidden_bot('UserBot.send_text')
        return self._request_with_retry({'msgtype': 'text', 'text': {'content': content}})

    def send_markdown(self, content):
        _violation_forbidden_bot('UserBot.send_markdown')
        return self._request_with_retry({'msgtype': 'markdown', 'markdown': {'content': content}})

    def send_news(self, articles):
        return self._request_with_retry({'msgtype': 'news', 'news': {'articles': articles}})


def get_bot():
    if not WECHAT_WORK_BOT_URL:
        return None
    return WeChatWorkBot(WECHAT_WORK_BOT_URL)


# ═══════════════════════════════════════════════
# 消息发送辅助
# ═══════════════════════════════════════════════
def _violation_forbidden_bot(method_name: str, detail: str = None):
    """[R13 T9] 写违规日志，禁止端点被调用"""
    try:
        from mobile_api_ai.process_code_validator import _write_violation
        _write_violation(
            scenario=f'wechat_work_bot_bp.{method_name}',
            violation_type='forbidden_direct_bot_call',
            severity='WARN',
            detail=detail or f'{method_name} 被直接调用，应改用 wechat_msg_dispatcher.send_templated()'
        )
    except Exception:
        pass


def _send_work_bot(content, msg_type='text'):
    _violation_forbidden_bot('_send_work_bot',
        f'直接调用 _send_work_bot，content={content[:50]!r}')
    bot = get_bot()
    if not bot:
        return False, 'bot未配置'
    if msg_type == 'markdown':
        return bot.send_markdown(content), ''
    return bot.send_text(content), ''


def send_task_notification(task_data):
    """[R13 T10] 通过 W3 dispatcher 发送任务分配通知"""
    try:
        from wechat_msg_dispatcher import send_templated, BotType
        send_templated(
            scenario='workorder_created',
            context={
                '订单号': task_data.get('order_no', ''),
                '工序': task_data.get('process', ''),
                '操作员': task_data.get('operator', ''),
                '数量': task_data.get('quantity', 0),
            },
            bot_type=BotType.GROUP,
        )
    except Exception as e:
        logger.warning(f'send_task_notification W3 error: {e}')


def send_report_notification(task_data):
    """[R13 T10] 通过 W3 dispatcher 发送报工完成通知"""
    try:
        from wechat_msg_dispatcher import send_templated, BotType
        send_templated(
            scenario='workorder_complete',
            context={
                '订单号': task_data.get('order_no', ''),
                '工序': task_data.get('process', ''),
                '操作员': task_data.get('operator', ''),
                '数量': task_data.get('quantity', 0),
            },
            bot_type=BotType.GROUP,
        )
    except Exception as e:
        logger.warning(f'send_report_notification W3 error: {e}')


def _sync_material_to_upstream(order_no, process, qty, unit, operator_id):
    """将实际用料同步回传给主软件"""
    if not MAIN_SOFTWARE_CALLBACK_URL:
        return
    try:
        payload = {
            'type': 'material_report',
            'order_no': order_no, 'process': process,
            'material_qty': qty, 'material_unit': unit,
            'operator': operator_id,
            'timestamp': datetime.now().isoformat()
        }
        requests.post(MAIN_SOFTWARE_CALLBACK_URL, json=payload, timeout=REQUEST_TIMEOUT_FAST)
    except Exception as e:
        logger.warning(f'物料同步失败: {e}')


# ═══════════════════════════════════════════════
# 消息处理
# ═══════════════════════════════════════════════
def handle_text_message(content, from_user, bot):
    """处理文本消息"""
    content = content.strip()
    logger.info(f'[Text] 来自 {from_user}: {content}')

    if not content:
        return jsonify({'code': 0, 'message': 'success'})

    # 报工指令: 报工 工单号 工序 数量
    if content.startswith('报工') or content.startswith('report'):
        parts = content.replace('报工', '').replace('report', '').strip().split()
        if len(parts) >= 2:
            order_no = parts[0]
            if len(parts) >= 3:
                process = parts[1]
                qty = int(parts[2]) if parts[2].isdigit() else 1
            else:
                process = ''
                qty = int(parts[1]) if parts[1].isdigit() else 1
            bot.send_markdown(
                f'📋 **报工指令已收到**\n'
                f'> 工单: {order_no}\n'
                f'> 工序: {process}\n'
                f'> 数量: {qty}\n'
                f'请在网页端完成报工'
            )
            return jsonify({'code': 0, 'message': 'success'})

    # 查询指令: 查单 工单号
    if content.startswith('查单') or content.startswith('查询'):
        order_no = content.replace('查单', '').replace('查询', '').strip()
        if order_no and container_center:
            try:
                pkgs = container_center.storage.get_packages(related_order=order_no, limit=20)
                if pkgs:
                    lines = [f'📦 **{order_no}** 任务列表:']
                    for pkg in pkgs:
                        raw_c = pkg.get('content', {})
                        c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
                        proc = pkg.get('related_process', '') or c.get('process_name', '')
                        stat = pkg.get('status', 'pending')
                        lines.append(f'  • {proc} [{stat}]')
                    bot.send_markdown('\n'.join(lines))
                else:
                    bot.send_text(f'未找到工单 {order_no} 的任务')
            except Exception as e:
                bot.send_text(f'查询失败: {e}')
        return jsonify({'code': 0, 'message': 'success'})

    # 领料: 领料 材料名 数量 单位
    if content.startswith('领料'):
        material_text = content.replace('领料', '').strip()
        mat = parse_material_input(material_text)
        bot.send_markdown(
            f'📦 **领料指令已收到**\n'
            f'> 材料: {mat["material_name"]}\n'
            f'> 数量: {mat["quantity"]} {mat["unit"]}'
        )
        return jsonify({'code': 0, 'message': 'success'})

    # 帮助
    if content in ('帮助', 'help', '?'):
        bot.send_markdown(
            '🤖 **生产任务助手**\n\n'
            '📋 报工 工单号 工序 数量\n'
            '🔍 查单 工单号\n'
            '📦 领料 材料名 数量 单位\n'
            '📊 进度 - 查看进度'
        )
        return jsonify({'code': 0, 'message': 'success'})

    return jsonify({'code': 0, 'message': 'success'})


def handle_voice_message(data, from_user, bot):
    """处理语音消息"""
    return jsonify({'code': 0, 'message': 'success'})


def handle_image_message(data, from_user, bot):
    """处理图片消息"""
    return jsonify({'code': 0, 'message': 'success'})


def _handle_wechat_xml_callback(raw_data):
    """处理企业微信XML加密回调"""
    from wechat_app_bot import get_app_bot
    app_bot = get_app_bot()
    if not app_bot:
        logger.warning('[WeChat] 企业微信应用机器人未配置')
        return 'success'

    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')

    try:
        xml_str = raw_data.decode('utf-8')
        token = os.getenv('WECHAT_TOKEN', '')
        aes_key = os.getenv('WECHAT_AES_KEY', '')
        encrypt = app_bot._extract_encrypt(xml_str)
        if not encrypt:
            return 'success'

        if token and aes_key:
            decrypted = app_bot._decrypt_message(encrypt, token, aes_key, msg_signature, timestamp, nonce)

            content_match = re.search(r'<Content><!\[CDATA\[(.*?)\]\]></Content>', decrypted)
            user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', decrypted)

            content = (content_match.group(1) if content_match else '').strip()
            from_user = (user_match.group(1) if user_match else '未知用户')

            if content and from_user:
                bot = get_bot()
                if bot:
                    handle_text_message(content, from_user, bot)
        else:
            logger.warning('[WeChat] 缺少WECHAT_TOKEN或WECHAT_AES_KEY')
    except Exception as e:
        logger.error(f'[WeChat] XML回调处理异常: {e}')
    return 'success'


def get_app_bot_proxy(to_user):
    """获取应用机器人的消息发送代理"""
    class AppBotProxy:
        def __init__(self, target_user):
            self.target_user = target_user

        def send_text(self, text):
            _violation_forbidden_bot('UserBot.AppBotProxy.send_text',
                'AppBotProxy.send_text 直接调用，应改用 wechat_msg_dispatcher.send_templated()')
            from wechat_app_bot import get_app_bot
            app_bot = get_app_bot()
            if app_bot:
                app_bot.send_text_to_user(self.target_user, text)

        def send_markdown(self, text):
            _violation_forbidden_bot('UserBot.AppBotProxy.send_markdown',
                'AppBotProxy.send_markdown 直接调用，应改用 wechat_msg_dispatcher.send_templated()')
            from wechat_app_bot import get_app_bot
            app_bot = get_app_bot()
            if app_bot:
                clean_text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
                clean_text = re.sub(r'#{1,6}\s+', '', clean_text)
                app_bot.send_text_to_user(self.target_user, clean_text)

        def send_news(self, articles):
            from wechat_app_bot import get_app_bot
            app_bot = get_app_bot()
            if app_bot:
                app_bot.send_news_message(self.target_user, articles)

    return AppBotProxy(to_user)


# ═══════════════════════════════════════════════
# Blueprint 路由
# ═══════════════════════════════════════════════
wechat_bot_bp = Blueprint('wechat_work_bot', __name__, url_prefix='/api/wechat')


@wechat_bot_bp.route('/hook', methods=['POST'])
def wechat_hook():
    """接收企业微信群消息 / 企业微信应用回调"""
    raw_data = request.data

    if raw_data and (raw_data.strip().startswith(b'<xml') or b'<Encrypt>' in raw_data):
        return _handle_wechat_xml_callback(raw_data)

    try:
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = request.get_json()
        else:
            data = request.get_json(silent=True)
    except Exception:
        data = None

    if not data:
        return jsonify({'code': 0, 'message': 'success'})

    msg_type = data.get('msgtype', 'text')
    content = data.get('text', {}).get('content', '').strip()
    from_user = data.get('sender', {}).get('name', '未知用户')

    bot = get_bot()
    if not bot:
        return jsonify({'code': 0, 'message': 'success'})

    if msg_type == 'text':
        return handle_text_message(content, from_user, bot)
    elif msg_type == 'voice':
        return handle_voice_message(data, from_user, bot)
    elif msg_type == 'image':
        return handle_image_message(data, from_user, bot)
    return jsonify({'code': 0, 'message': 'success'})


@wechat_bot_bp.route('/app/hook', methods=['GET'])
def wechat_app_hook_verify():
    """企业微信应用 - URL验证接口"""
    from wechat_app_bot import get_app_bot
    app_bot = get_app_bot()
    if not app_bot:
        return '企业微信应用机器人未配置'

    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    echo_str = request.args.get('echostr', '')

    result = app_bot.verify_url(msg_signature, timestamp, nonce, echo_str)
    if result:
        return result
    return '验证失败', 400


@wechat_bot_bp.route('/app/hook', methods=['POST'])
def wechat_app_hook_message():
    """企业微信应用 - 接收消息接口"""
    from wechat_app_bot import get_app_bot
    app_bot = get_app_bot()
    if not app_bot:
        return 'success'

    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    data = request.data.decode('utf-8')

    try:
        msg_type, content, from_user = app_bot.parse_message(msg_signature, timestamp, nonce, data)
        if msg_type and content:
            bot_proxy = get_app_bot_proxy(from_user)
            handle_text_message(content, from_user, bot_proxy)
    except Exception as e:
        logger.error(f'[WeChatApp] 处理消息失败: {e}', exc_info=True)

    return 'success'


@wechat_bot_bp.route('/proxy_send', methods=['POST'])
def proxy_send():
    """代理发送企业微信消息"""
    data = request.get_json(silent=True) or {}
    msg_type = data.get('msgtype', 'text')
    content = data.get('content', '')
    bot = get_bot()

    if not bot:
        return jsonify({'code': 1, 'message': '企业微信机器人未配置'})

    if msg_type == 'text':
        ok, _ = bot.send_text(content), None
    elif msg_type == 'markdown':
        ok, _ = bot.send_markdown(content), None
    else:
        return jsonify({'code': 1, 'message': f'不支持的消息类型: {msg_type}'})

    return jsonify({'code': 0 if ok else 1, 'message': '发送成功' if ok else '发送失败'})


@wechat_bot_bp.route('/status', methods=['GET'])
def wechat_status():
    """企业微信连接状态"""
    return jsonify({
        'code': 0,
        'data': {
            'webhook_configured': bool(WECHAT_WORK_BOT_URL),
            'app_configured': bool(WeChatConfig.get('corp_id')),
            'operators_count': len(OPERATORS),
            'processes_count': len(PROCESS_NAMES),
        }
    })


@wechat_bot_bp.route('/test', methods=['GET'])
def wechat_test():
    """测试接口"""
    bot = get_bot()
    if bot:
        ok = bot.send_text('🤖 企业微信机器人测试消息')
        return jsonify({'code': 0 if ok else 1, 'message': '发送成功' if ok else '发送失败'})
    return jsonify({'code': 1, 'message': '机器人未配置'})


# ═══════════════════════════════════════════════
# 模块初始化 — 导入时自动执行
# ═══════════════════════════════════════════════
PROCESS_NAMES = []


def init_module():
    """初始化模块（容器中心 + 配置 + 缓存）"""
    ContainerCenterHolder.initialize({'type': os.getenv('CONTAINER_STORAGE_TYPE', 'mysql')})
    WeChatConfig.load()
    _refresh_process_names()
    _refresh_operators()
    logger.info('[WeChatBot BP] 模块已初始化')
