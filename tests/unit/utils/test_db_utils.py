# -*- coding: utf-8 -*-
"""utils/db_utils.py 测试 —— 覆盖全部 70 行"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestGetMysqlPassword:
    """get_mysql_password() 测试 —— 覆盖 L15-28"""

    def test_get_password_from_env(self):
        """环境变量存在时返回密码"""
        from utils.db_utils import get_mysql_password
        saved = os.environ.get('MYSQL_PASSWORD')
        os.environ['MYSQL_PASSWORD'] = 'my_secret_pwd'
        try:
            pwd = get_mysql_password()
            assert pwd == 'my_secret_pwd'
        finally:
            if saved is not None:
                os.environ['MYSQL_PASSWORD'] = saved
            else:
                del os.environ['MYSQL_PASSWORD']

    def test_get_password_from_env_empty(self):
        """环境变量为空时抛出 ValueError"""
        from utils.db_utils import get_mysql_password
        saved = os.environ.get('MYSQL_PASSWORD')
        os.environ['MYSQL_PASSWORD'] = ''
        try:
            with pytest.raises(ValueError, match="MYSQL_PASSWORD 环境变量未设置"):
                get_mysql_password()
        finally:
            if saved is not None:
                os.environ['MYSQL_PASSWORD'] = saved
            else:
                os.environ.pop('MYSQL_PASSWORD', None)

    def test_get_password_env_not_set(self):
        """环境变量不存在时抛出 ValueError"""
        from utils.db_utils import get_mysql_password
        saved = os.environ.pop('MYSQL_PASSWORD', None)
        try:
            with pytest.raises(ValueError, match="MYSQL_PASSWORD 环境变量未设置"):
                get_mysql_password()
        finally:
            if saved is not None:
                os.environ['MYSQL_PASSWORD'] = saved


class TestGetDbConfig:
    """get_db_config() 测试 —— 覆盖 L31-45"""

    def _set_env(self, **env):
        """安全设置环境变量，返回 restore 函数"""
        saved = {}
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = str(v)
        return saved

    def _restore_env(self, saved):
        for k, orig in saved.items():
            if orig is not None:
                os.environ[k] = orig
            else:
                os.environ.pop(k, None)

    def test_get_db_config_with_env(self):
        """环境变量存在时返回完整配置"""
        from utils.db_utils import get_db_config
        saved = self._set_env(
            MYSQL_HOST='192.168.1.1',
            MYSQL_PORT='3307',
            MYSQL_USER='admin',
            MYSQL_PASSWORD='admin123',
            MYSQL_DATABASE='test_db',
        )
        try:
            config = get_db_config()
            assert config['host'] == '192.168.1.1'
            assert config['port'] == 3307
            assert config['user'] == 'admin'
            assert config['password'] == 'admin123'
            assert config['database'] == 'test_db'
            assert config['charset'] == 'utf8mb4'
        finally:
            self._restore_env(saved)

    def test_get_db_config_defaults(self):
        """环境变量不存在时使用默认值"""
        from utils.db_utils import get_db_config
        saved_pwd = os.environ.get('MYSQL_PASSWORD')
        os.environ['MYSQL_PASSWORD'] = 'pwd'
        for k in ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_DATABASE']:
            os.environ.pop(k, None)
        try:
            config = get_db_config()
            assert config['host'] == 'localhost'
            assert config['port'] == 3306
            assert config['user'] == 'root'
            assert config['database'] == 'steel_belt'
            assert config['charset'] == 'utf8mb4'
        finally:
            if saved_pwd is not None:
                os.environ['MYSQL_PASSWORD'] = saved_pwd
            else:
                os.environ.pop('MYSQL_PASSWORD', None)

    def test_get_db_config_port_string(self):
        """端口从字符串转为 int"""
        from utils.db_utils import get_db_config
        saved = self._set_env(MYSQL_PORT='4000', MYSQL_PASSWORD='pwd')
        try:
            config = get_db_config()
            assert config['port'] == 4000
            assert isinstance(config['port'], int)
        finally:
            self._restore_env(saved)

    def test_get_db_config_password_calls_get_mysql_password(self):
        """get_db_config 内部调用 get_mysql_password"""
        from utils.db_utils import get_db_config
        with patch('utils.db_utils.get_mysql_password', return_value='from_func'):
            config = get_db_config()
            assert config['password'] == 'from_func'


class TestCreateDbConnection:
    """create_db_connection() 测试 —— 覆盖 L48-73"""

    # pymysql 在函数内部 import，patch 'pymysql.connect' 全局路径
    @patch('core.db.get_direct_connection')
    def test_create_connection_success(self, mock_connect):
        """连接成功返回连接对象"""
        from utils.db_utils import create_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_db_config') as mock_config:
            mock_config.return_value = {
                'host': 'localhost', 'port': 3306, 'user': 'root',
                'password': 'pwd', 'database': 'test', 'charset': 'utf8mb4'
            }

            result = create_db_connection()
            assert result is mock_conn
            mock_connect.assert_called_once_with(
                host='localhost', port=3306, user='root',
                password='pwd', database='test', charset='utf8mb4'
            )

    @patch('core.db.get_direct_connection')
    def test_create_connection_with_database_override(self, mock_connect):
        """指定 database 参数覆盖默认配置"""
        from utils.db_utils import create_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_db_config') as mock_config:
            mock_config.return_value = {
                'host': 'localhost', 'port': 3306, 'user': 'root',
                'password': 'pwd', 'database': 'default_db', 'charset': 'utf8mb4'
            }

            result = create_db_connection(database='override_db')
            assert result is mock_conn
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['database'] == 'override_db'

    @patch('core.db.get_direct_connection')
    def test_create_connection_with_kwargs(self, mock_connect):
        """额外 kwargs 传递到 pymysql.connect"""
        from utils.db_utils import create_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_db_config') as mock_config:
            mock_config.return_value = {
                'host': 'localhost', 'port': 3306, 'user': 'root',
                'password': 'pwd', 'database': 'test', 'charset': 'utf8mb4'
            }

            result = create_db_connection(connect_timeout=5, autocommit=True)
            assert result is mock_conn
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['connect_timeout'] == 5
            assert call_kwargs['autocommit'] is True

    @patch('core.db.get_direct_connection')
    def test_create_connection_failure(self, mock_connect):
        """连接失败时抛出异常"""
        from utils.db_utils import create_db_connection
        mock_connect.side_effect = RuntimeError("Connection refused")
        with patch('utils.db_utils.get_db_config') as mock_config, \
             patch('utils.db_utils.logger') as mock_logger:
            mock_config.return_value = {
                'host': 'badhost', 'port': 3306, 'user': 'root',
                'password': 'pwd', 'database': 'test', 'charset': 'utf8mb4'
            }

            with pytest.raises(RuntimeError, match="Connection refused"):
                create_db_connection()

            mock_logger.error.assert_called_once()
            assert "连接数据库失败" in str(mock_logger.error.call_args)


class TestCreateRemoteDbConnection:
    """create_remote_db_connection() 测试 —— 覆盖 L76-119"""

    @patch('core.db.get_direct_connection')
    def test_remote_connection_success(self, mock_connect):
        """远程连接成功"""
        from utils.db_utils import create_remote_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_mysql_password', return_value='default_pwd'):
            result = create_remote_db_connection('10.0.0.1', port=3307)
            assert result is mock_conn
            mock_connect.assert_called_once_with(
                host='10.0.0.1', port=3307, user='root',
                password='default_pwd', charset='utf8mb4'
            )

    @patch('core.db.get_direct_connection')
    def test_remote_connection_with_custom_credentials(self, mock_connect):
        """自定义用户名和密码"""
        from utils.db_utils import create_remote_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        result = create_remote_db_connection(
            '10.0.0.2', user='custom_user', password='custom_pwd'
        )
        assert result is mock_conn
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs['user'] == 'custom_user'
        assert call_kwargs['password'] == 'custom_pwd'

    @patch('core.db.get_direct_connection')
    def test_remote_connection_with_database(self, mock_connect):
        """指定数据库名"""
        from utils.db_utils import create_remote_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_mysql_password', return_value='pwd'):
            result = create_remote_db_connection('10.0.0.3', database='my_db')
            assert result is mock_conn
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['database'] == 'my_db'

    @patch('core.db.get_direct_connection')
    def test_remote_connection_no_password_from_env(self, mock_connect):
        """未提供 password，从环境变量读取"""
        from utils.db_utils import create_remote_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_mysql_password', return_value='env_pwd'):
            result = create_remote_db_connection('10.0.0.4')
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['password'] == 'env_pwd'

    @patch('core.db.get_direct_connection')
    def test_remote_connection_with_kwargs(self, mock_connect):
        """额外 kwargs 传递"""
        from utils.db_utils import create_remote_db_connection
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        with patch('utils.db_utils.get_mysql_password', return_value='pwd'):
            result = create_remote_db_connection('10.0.0.5', charset='latin1', connect_timeout=10)
            call_kwargs = mock_connect.call_args[1]
            assert call_kwargs['charset'] == 'latin1'
            assert call_kwargs['connect_timeout'] == 10

    @patch('core.db.get_direct_connection')
    def test_remote_connection_failure(self, mock_connect):
        """远程连接失败"""
        from utils.db_utils import create_remote_db_connection
        mock_connect.side_effect = RuntimeError("Timeout")
        with patch('utils.db_utils.get_mysql_password', return_value='pwd'), \
             patch('utils.db_utils.logger') as mock_logger:
            with pytest.raises(RuntimeError, match="Timeout"):
                create_remote_db_connection('10.0.0.6', port=3306)

            mock_logger.error.assert_called_once()
            assert "连接远程数据库失败" in str(mock_logger.error.call_args)
            assert "10.0.0.6" in str(mock_logger.error.call_args)


class TestWithDbConnection:
    """with_db_connection() 装饰器测试 —— 覆盖 L122-141"""

    def test_decorator_normal(self):
        """装饰器自动创建和关闭连接"""
        from utils.db_utils import with_db_connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1}]
        mock_conn.cursor.return_value = mock_cursor

        @with_db_connection
        def query_data(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders")
            return cursor.fetchall()

        with patch('utils.db_utils.create_db_connection', return_value=mock_conn):
            result = query_data()

        assert result == [{"id": 1}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM orders")
        mock_conn.close.assert_called_once()

    def test_decorator_exception_closes_connection(self):
        """装饰器内函数抛异常时仍关闭连接"""
        from utils.db_utils import with_db_connection
        mock_conn = MagicMock()

        @with_db_connection
        def failing_query(conn):
            raise ValueError("查询失败")

        with patch('utils.db_utils.create_db_connection', return_value=mock_conn):
            with pytest.raises(ValueError, match="查询失败"):
                failing_query()

        mock_conn.close.assert_called_once()

    def test_decorator_conn_is_none(self):
        """连接为 None 时 close 安全"""
        from utils.db_utils import with_db_connection

        @with_db_connection
        def query(conn):
            return "no conn needed"

        with patch('utils.db_utils.create_db_connection', return_value=None):
            result = query()

        assert result == "no conn needed"

    def test_decorator_args_passed_through(self):
        """装饰器将额外参数原样传递"""
        from utils.db_utils import with_db_connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_conn.cursor.return_value = mock_cursor

        @with_db_connection
        def query_by_id(conn, table, record_id):
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table} WHERE id=%s", (record_id,))
            return cursor.fetchall()

        with patch('utils.db_utils.create_db_connection', return_value=mock_conn):
            result = query_by_id('orders', 42)

        assert result == [{"id": 1, "name": "test"}]
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM orders WHERE id=%s", (42,)
        )
