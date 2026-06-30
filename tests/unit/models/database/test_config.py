# -*- coding: utf-8 -*-
"""测试 models/database/config.py"""
import os
import sys
import importlib
import subprocess
import pytest


class TestGetDbConfig:
    """测试 _get_db_config()"""

    def test_reads_from_env(self):
        """_get_db_config() 从 os.environ 读取值"""
        from models.database.config import _get_db_config
        config = _get_db_config()
        assert config["host"] == os.getenv("MYSQL_HOST", "localhost")
        assert config["port"] == int(os.getenv("MYSQL_PORT", 3306))
        assert config["user"] == os.getenv("MYSQL_USER", "root")
        assert config["password"] == os.getenv("MYSQL_PASSWORD", "")
        assert config["database"] == os.getenv("MYSQL_DATABASE", "steel_belt")
        assert config["charset"] == "utf8mb4"

    def test_env_override(self, monkeypatch):
        """手动设置环境变量后，_get_db_config() 返回新值"""
        monkeypatch.setenv("MYSQL_HOST", "192.168.1.100")
        monkeypatch.setenv("MYSQL_PORT", "4000")
        monkeypatch.setenv("MYSQL_USER", "admin")
        monkeypatch.setenv("MYSQL_PASSWORD", "secret123")
        monkeypatch.setenv("MYSQL_DATABASE", "test_db")
        from models.database.config import _get_db_config
        config = _get_db_config()
        assert config == {
            "host": "192.168.1.100",
            "port": 4000,
            "user": "admin",
            "password": "secret123",
            "database": "test_db",
            "charset": "utf8mb4",
        }


class TestMYSQL_CONFIG:
    """测试模块级 MYSQL_CONFIG 变量"""

    def _run_script(self, script_lines):
        """将多行脚本写入临时文件并执行，避免 -c 模式下 if/for 等语句语法问题"""
        import tempfile
        import textwrap
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        script = textwrap.dedent("\n".join(script_lines))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(script)
            tmppath = f.name
        try:
            env = os.environ.copy()
            for k in list(env.keys()):
                if k.startswith("MYSQL_"):
                    del env[k]
            env["PYTHONPATH"] = here + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, tmppath],
                capture_output=True, text=True, timeout=10,
                env=env,
            )
        finally:
            try:
                os.unlink(tmppath)
            except OSError:
                pass
        return result.returncode, result.stdout, result.stderr

    def test_fallback_when_db_config_missing(self):
        """db_config 不可用时，MYSQL_CONFIG 由 _get_db_config() 构建"""
        # 验证 fallback 路径：db_config 模块不存在，走 except 分支
        ret, out, err = self._run_script([
            "import sys",
            "if 'db_config' in sys.modules:",
            "    del sys.modules['db_config']",
            "if 'models.database.config' in sys.modules:",
            "    del sys.modules['models.database.config']",
            "if 'db_config' in sys.modules: sys.modules.pop('db_config', None)",
            "for k in list(sys.modules.keys()):",
            "    if k.startswith('models.database'): del sys.modules[k]",
            "from models.database.config import MYSQL_CONFIG",
            "print(type(MYSQL_CONFIG).__name__)",
            "print(MYSQL_CONFIG.get('host', 'N/A'))",
            "print('host' in MYSQL_CONFIG and 'port' in MYSQL_CONFIG)",
        ])
        assert ret == 0, f"stderr: {err}"
        lines = out.strip().splitlines()
        assert lines[0] == "dict"
        assert lines[2] == "True", f"输出: {out}"

    def test_import_from_db_config(self):
        """db_config 可导入时，MYSQL_CONFIG 使用导入的值"""
        # 验证 try 分支：预置 db_config 模拟模块
        ret, out, err = self._run_script([
            "import sys",
            "mock = type('_', (), {'MYSQL_CONFIG': {'from_db_config': True}})()",
            "sys.modules['db_config'] = mock",
            "for k in list(sys.modules.keys()):",
            "    if k.startswith('models.database'): del sys.modules[k]",
            "from models.database.config import MYSQL_CONFIG",
            "print(MYSQL_CONFIG.get('from_db_config'))",
            "print(MYSQL_CONFIG is mock.MYSQL_CONFIG)",
        ])
        assert ret == 0, f"stderr: {err}"
        lines = out.strip().splitlines()
        assert lines[0] == "True"
        assert lines[1] == "True"
