# -*- coding: utf-8 -*-
"""
容器中心 API 客户端

为外部模块提供统一的容器中心 HTTP API 调用入口
集成 7 个保护模块的能力:
  - circuit_breaker: API调用熔断保护
  - api_signature: 请求签名认证
  - queue_manager: 服务不可用时的消息缓冲
  - clock_sync: 请求时间戳同步
  - data_integrity: 数据完整性校验
  - health_checker: 容器中心健康探测
  - deployment_manager: 配置版本管理
"""

import os
import json
import time
import logging
from core.config import REQUEST_TIMEOUT_NORMAL, SOCKET_CONNECT_TIMEOUT, QUEUE_POLL_TIMEOUT
import threading
from typing import Optional, Dict, Any, List, Callable
from urllib.parse import urljoin
from functools import wraps
from datetime import datetime

import requests

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
    class CircuitState:
        CLOSED = 'closed'
        OPEN = 'open'
        HALF_OPEN = 'half_open'
try:
    from modules.api_signature import EnhancedAPISignature
except ImportError:
    class EnhancedAPISignature:
        def __init__(self, **kwargs): pass
        def sign_request(self, req): return req
try:
    from modules.health_checker import DetailedHealthChecker as HealthChecker, HealthStatus
except ImportError:
    class HealthChecker:
        def __init__(self, **kwargs): pass
        def check(self, *a, **kw): return True
    class HealthStatus:
        HEALTHY = 'healthy'
        UNHEALTHY = 'unhealthy'
try:
    from modules.deployment_manager import DeploymentManager
except ImportError:
    class DeploymentManager:
        def __init__(self, **kwargs): pass
        def deploy(self, *a, **kw): return True
from clock_sync import ClockSync, clock_sync as global_clock_sync
from data_integrity import DataIntegrity
# Config 已迁移至 core.config

logger = logging.getLogger(__name__)

# QueueManager 可能不可用（需要Redis），定义内存降级
try:
    from modules.queue_manager import QueueManager, QueueOverflowError
    _queue_available = True
except Exception as e:
    logger.warning(f"队列管理器导入失败（将使用内存降级模式）: {e}")
    _queue_available = False
    QueueOverflowError = Exception


class ContainerCenterAPIError(Exception):
    """容器中心API调用异常"""
    pass


class ContainerCenterAuthError(ContainerCenterAPIError):
    """容器中心认证异常"""
    pass


class ContainerCenterUnavailableError(ContainerCenterAPIError):
    """容器中心不可用异常"""
    pass


class QueuedContainerRequest:
    """缓冲的容器中心请求"""

    def __init__(self, method: str, path: str, json_data: Optional[Dict] = None):
        self.method = method
        self.path = path
        self.json_data = json_data
        self.created_at = time.time()
        self.retry_count = 0

    def to_dict(self) -> Dict:
        return {
            'method': self.method,
            'path': self.path,
            'json_data': self.json_data,
            'created_at': self.created_at,
            'retry_count': self.retry_count
        }


