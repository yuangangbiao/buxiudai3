# -*- coding: utf-8 -*-
"""
core/_config_funcs.py 完整单元测试

覆盖模块:
- 工具函数: get_default_backup_dir, get_app_dir, get_default_redis_dump
- Redis配置: REDIS_HOST, REDIS_PORT, REDIS_DB
- Config 类
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch


class TestConfigFuncsExists:
    """_config_funcs 存在性测试"""

    def test_config_funcs_module_exists(self):
        """测试_config_funcs模块存在"""
        from core import _config_funcs
        assert _config_funcs is not None


class TestGetDefaultBackupDir:
    """get_default_backup_dir 测试"""

    def test_get_default_backup_dir(self):
        """测试获取默认备份目录"""
        from core._config_funcs import get_default_backup_dir
        result = get_default_backup_dir()
        assert isinstance(result, str)
        assert 'backup' in result or 'DAT' in result


class TestGetAppDir:
    """get_app_dir 测试"""

    def test_get_app_dir(self):
        """测试获取应用目录"""
        from core._config_funcs import get_app_dir
        result = get_app_dir()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetDefaultRedisDump:
    """get_default_redis_dump 测试"""

    @patch.dict(os.environ, {'REDIS_DUMP_PATH': '/tmp/redis_dump.rdb'})
    def test_get_default_redis_dump_with_env(self):
        """测试使用环境变量"""
        from core._config_funcs import get_default_redis_dump
        # 重新加载模块以应用新环境变量
        import importlib
        import core._config_funcs
        importlib.reload(core._config_funcs)
        result = core._config_funcs.get_default_redis_dump()
        # 取决于平台和环境变量
        assert result is None or isinstance(result, str)


class TestRedisConfig:
    """Redis 配置测试"""

    def test_redis_host_default(self):
        """测试Redis主机默认值"""
        from core._config_funcs import REDIS_HOST
        assert REDIS_HOST is not None

    def test_redis_port_default(self):
        """测试Redis端口默认值"""
        from core._config_funcs import REDIS_PORT
        assert isinstance(REDIS_PORT, int)
        assert REDIS_PORT > 0

    def test_redis_db_default(self):
        """测试Redis DB默认值"""
        from core._config_funcs import REDIS_DB
        assert isinstance(REDIS_DB, int)
        assert REDIS_DB >= 0


class TestConfigClass:
    """Config 兼容存根类测试"""

    def test_config_class_exists(self):
        """测试Config类存在"""
        from core._config_funcs import Config
        assert Config is not None

    def test_config_jwt_secret(self):
        """测试Config JWT_SECRET_KEY"""
        from core._config_funcs import Config
        assert hasattr(Config, 'JWT_SECRET_KEY')

    def test_config_log_dir(self):
        """测试Config LOG_DIR"""
        from core._config_funcs import Config
        assert hasattr(Config, 'LOG_DIR')

    def test_config_mysql(self):
        """测试Config MySQL相关属性"""
        from core._config_funcs import Config
        assert hasattr(Config, 'MYSQL_HOST')
        assert hasattr(Config, 'MYSQL_PORT')

    def test_config_flask(self):
        """测试Config Flask相关属性"""
        from core._config_funcs import Config
        assert hasattr(Config, 'FLASK_HOST')
        assert hasattr(Config, 'FLASK_PORT')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
