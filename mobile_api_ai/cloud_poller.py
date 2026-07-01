# -*- coding: utf-8 -*-
"""
云端轮询模块 - 混合模式本地部分
负责：
1. 轮询云端获取微信消息
2. 本地主动发送消息到云端/微信

增强特性：
- ACK 失败指数退避重试，防止云端重复投递
- 线程池并发处理消息，不阻塞轮询主循环
- send_message 失败自动重试
"""
import os
import sys
import logging
import time
import threading
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError, wait as futures_wait
from core.config import DB_PATHS

logger = logging.getLogger(__name__)

# ============== 配置 ==============
CLOUD_HOST = os.getenv('WECHAT_CLOUD_HOST', '')
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY', '')

# 端口配置
CLOUD_PORT = int(os.getenv('WECHAT_CLOUD_PORT', '5006'))
GROUP_BOT_PORT = int(os.getenv('WECHAT_GROUP_BOT_PORT', '5004'))

# 轮询间隔配置（秒），可从 .env 环境变量配置
POLL_INTERVAL_IDLE = int(os.getenv('POLL_INTERVAL_IDLE', '5'))
POLL_INTERVAL_BUSY = int(os.getenv('POLL_INTERVAL_BUSY', '5'))
POLL_IDLE_THRESHOLD = int(os.getenv('POLL_IDLE_THRESHOLD', '3'))

# ACK 重试配置
ACK_RETRY_MAX = int(os.getenv('ACK_RETRY_MAX', '5'))
ACK_RETRY_INTERVALS = [int(x) for x in os.getenv('ACK_RETRY_INTERVALS', '1,2,4,8,16').split(',')]

# 发送重试配置
SEND_RETRY_MAX = int(os.getenv('SEND_RETRY_MAX', '3'))
SEND_RETRY_INTERVALS = [int(x) for x in os.getenv('SEND_RETRY_INTERVALS', '1,2,4').split(',')]

# 线程池配置
POLL_WORKERS = int(os.getenv('POLL_WORKERS', '4'))
POLL_MAX_PENDING = int(os.getenv('POLL_MAX_PENDING', '20'))

# 本地去重缓存配置（防御云端 claim_messages 失效导致的消息重复投递）
DEDUP_CACHE_TTL = int(os.getenv('DEDUP_CACHE_TTL', '300'))  # 缓存有效期（秒），默认5分钟
DEDUP_CACHE_CLEANUP_INTERVAL = int(os.getenv('DEDUP_CACHE_CLEANUP_INTERVAL', '60'))  # 清理间隔（秒）

# 游标轮询配置
POLL_LIMIT = int(os.getenv('POLL_LIMIT', '5'))  # 每次轮询最大拉取条数
POLL_CURSOR_MAX = int(os.getenv('POLL_CURSOR_MAX', '99999'))  # 游标到达此值后自动归零

# 游标持久化文件
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURSOR_FILE = os.path.join(_BASE_DIR, 'cloud_cursor.txt')


# ============== 轮询客户端 ==============

