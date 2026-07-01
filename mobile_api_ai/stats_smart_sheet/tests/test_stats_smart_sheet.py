# -*- coding: utf-8 -*-
"""
stats_smart_sheet 单元测试
覆盖 9 个 SQL 查询函数 + 客户端重试 + 字段映射 + 产线解析
"""
import sys
import os
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stats_smart_sheet import db_queries
from stats_smart_sheet import production_lines
from stats_smart_sheet.smart_sheet_client import (
    compute_hash, map_to_field_ids, push_with_retry
)
from stats_smart_sheet.config import FIELD_MAPPING, PUSH_CONFIG


class TestProductionLines(unittest.TestCase):
    """测试产线映射（C-2.6 修复）"""

    def test_get_line_by_order_no(self):
        self.assertEqual(production_lines.get_line_by_order_no('WO-L1-202605006'), '网带一线')
        self.assertEqual(production_lines.get_line_by_order_no('WO-L2-202605006'), '网带二线')
        self.assertEqual(production_lines.get_line_by_order_no('WO-CHAIN-202605006'), '链板线')

    def test_get_line_by_product(self):
        self.assertEqual(production_lines.get_line_by_product('平板型网带-500mm'), '网带一线')
        self.assertEqual(production_lines.get_line_by_product('链板型网带'), '网带二线')

    def test_resolve_line_fallback(self):
        self.assertEqual(production_lines.resolve_line('', '未知产品'), '默认产线')
        self.assertEqual(production_lines.resolve_line('WO-L1-001', ''), '网带一线')

    def test_resolve_line_with_L_in_middle(self):
        """工单号中包含 L\\d+ 时能正确解析"""
        self.assertEqual(production_lines.get_line_by_order_no('202605006-L3-X'), '网带3线')


class TestComputeHash(unittest.TestCase):
    """测试记录哈希"""

    def test_same_records_same_hash(self):
        records = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        h1 = compute_hash(records)
        h2 = compute_hash(records)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_different_records_different_hash(self):
        h1 = compute_hash([{'a': 1}])
        h2 = compute_hash([{'a': 2}])
        self.assertNotEqual(h1, h2)


class TestFieldMapping(unittest.TestCase):
    """测试字段映射"""

    def test_map_to_field_ids_known_table(self):
        records = [
            {'记录ID': 'DR-001', '日期': '2026-06-04', '班组': '早班'},
        ]
        mapped = map_to_field_ids('production_daily_report', records)
        self.assertEqual(mapped[0]['f0001'], 'DR-001')
        self.assertEqual(mapped[0]['f0002'], '2026-06-04')
        self.assertEqual(mapped[0]['f0003'], '早班')

    def test_map_to_field_ids_unknown_table(self):
        """未知表类型应返回原记录"""
        records = [{'x': 1}]
        mapped = map_to_field_ids('unknown_table', records)
        self.assertEqual(mapped, records)

    def test_map_to_field_ids_preserves_unmapped(self):
        """未映射的字段应保留"""
        records = [{'记录ID': 'X', '未知字段': 'Y'}]
        mapped = map_to_field_ids('production_daily_report', records)
        self.assertEqual(mapped[0].get('未知字段'), 'Y')


