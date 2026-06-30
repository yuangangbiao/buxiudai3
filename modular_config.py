# -*- coding: utf-8 -*-
"""
模块化配置管理器 - 统一管理所有模块配置

功能：
    - 从 modular_config.json 读取配置
    - 从 .env 文件读取环境变量（敏感配置）
    - 提供配置读取、设置、保存接口
    - 支持配置热重载

使用方式：
    from modular_config import ModularConfig

    # 读取自动发布开关
    enabled = ModularConfig.get_auto_publish_enabled()

    # 设置自动发布开关
    ModularConfig.set_auto_publish_enabled(True)

    # 获取任意配置项
    retry_count = ModularConfig.get_config('auto_publish.retry_count', 3)
"""

import os
import json
import logging
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_FILE = os.path.join(DATA_DIR, 'modular_config.json')


class ModularConfig:
    """
    模块化配置管理器（单例模式）
    """
    _instance = None
    _config = None
    _lock = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_config()

    def _load_config(self) -> None:
        """
        加载配置文件

        优先级：.env > 环境变量 > JSON配置 > 默认值
        """
        self._config = self._read_json_config()
        self._override_from_env()
        logger.info(f"模块配置已加载: {CONFIG_FILE}")

    def _read_json_config(self) -> dict:
        """
        从 JSON 文件读取配置

        Returns:
            配置字典，读取失败返回空字典
        """
        if not os.path.exists(CONFIG_FILE):
            logger.warning(f"配置文件不存在: {CONFIG_FILE}，使用默认配置")
            return self._get_default_config()

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """
        获取默认配置

        Returns:
            默认配置字典
        """
        return {
            "auto_publish": {
                "enabled": False,
                "retry_count": 3,
                "retry_interval": 1,
                "auto_sync_after_publish": False
            },
            "material_publish": {
                "enabled": True,
                "auto_sync": False,
                "default_priority": "normal"
            },
            "container": {
                "db_path": "mobile_api_ai/wechat_container.db",
                "api_url": "",
                "sync_interval": 60,
                "task_expiry_hours": 24
            },
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 50,
                "success_threshold": 3,
                "failure_rate_threshold": 0.01,
                "open_timeout": 30.0,
                "recovery_timeout": 60.0
            },
            "queue": {
                "max_size": 1000,
                "retry_count": 3,
                "retry_delay": 5
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }

    def _override_from_env(self) -> None:
        """
        从环境变量覆盖配置

        环境变量命名规范：MODULAR_{SECTION}_{KEY}，全大写
        例如：
            MODULAR_AUTO_PUBLISH_ENABLED=true
            MODULAR_CONTAINER_DB_PATH=/path/to/db
        """
        env_prefix = 'MODULAR_'

        for section in self._config:
            section_upper = section.upper()
            for key in self._config[section]:
                env_var = f"{env_prefix}{section_upper}_{key.upper()}"
                env_value = os.getenv(env_var)

                if env_value is not None:
                    original_type = type(self._config[section][key])
                    try:
                        if original_type == bool:
                            self._config[section][key] = env_value.lower() in ('true', '1', 'yes')
                        elif original_type == int:
                            self._config[section][key] = int(env_value)
                        elif original_type == float:
                            self._config[section][key] = float(env_value)
                        else:
                            self._config[section][key] = env_value
                        logger.info(f"环境变量覆盖: {env_var} = {self._config[section][key]}")
                    except Exception as e:
                        logger.warning(f"环境变量转换失败 {env_var}: {e}")

    def _get_nested_value(self, config: dict, key_path: str, default: Any = None) -> Any:
        """
        获取嵌套配置值

        Args:
            config: 配置字典
            key_path: 键路径，使用点分隔（如 'auto_publish.enabled'）
            default: 默认值

        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_config(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key_path: 键路径，使用点分隔（如 'auto_publish.enabled'）
            default: 默认值

        Returns:
            配置值，获取失败返回默认值

        Example:
            retry_count = ModularConfig.get_config('auto_publish.retry_count', 3)
            db_path = ModularConfig.get_config('container.db_path', 'default.db')
        """
        value = self._get_nested_value(self._config, key_path, default)
        return value

    def set_config(self, key_path: str, value: Any) -> bool:
        """
        设置配置项

        Args:
            key_path: 键路径，使用点分隔
            value: 配置值

        Returns:
            设置是否成功

        Example:
            ModularConfig.set_config('auto_publish.enabled', True)
        """
        keys = key_path.split('.')
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        logger.info(f"配置已设置: {key_path} = {value}")
        return True

    def save_config(self) -> bool:
        """
        保存配置到文件

        Returns:
            保存是否成功
        """
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存: {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def reload(self) -> None:
        """
        重新加载配置

        从文件重新读取配置，丢弃内存中的修改
        """
        self._load_config()
        logger.info("配置已重新加载")

    @staticmethod
    def get_auto_publish_enabled() -> bool:
        """
        获取自动发布开关状态

        Returns:
            自动发布是否开启
        """
        config = ModularConfig()
        return config.get_config('auto_publish.enabled', False)

    @staticmethod
    def set_auto_publish_enabled(enabled: bool) -> bool:
        """
        设置自动发布开关状态

        Args:
            enabled: 开关状态

        Returns:
            设置是否成功
        """
        config = ModularConfig()
        config.set_config('auto_publish.enabled', enabled)
        return config.save_config()

    @staticmethod
    def get_material_publish_enabled() -> bool:
        """
        获取备料发布开关状态

        Returns:
            备料发布是否开启
        """
        config = ModularConfig()
        return config.get_config('material_publish.enabled', True)

    @staticmethod
    def set_material_publish_enabled(enabled: bool) -> bool:
        """
        设置备料发布开关状态

        Args:
            enabled: 开关状态

        Returns:
            设置是否成功
        """
        config = ModularConfig()
        config.set_config('material_publish.enabled', enabled)
        return config.save_config()

    @staticmethod
    def get_container_db_path() -> str:
        """
        获取容器数据库路径

        优先级：CONTAINER_DB_PATH 环境变量 > JSON配置 > 默认路径

        Returns:
            数据库文件路径（始终返回绝对路径）
        """
        env_path = os.getenv('CONTAINER_DB_PATH', '').strip()
        if env_path:
            abs_path = os.path.abspath(env_path)
            logger.info(f'[Config] 使用环境变量 CONTAINER_DB_PATH: {abs_path}')
            return abs_path

        config = ModularConfig()
        default_path = os.path.join(BASE_DIR, 'mobile_api_ai', 'wechat_container.db')
        config_path = config.get_config('container.db_path', '')
        if config_path:
            abs_path = os.path.abspath(config_path)
            return abs_path
        return default_path

    @staticmethod
    def get_circuit_breaker_config() -> dict:
        """
        获取熔断器配置

        Returns:
            熔断器配置字典
        """
        config = ModularConfig()
        return {
            'enabled': config.get_config('circuit_breaker.enabled', True),
            'failure_threshold': config.get_config('circuit_breaker.failure_threshold', 50),
            'success_threshold': config.get_config('circuit_breaker.success_threshold', 3),
            'failure_rate_threshold': config.get_config('circuit_breaker.failure_rate_threshold', 0.01),
            'open_timeout': config.get_config('circuit_breaker.open_timeout', 30.0),
            'recovery_timeout': config.get_config('circuit_breaker.recovery_timeout', 60.0),
        }

    def to_dict(self) -> dict:
        """
        获取完整配置字典

        Returns:
            配置字典
        """
        return self._config.copy()
