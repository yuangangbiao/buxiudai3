# -*- coding: utf-8 -*-
"""核心配置模块单元测试"""
import os
import pytest


class TestDatabaseConfig:
    def test_host_default(self, monkeypatch):
        monkeypatch.delenv("MYSQL_HOST", raising=False)
        from core.config import DatabaseConfig
        cfg = DatabaseConfig()
        assert cfg.HOST == "localhost"

    def test_port_default(self, monkeypatch):
        monkeypatch.delenv("MYSQL_PORT", raising=False)
        from core.config import DatabaseConfig
        cfg = DatabaseConfig()
        assert cfg.PORT == 3306

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "192.168.1.1")
        monkeypatch.setenv("MYSQL_PORT", "3307")
        from core.config import DatabaseConfig
        cfg = DatabaseConfig()
        assert cfg.HOST == "192.168.1.1"
        assert cfg.PORT == 3307


class TestConfigLoading:
    def test_env_file_loads(self):
        from core.config import load_env
        result = load_env()
        assert isinstance(result, bool)

    def test_ensure_dir_creates(self, tmp_path):
        from core.config import ensure_dir
        new_dir = str(tmp_path / "test_config_dir")
        ensure_dir(new_dir)
        assert os.path.isdir(new_dir)
