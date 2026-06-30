# -*- coding: utf-8 -*-
"""
modular_config.py 单元测试
"""

import json
import os
import tempfile

import pytest


class TestModularConfig:

    def test_config_singleton(self):
        """验证单例模式"""
        from modular_config import ModularConfig

        config1 = ModularConfig()
        config2 = ModularConfig()
        assert config1 is config2

    def test_get_config(self):
        """验证配置读取"""
        from modular_config import ModularConfig

        config = ModularConfig()
        enabled = config.get_config('auto_publish.enabled', False)
        assert isinstance(enabled, bool)

        retry_count = config.get_config('auto_publish.retry_count', 3)
        assert isinstance(retry_count, int)

    def test_get_config_nested(self):
        """验证嵌套配置读取"""
        from modular_config import ModularConfig

        config = ModularConfig()
        threshold = config.get_config('circuit_breaker.failure_threshold', 50)
        assert isinstance(threshold, int)

    def test_get_config_default(self):
        """验证默认值"""
        from modular_config import ModularConfig

        config = ModularConfig()
        value = config.get_config('nonexistent.key', 'default_value')
        assert value == 'default_value'

        int_value = config.get_config('nonexistent.key', 100)
        assert int_value == 100

    def test_get_auto_publish_enabled(self):
        """验证自动发布开关读取"""
        from modular_config import ModularConfig

        enabled = ModularConfig.get_auto_publish_enabled()
        assert isinstance(enabled, bool)

    def test_get_material_publish_enabled(self):
        """验证备料发布开关读取"""
        from modular_config import ModularConfig

        enabled = ModularConfig.get_material_publish_enabled()
        assert isinstance(enabled, bool)

    def test_get_container_db_path(self):
        """验证容器数据库路径读取"""
        from modular_config import ModularConfig

        path = ModularConfig.get_container_db_path()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_get_circuit_breaker_config(self):
        """验证熔断器配置读取"""
        from modular_config import ModularConfig

        cb_config = ModularConfig.get_circuit_breaker_config()
        assert isinstance(cb_config, dict)
        assert 'enabled' in cb_config
        assert 'failure_threshold' in cb_config
        assert 'open_timeout' in cb_config

    def test_set_and_save_config(self):
        """验证配置设置和保存"""
        from modular_config import ModularConfig

        config = ModularConfig()
        original = config.get_config('auto_publish.enabled', False)

        config.set_config('auto_publish.enabled', not original)
        config.save_config()

        config.reload()
        new_value = config.get_config('auto_publish.enabled', False)
        assert new_value == (not original)

        config.set_config('auto_publish.enabled', original)
        config.save_config()

    def test_to_dict(self):
        """验证配置转字典"""
        from modular_config import ModularConfig

        config = ModularConfig()
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'auto_publish' in config_dict
        assert 'material_publish' in config_dict
        assert 'container' in config_dict


class TestModularConfigWithTempFile:

    def test_load_from_temp_config(self):
        """验证从临时配置文件加载"""
        temp_config = {
            "test_section": {
                "test_key": "test_value",
                "test_int": 42,
                "test_bool": True
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(temp_config, f)
            temp_path = f.name

        try:
            temp_dir = os.path.dirname(temp_path)
            temp_data_dir = os.path.join(temp_dir, 'data')
            os.makedirs(temp_data_dir, exist_ok=True)

            temp_config_file = os.path.join(temp_data_dir, 'modular_config.json')
            with open(temp_config_file, 'w', encoding='utf-8') as f:
                json.dump(temp_config, f)

            original_dir = os.environ.get('MODULAR_TEST_DIR', temp_dir)
            os.environ['MODULAR_TEST_DIR'] = temp_dir

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
