# -*- coding: utf-8 -*-
"""models/operation_log.py 完整测试——操作日志 DAO"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestOperationLogDAOCreate:
    """OperationLogDAO.create"""

    def test_create_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.create(1, 'ORD-001', '订单管理', '创建订单', '张三', '创建新订单')
        assert result is True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'INSERT INTO operation_logs' in call_args[0]
        assert call_args[1][0] == 1
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_create_no_details(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.create(2, 'ORD-002', '报工管理', '开始工序', '李四')
        assert result is True
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1][5] is None

    def test_create_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("db error")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.create(1, 'ORD-001', '订单管理', '创建订单', '张三')
        assert result is False
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestOperationLogDAOGetByOrderId:
    """OperationLogDAO.get_by_order_id"""

    def test_get_by_order_id_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1}, {'id': 2}]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_order_id(42)
        assert result == [{'id': 1}, {'id': 2}]
        call_args = mock_cursor.execute.call_args[0]
        assert 'WHERE order_id = %s' in call_args[0]
        assert call_args[1][0] == 42
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_get_by_order_id_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("query fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_order_id(99)
        assert result == []
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestOperationLogDAOGetByModule:
    """OperationLogDAO.get_by_module"""

    def test_get_by_module_default_limit(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'module': '订单管理'}]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_module('订单管理')
        assert len(result) == 1
        call_args = mock_cursor.execute.call_args[0]
        assert 'WHERE module = %s' in call_args[0]
        assert call_args[1][1] == 100

    def test_get_by_module_custom_limit(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_module('报工管理', limit=5)
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1][1] == 5

    def test_get_by_module_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_module('订单管理')
        assert result == []


class TestOperationLogDAOGetByAction:
    """OperationLogDAO.get_by_action"""

    def test_get_by_action_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'action': '创建订单'}]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_action('创建订单', limit=50)
        call_args = mock_cursor.execute.call_args[0]
        assert 'WHERE action = %s' in call_args[0]
        assert call_args[1][1] == 50
        assert len(result) == 1

    def test_get_by_action_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_by_action('创建订单')
        assert result == []


class TestOperationLogDAOGetRecent:
    """OperationLogDAO.get_recent"""

    def test_get_recent_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1}, {'id': 2}, {'id': 3}]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_recent(limit=3)
        assert len(result) == 3
        call_args = mock_cursor.execute.call_args[0]
        assert 'ORDER BY created_at DESC' in call_args[0]
        assert call_args[1][0] == 3

    def test_get_recent_default_limit(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            OperationLogDAO.get_recent()
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1][0] == 100

    def test_get_recent_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.get_recent()
        assert result == []


class TestOperationLogDAOSearch:
    """OperationLogDAO.search"""

    def test_search_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'order_no': 'ORD-001', 'operator': '张三'}]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.search('张三')
        assert len(result) == 1
        call_args = mock_cursor.execute.call_args[0]
        assert 'LIKE %s' in call_args[0]
        assert call_args[1][0] == '%张三%'
        assert call_args[1][3] == 100

    def test_search_custom_limit(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            OperationLogDAO.search('ORD', limit=10)
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1][3] == 10

    def test_search_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("search fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.search('test')
        assert result == []


class TestOperationLogDAOCleanExpired:
    """OperationLogDAO.clean_expired_logs"""

    def test_clean_no_completed_orders(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # 没有已完成的订单
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.clean_expired_logs()
        assert result == 0
        mock_conn.commit.assert_called_once()

    def test_clean_expired_deletes(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # 第一次 execute 后 fetchall 返回已完成订单
        # 第二次 execute(fetch completed order) 后 fetchone 返回过期时间
        mock_cursor.fetchall.side_effect = [
            [{'id': 1}],   # completed_orders
            [],             # operation_logs delete 后的 fetchall（实际是第二个查询，这里用不到）
        ]
        mock_cursor.fetchone.side_effect = [
            {'updated_at': (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S")},
        ]
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.clean_expired_logs()
        assert result == 5
        assert mock_cursor.execute.call_count >= 3
        mock_conn.commit.assert_called_once()

    def test_clean_not_expired_skips(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [{'id': 1}],   # completed_orders
            [],             # unused
        ]
        mock_cursor.fetchone.side_effect = [
            {'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")},  # 刚刚完成，未过期
        ]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.clean_expired_logs()
        assert result == 0
        mock_conn.commit.assert_called_once()

    def test_clean_order_not_found(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [{'id': 1}],  # completed_orders
            [],            # unused
        ]
        mock_cursor.fetchone.side_effect = [None]  # 订单不存在
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.clean_expired_logs()
        assert result == 0

    def test_clean_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("clean fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.clean_expired_logs()
        assert result == 0
        mock_conn.rollback.assert_called_once()


class TestOperationLogDAOCountByModule:
    """OperationLogDAO.count_by_module"""

    def test_count_by_module_success(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'module': '订单管理', 'count': 10},
            {'module': '报工管理', 'count': 5},
        ]
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.count_by_module()
        assert len(result) == 2
        assert result[0]['count'] == 10
        call_args = mock_cursor.execute.call_args[0]
        assert 'GROUP BY module' in call_args[0]

    def test_count_by_module_failure(self):
        from models.operation_log import OperationLogDAO
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("count fail")
        mock_conn.cursor.return_value = mock_cursor
        with patch('models.operation_log.get_connection', return_value=mock_conn):
            result = OperationLogDAO.count_by_module()
        assert result == []


class TestLogOperation:
    """log_operation 便捷函数"""

    def test_log_operation_with_valid_keys(self):
        from models.operation_log import log_operation, OperationLogDAO
        with patch.object(OperationLogDAO, 'create', return_value=True) as mock_create:
            log_operation(1, 'ORD-001', 'MATERIAL_PREP', 'MAT_ADD', operator='张三', details='添加物料A')
        # 验证键被转换为中文
        mock_create.assert_called_once_with(1, 'ORD-001', '物料准备', '添加物料', '张三', '添加物料A')

    def test_log_operation_with_raw_keys(self):
        """如果键不在常量字典中，应直接作为值传递"""
        from models.operation_log import log_operation, OperationLogDAO
        with patch.object(OperationLogDAO, 'create', return_value=True) as mock_create:
            log_operation(1, 'ORD-001', '自定义模块', '自定义操作')
        mock_create.assert_called_once_with(1, 'ORD-001', '自定义模块', '自定义操作', '系统', None)

    def test_log_operation_default_operator(self):
        from models.operation_log import log_operation, OperationLogDAO
        with patch.object(OperationLogDAO, 'create', return_value=True) as mock_create:
            log_operation(1, 'ORD-001', 'PROCESS', 'PROC_START')
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[0]
        assert call_kwargs[4] == '系统'  # operator 默认值


class TestConstants:
    """LOG_MODULE 和 LOG_ACTION 常量"""

    def test_log_module_values(self):
        from models.operation_log import LOG_MODULE
        assert LOG_MODULE['MATERIAL_PREP'] == '物料准备'
        assert LOG_MODULE['PROCESS'] == '报工管理'
        assert LOG_MODULE['INSPECTION'] == '质量检验'
        assert LOG_MODULE['PRODUCTION'] == '生产排产'
        assert LOG_MODULE['ORDER'] == '订单管理'
        assert LOG_MODULE['INVENTORY'] == '库存管理'

    def test_log_action_values(self):
        from models.operation_log import LOG_ACTION
        assert LOG_ACTION['MAT_ADD'] == '添加物料'
        assert LOG_ACTION['ORD_CREATE'] == '创建订单'
        assert LOG_ACTION['INSP_APPROVE'] == '质检通过'
        assert LOG_ACTION['PROD_START'] == '开始生产'
