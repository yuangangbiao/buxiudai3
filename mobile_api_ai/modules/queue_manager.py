#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""队列管理模块 - 含上限控制、延迟监控、死信队列"""

import os
import json
import time
import logging
from typing import Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock
from collections import deque
import redis

logger = logging.getLogger(__name__)


class QueueOverflowError(Exception):
    """队列溢出异常"""
    pass


class QueueEmptyError(Exception):
    """队列为空异常"""
    pass


class QueueLatencyWarning(Exception):
    """队列延迟告警异常"""
    pass


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
        self.recent_latencies = deque(maxlen=int(os.getenv('QUEUE_LATENCY_MAXLEN', '100')))

    def record_enqueue(self):
        """记录入队"""
        self.enqueued_total += 1
        self.last_enqueue_time = time.time()

    def record_dequeue(self, latency: float = 0):
        """记录出队"""
        self.dequeued_total += 1
        self.last_dequeue_time = time.time()
        if latency > 0:
            self.recent_latencies.append(latency)
            self.avg_latency = sum(self.recent_latencies) / len(self.recent_latencies)
            self.max_latency = max(self.recent_latencies)

    def record_failure(self):
        """记录失败"""
        self.failed_total += 1

    def record_overflow_rejected(self):
        """记录溢出拒绝"""
        self.overflow_rejected_total += 1

    def to_dict(self) -> dict:
        """转换为字典"""
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
    队列管理器（含上限控制、延迟监控、死信队列）

    功能特性:
    - 队列大小上限控制
    - 队列延迟监控
    - 死信队列（处理失败的消息）
    - 消息重试机制
    - 队列统计
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_max_size: int = 1000,
        default_timeout: int = 5,
        latency_warning_threshold: float = 60.0,
        max_retries: int = 3,
        dead_letter_suffix: str = '_dlq',
        stats_enabled: bool = True
    ):
        """
        初始化队列管理器

        Args:
            redis_client: Redis客户端
            default_max_size: 默认队列最大容量
            default_timeout: 默认阻塞等待超时（秒）
            latency_warning_threshold: 延迟告警阈值（秒）
            max_retries: 最大重试次数
            dead_letter_suffix: 死信队列后缀
            stats_enabled: 是否启用统计
        """
        self.redis_client = redis_client
        self.default_max_size = default_max_size
        self.default_timeout = default_timeout
        self.latency_warning_threshold = latency_warning_threshold
        self.max_retries = max_retries
        self.dead_letter_suffix = dead_letter_suffix
        self.stats_enabled = stats_enabled

        self._queue_stats = {}
        self._lock = Lock()
        self._retry_counts = {}

        logger.info(
            f"QueueManager initialized: max_size={default_max_size}, "
            f"latency_threshold={latency_warning_threshold}s, "
            f"max_retries={max_retries}"
        )

    def _get_stats(self, queue_name: str) -> QueueStats:
        """获取队列统计"""
        with self._lock:
            if queue_name not in self._queue_stats:
                self._queue_stats[queue_name] = QueueStats()
            return self._queue_stats[queue_name]

    def _get_queue_size(self, queue_name: str) -> int:
        """获取队列当前大小"""
        if self.redis_client:
            return self.redis_client.llen(queue_name)
        return 0

    def _check_queue_overflow(self, queue_name: str, max_size: Optional[int] = None) -> bool:
        """
        检查队列是否溢出

        Args:
            queue_name: 队列名称
            max_size: 最大容量

        Returns:
            bool: 是否溢出
        """
        if max_size is None:
            max_size = self.default_max_size

        if max_size <= 0:
            return False

        current_size = self._get_queue_size(queue_name)
        return current_size >= max_size

    def enqueue(
        self,
        queue_name: str,
        data: Any,
        max_size: Optional[int] = None,
        priority: int = 0,
        retry_count: int = 0,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        入队（支持优先级）

        Args:
            queue_name: 队列名称
            data: 消息数据
            max_size: 队列最大容量
            priority: 优先级（数值越大优先级越高）
            retry_count: 重试次数
            metadata: 元数据

        Returns:
            bool: 是否入队成功

        Raises:
            QueueOverflowError: 队列已满
        """
        if self._check_queue_overflow(queue_name, max_size):
            stats = self._get_stats(queue_name)
            stats.record_overflow_rejected()
            logger.error(f"队列 {queue_name} 已满({current_size})，拒绝入队")
            raise QueueOverflowError(f"Queue {queue_name} overflow (size={current_size})")

        message = {
            'data': data,
            'enqueued_at': time.time(),
            'retry_count': retry_count,
            'metadata': metadata or {},
            'priority': priority,
            'message_id': f"{queue_name}:{time.time()}:{id(data)}"
        }

        if priority > 0:
            self.redis_client.lpush(queue_name, json.dumps(message, ensure_ascii=False))
        else:
            self.redis_client.rpush(queue_name, json.dumps(message, ensure_ascii=False))

        stats = self._get_stats(queue_name)
        stats.record_enqueue()

        self.redis_client.set(
            f'queue:{queue_name}:size',
            self._get_queue_size(queue_name),
            ex=86400
        )
        self.redis_client.set(
            f'queue:{queue_name}:last_enqueue',
            time.time(),
            ex=86400
        )

        logger.debug(f"消息入队: {queue_name}, size={self._get_queue_size(queue_name)}")
        return True

    def dequeue(
        self,
        queue_name: str,
        timeout: Optional[int] = None,
        auto_retry: bool = True,
        on_failure: Optional[Callable] = None
    ) -> Optional[dict]:
        """
        出队（阻塞）

        Args:
            queue_name: 队列名称
            timeout: 阻塞等待超时（秒）
            auto_retry: 是否自动重试
            on_failure: 失败回调

        Returns:
            消息字典，包含 data, enqueued_at, latency 等

        Raises:
            QueueEmptyError: 队列为空且超时
        """
        if timeout is None:
            timeout = self.default_timeout

        result = self.redis_client.blpop(queue_name, timeout=timeout)

        if not result:
            raise QueueEmptyError(f"Queue {queue_name} is empty (timeout={timeout}s)")

        _, raw_message = result
        message = json.loads(raw_message)

        latency = time.time() - message.get('enqueued_at', time.time())
        stats = self._get_stats(queue_name)
        stats.record_dequeue(latency)

        if latency > self.latency_warning_threshold:
            logger.warning(
                f"队列 {queue_name} 延迟过高: {latency:.1f}秒 "
                f"(阈值={self.latency_warning_threshold}秒)"
            )

        retry_key = f"retry:{message.get('message_id', '')}"
        current_retry = self.redis_client.get(retry_key)

        if auto_retry and on_failure:
            try:
                result = on_failure(message)
                if result is False:
                    raise Exception("处理失败")
                self.redis_client.delete(retry_key)
            except Exception as e:
                retry_count = message.get('retry_count', 0) + 1

                if retry_count < self.max_retries:
                    logger.warning(
                        f"消息处理失败，准备重试: {message.get('message_id')} "
                        f"(retry={retry_count}/{self.max_retries})"
                    )
                    message['retry_count'] = retry_count
                    self.redis_client.incr(retry_key)
                    self.redis_client.expire(retry_key, 3600)
                    self.redis_client.rpush(queue_name, json.dumps(message, ensure_ascii=False))
                    return None
                else:
                    logger.error(
                        f"消息处理失败次数超限，发送到死信队列: "
                        f"{message.get('message_id')}"
                    )
                    self._send_to_dead_letter(queue_name, message)
                    self.redis_client.delete(retry_key)

        self.redis_client.set(
            f'queue:{queue_name}:last_dequeue',
            time.time(),
            ex=86400
        )

        return message

    def _send_to_dead_letter(self, original_queue: str, message: dict):
        """发送消息到死信队列"""
        dlq_name = original_queue + self.dead_letter_suffix
        message['dead_letter_at'] = time.time()
        message['original_queue'] = original_queue

        self.redis_client.lpush(dlq_name, json.dumps(message, ensure_ascii=False))

        stats = self._get_stats(original_queue)
        stats.record_failure()

        dlq_size_key = f'dlq:{original_queue}:size'
        self.redis_client.incr(dlq_size_key)

        logger.info(f"消息已发送到死信队列: {dlq_name}")

    def get_queue_info(self, queue_name: str) -> dict:
        """
        获取队列信息

        Args:
            queue_name: 队列名称

        Returns:
            队列信息字典
        """
        size = self._get_queue_size(queue_name)
        dlq_size = self._get_queue_size(queue_name + self.dead_letter_suffix)
        stats = self._get_stats(queue_name)

        last_enqueue = self.redis_client.get(f'queue:{queue_name}:last_enqueue')
        last_dequeue = self.redis_client.get(f'queue:{queue_name}:last_dequeue')

        return {
            'queue_name': queue_name,
            'size': size,
            'max_size': self.default_max_size,
            'usage_percent': round(size / self.default_max_size * 100, 2) if self.default_max_size > 0 else 0,
            'dlq_size': dlq_size,
            'is_full': size >= self.default_max_size,
            'last_enqueue_time': float(last_enqueue) if last_enqueue else None,
            'last_dequeue_time': float(last_dequeue) if last_dequeue else None,
            'stats': stats.to_dict()
        }

    def get_all_queues_info(self) -> dict:
        """获取所有队列信息"""
        return {
            'queues': {},
            'summary': {
                'total_queues': len(self._queue_stats),
                'total_enqueued': sum(s.enqueued_total for s in self._queue_stats.values()),
                'total_dequeued': sum(s.dequeued_total for s in self._queue_stats.values()),
                'total_failed': sum(s.failed_total for s in self._queue_stats.values()),
                'total_overflow_rejected': sum(s.overflow_rejected_total for s in self._queue_stats.values())
            }
        }

    def purge_queue(self, queue_name: str) -> int:
        """
        清空队列

        Args:
            queue_name: 队列名称

        Returns:
            删除的消息数量
        """
        size = self._get_queue_size(queue_name)
        self.redis_client.delete(queue_name)

        stats = self._get_stats(queue_name)
        logger.warning(f"队列 {queue_name} 已被清空，删除 {size} 条消息")

        return size

    def recover_from_dead_letter(self, dlq_name: str, target_queue: str, limit: int = 100) -> int:
        """
        从死信队列恢复消息到目标队列

        Args:
            dlq_name: 死信队列名称
            target_queue: 目标队列名称
            limit: 最大恢复数量

        Returns:
            恢复的消息数量
        """
        recovered = 0

        for _ in range(limit):
            result = self.redis_client.rpop(dlq_name)
            if not result:
                break

            message = json.loads(result)
            message['retry_count'] = 0
            message['recovered_at'] = time.time()

            self.redis_client.lpush(target_queue, json.dumps(message, ensure_ascii=False))
            recovered += 1

        logger.info(f"从死信队列 {dlq_name} 恢复到 {target_queue}，共 {recovered} 条消息")
        return recovered

    def requeue_expired_messages(self, queue_name: str, max_age_seconds: float) -> int:
        """
        重新入队超时的消息

        Args:
            queue_name: 队列名称
            max_age_seconds: 最大存活时间（秒）

        Returns:
            重新入队的消息数量
        """
        recovered = 0
        current_time = time.time()

        temp_queue = f"{queue_name}:_temp"
        self.redis_client.rename(queue_name, temp_queue)

        while True:
            result = self.redis_client.rpop(temp_queue)
            if not result:
                break

            message = json.loads(result)
            age = current_time - message.get('enqueued_at', current_time)

            if age > max_age_seconds:
                message['enqueued_at'] = current_time
                message['retry_count'] += 1
                recovered += 1
                logger.warning(
                    f"消息 {message.get('message_id')} 超过最大存活时间"
                    f"({age:.1f}秒)，重新入队"
                )

            self.redis_client.lpush(queue_name, json.dumps(message, ensure_ascii=False))

        self.redis_client.delete(temp_queue)
        return recovered


_global_queue_manager = None


def init_queue_manager(redis_client: redis.Redis, **kwargs) -> QueueManager:
    """初始化全局队列管理器"""
    global _global_queue_manager
    _global_queue_manager = QueueManager(redis_client=redis_client, **kwargs)
    return _global_queue_manager


def get_queue_manager() -> QueueManager:
    """获取全局队列管理器"""
    global _global_queue_manager
    if _global_queue_manager is None:
        raise RuntimeError("队列管理器未初始化，请先调用 init_queue_manager()")
    return _global_queue_manager
