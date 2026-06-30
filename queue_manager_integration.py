# -*- coding: utf-8 -*-
"""
队列管理器主系统集成模块

为桌面端提供消息队列能力
支持内存队列（无Redis时）和Redis队列
基于 mobile_api_ai/modules/queue_manager.py 封装
"""

import os
import json
import time
import logging
from typing import Any, Optional, Callable, Dict
from threading import Lock
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class QueueOverflowError(Exception):
    """队列溢出异常"""
    pass


class QueueEmptyError(Exception):
    """队列为空异常"""
    pass


@dataclass
class QueueMessage:
    """队列消息"""
    data: Any
    enqueued_at: float = field(default_factory=time.time)
    retry_count: int = 0
    metadata: Dict = field(default_factory=dict)
    priority: int = 0
    message_id: str = ""


class InMemoryQueue:
    """内存队列实现（无Redis时使用）"""

    def __init__(self, max_size: int = 1000):
        self._queue = deque()
        self._max_size = max_size
        self._lock = Lock()

    def size(self) -> int:
        return len(self._queue)

    def is_full(self) -> bool:
        return len(self._queue) >= self._max_size

    def enqueue(self, message: QueueMessage) -> bool:
        with self._lock:
            if self.is_full():
                return False
            self._queue.append(message)
            return True

    def dequeue(self) -> Optional[QueueMessage]:
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def peek(self) -> Optional[QueueMessage]:
        with self._lock:
            if not self._queue:
                return None
            return self._queue[0]


class QueueStats:
    """队列统计信息"""

    def __init__(self):
        self.enqueued_total = 0
        self.dequeued_total = 0
        self.failed_total = 0
        self.overflow_rejected_total = 0
        self.last_enqueue_time: Optional[float] = None
        self.last_dequeue_time: Optional[float] = None
        self.avg_latency = 0.0
        self.max_latency = 0.0
        self._recent_latencies = deque(maxlen=100)

    def record_enqueue(self) -> None:
        self.enqueued_total += 1
        self.last_enqueue_time = time.time()

    def record_dequeue(self, latency: float = 0) -> None:
        self.dequeued_total += 1
        self.last_dequeue_time = time.time()
        if latency > 0:
            self._recent_latencies.append(latency)
            self.avg_latency = sum(self._recent_latencies) / len(self._recent_latencies)
            self.max_latency = max(self._recent_latencies)

    def record_failure(self) -> None:
        self.failed_total += 1

    def record_overflow_rejected(self) -> None:
        self.overflow_rejected_total += 1

    def to_dict(self) -> dict:
        return {
            'enqueued_total': self.enqueued_total,
            'dequeued_total': self.dequeued_total,
            'failed_total': self.failed_total,
            'overflow_rejected_total': self.overflow_rejected_total,
            'last_enqueue_time': self.last_enqueue_time,
            'last_dequeue_time': self.last_dequeue_time,
            'avg_latency_ms': round(self.avg_latency * 1000, 2) if self.avg_latency > 0 else 0,
            'max_latency_ms': round(self.max_latency * 1000, 2) if self.max_latency > 0 else 0
        }


