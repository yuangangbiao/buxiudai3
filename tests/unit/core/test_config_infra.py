# -*- coding: utf-8 -*-
"""
core/_config_infra.py 完整单元测试

覆盖模块:
- load_env
- DatabaseConfig
- 各配置常量
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest


class TestConfigInfraExists:
    """_config_infra 存在性测试"""

    def test_config_infra_module_exists(self):
        """测试_config_infra模块存在"""
        from core import _config_infra
        assert _config_infra is not None


class TestLoadEnv:
    """load_env 测试"""

    def test_load_env_returns_bool(self):
        """测试load_env返回布尔值"""
        from core._config_infra import load_env
        result = load_env()
        assert isinstance(result, bool)


class TestPathConfig:
    """路径配置测试"""

    def test_base_dir(self):
        """测试BASE_DIR"""
        from core._config_infra import BASE_DIR
        assert BASE_DIR is not None
        assert str(BASE_DIR).endswith('不锈钢网带跟单3.0')

    def test_data_dir(self):
        """测试DATA_DIR"""
        from core._config_infra import DATA_DIR
        assert DATA_DIR is not None

    def test_config_dir(self):
        """测试CONFIG_DIR"""
        from core._config_infra import CONFIG_DIR
        assert CONFIG_DIR is not None

    def test_log_dir(self):
        """测试LOG_DIR"""
        from core._config_infra import LOG_DIR
        assert LOG_DIR is not None


class TestGetDataPath:
    """get_data_path 测试"""

    def test_get_data_path(self):
        """测试获取数据路径"""
        from core._config_infra import get_data_path
        result = get_data_path("test.txt")
        assert result.endswith("test.txt")
        assert 'data' in result

    def test_get_data_path_with_subdir(self):
        """测试子目录数据路径"""
        from core._config_infra import get_data_path
        result = get_data_path("subdir/test.txt")
        assert result.endswith("test.txt")


class TestGetConfigPath:
    """get_config_path 测试"""

    def test_get_config_path(self):
        """测试获取配置路径"""
        from core._config_infra import get_config_path
        result = get_config_path("config.yaml")
        assert result.endswith("config.yaml")


class TestEnsureDir:
    """ensure_dir 测试"""

    def test_ensure_dir(self, tmp_path):
        """测试确保目录存在"""
        from core._config_infra import ensure_dir
        new_dir = str(tmp_path / "new" / "nested" / "dir")
        ensure_dir(new_dir)
        assert os.path.exists(new_dir)


class TestDatabaseConfig:
    """DatabaseConfig 测试"""

    def test_database_config_exists(self):
        """测试DatabaseConfig类存在"""
        from core._config_infra import DatabaseConfig
        assert DatabaseConfig is not None

    def test_database_config_get(self):
        """测试DatabaseConfig.get方法"""
        from core._config_infra import DatabaseConfig
        result = DatabaseConfig.get('NONEXISTENT_KEY', 'default_value')
        assert result == 'default_value'

    def test_database_config_host(self):
        """测试HOST属性"""
        from core._config_infra import DatabaseConfig
        db = DatabaseConfig()
        assert db.HOST is not None

    def test_database_config_port(self):
        """测试PORT属性"""
        from core._config_infra import DatabaseConfig
        db = DatabaseConfig()
        assert isinstance(db.PORT, int)
        assert db.PORT > 0

    def test_database_config_user(self):
        """测试USER属性"""
        from core._config_infra import DatabaseConfig
        db = DatabaseConfig()
        assert db.USER is not None

    def test_database_config_database(self):
        """测试DATABASE属性"""
        from core._config_infra import DatabaseConfig
        db = DatabaseConfig()
        assert db.DATABASE is not None


class TestMysqlConfig:
    """MySQL配置测试"""

    def test_mysql_host(self):
        """测试MYSQL_HOST"""
        from core._config_infra import MYSQL_HOST
        assert MYSQL_HOST is not None

    def test_mysql_port(self):
        """测试MYSQL_PORT"""
        from core._config_infra import MYSQL_PORT
        assert isinstance(MYSQL_PORT, int)

    def test_mysql_user(self):
        """测试MYSQL_USER"""
        from core._config_infra import MYSQL_USER
        assert MYSQL_USER is not None

    def test_mysql_database(self):
        """测试MYSQL_DATABASE"""
        from core._config_infra import MYSQL_DATABASE
        assert MYSQL_DATABASE is not None


class TestFlaskConfig:
    """Flask配置测试"""

    def test_flask_host(self):
        """测试FLASK_HOST"""
        from core._config_infra import FLASK_HOST
        assert FLASK_HOST is not None

    def test_flask_port(self):
        """测试FLASK_PORT"""
        from core._config_infra import FLASK_PORT
        assert isinstance(FLASK_PORT, int)
        assert FLASK_PORT > 0


class TestServiceUrls:
    """服务URL配置测试"""

    def test_service_urls_dict(self):
        """测试服务URL字典"""
        from core._config_infra import SERVICE_URLS
        assert isinstance(SERVICE_URLS, dict)
        assert len(SERVICE_URLS) > 0

    def test_container_center_url(self):
        """测试容器中心URL"""
        from core._config_infra import CONTAINER_CENTER_URL
        assert CONTAINER_CENTER_URL is not None

    def test_dispatch_center_url(self):
        """测试调度中心URL"""
        from core._config_infra import DISPATCH_CENTER_URL
        assert DISPATCH_CENTER_URL is not None


class TestTimeConfig:
    """时间配置测试"""

    def test_db_connect_timeout(self):
        """测试DB_CONNECT_TIMEOUT"""
        from core._config_infra import DB_CONNECT_TIMEOUT
        assert isinstance(DB_CONNECT_TIMEOUT, int)

    def test_sqlite_timeout(self):
        """测试SQLITE_TIMEOUT"""
        from core._config_infra import SQLITE_TIMEOUT
        assert isinstance(SQLITE_TIMEOUT, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