class CloudPoller:
    """云端消息轮询器"""

    def __init__(self, message_handler=None, cloud_host=None, api_key=None, cloud_port=None):
        """
        Args:
            message_handler: 消息处理回调函数，接收 (data: dict) 参数
            cloud_host: 云端地址
            api_key: API密钥
            cloud_port: 云端端口
        """
        self.message_handler = message_handler
        self.cloud_host = cloud_host or CLOUD_HOST
        self.api_key = api_key or API_KEY
        self.cloud_port = cloud_port or CLOUD_PORT
        self.group_bot_port = GROUP_BOT_PORT
        self.running = False
        self.poll_thread = None
        self.last_poll_time = None
        self.success_count = 0
        self.error_count = 0
        self.message_count = 0
        self._current_poll_token = ''
        self._last_polled_id = self._load_cursor()  # 游标：已拉取的最大 rowid，用于 since_id 轮询（从文件恢复）
        self._idle_poll_count = 0  # 连续空轮询计数（用于降低日志频率）

        # message_hub（由外部通过 set_message_hub 注入）
        self._message_hub = None

        # 动态间隔状态
        self._idle_count = 0
        self._current_interval = POLL_INTERVAL_IDLE

        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=POLL_WORKERS, thread_name_prefix='msg-handler')
        self._pending_futures = []

        # 本地去重缓存（防御云端 claim_messages 失效导致的消息重复投递）
        self._processed_cache = {}  # {dedup_key: timestamp}
        self._cache_lock = threading.Lock()
        self._last_cache_cleanup = 0

    def _load_cursor(self):
        """从文件恢复上次轮询游标，不存在时返回 0"""
        try:
            if os.path.exists(CURSOR_FILE):
                with open(CURSOR_FILE, 'r', encoding='utf-8') as f:
                    val = int(f.read().strip())
                    val = 0 if val < 0 else val
                    logger.info(f'[CloudPoller] 游标恢复: cloud_cursor.txt -> {val}')
                    return val
        except (ValueError, OSError) as e:
            logger.warning(f'[CloudPoller] 游标文件读取失败，使用 0: {e}')
        return 0

    def _save_cursor(self):
        """将当前游标持久化到文件"""
        try:
            val = max(self._last_polled_id, 0)
            with open(CURSOR_FILE, 'w', encoding='utf-8') as f:
                f.write(str(val))
        except OSError as e:
            logger.error(f'[CloudPoller] 游标写入失败: {e}')

    def _request(self, method, endpoint, **kwargs):
        """发送带认证的请求"""
        if not self.cloud_host:
            logger.warning('[云端请求] 云端地址未配置')
            return {'code': -1, 'message': '云端地址未配置'}

        port = kwargs.pop('port', self.cloud_port)

        if ':' in self.cloud_host.split('//')[1].split('/')[0] if '//' in self.cloud_host else '':
            url = f'{self.cloud_host}{endpoint}'
        else:
            url = f'{self.cloud_host}:{port}{endpoint}'

        headers = kwargs.pop('headers', {})
        headers['X-API-Key'] = self.api_key
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                timeout=kwargs.pop('timeout', 30),
                **kwargs
            )
            if not resp.content:
                logger.warning(f'[云端请求] 响应为空')
                return {'code': -1, 'message': '响应为空'}
            return resp.json()
        except json.JSONDecodeError as e:
            logger.error(f'[云端请求] JSON解析失败: {e}, 响应内容: {resp.text[:200] if resp.content else "empty"}')
            return {'code': -1, 'message': 'JSON解析失败'}
        except requests.exceptions.SSLError as e:
            logger.error(f'[云端请求] SSL错误: {e}')
            return {'code': -1, 'message': 'SSL错误'}
        except requests.exceptions.ConnectionError as e:
            logger.error(f'[云端请求] 连接错误: {e}')
            logger.error(f'[云端] 连接云端失败: {e}')
            return {'code': -1, 'message': '连接失败'}
        except Exception as e:
            logger.error(f'[云端请求] 异常: {e}')
            return {'code': -1, 'message': str(e)}

    def get_messages(self):
        """游标式轮询：按 rowid 顺序拉取消息，每次最多 POLL_LIMIT 条"""
        result = self._request(
            'GET', '/api/poll',
            params={'since_id': self._last_polled_id, 'limit': POLL_LIMIT}
        )

        if result.get('code') == 0:
            messages = result.get('messages', [])
            max_rowid = result.get('max_rowid', self._last_polled_id)
            archived = result.get('archived', False)

            # 调试：打印完整响应中的 max_rowid
            if messages:
                logger.debug(f'[云端] 调试: 响应中 messages={len(messages)}条, max_rowid={max_rowid}, archived={archived}, has_more={result.get("has_more")}')

            if archived:
                logger.warning(f'[轮询] 云端消息库已归档，游标从 {self._last_polled_id} 重置为 0')
                self._last_polled_id = 0
                self._save_cursor()
            elif max_rowid < self._last_polled_id:
                logger.warning(f'[轮询] 云端max_rowid({max_rowid})小于本地游标({self._last_polled_id})，云端DB已重置，游标归零')
                self._last_polled_id = 0
                self._save_cursor()
            elif max_rowid > self._last_polled_id:
                self._last_polled_id = max_rowid
                self._save_cursor()

            if self._last_polled_id >= POLL_CURSOR_MAX:
                logger.warning(f'[轮询] 游标已达上限 {POLL_CURSOR_MAX}，自动归零')
                self._last_polled_id = 0
                self._save_cursor()

            self.message_count += len(messages)
            logger.info(f'[轮询] 获取消息 {len(messages)} 条，游标={self._last_polled_id}，累计 {self.message_count}')
            if messages:
                self._idle_poll_count = 0
                logger.info(f'[云端] 收到 {len(messages)} 条消息，游标={self._last_polled_id}')
            else:
                self._idle_poll_count += 1
                if self._idle_poll_count % 6 == 0:
                    logger.info(f'[云端] 轮询正常（无新消息），游标={self._last_polled_id}')
            return messages
        else:
            self.error_count += 1
            logger.warning(f'[轮询] 获取失败({self.error_count}): {result.get("message")}')
            logger.warning(f'[云端] 拉取失败: {result.get("message")}')
            return []

    def _send_with_retry(self, endpoint, payload, retry_intervals, max_retries, name='操作'):
        """通用带重试的请求发送

        Args:
            endpoint: API端点
            payload: 请求体
            retry_intervals: 重试间隔列表（秒）
            max_retries: 最大重试次数
            name: 操作名称（用于日志）

        Returns:
            dict: 响应结果
        """
        last_result = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    interval = retry_intervals[attempt - 1] if attempt - 1 < len(retry_intervals) else retry_intervals[-1]
                    logger.info(f'[{name}] 第{attempt}次重试，等待{interval}s...')
                    time.sleep(interval)

                result = self._request('POST', endpoint, json=payload)
                last_result = result

                if result.get('code') == 0:
                    return result

                logger.warning(f'[{name}] 尝试{attempt + 1}/{max_retries + 1}失败: {result.get("message", "未知错误")}')
            except Exception as e:
                last_result = {'code': -1, 'message': str(e)}
                logger.warning(f'[{name}] 尝试{attempt + 1}/{max_retries + 1}异常: {e}')
                if attempt == max_retries:
                    break

        logger.error(f'[{name}] 重试{max_retries}次后仍失败')
        return last_result or {'code': -1, 'message': '重试失败'}

    def send_message(self, content, to_user='@all', msg_type='text', bot_type='group'):
        """
        主动发送消息到微信（通过云端5006端口），带重试

        Args:
            content: 消息内容
            to_user: 发送给谁，@all 表示所有人
            msg_type: 消息类型 text/markdown
            bot_type: 机器人类型 'group'（群机器人）或 'app'（企业微信应用）

        Returns:
            bool: 是否成功
        """
        logger.info(f'[发送] [{bot_type}] 发送给 {to_user}: {content[:50]}...')

        payload = {
            'to_user': to_user,
            'content': content,
            'msg_type': msg_type,
            'bot_type': bot_type,
            'route_tag': 'wechat_message'
        }

        payload['_corp_id'] = os.getenv('WECHAT_CORP_ID', '')
        payload['_agent_id'] = os.getenv('WECHAT_AGENT_ID', '')
        payload['_secret'] = os.getenv('WECHAT_SECRET', '')

        result = self._send_with_retry(
            '/api/send',
            payload,
            SEND_RETRY_INTERVALS,
            SEND_RETRY_MAX,
            f'send_{bot_type}'
        )

        if result.get('code') == 0:
            logger.info(f'[发送] 成功（通过云端端口{self.cloud_port}）')
            return True
        else:
            logger.error(f'[发送] 最终失败: {result.get("message", "未知错误")}')
            return False

    def send_via_message_hub(self, content, target=None, bot_type='group'):
        """
        通过本地message_hub发送消息（需要云端支持local/send接口）

        Args:
            content: 消息内容
            target: 目标用户/群，None表示广播
            bot_type: 机器人类型

        Returns:
            bool: 是否成功
        """
        if not self._message_hub:
            logger.warning('[发送] message_hub未初始化')
            return False

        try:
            from bots.base import BotType
            bt = BotType.APP if bot_type == 'app' else BotType.GROUP

            if target:
                success = self._message_hub.send_to_user(target, content, bot_type=bt)
            else:
                success = self._message_hub.broadcast(content)

            return success
        except Exception as e:
            logger.error(f'[发送] message_hub异常: {e}')
            return False

    def get_queue_status(self):
        """获取队列状态"""
        return self._request('GET', '/api/queue/status')

    def _send_ack(self, ids):
        """确认消息已处理完成（带poll_token校验），失败后指数退避重试

        确保云端不会重复投递消息。
        """
        if not ids:
            return

        payload = {'ids': ids}
        if self._current_poll_token:
            payload['poll_token'] = self._current_poll_token

        logger.info(f'[ACK] 开始确认 {len(ids)} 条消息, token={self._current_poll_token[:16] if self._current_poll_token else "无"}...')

        result = self._send_with_retry(
            '/api/poll/ack',
            payload,
            ACK_RETRY_INTERVALS,
            ACK_RETRY_MAX,
            'ACK'
        )

        if result.get('code') == 0:
            logger.info(f'[ACK] 已确认 {len(ids)} 条消息')
        else:
            logger.error(f'[ACK] 重试{ACK_RETRY_MAX}次后仍失败，需人工确认消息状态: ids={ids[:5]}...')

    def _process_message_async(self, msg):
        """异步处理单条消息（在线程池中执行）"""
        if not self.message_handler:
            logger.warning('[处理] message_handler未设置')
            return None

        msg_id = msg.get('id', 'unknown')
        try:
            logger.info(f'[处理] 开始处理消息: id={msg_id}')
            self.message_handler(msg)
            logger.info(f'[处理] 消息处理完成: id={msg_id}')
            return msg_id
        except Exception as e:
            logger.error(f'[处理] 消息处理异常: id={msg_id}, error={e}')
            # 处理失败仍返回msg_id，确保ACK会发送
            # 云端会重新投递这条消息
            return msg_id

    def _cleanup_futures(self):
        """清理已完成的future，控制pending数量"""
        self._pending_futures = [f for f in self._pending_futures if not f.done()]
        max_wait = max(1, POLL_MAX_PENDING - len(self._pending_futures))
        while len(self._pending_futures) > POLL_MAX_PENDING:
            done, _ = futures_wait(self._pending_futures, return_when='FIRST_COMPLETED')
            self._pending_futures = [f for f in self._pending_futures if f is not None and not f.done()]
            if len(self._pending_futures) <= POLL_MAX_PENDING:
                break
            logger.warning(f'[线程池] 待处理消息过多({len(self._pending_futures)})，等待...')
            time.sleep(0.5)

    def _get_msg_dedup_key(self, msg):
        """获取消息去重键，优先使用 WeChat msg_id"""
        msg_id = msg.get('msg_id') or msg.get('MsgId')
        if msg_id:
            return f'wx:{msg_id}'
        db_id = msg.get('id')
        if db_id is not None:
            return f'db:{db_id}'
        return None

    def _is_processed(self, msg):
        """检查消息是否已被处理过（去重缓存命中）"""
        key = self._get_msg_dedup_key(msg)
        if key is None:
            return False
        with self._cache_lock:
            if key in self._processed_cache:
                if time.time() - self._processed_cache[key] < DEDUP_CACHE_TTL:
                    return True
                del self._processed_cache[key]
            return False

    def _mark_processed(self, msg):
        """标记消息为已处理（提交到线程池前调用，防竞态）"""
        key = self._get_msg_dedup_key(msg)
        if key is None:
            return
        with self._cache_lock:
            self._processed_cache[key] = time.time()

    def _cleanup_cache(self):
        """清理过期的去重缓存记录"""
        now = time.time()
        with self._cache_lock:
            expired = [k for k, v in self._processed_cache.items() if now - v > DEDUP_CACHE_TTL]
            for k in expired:
                del self._processed_cache[k]
            if expired:
                logger.debug(f'[去重缓存] 清理 {len(expired)} 条过期记录')

    def _poll_loop(self):
        """轮询主循环（动态间隔 + 线程池并发处理）"""
        logger.info(
            f'[轮询] 启动，动态间隔 {POLL_INTERVAL_IDLE}s(空闲)/{POLL_INTERVAL_BUSY}s(忙碌)，'
            f'线程池={POLL_WORKERS}workers，云端: {self.cloud_host}'
        )
        logger.info(f'[云端] 轮询循环已启动，间隔{POLL_INTERVAL_IDLE}s，云端: {self.cloud_host}')

        while self.running:
            try:
                messages = self.get_messages()

                # 处理消息 — 提交到线程池并发处理（先经过去重缓存检查）
                if messages and self.message_handler:
                    self._cleanup_futures()
                    skipped = 0
                    for msg in messages:
                        if self._is_processed(msg):
                            skipped += 1
                            continue
                        self._mark_processed(msg)
                        future = self._executor.submit(self._process_message_async, msg)
                        self._pending_futures.append(future)
                    if skipped:
                        logger.info(f'[去重缓存] 跳过 {skipped} 条已处理消息')
                    logger.info(f'[线程池] 提交 {len(messages) - skipped} 条消息到线程池，待处理={len(self._pending_futures)}')

                # 收集所有已完成的future的结果作为ACK
                processed_ids = []
                done_futures = [f for f in self._pending_futures if f.done()]
                for f in done_futures:
                    try:
                        result = f.result(timeout=1)
                        if result is not None:
                            processed_ids.append(result)
                    except TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f'[线程池] 取结果异常: {e}')
                self._pending_futures = [f for f in self._pending_futures if not f.done()]

                # 确认已处理的消息
                if processed_ids:
                    self._send_ack(processed_ids)
                    self.success_count += len(processed_ids)

                # 动态调整间隔
                if messages:
                    self._idle_count = 0
                    self._current_interval = POLL_INTERVAL_BUSY
                    if len(messages) > 3:
                        logger.info(f'[轮询] 消息较多({len(messages)}条)，保持快速轮询')
                else:
                    self._idle_count += 1
                    if self._idle_count >= POLL_IDLE_THRESHOLD:
                        self._current_interval = POLL_INTERVAL_IDLE

                self.last_poll_time = datetime.now()

                # 定时清理去重缓存
                now_ts = time.time()
                if now_ts - self._last_cache_cleanup > DEDUP_CACHE_CLEANUP_INTERVAL:
                    self._cleanup_cache()
                    self._last_cache_cleanup = now_ts

            except Exception as e:
                self.error_count += 1
                logger.error(f'[轮询] 异常({self.error_count}): {e}')

            time.sleep(self._current_interval)

        logger.info('[轮询] 已停止')

    def start(self):
        """启动轮询"""
        if self.running:
            logger.warning('[轮询] 已经在运行')
            return

        if not self.cloud_host:
            logger.warning('[轮询] 云端地址未配置，无法启动')
            return

        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        logger.info('[轮询] 已启动')
        logger.info(f'[云端] 轮询线程已启动，目标: {self.cloud_host}/api/poll')

    def stop(self):
        """停止轮询"""
        self.running = False
        if self.poll_thread:
            _timeout_str = os.environ.get('REQUEST_TIMEOUT_FAST', '5')
            try:
                _timeout = max(1, int(_timeout_str))
            except (ValueError, TypeError):
                _timeout = 5
                logger.warning(f'[轮询] REQUEST_TIMEOUT_FAST 环境变量无效({_timeout_str!r})，使用默认值 5 秒')
            self.poll_thread.join(timeout=_timeout)
        self._executor.shutdown(wait=False)
        self._pending_futures.clear()
        logger.info('[轮询] 已停止')

    def get_status(self):
        """获取状态"""
        self._cleanup_futures()
        return {
            'running': self.running,
            'last_poll': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'message_count': self.message_count,
            'cloud_host': self.cloud_host,
            'current_interval': self._current_interval,
            'idle_count': self._idle_count,
            'thread_pool': {
                'workers': POLL_WORKERS,
                'max_pending': POLL_MAX_PENDING,
                'current_pending': len(self._pending_futures)
            }
        }

    def set_message_hub(self, hub):
        """设置本地message_hub"""
        self._message_hub = hub

    def validate_cursor(self):
        """启动探针：用 since_id=0 请求云端，验证本地游标是否有效
        
        当云端 DB 被重置（max_rowid 远小于本地游标），自动归零游标。
        此方法独立于轮询线程，可在启动时立即调用一次做校验。
        """
        logger.info('[启动校验] 正在执行云端游标探针...')
        try:
            result = self._request(
                'GET', '/api/poll',
                params={'since_id': 0, 'limit': 1}
            )
            if result.get('code') == 0:
                max_rowid = result.get('max_rowid', 0)
                old_cursor = self._last_polled_id

                if max_rowid < old_cursor:
                    logger.warning(
                        f'[启动校验] 云端max_rowid({max_rowid}) < 本地游标({old_cursor})，'
                        f'云端DB已重置，游标归零'
                    )
                    self._last_polled_id = 0
                    self._save_cursor()
                    return {'valid': False, 'action': 'RESET', 'old_cursor': old_cursor, 'max_rowid': max_rowid}
                else:
                    logger.info(f'[启动校验] 游标有效: 本地={old_cursor}, 云端max={max_rowid}')
                    return {'valid': True, 'action': 'OK', 'cursor': old_cursor, 'max_rowid': max_rowid}
            else:
                logger.warning(f'[启动校验] 云端探针请求失败: {result.get("message")}')
                return {'valid': False, 'action': 'PROBE_FAILED', 'error': result.get('message')}
        except Exception as e:
            logger.warning(f'[启动校验] 探针异常: {e}')
            return {'valid': False, 'action': 'EXCEPTION', 'error': str(e)}