class QueueManager:
    """
    队列管理器（支持内存队列和Redis队列）

    功能特性:
    - 队列大小上限控制
    - 队列延迟监控
    - 消息重试机制
    - 队列统计
    - 死信队列
    """

    def __init__(
        self,
        redis_host: Optional[str] = None,
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        use_redis: bool = False,
        default_max_size: int = 1000,
        max_retries: int = 3
    ):
        """
        初始化队列管理器

        Args:
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_password: Redis密码
            use_redis: 是否使用Redis，为False时使用内存队列
            default_max_size: 默认队列最大容量
            max_retries: 最大重试次数
        """
        self.use_redis = use_redis and redis_host is not None
        self.default_max_size = default_max_size
        self.max_retries = max_retries

        self._redis_client = None
        self._memory_queues: Dict[str, InMemoryQueue] = {}
        self._queue_stats: Dict[str, QueueStats] = {}
        self._lock = Lock()

        if self.use_redis:
            self._init_redis(redis_host, redis_port, redis_password)
        else:
            logger.info("QueueManager 初始化: 使用内存队列模式")

    def _init_redis(self, host: str, port: int, password: Optional[str]) -> None:
        """初始化Redis连接"""
        try:
            import redis
            self._redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True,
                socket_timeout=5
            )
            self._redis_client.ping()
            logger.info(f"QueueManager 初始化: Redis连接成功 ({host}:{port})")
        except ImportError:
            logger.warning("redis模块未安装，切换到内存队列模式")
            self.use_redis = False
        except Exception as e:
            logger.warning(f"Redis连接失败，切换到内存队列模式: {e}")
            self.use_redis = False

    def _get_queue(self, queue_name: str) -> InMemoryQueue:
        """获取或创建内存队列"""
        with self._lock:
            if queue_name not in self._memory_queues:
                self._memory_queues[queue_name] = InMemoryQueue(self.default_max_size)
            return self._memory_queues[queue_name]

    def _get_stats(self, queue_name: str) -> QueueStats:
        """获取队列统计"""
        with self._lock:
            if queue_name not in self._queue_stats:
                self._queue_stats[queue_name] = QueueStats()
            return self._queue_stats[queue_name]

    def enqueue(
        self,
        queue_name: str,
        data: Any,
        max_size: Optional[int] = None,
        priority: int = 0,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        入队

        Args:
            queue_name: 队列名称
            data: 消息数据
            max_size: 队列最大容量
            priority: 优先级（数值越大优先级越高，暂不支持）
            metadata: 元数据

        Returns:
            bool: 是否入队成功

        Raises:
            QueueOverflowError: 队列已满
        """
        max_size = max_size or self.default_max_size
        message_id = f"{queue_name}:{time.time()}:{id(data)}"

        if self.use_redis and self._redis_client:
            return self._redis_enqueue(queue_name, data, max_size, priority, metadata, message_id)
        else:
            return self._memory_enqueue(queue_name, data, max_size, priority, metadata, message_id)

    def _redis_enqueue(
        self,
        queue_name: str,
        data: Any,
        max_size: int,
        priority: int,
        metadata: Optional[Dict],
        message_id: str
    ) -> bool:
        """Redis入队"""
        current_size = self._redis_client.llen(queue_name)
        if current_size >= max_size:
            stats = self._get_stats(queue_name)
            stats.record_overflow_rejected()
            raise QueueOverflowError(f"Queue {queue_name} overflow (size={current_size})")

        message = {
            'data': data,
            'enqueued_at': time.time(),
            'retry_count': 0,
            'metadata': metadata or {},
            'priority': priority,
            'message_id': message_id
        }

        self._redis_client.rpush(queue_name, json.dumps(message, ensure_ascii=False))
        self._get_stats(queue_name).record_enqueue()

        logger.debug(f"[Redis] 消息入队: {queue_name}, size={current_size + 1}")
        return True

    def _memory_enqueue(
        self,
        queue_name: str,
        data: Any,
        max_size: int,
        priority: int,
        metadata: Optional[Dict],
        message_id: str
    ) -> bool:
        """内存队列入队"""
        queue = self._get_queue(queue_name)

        if queue.is_full():
            stats = self._get_stats(queue_name)
            stats.record_overflow_rejected()
            raise QueueOverflowError(f"Queue {queue_name} overflow (size={queue.size()})")

        message = QueueMessage(
            data=data,
            enqueued_at=time.time(),
            retry_count=0,
            metadata=metadata or {},
            priority=priority,
            message_id=message_id
        )

        queue.enqueue(message)
        self._get_stats(queue_name).record_enqueue()

        logger.debug(f"[Memory] 消息入队: {queue_name}, size={queue.size()}")
        return True

    def dequeue(self, queue_name: str, timeout: int = 5) -> Optional[Any]:
        """
        出队

        Args:
            queue_name: 队列名称
            timeout: 阻塞等待超时（秒），仅对Redis有效

        Returns:
            消息数据，队列为空时返回None
        """
        if self.use_redis and self._redis_client:
            return self._redis_dequeue(queue_name, timeout)
        else:
            return self._memory_dequeue(queue_name)

    def _redis_dequeue(self, queue_name: str, timeout: int) -> Optional[Any]:
        """Redis出队"""
        try:
            result = self._redis_client.blpop(queue_name, timeout=timeout)
            if result:
                _, message_json = result
                message = json.loads(message_json)
                latency = time.time() - message.get('enqueued_at', time.time())
                self._get_stats(queue_name).record_dequeue(latency)
                return message.get('data')
        except Exception as e:
            logger.error(f"[Redis] 出队失败: {e}")
            self._get_stats(queue_name).record_failure()

        return None

    def _memory_dequeue(self, queue_name: str) -> Optional[Any]:
        """内存队列出队"""
        queue = self._get_queue(queue_name)
        message = queue.dequeue()

        if message:
            latency = time.time() - message.enqueued_at
            self._get_stats(queue_name).record_dequeue(latency)
            return message.data

        return None

    def size(self, queue_name: str) -> int:
        """获取队列大小"""
        if self.use_redis and self._redis_client:
            return self._redis_client.llen(queue_name)
        else:
            return self._get_queue(queue_name).size()

    def is_empty(self, queue_name: str) -> bool:
        """检查队列是否为空"""
        return self.size(queue_name) == 0

    def clear(self, queue_name: str) -> int:
        """清空队列，返回清空的消息数"""
        if self.use_redis and self._redis_client:
            count = self._redis_client.llen(queue_name)
            self._redis_client.delete(queue_name)
            logger.info(f"[Redis] 队列 {queue_name} 已清空，{count}条消息")
            return count
        else:
            queue = self._get_queue(queue_name)
            count = queue.size()
            self._memory_queues[queue_name] = InMemoryQueue(self.default_max_size)
            logger.info(f"[Memory] 队列 {queue_name} 已清空，{count}条消息")
            return count

    def get_stats(self, queue_name: str) -> Optional[dict]:
        """获取队列统计"""
        if self.use_redis and self._redis_client:
            stats = self._get_stats(queue_name)
            return stats.to_dict()
        else:
            queue = self._get_queue(queue_name)
            stats = self._get_stats(queue_name)
            result = stats.to_dict()
            result['current_size'] = queue.size()
            return result

    def get_all_stats(self) -> dict:
        """获取所有队列统计"""
        if self.use_redis and self._redis_client:
            keys = self._redis_client.keys('queue:*:size')
            queue_names = set(k.replace('queue:', '').replace(':size', '') for k in keys)
        else:
            queue_names = set(self._memory_queues.keys())

        return {
            name: self.get_stats(name)
            for name in queue_names
        }

    def retry_failed(self, queue_name: str, dead_letter_queue: Optional[str] = None) -> int:
        """
        重试失败的消息

        Args:
            queue_name: 原队列名称
            dead_letter_queue: 死信队列名称

        Returns:
            重试的消息数
        """
        if dead_letter_queue:
            count = 0
            dlq_name = dead_letter_queue or f"{queue_name}_dlq"

            if self.use_redis and self._redis_client:
                while True:
                    result = self._redis_client.blpop(dlq_name, timeout=1)
                    if not result:
                        break

                    _, message_json = result
                    message = json.loads(message_json)

                    if message.get('retry_count', 0) < self.max_retries:
                        message['retry_count'] += 1
                        self._redis_client.rpush(queue_name, json.dumps(message, ensure_ascii=False))
                        count += 1
                    else:
                        logger.warning(f"消息已超过最大重试次数: {message.get('message_id')}")

            return count

        return 0


_queue_manager_instance = None


def get_queue_manager() -> QueueManager:
    """获取队列管理器单例"""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        redis_host = os.getenv('REDIS_HOST')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD')
        use_redis = redis_host is not None

        _queue_manager_instance = QueueManager(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            use_redis=use_redis,
            default_max_size=1000,
            max_retries=3
        )

    return _queue_manager_instance


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = get_queue_manager()

    print("=" * 60)
    print("队列管理器集成模块测试")
    print("=" * 60)

    test_queue = "test_queue"

    print("\n--- 入队测试 ---")
    for i in range(5):
        try:
            manager.enqueue(test_queue, {"msg": f"消息{i+1}", "index": i})
            print(f"入队成功: 消息{i+1}")
        except QueueOverflowError as e:
            print(f"入队失败: {e}")

    print(f"\n队列大小: {manager.size(test_queue)}")

    print("\n--- 出队测试 ---")
    while not manager.is_empty(test_queue):
        msg = manager.dequeue(test_queue)
        if msg:
            print(f"出队: {msg}")

    print(f"\n队列大小: {manager.size(test_queue)}")

    print("\n--- 统计信息 ---")
    print(manager.get_stats(test_queue))

    print("\n" + "=" * 60)
