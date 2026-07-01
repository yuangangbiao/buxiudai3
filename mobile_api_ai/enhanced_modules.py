#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强模块集成模块 - 统一初始化和管理所有增强组件"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EnhancedModules集成:
    """增强模块集成类（单例模式）"""
    _instance = None

    def __init__(self):
        self._components: Dict[str, Any] = {}
        self._initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize_client_side(self, redis_client=None, config: Dict[str, Any] = None):
        if self._initialized:
            logger.warning("[EnhancedModules] 已初始化，跳过")
            return

        self._initialized = True
        config = config or {}

        try:
            from modules.circuit_breaker import CircuitBreaker, CircuitState
            self._components['circuit_breaker'] = CircuitBreaker(
                name='wechat_bot_client',
                failure_threshold=config.get('CB_FAILURE_THRESHOLD', 50),
                success_threshold=config.get('CB_SUCCESS_THRESHOLD', 3),
                failure_rate_threshold=config.get('CB_FAILURE_RATE_THRESHOLD', 0.5),
                half_open_max_requests=config.get('CB_HALF_OPEN_REQUESTS', 3),
                open_timeout=config.get('CB_OPEN_TIMEOUT', 30.0)
            )
            logger.info("[OK] 熔断器模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 熔断器模块初始化失败: {e}")
            self._components['circuit_breaker'] = None

        try:
            from modules.queue_manager import QueueManager, QueueOverflowError
            self._components['queue_manager'] = QueueManager(
                redis_client=redis_client,
                default_max_size=config.get('QUEUE_MAX_SIZE', 1000),
                default_timeout=config.get('QUEUE_TIMEOUT', 5)
            )
            logger.info("[OK] 队列管理器模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 队列管理器模块初始化失败: {e}")
            self._components['queue_manager'] = None

        logger.info("[OK] 增强模块客户端初始化完成")

    def initialize_server_side(self, redis_client=None, config: Dict[str, Any] = None):
        if self._initialized:
            logger.warning("[EnhancedModules] 已初始化，跳过")
            return

        self._initialized = True
        config = config or {}

        try:
            from modules.circuit_breaker import CircuitBreaker, CircuitState
            self._components['circuit_breaker'] = CircuitBreaker(
                name='wechat_bot_main',
                failure_threshold=config.get('CB_FAILURE_THRESHOLD', 50),
                success_threshold=config.get('CB_SUCCESS_THRESHOLD', 3),
                failure_rate_threshold=config.get('CB_FAILURE_RATE_THRESHOLD', 0.5),
                half_open_max_requests=config.get('CB_HALF_OPEN_REQUESTS', 3),
                open_timeout=config.get('CB_OPEN_TIMEOUT', 30.0)
            )
            logger.info("[OK] 熔断器模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 熔断器模块初始化失败: {e}")
            self._components['circuit_breaker'] = None

        try:
            from modules.queue_manager import QueueManager, QueueOverflowError
            self._components['queue_manager'] = QueueManager(
                redis_client=redis_client,
                default_max_size=config.get('QUEUE_MAX_SIZE', 1000),
                default_timeout=config.get('QUEUE_TIMEOUT', 5)
            )
            logger.info("[OK] 队列管理器模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 队列管理器模块初始化失败: {e}")
            self._components['queue_manager'] = None

        try:
            from modules.health_checker import HealthChecker, DetailedHealthChecker, HealthStatus
            self._components['health_checker'] = HealthChecker(
                redis_client=redis_client,
                es_hosts=config.get('ES_HOSTS', '').split(',') if config.get('ES_HOSTS') else None
            )
            logger.info("[OK] 健康检查模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 健康检查模块初始化失败: {e}")
            self._components['health_checker'] = None

        try:
            from modules.deployment_manager import DeploymentManager
            self._components['deployment_manager'] = DeploymentManager(
                backup_dir=config.get('BACKUP_DIR', '_backup'),
                config_dir=config.get('CONFIG_DIR', '_config'),
                deploy_dir=config.get('DEPLOY_DIR', '_deploy')
            )
            logger.info("[OK] 部署管理器模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 部署管理器模块初始化失败: {e}")
            self._components['deployment_manager'] = None

        try:
            from modules.enhanced_audit_logger import EnhancedAuditLogger
            self._components['audit_logger'] = EnhancedAuditLogger(
                es_hosts=config.get('ES_HOSTS', 'localhost:9200').split(','),
                redis_client=redis_client
            )
            logger.info("[OK] 审计日志模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 审计日志模块初始化失败: {e}")
            self._components['audit_logger'] = None

        try:
            from modules.enhanced_backup import EnhancedBackupManager
            self._components['backup_manager'] = EnhancedBackupManager(
                backup_dir=config.get('ENHANCED_BACKUP_DIR'),
                redis_password=config.get('REDIS_PASSWORD')
            )
            logger.info("[OK] 增强备份模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 增强备份模块初始化失败: {e}")
            self._components['backup_manager'] = None

        try:
            from clock_sync import global_clock_sync
            self._components['clock_sync'] = global_clock_sync
            logger.info("[OK] 时钟同步模块初始化完成")
        except Exception as e:
            logger.warning(f"[X] 时钟同步模块初始化失败: {e}")
            self._components['clock_sync'] = None

        logger.info("[OK] 增强模块服务端初始化完成")

    def get_component(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    @property
    def circuit_breaker(self):
        return self._components.get('circuit_breaker')

    @property
    def queue_manager(self):
        return self._components.get('queue_manager')

    @property
    def health_checker(self):
        return self._components.get('health_checker')

    @property
    def deployment_manager(self):
        return self._components.get('deployment_manager')

    @property
    def audit_logger(self):
        return self._components.get('audit_logger')

    @property
    def backup_manager(self):
        return self._components.get('backup_manager')