# ============== 单例全局实例 ==============
_cloud_poller = None

def _load_cloud_config():
    """从配置文件加载云端配置"""
    config_file = DB_PATHS['cloud_config']
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载云端配置失败: {e}")
    return {'cloud_host': '', 'api_key': '', 'enabled': False}

def init_cloud_poller(message_handler=None, cloud_host=None, api_key=None):
    """初始化云端轮询器（自动从配置文件读取）

    配置不全时（cloud_host为空或enabled=false），不创建实例，返回None。
    """
    global _cloud_poller

    if not cloud_host or not api_key:
        cfg = _load_cloud_config()
        cloud_host = cloud_host or cfg.get('cloud_host', '')
        api_key = api_key or cfg.get('api_key', '')
        if not cfg.get('enabled', True):
            logger.info('[云端] 云端功能未启用（cloud_config.json enabled=false），跳过初始化')
            _cloud_poller = None
            return _cloud_poller

    if not cloud_host:
        logger.info('[云端] 云端地址未配置，跳过初始化')
        _cloud_poller = None
        return _cloud_poller

    _cloud_poller = CloudPoller(
        message_handler=message_handler,
        cloud_host=cloud_host,
        api_key=api_key,
        cloud_port=CLOUD_PORT
    )
    return _cloud_poller

