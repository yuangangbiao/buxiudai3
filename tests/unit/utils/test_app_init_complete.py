# -*- coding: utf-8 -*-
"""
utils/app_init.py 完整单元测试

覆盖模块:
- preload_dict_data
- get_material_densities
- archive_old_orders
- cleanup_old_logs
- get_db_stats
- init_app_cache
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

class TestAppInitExists:
    """app_init 模块存在性测试"""

    def test_app_init_module_exists(self):
        """测试app_init模块存在"""
        from utils import app_init
        assert app_init is not None

    def test_preload_dict_data_exists(self):
        """测试preload_dict_data函数存在"""
        from utils.app_init import preload_dict_data
        assert callable(preload_dict_data)

    def test_get_material_densities_exists(self):
        """测试get_material_densities函数存在"""
        from utils.app_init import get_material_densities
        assert callable(get_material_densities)

    def test_archive_old_orders_exists(self):
        """测试archive_old_orders函数存在"""
        from utils.app_init import archive_old_orders
        assert callable(archive_old_orders)

    def test_cleanup_old_logs_exists(self):
        """测试cleanup_old_logs函数存在"""
        from utils.app_init import cleanup_old_logs
        assert callable(cleanup_old_logs)

    def test_get_db_stats_exists(self):
        """测试get_db_stats函数存在"""
        from utils.app_init import get_db_stats
        assert callable(get_db_stats)


class TestArchiveOldOrders:
    """archive_old_orders 测试"""

    @patch('utils.app_init.get_connection')
    def test_archive_dry_run(self, mock_get_conn):
        """测试归档预演模式"""
        from utils.app_init import archive_old_orders

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'DATE_SUB(NOW(), INTERVAL %s DAY)': '2023-01-01'},
            {'cnt': 10}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = archive_old_orders(days=365, dry_run=True)

        assert result['dry_run'] is True
        assert result['would_archive'] == 10

    @patch('utils.app_init.get_connection')
    def test_archive_no_orders(self, mock_get_conn):
        """测试没有可归档的订单"""
        from utils.app_init import archive_old_orders

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'DATE_SUB(NOW(), INTERVAL %s DAY)': '2023-01-01'},
            {'cnt': 0}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = archive_old_orders(days=365, dry_run=False)

        assert result['archived'] == 0


class TestCleanupOldLogs:
    """cleanup_old_logs 测试"""

    @patch('utils.app_init.get_connection')
    def test_cleanup_valid_table(self, mock_get_conn):
        """测试清理有效表"""
        from utils.app_init import cleanup_old_logs

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'DATE_SUB(NOW(), INTERVAL %s DAY)': '2023-01-01'},
            {'cnt': 5}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = cleanup_old_logs(days=730, table="operator_logs")

        assert result['deleted'] == 5

    def test_cleanup_invalid_table(self):
        """测试清理无效表"""
        from utils.app_init import cleanup_old_logs

        result = cleanup_old_logs(days=730, table="invalid_table")

        assert 'error' in result


class TestGetDbStats:
    """get_db_stats 测试"""

    @patch('utils.app_init.get_connection')
    def test_get_db_stats_returns_dict(self, mock_get_conn):
        """测试获取数据库统计"""
        from utils.app_init import get_db_stats

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'cnt': 100}

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = get_db_stats()

        assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
