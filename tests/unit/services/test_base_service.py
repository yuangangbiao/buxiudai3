# -*- coding: utf-8 -*-
"""services/base_service.py 测试 —— 覆盖 L66-78 transaction() 全部路径"""
import pytest
from unittest.mock import patch, MagicMock


class TestBaseServiceInit:
    """BaseService 初始化测试"""

    def test_init_with_dao(self):
        from services.base_service import BaseService
        mock_dao = MagicMock()
        svc = BaseService(dao=mock_dao)
        assert svc.dao is mock_dao

    def test_init_without_dao(self):
        from services.base_service import BaseService
        svc = BaseService()
        assert svc.dao is None


class TestBaseServiceTransaction:
    """BaseService.transaction() 上下文管理器测试 —— 覆盖 L66-78"""

    def test_transaction_commit(self):
        """正常路径：提交并关闭连接"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            svc = BaseService()
            with svc.transaction() as conn:
                conn.cursor().execute("SELECT 1")

            mock_get_conn.assert_called_once()
            mock_conn.commit.assert_called_once()
            mock_conn.rollback.assert_not_called()
            mock_conn.close.assert_called_once()

    def test_transaction_rollback(self):
        """异常路径：回滚并抛出异常"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            svc = BaseService()
            with pytest.raises(ValueError, match="模拟异常"):
                with svc.transaction() as conn:
                    conn.cursor().execute("INSERT INTO test VALUES(1)")
                    raise ValueError("模拟异常")

            mock_get_conn.assert_called_once()
            mock_conn.commit.assert_not_called()
            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_transaction_rollback_with_dao(self):
        """异常回滚时，logger 包含 DAO 类型信息"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn, \
             patch('services.base_service.logger') as mock_logger:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            mock_dao = MagicMock()
            mock_dao.__class__.__name__ = "MockDAO"
            svc = BaseService(dao=mock_dao)

            with pytest.raises(RuntimeError):
                with svc.transaction() as conn:
                    conn.cursor().execute("UPDATE test SET x=1")
                    raise RuntimeError("事务失败")

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert "[BaseService] 事务回滚" in str(call_args)
            assert "MockDAO" in str(call_args)

    def test_transaction_rollback_no_dao(self):
        """异常回滚时，dao 为 None 应显示 None"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn, \
             patch('services.base_service.logger') as mock_logger:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            svc = BaseService(dao=None)

            with pytest.raises(ValueError):
                with svc.transaction() as conn:
                    raise ValueError("no dao test")

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert "None" in str(call_args)

    def test_transaction_yields_connection(self):
        """验证 yield 返回的确实是 get_connection() 返回的连接"""
        from services.base_service import BaseService
        mock_conn = MagicMock()
        mock_connection = MagicMock()

        class FakeCursor:
            def execute(self, sql): pass

        mock_conn.cursor.return_value = FakeCursor()
        mock_connection.__enter__ = lambda s: mock_conn
        mock_connection.__exit__ = lambda s, *a: None

        with patch('services.base_service.get_connection', return_value=mock_conn):
            svc = BaseService()
            with svc.transaction() as conn:
                assert conn is mock_conn

    def test_transaction_multiple_statements(self):
        """事务内多条 SQL 语句正常执行"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            svc = BaseService()
            with svc.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO a VALUES(1)")
                cursor.execute("INSERT INTO b VALUES(2)")

            assert mock_conn.cursor().execute.call_count == 2
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_transaction_finally_closes_on_exception(self):
        """异常时 finally 块仍然执行 close"""
        from services.base_service import BaseService
        with patch('services.base_service.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn

            svc = BaseService()
            try:
                with svc.transaction():
                    raise SystemError("致命错误")
            except SystemError:
                pass

            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called_once()


class TestBaseServiceIntegration:
    """BaseService 与 ProcessService 集成的模拟测试"""

    def test_shift_seq_up_uses_transaction(self):
        """验证 ProcessService.shift_seq_up 实际调用 transaction()"""
        from services.process_service import ProcessService
        with patch.object(ProcessService, 'transaction') as mock_txn:
            mock_cm = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cm.__enter__.return_value = mock_conn
            mock_txn.return_value = mock_cm

            svc = ProcessService()
            svc.shift_seq_up(1, 2)

            mock_txn.assert_called_once()
            mock_cursor.execute.assert_called_once()
            sql = mock_cursor.execute.call_args[0][0]
            assert 'UPDATE process_records' in sql
            assert 'process_seq' in sql