def get_cloud_poller():
    """获取云端轮询器实例"""
    return _cloud_poller

def start_polling():
    """启动轮询"""
    if _cloud_poller:
        _cloud_poller.start()
        return True

def validate_cursor():
    """启动探针校验：检查云端游标是否有效（独立于轮询线程的单次探针）
    
    在 init_cloud_poller_from_config() 中 start_polling() 后调用。
    """
    if _cloud_poller:
        return _cloud_poller.validate_cursor()
    logger.warning('[云端] 轮询器未初始化，跳过启动校验')
    return {'valid': False, 'action': 'NOT_INITIALIZED'}

def stop_polling():
    """停止轮询"""
    if _cloud_poller:
        _cloud_poller.stop()
        return True
    return False

def send_to_cloud(to_user='@all', content='', msg_type='text', bot_type='group', route_tag=None):
    """便捷函数：发送消息到微信（fallback：直连云端 relay 发送）"""
    if _cloud_poller:
        return _cloud_poller.send_message(content, to_user, msg_type, bot_type)
    # 轮询器未初始化时，直接 HTTP 调用云端 relay 发送
    try:
        import requests
        cfg = _load_cloud_config()
        host = cfg.get('cloud_host', '') or os.getenv('WECHAT_CLOUD_HOST', '')
        api_key = cfg.get('api_key', '') or os.getenv('WECHAT_CLOUD_API_KEY', '')
        if not host:
            return {'code': -1, 'message': '云端地址未配置'}
        resp = requests.post(f'{host}/api/send', json={
            'to_user': to_user, 'content': content,
            'msg_type': msg_type, 'bot_type': bot_type,
        }, headers={'X-API-Key': api_key}, timeout=10)
        return resp.json()
    except Exception as e:
        return {'code': -1, 'message': str(e)}

def set_message_hub(hub):
    """设置本地message_hub"""
    if _cloud_poller:
        _cloud_poller.set_message_hub(hub)


# ============== 使用示例 ==============

if __name__ == '__main__':
    from logging_setup import setup_daily_logger
    setup_daily_logger('cloud_poller')

    def handle_message(data):
        logger.debug(f'收到消息: {data}')

    poller = init_cloud_poller(
        message_handler=handle_message,
        cloud_host=os.getenv('WECHAT_CLOUD_HOST', ''),
        api_key=os.getenv('WECHAT_CLOUD_API_KEY', '')
    )

    poller.start()

    try:
        while True:
            time.sleep(10)
            status = poller.get_status()
            logger.info(f'状态: 运行={status["running"]}, 消息数={status["message_count"]}')
    except KeyboardInterrupt:
        poller.stop()
        logger.info('已停止')