class ContainerCenterClient:
    """
    容器中心 API 客户端

    统一管理所有对容器中心API的HTTP调用，
    自动集成熔断保护、签名认证、消息缓冲、时间同步、完整性校验等能力。

    使用方式:
        client = ContainerCenterClient(base_url='http://localhost:5002')
        result = client.publish_task(
            task_type='report',
            title='报工：编织',
            content={'order_no': 'WO001', ...},
            operator_id='OP001'
        )
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_secret_key: Optional[str] = None,
        redis_host: Optional[str] = None,
        redis_port: int = 6379,
        request_timeout: Optional[int] = None,
        max_retries: int = 3,
        queue_max_size: int = 500
    ):
        self.base_url = (base_url or os.getenv('CONTAINER_CENTER_API_URL', '')).rstrip('/')
        if not self.base_url:
            raise ContainerCenterAPIError(
                '容器中心API地址未配置，请设置 CONTAINER_CENTER_API_URL 环境变量'
            )

        self.request_timeout = request_timeout or REQUEST_TIMEOUT_NORMAL
        self.max_retries = max_retries
        self._token: Optional[str] = None
        self._lock = threading.Lock()
        self._queue_consumer_running = False
        self._queue_consumer_thread: Optional[threading.Thread] = None

        secret_key = api_secret_key or os.getenv('API_SECRET_KEY')
        self.api_signature = EnhancedAPISignature(secret_key=secret_key) if secret_key else None

        self.circuit_breaker = CircuitBreaker(
            name='container_center_api',
            failure_threshold=int(os.getenv('CB_CONTAINER_FAILURE_THRESHOLD', '10')),
            success_threshold=int(os.getenv('CB_CONTAINER_SUCCESS_THRESHOLD', '3')),
            failure_rate_threshold=float(os.getenv('CB_CONTAINER_FAILURE_RATE', '0.5')),
            open_timeout=float(os.getenv('CB_CONTAINER_OPEN_TIMEOUT', '30.0')),
            recovery_timeout=float(os.getenv('CB_CONTAINER_RECOVERY_TIMEOUT', '60.0'))
        )

        self._redis_client = None
        if _queue_available:
            try:
                _rh = redis_host or os.getenv('REDIS_HOST')
                _rp = redis_port
                if _rh:
                    import redis as _redis
                    self._redis_client = _redis.Redis(
                        host=_rh, port=_rp, decode_responses=True,
                        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT
                    )
                self.queue_manager = QueueManager(redis_client=self._redis_client)
            except Exception as e:
                logger.warning(f"队列管理器初始化失败，使用内存降级: {e}")
                self.queue_manager = None
        else:
            logger.warning("QueueManager模块不可用，使用内存队列降级")
            self.queue_manager = None

        self._memory_buffer: List[Dict] = []
        self._memory_buffer_lock = threading.Lock()

        self.clock_sync = global_clock_sync
        self.data_integrity = DataIntegrity()
        self.health_checker = HealthChecker() if 'HealthChecker' else None
        self.deployment_manager: Optional[DeploymentManager] = None

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ContainerCenterClient/1.0'
        })
        self._session_timeout = request_timeout

        logger.info(f"容器中心客户端初始化: {self.base_url}")

    # ──────────────────────────────────────────────
    # 认证管理
    # ──────────────────────────────────────────────

    def login(self, operator_id: str) -> bool:
        """
        登录获取JWT Token

        Args:
            operator_id: 操作员ID

        Returns:
            是否登录成功
        """
        try:
            resp = self._session.post(
                urljoin(self.base_url, '/api/auth/login'),
                json={'operator_id': operator_id},
                timeout=self.request_timeout
            )
            result = resp.json()
            if result.get('code') == 0 and result.get('data', {}).get('token'):
                self._token = result['data']['token']
                self._session.headers.update({'Authorization': f'Bearer {self._token}'})
                logger.info(f"容器中心登录成功: {operator_id}")
                return True

            logger.warning(f"容器中心登录失败: {result.get('message')}")
            return False
        except requests.RequestException as e:
            logger.error(f"容器中心登录请求失败: {e}")
            return False

    @property
    def is_authenticated(self) -> bool:
        """是否已认证"""
        return bool(self._token)

    def clear_auth(self):
        """清除认证信息"""
        self._token = None
        self._session.headers.pop('Authorization', None)

    # ──────────────────────────────────────────────
    # 核心API调用
    # ──────────────────────────────────────────────

    def _build_signed_headers(self, body: bytes = b'') -> Dict[str, str]:
        """构建签名头"""
        headers = {}
        if self.api_signature:
            try:
                sig_params = self.api_signature.generate_signature(body=body)
                headers.update(sig_params)
            except Exception as e:
                logger.warning(f"生成签名失败: {e}")
        return headers

    def _request(self, method: str, path: str, json_data: Optional[Dict] = None) -> Dict:
        """
        统一的HTTP请求（带熔断保护）

        Args:
            method: HTTP方法
            path: API路径
            json_data: 请求体

        Returns:
            API响应字典

        Raises:
            ContainerCenterUnavailableError: 熔断开启或服务不可用
            ContainerCenterAPIError: API调用失败
        """
        if self.circuit_breaker.state == CircuitState.OPEN:
            logger.warning(f"容器中心熔断开启({self.circuit_breaker.name})，请求被拒绝: {method} {path}")
            raise ContainerCenterUnavailableError(f"容器中心熔断开启")

        url = urljoin(self.base_url, path)
        body_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8') if json_data else b''

        try:
            signed_headers = self._build_signed_headers(body_bytes)

            resp = self._session.request(
                method=method,
                url=url,
                json=json_data,
                headers=signed_headers,
                timeout=self.request_timeout
            )
            resp.raise_for_status()
            result = resp.json()

            self.circuit_breaker.record_success()
            return result

        except requests.Timeout as e:
            self.circuit_breaker.record_failure()
            raise ContainerCenterUnavailableError(f"容器中心请求超时: {path}") from e
        except requests.ConnectionError as e:
            self.circuit_breaker.record_failure()
            raise ContainerCenterUnavailableError(f"容器中心连接失败: {path}") from e
        except requests.HTTPError as e:
            self.circuit_breaker.record_failure()
            status = e.response.status_code if e.response is not None else 0
            if status == 401:
                raise ContainerCenterAuthError(f"容器中心认证失败: {path}") from e
            raise ContainerCenterAPIError(f"容器中心请求失败 [{status}]: {path}") from e
        except requests.RequestException as e:
            self.circuit_breaker.record_failure()
            raise ContainerCenterUnavailableError(f"容器中心请求异常: {path}") from e

    def _request_with_retry(self, method: str, path: str, json_data: Optional[Dict] = None) -> Dict:
        """
        带重试的统一HTTP请求

        首次失败后，会将请求放入队列缓冲
        """
        for attempt in range(self.max_retries):
            try:
                return self._request(method, path, json_data)
            except ContainerCenterUnavailableError:
                if attempt < self.max_retries - 1:
                    wait = (attempt + 1) * 2
                    logger.info(f"容器中心不可用，{wait}秒后重试({attempt + 1}/{self.max_retries}): {path}")
                    time.sleep(wait)
                else:
                    logger.warning(f"容器中心不可用，请求已缓冲: {method} {path}")
                    self._buffer_request(method, path, json_data)
                    raise
            except (ContainerCenterAuthError, ContainerCenterAPIError):
                raise

    def _buffer_request(self, method: str, path: str, json_data: Optional[Dict] = None):
        """将请求缓冲到队列或内存"""
        queued = QueuedContainerRequest(method, path, json_data)
        queued_dict = queued.to_dict()

        if self.queue_manager is not None:
            try:
                self.queue_manager.enqueue(
                    queue_name='container_center_api',
                    data=queued_dict,
                    priority=1
                )
                logger.info(f"请求已缓冲(队列): {method} {path}")
                return
            except QueueOverflowError:
                logger.warning(f"队列已满，切换到内存缓冲: {method} {path}")
            except Exception as e:
                logger.warning(f"队列缓冲失败，切换到内存缓冲: {e}")

        with self._memory_buffer_lock:
            self._memory_buffer.append(queued_dict)
            if len(self._memory_buffer) > 1000:
                self._memory_buffer.pop(0)
            logger.info(f"请求已缓冲(内存): {method} {path} (缓冲大小: {len(self._memory_buffer)})")

    # ──────────────────────────────────────────────
    # 业务API方法
    # ──────────────────────────────────────────────

    def health_check(self) -> Dict:
        """
        检查容器中心健康状态

        Returns:
            健康检查结果
        """
        try:
            result = self._request('GET', '/health')
            return {
                'available': result.get('code') == 0,
                'service': result.get('data', {}).get('service'),
                'version': result.get('data', {}).get('version')
            }
        except ContainerCenterUnavailableError:
            return {'available': False, 'service': 'unknown', 'version': 'unknown'}

    def get_pool_status(self) -> Dict:
        """
        获取容器池状态

        Returns:
            容器池状态
        """
        result = self._request('GET', '/api/pool/status')
        return result.get('data', {})

    def publish_task(
        self,
        task_type: str = 'report',
        title: str = '任务',
        content: Optional[Dict] = None,
        operator_id: Optional[str] = None,
        priority: str = 'normal',
        related_order: Optional[str] = None,
        related_process: Optional[str] = None
    ) -> Dict:
        """
        发布任务到容器中心

        Args:
            task_type: 任务类型(report/quality/material/approval/repair)
            title: 任务标题
            content: 任务内容
            operator_id: 目标操作员
            priority: 优先级
            related_order: 关联订单号
            related_process: 关联工序

        Returns:
            发布结果
        """
        synced_ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        if hasattr(self.clock_sync, 'get_synced_datetime'):
            try:
                synced_ts = self.clock_sync.get_synced_datetime().strftime('%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                logger.warning(f"获取同步时间失败: {e}")

        payload = {
            'task_type': task_type,
            'title': title,
            'content': content or {},
            'operator_id': operator_id,
            'priority': priority,
            'related_order': related_order,
            'related_process': related_process,
            'timestamp': synced_ts
        }

        checksum = self.data_integrity.calculate_hash(payload)
        payload['_checksum'] = checksum

        result = self._request_with_retry('POST', '/api/internal/publish', payload)
        return result

    def get_tasks(
        self,
        status_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取任务列表

        Args:
            status_filter: 按状态过滤
            limit: 返回数量限制

        Returns:
            任务列表
        """
        if not self.is_authenticated:
            raise ContainerCenterAuthError("未登录，请先调用 login()")

        params = {'limit': limit}
        if status_filter:
            params['status'] = status_filter

        path = f"/api/tasks?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        result = self._request('GET', path)
        return result.get('data', {}).get('tasks', [])

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务详情
        """
        if not self.is_authenticated:
            raise ContainerCenterAuthError("未登录，请先调用 login()")

        result = self._request('GET', f'/api/tasks/{task_id}')
        return result.get('data') if result.get('code') == 0 else None

    def acknowledge_task(self, task_id: str) -> Dict:
        """
        确认任务接收

        Args:
            task_id: 任务ID

        Returns:
            确认结果
        """
        if not self.is_authenticated:
            raise ContainerCenterAuthError("未登录，请先调用 login()")

        return self._request_with_retry('POST', f'/api/tasks/{task_id}/acknowledge')

    def complete_task(self, task_id: str, return_data: Dict) -> Dict:
        """
        完成任务

        Args:
            task_id: 任务ID
            return_data: 回传数据

        Returns:
            完成结果
        """
        if not self.is_authenticated:
            raise ContainerCenterAuthError("未登录，请先调用 login()")

        checksum = self.data_integrity.calculate_hash(return_data)
        payload = {'return_data': return_data, '_checksum': checksum}

        return self._request_with_retry('POST', f'/api/tasks/{task_id}/complete', payload)

    def get_unacknowledged_tasks(self) -> List[Dict]:
        """
        获取未确认的任务

        Returns:
            未确认任务列表
        """
        if not self.is_authenticated:
            raise ContainerCenterAuthError("未登录，请先调用 login()")

        result = self._request('GET', '/api/tasks/unacknowledged')
        return result.get('data', {}).get('tasks', [])

    # ──────────────────────────────────────────────
    # 队列消费者（重试缓冲的请求）
    # ──────────────────────────────────────────────

    def start_queue_consumer(self, interval: float = 10.0):
        """
        启动队列消费者线程，自动重试缓冲的请求

        Args:
            interval: 重试间隔（秒）
        """
        if self._queue_consumer_running:
            logger.warning("队列消费者已在运行")
            return

        self._queue_consumer_running = True
        self._queue_consumer_thread = threading.Thread(
            target=self._queue_consumer_loop,
            args=(interval,),
            daemon=True,
            name='container-client-consumer'
        )
        self._queue_consumer_thread.start()
        logger.info(f"队列消费者已启动(间隔{interval}秒)")

    def stop_queue_consumer(self):
        """停止队列消费者"""
        self._queue_consumer_running = False
        logger.info("队列消费者已停止")

    def _queue_consumer_loop(self, interval: float):
        """队列消费者主循环（支持Redis队列和内存缓冲两种模式）"""
        while self._queue_consumer_running:
            try:
                request_data = None

                if self.queue_manager is not None:
                    try:
                        message = self.queue_manager.dequeue('container_center_api', timeout=int(os.environ.get('QUEUE_POLL_TIMEOUT', '1')))
                        if message:
                            raw = message.get('data') if isinstance(message, dict) else message
                            if isinstance(raw, str):
                                request_data = json.loads(raw)
                            else:
                                request_data = raw
                    except Exception as e:
                        logger.warning(f"解析队列消息失败: {e}")

                if request_data is None:
                    with self._memory_buffer_lock:
                        if self._memory_buffer:
                            request_data = self._memory_buffer.pop(0)

                if request_data is None:
                    time.sleep(interval)
                    continue

                method = request_data.get('method', 'POST')
                path = request_data.get('path', '/')
                json_data = request_data.get('json_data')

                try:
                    self._request(method, path, json_data)
                    logger.info(f"缓冲请求重试成功: {method} {path}")
                except ContainerCenterUnavailableError:
                    retry_count = request_data.get('retry_count', 0) + 1
                    if retry_count < 5:
                        request_data['retry_count'] = retry_count
                        self._buffer_request(method, path, json_data)
                        logger.info(f"缓冲请求重试失败({retry_count}/5)，重新缓冲: {method} {path}")
                    else:
                        logger.error(f"缓冲请求超过最大重试次数，丢弃: {method} {path}")
                except Exception as e:
                    logger.error(f"缓冲请求重试异常: {e}")

            except Exception as e:
                logger.error(f"队列消费者异常: {e}")
                time.sleep(interval)

    # ──────────────────────────────────────────────
    # 熔断器管理
    # ──────────────────────────────────────────────

    @property
    def is_circuit_open(self) -> bool:
        """熔断器是否开启"""
        return self.circuit_breaker.state == CircuitState.OPEN

    def reset_circuit_breaker(self):
        """重置熔断器"""
        self.circuit_breaker.reset()
        logger.info("容器中心熔断器已重置")

    def get_circuit_breaker_status(self) -> Dict:
        """获取熔断器状态"""
        return {
            'state': self.circuit_breaker.state.value,
            'metrics': self.circuit_breaker.get_metrics().__dict__
        }

    # ──────────────────────────────────────────────
    # 部署/配置管理
    # ──────────────────────────────────────────────

    def deploy_config(self, config_name: str, config_data: Dict) -> bool:
        """
        部署配置到容器中心

        Args:
            config_name: 配置名称
            config_data: 配置数据

        Returns:
            是否部署成功
        """
        try:
            result = self._request('POST', '/api/internal/config/deploy', {
                'config_name': config_name,
                'config_data': config_data,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
            })
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"配置部署失败: {e}")
            return False

    def get_config_versions(self, config_name: str) -> List[Dict]:
        """
        获取配置版本列表

        Args:
            config_name: 配置名称

        Returns:
            版本列表
        """
        try:
            result = self._request('GET', f'/api/internal/config/versions/{config_name}')
            return result.get('data', {}).get('versions', [])
        except ContainerCenterAPIError:
            return []

    def rollback_config(self, config_name: str, version: str) -> bool:
        """
        回滚配置

        Args:
            config_name: 配置名称
            version: 目标版本

        Returns:
            是否回滚成功
        """
        try:
            result = self._request('POST', '/api/internal/config/rollback', {
                'config_name': config_name,
                'version': version
            })
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"配置回滚失败: {e}")
            return False

    # ──────────────────────────────────────────────
    # 外协管理
    # ──────────────────────────────────────────────

    def publish_outsource_task(
        self,
        order_no: str,
        process_name: str,
        planned_qty: int,
        process_seq: int = 1,
        outsource_remark: str = '',
        operator_id: str = ''
    ) -> Optional[Dict]:
        """
        发布外协任务到容器中心

        Args:
            order_no: 订单号
            process_name: 工序名称
            planned_qty: 计划数量
            process_seq: 工序序号
            outsource_remark: 外协备注
            operator_id: 操作员ID

        Returns:
            发布结果 {'id': task_id, 'message': ...} 或 None
        """
        try:
            payload = {
                'order_no': order_no,
                'process_name': process_name,
                'planned_qty': planned_qty,
                'process_seq': process_seq,
                'outsource_remark': outsource_remark,
                'operator_id': operator_id,
            }
            if self.data_integrity:
                payload['_checksum'] = self.data_integrity.calculate_hash(payload)
            result = self._request('POST', '/api/internal/outsource/publish', payload)
            if result.get('code') == 0:
                return result.get('data', {})
            logger.warning(f"外协任务发布失败: {result.get('message')}")
            return None
        except ContainerCenterAPIError as e:
            logger.error(f"外协任务发布异常: {e}")
            return None

    def get_outsource_records(self, status: str = None) -> List[Dict]:
        """
        获取外协记录列表

        Args:
            status: 状态过滤（pending/processing/completed/received）

        Returns:
            外协记录列表
        """
        try:
            params = {}
            if status:
                params['status'] = status
            result = self._request('GET', '/api/outsource/records', params=params)
            return result.get('data', [])
        except ContainerCenterAPIError:
            return []

    def get_outsource_record(self, record_id: str) -> Optional[Dict]:
        """
        获取单条外协记录

        Args:
            record_id: 记录ID

        Returns:
            外协记录或 None
        """
        try:
            result = self._request('GET', f'/api/outsource/records/{record_id}')
            if result.get('code') == 0:
                return result.get('data')
            return None
        except ContainerCenterAPIError:
            return None

    def feedback_outsource(self, record_id: str, promised_days: int) -> bool:
        """
        外协反馈承诺天数

        Args:
            record_id: 记录ID
            promised_days: 承诺完成天数

        Returns:
            是否成功
        """
        try:
            result = self._request('POST', f'/api/outsource/records/{record_id}/feedback', {
                'promised_days': promised_days
            })
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"外协反馈失败: {e}")
            return False

    def complete_outsource(self, record_id: str) -> bool:
        """
        完成外协任务

        Args:
            record_id: 记录ID

        Returns:
            是否成功
        """
        try:
            result = self._request('POST', f'/api/outsource/records/{record_id}/complete')
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"外协完成失败: {e}")
            return False

    def receive_outsource(self, record_id: str) -> bool:
        """
        外协收货确认

        Args:
            record_id: 记录ID

        Returns:
            是否成功
        """
        try:
            result = self._request('POST', f'/api/outsource/records/{record_id}/receive')
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"外协收货失败: {e}")
            return False

    def get_outsource_config(self) -> Dict:
        """
        获取外协配置

        Returns:
            外协配置字典
        """
        try:
            result = self._request('GET', '/api/outsource/config')
            return result.get('data', {})
        except ContainerCenterAPIError:
            return {}

    def update_outsource_config(self, **kwargs) -> bool:
        """
        更新外协配置

        Args:
            **kwargs: 配置项（enabled, default_operator_id, remind_days, overdue_remind_times）

        Returns:
            是否成功
        """
        try:
            result = self._request('POST', '/api/outsource/config', kwargs)
            return result.get('code') == 0
        except ContainerCenterAPIError as e:
            logger.error(f"外协配置更新失败: {e}")
            return False

    def report_dead_letter(self, msg_id: str, user_id: str, content: str, error: str) -> Dict:
        """
        上报死信消息到容器中心，请求人工介入处理

        Args:
            msg_id: 消息ID
            user_id: 目标用户ID
            content: 消息内容
            error: 错误信息

        Returns:
            上报结果
        """
        try:
            payload = {
                'task_type': 'dead_letter',
                'title': f'【死信告警】微信消息发送失败',
                'content': {
                    'msg_id': msg_id,
                    'user_id': user_id,
                    'content': content,
                    'error': error,
                    'dead_letter_at': datetime.now().isoformat()
                },
                'operator_id': user_id,
                'priority': 'high'
            }
            return self._request_with_retry('POST', '/api/tasks', payload)
        except ContainerCenterAPIError as e:
            logger.error(f"死信上报失败: {e}")
            return {'code': 500, 'message': str(e)}

    def close(self):
        """关闭客户端，释放连接池资源"""
        if hasattr(self, '_session') and self._session:
            try:
                self._session.close()
            except Exception as e:
                logger.warning(f"关闭HTTP会话失败: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局单例
_client_instance: Optional[ContainerCenterClient] = None
_client_lock = threading.Lock()


def get_container_center_client(
    base_url: Optional[str] = None,
    api_secret_key: Optional[str] = None
) -> ContainerCenterClient:
    """
    获取容器中心客户端（单例）

    Args:
        base_url: 容器中心API地址
        api_secret_key: API签名密钥

    Returns:
        容器中心客户端实例
    """
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                _client_instance = ContainerCenterClient(
                    base_url=base_url,
                    api_secret_key=api_secret_key
                )
    return _client_instance


# 便捷函数
def publish_task_to_container(
    task_type: str = 'report',
    title: str = '任务',
    content: Optional[Dict] = None,
    operator_id: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    便捷发布任务到容器中心

    自动使用全局客户端实例

    Args:
        task_type: 任务类型
        title: 任务标题
        content: 任务内容
        operator_id: 目标操作员
        **kwargs: 其他参数

    Returns:
        发布结果
    """
    client = get_container_center_client()
    return client.publish_task(
        task_type=task_type,
        title=title,
        content=content,
        operator_id=operator_id,
        **kwargs
    )