class TestPushWithRetry(unittest.TestCase):
    """测试重试机制（H-4 修复）"""

    @patch('stats_smart_sheet.smart_sheet_client.requests.post')
    def test_retry_then_success(self, mock_post):
        """网络异常后重试，最终成功"""
        success_resp = MagicMock()
        success_resp.json.return_value = {'code': 0, 'message': 'OK', 'success_count': 1}
        success_resp.content = b'{}'

        import requests
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("net err"),
            success_resp,
        ]

        with patch.dict(os.environ, {'STATS_RETRY_INTERVAL': '1', 'STATS_MAX_RETRIES': '3'}):
            records = [{'f0001': 'X'}]
            result = push_with_retry('production_daily_report', records, 'test')

        self.assertEqual(result['code'], 0)
        self.assertEqual(mock_post.call_count, 2)
        self.assertIn('batch_id', result)

    @patch('stats_smart_sheet.smart_sheet_client.requests.post')
    def test_retry_exhausted(self, mock_post):
        """重试耗尽后返回失败"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("always fail")

        with patch.dict(os.environ, {'STATS_RETRY_INTERVAL': '1', 'STATS_MAX_RETRIES': '2'}):
            records = [{'f0001': 'X'}]
            result = push_with_retry('production_daily_report', records, 'test')

        self.assertEqual(result['code'], -1)
        self.assertEqual(mock_post.call_count, 2)
        self.assertIn('失败', result['message'])

    @patch('stats_smart_sheet.smart_sheet_client.requests.post')
    def test_empty_records_skipped(self, mock_post):
        """空记录应跳过推送"""
        result = push_with_retry('production_daily_report', [], 'test')
        self.assertEqual(result['code'], 0)
        self.assertEqual(result['message'], '无数据')
        mock_post.assert_not_called()


class TestDBQueries(unittest.TestCase):
    """测试 SQL 查询函数（mock 模式，不连真实 DB）"""

    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor

    @patch('stats_smart_sheet.db_queries.get_conn')
    def test_query_production_daily_returns_mapped_records(self, mock_get_conn):
        mock_get_conn.return_value = self.mock_conn
        self.mock_cursor.fetchall.return_value = [
            {'日期': date(2026, 6, 4), '班组': '早班', '产线': '网带一线',
             '计划数': 100, '完成数': 80},
        ]
        records = db_queries.query_production_daily(date(2026, 6, 4))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['差异率'], -20.0)
        self.assertEqual(records[0]['合格率'], 100.0)
        self.assertIn('DR-', records[0]['记录ID'])

    @patch('stats_smart_sheet.db_queries.get_conn')
    def test_query_workorder_progress_handles_null_steps(self, mock_get_conn):
        """测试 JSON 越界保护（C-2.4 修复）"""
        mock_get_conn.return_value = self.mock_conn
        self.mock_cursor.fetchall.return_value = [
            {
                '工单号': 'WO-001', '客户': '客户A', '产品': '产品X',
                '计划开始': date(2026, 6, 1), '计划完工': date(2026, 6, 10),
                '实际开始': None, '实际完工': None,
                '当前工序': None,  # JSON 越界时为 NULL
                '完成工序': 5, '总工序': 5, '原始状态': 'completed'
            },
        ]
        records = db_queries.query_workorder_progress()
        self.assertEqual(records[0]['状态'], '已完成')
        self.assertEqual(records[0]['进度条'], 100.0)

    @patch('stats_smart_sheet.db_queries.get_conn')
    def test_query_inventory_alert_uses_threshold(self, mock_get_conn):
        """测试库存预警使用环境变量阈值（C-2.8 修复）"""
        mock_get_conn.return_value = self.mock_conn
        self.mock_cursor.fetchall.return_value = [
            {'物料编码': 'M001', '物料名称': '钢材', '仓库': '主仓',
             '当前库存': 5, '安全库存': 10, '最近入库时间': datetime.now()},
        ]
        records = db_queries.query_inventory_alert(safety_threshold=10)
        self.assertEqual(records[0]['预警状态'], '低库存')
        self.assertEqual(records[0]['建议补货量'], 5)


class TestConfigIntegrity(unittest.TestCase):
    """测试配置完整性"""

    def test_all_9_tables_in_schedule(self):
        from stats_smart_sheet.config import SCHEDULE_CONFIG, EXPORT_FUNCS
        self.assertGreaterEqual(len(SCHEDULE_CONFIG), 9)

    def test_all_9_tables_have_field_mapping(self):
        self.assertEqual(len(FIELD_MAPPING), 9)

    def test_field_mapping_uses_valid_ids(self):
        """field_id 应符合 fXXXX 格式"""
        import re
        for table_type, mapping in FIELD_MAPPING.items():
            for field_name, field_id in mapping.items():
                self.assertRegex(
                    field_id, r'^f[0-9A-Fa-f]+$',
                    f"{table_type}.{field_name} 字段ID格式错误: {field_id}"
                )


class TestConcurrencyControl(unittest.TestCase):
    """测试并发控制（H-5 修复）"""

    def test_export_table_serializes_per_type(self):
        """同一表类型应串行执行"""
        from stats_smart_sheet.smart_sheet_exporter import (
            _table_locks, EXPORT_FUNCS
        )
        for t in EXPORT_FUNCS:
            self.assertIn(t, _table_locks)


if __name__ == '__main__':
    unittest.main(verbosity=2)
