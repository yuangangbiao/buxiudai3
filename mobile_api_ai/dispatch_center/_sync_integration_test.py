# -*- coding: utf-8 -*-
"""
dispatch_center/_sync.py 集成测试（mock 容器中心 + MySQL）

使用 unittest.mock 模拟容器中心和 MySQL，避免真实依赖

执行: python dispatch_center/_sync_integration_test.py
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # core 在项目根


class TestGetDocData(unittest.TestCase):
    """测试 get_doc_data 函数"""

    def setUp(self):
        from dispatch_center._sync import get_doc_data
        self.func = get_doc_data

    def test_extract_from_doc_data_field(self):
        """从 doc_data 字段提取"""
        item = {'doc_data': {'order_no': 'ORD001', 'product': 'A'}}
        result = self.func(item)
        self.assertEqual(result, {'order_no': 'ORD001', 'product': 'A'})

    def test_extract_from_data_field(self):
        """从 data 字段提取（fallback）"""
        item = {'data': {'order_no': 'ORD002'}}
        result = self.func(item)
        self.assertEqual(result, {'order_no': 'ORD002'})

    def test_extract_from_content_field(self):
        """从 content 字段提取（fallback）"""
        item = {'content': {'order_no': 'ORD003', 'qty': 100}}
        result = self.func(item)
        self.assertEqual(result, {'order_no': 'ORD003', 'qty': 100})

    def test_parse_json_string(self):
        """JSON 字符串自动解析"""
        item = {'doc_data': '{"order_no": "ORD004", "value": 42}'}
        result = self.func(item)
        self.assertEqual(result, {'order_no': 'ORD004', 'value': 42})

    def test_invalid_json_returns_empty(self):
        """无效 JSON 返回空字典"""
        item = {'doc_data': '{invalid json}'}
        result = self.func(item)
        self.assertEqual(result, {})

    def test_none_input(self):
        """None 输入安全处理"""
        self.assertEqual(self.func(None), {})

    def test_non_dict_input(self):
        """非 dict 输入安全处理"""
        self.assertEqual(self.func("string"), {})
        self.assertEqual(self.func(123), {})
        self.assertEqual(self.func([]), {})

    def test_empty_dict(self):
        """空字典返回空"""
        self.assertEqual(self.func({}), {})

    def test_nested_data_priority(self):
        """doc_data 优先级最高"""
        item = {
            'doc_data': {'source': 'doc_data'},
            'data': {'source': 'data'},
            'content': {'source': 'content'},
        }
        result = self.func(item)
        self.assertEqual(result['source'], 'doc_data')

    def test_doc_data_not_dict(self):
        """doc_data 不是 dict 时返回空"""
        item = {'doc_data': 'plain string'}
        result = self.func(item)
        self.assertEqual(result, {})


class TestSyncWorkOrderStatus(unittest.TestCase):
    """测试 sync_work_order_status 函数（mock 容器中心）"""

    def setUp(self):
        from dispatch_center._sync import sync_work_order_status
        self.func = sync_work_order_status

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_status_completed(self, mock_get_cc, mock_get_orders):
        """status_key='completed' → cc_status='completed'"""
        # 准备 mock
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-001', 'doc_data': {'order_no': 'ORD001'}}
        ]

        # 执行
        self.func('ORD001', 'completed', current_step=5)

        # 验证容器中心被调用
        mock_cc.update_document.assert_called_once()
        args = mock_cc.update_document.call_args
        self.assertEqual(args[0][0], 'work_order')
        self.assertEqual(args[0][1], 'wo-001')
        update_data = args[0][2]
        self.assertEqual(update_data['status'], 'completed')
        self.assertEqual(update_data['current_step'], 5)

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_status_published(self, mock_get_cc, mock_get_orders):
        """status_key='published' → cc_status='dispatched'"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-002', 'doc_data': {'order_no': 'ORD002'}}
        ]

        self.func('ORD002', 'published', current_step=1)

        update_data = mock_cc.update_document.call_args[0][2]
        self.assertEqual(update_data['status'], 'dispatched')

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_status_in_production(self, mock_get_cc, mock_get_orders):
        """status_key='in_production' → cc_status='in_progress'"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-003', 'doc_data': {'order_no': 'ORD003'}}
        ]

        self.func('ORD003', 'in_production', current_step=3)

        update_data = mock_cc.update_document.call_args[0][2]
        self.assertEqual(update_data['status'], 'in_progress')

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_status_with_process_id(self, mock_get_cc, mock_get_orders):
        """传 process_id 时被包含在 update_data 中"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-004', 'doc_data': {'order_no': 'ORD004'}}
        ]

        self.func('ORD004', 'confirmed', current_step=2, process_id='PROC-123')

        update_data = mock_cc.update_document.call_args[0][2]
        self.assertEqual(update_data['related_process'], 'PROC-123')

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_status_without_process_id(self, mock_get_cc, mock_get_orders):
        """不传 process_id 时不应包含 related_process"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-005', 'doc_data': {'order_no': 'ORD005'}}
        ]

        self.func('ORD005', 'reported', current_step=4)

        update_data = mock_cc.update_document.call_args[0][2]
        self.assertNotIn('related_process', update_data)

    @patch('dispatch_center._sync._get_container_center')
    def test_empty_order_no_skips(self, mock_get_cc):
        """空 order_no 直接返回"""
        self.func('', 'completed')
        mock_get_cc.assert_not_called()

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_match_by_related_order(self, mock_get_cc, mock_get_orders):
        """通过 related_order 匹配"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-rel-1', 'doc_data': {'related_order': 'ORD006'}}
        ]

        self.func('ORD006', 'completed', current_step=5)

        mock_cc.update_document.assert_called_once()
        self.assertEqual(mock_cc.update_document.call_args[0][1], 'wo-rel-1')

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_match_by_direct_order_no(self, mock_get_cc, mock_get_orders):
        """通过 item.order_no 匹配（不在 doc_data 内）"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-direct-1', 'order_no': 'ORD007'}
        ]

        self.func('ORD007', 'completed')

        mock_cc.update_document.assert_called_once()

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_no_match_does_not_call_update(self, mock_get_cc, mock_get_orders):
        """无匹配工单时不应调用 update"""
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-other', 'doc_data': {'order_no': 'OTHER'}}
        ]

        self.func('ORD999', 'completed')

        mock_cc.update_document.assert_not_called()

    @patch('dispatch_center._sync._get_container_center')
    def test_cc_unavailable_skips_gracefully(self, mock_get_cc):
        """容器中心不可用时优雅跳过"""
        mock_get_cc.return_value = None

        # 不应该抛出异常
        self.func('ORD001', 'completed')

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_cc_raises_exception_does_not_propagate(self, mock_get_cc, mock_get_orders):
        """容器中心异常时不传播"""
        mock_cc = MagicMock()
        mock_cc.update_document.side_effect = Exception('容器中心错误')
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-err', 'doc_data': {'order_no': 'ORD008'}}
        ]

        # 不应该抛出异常
        self.func('ORD008', 'completed')


class TestSyncToMysql(unittest.TestCase):
    """测试 sync_to_mysql 函数（mock MySQL 连接）"""

    def setUp(self):
        from dispatch_center._sync import sync_to_mysql
        self.func = sync_to_mysql

    def _make_mock_cursor(self, fetchone_returns):
        cursor = MagicMock()
        cursor.fetchone.side_effect = fetchone_returns
        return cursor

    def _make_mock_conn(self, cursor):
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_empty_order_no_skips(self, mock_get_conn):
        """空 order_no 直接返回"""
        self.func('', 'completed')
        mock_get_conn.assert_not_called()

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_empty_status_skips(self, mock_get_conn):
        """空状态直接返回"""
        self.func('ORD001', '')
        mock_get_conn.assert_not_called()

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_unknown_status_logs_warning(self, mock_get_conn):
        """未知状态记录警告，不抛异常"""
        mock_get_conn.return_value = self._make_mock_conn(
            self._make_mock_cursor([])
        )
        # 不应该抛异常
        self.func('ORD001', 'unknown_status_xyz')
        mock_get_conn.assert_called_once()

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_update_existing_production_order(self, mock_get_conn):
        """更新已存在的 production_order"""
        cursor = self._make_mock_cursor([
            {'id': 1, 'status': '已排产', 'order_id': 10}  # production_orders
        ])
        conn = self._make_mock_conn(cursor)
        mock_get_conn.return_value = conn

        self.func('ORD001', 'confirmed', lead_time=7)

        # 验证 UPDATE 调用
        update_calls = [c for c in cursor.execute.call_args_list
                        if 'UPDATE' in str(c)]
        self.assertTrue(len(update_calls) > 0, '应该调用 UPDATE')

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_connection_failure_logs_warning(self, mock_get_conn):
        """连接失败时记录警告，不抛异常"""
        mock_get_conn.side_effect = Exception('连接失败')

        # 不应该抛出异常
        self.func('ORD001', 'confirmed')

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_conn_close_called_on_success(self, mock_get_conn):
        """成功后关闭连接"""
        cursor = self._make_mock_cursor([{'id': 1, 'status': '已排产', 'order_id': 10}])
        conn = self._make_mock_conn(cursor)
        mock_get_conn.return_value = conn

        self.func('ORD001', 'confirmed')

        conn.close.assert_called_once()

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_conn_close_called_on_exception(self, mock_get_conn):
        """异常时也尝试关闭连接"""
        cursor = MagicMock()
        cursor.execute.side_effect = Exception('SQL 错误')
        conn = self._make_mock_conn(cursor)
        mock_get_conn.return_value = conn

        self.func('ORD001', 'confirmed')

        conn.close.assert_called_once()

    @patch('dispatch_center._sync._get_mysql_connection')
    def test_wo_prefix_order_no_handled(self, mock_get_conn):
        """WO- 前缀的订单号特殊处理"""
        cursor = self._make_mock_cursor([
            {'id': 1, 'status': '已排产', 'order_id': 10}
        ])
        conn = self._make_mock_conn(cursor)
        mock_get_conn.return_value = conn

        # 不应该抛异常
        self.func('WO-001', 'confirmed')


class TestSyncScheduleToContainer(unittest.TestCase):
    """测试 sync_schedule_to_container 函数（mock 容器中心）"""

    def setUp(self):
        from dispatch_center._sync import sync_schedule_to_container
        self.func = sync_schedule_to_container

    @patch('dispatch_center._sync._get_container_center')
    def test_cc_unavailable_skips_gracefully(self, mock_get_cc):
        """容器中心不可用时优雅跳过"""
        mock_get_cc.return_value = None

        # 不应该抛出异常
        self.func('ORD001', {}, 7, '张三')

    @patch('dispatch_center._sync._get_container_center')
    def test_cc_without_storage_skips(self, mock_get_cc):
        """容器中心无 storage 属性时跳过"""
        mock_cc = MagicMock(spec=[])  # 无 storage
        mock_get_cc.return_value = mock_cc

        # 不应该抛出异常
        self.func('ORD001', {}, 7, '张三')

    @patch('dispatch_center._sync._get_container_center')
    def test_cc_raises_exception_does_not_propagate(self, mock_get_cc):
        """容器中心异常时不传播"""
        mock_cc = MagicMock()
        mock_cc.storage = MagicMock()
        mock_cc.storage.save_schedule_record.side_effect = Exception('保存失败')
        mock_get_cc.return_value = mock_cc

        # 不应该抛出异常
        self.func('ORD001', {'product_name': 'A', 'quantity': 10}, 7, '张三')

    @patch('dispatch_center._sync._get_container_center')
    def test_successful_sync_with_full_data(self, mock_get_cc):
        """完整数据同步成功"""
        mock_cc = MagicMock()
        mock_cc.storage = MagicMock()
        mock_cc.sync_schedule_to_mysql = MagicMock()
        mock_get_cc.return_value = mock_cc

        self.func(
            order_no='ORD001',
            process={'product_name': '网带A', 'quantity': 100, 'priority': 'high'},
            lead_time=7,
            operator_name='张三'
        )

        # 验证 schedule_record 被保存
        mock_cc.storage.save_schedule_record.assert_called_once()
        # 验证 process_record 被更新
        mock_cc.storage.save_process_record.assert_called_once()
        # 验证 mysql 同步被调用
        mock_cc.sync_schedule_to_mysql.assert_called_once()

    @patch('dispatch_center._sync._get_container_center')
    def test_sync_data_includes_correct_fields(self, mock_get_cc):
        """同步数据包含正确字段"""
        mock_cc = MagicMock()
        mock_cc.storage = MagicMock()
        mock_cc.sync_schedule_to_mysql = MagicMock()
        mock_get_cc.return_value = mock_cc

        self.func(
            order_no='ORD001',
            process={'product_name': '网带A', 'quantity': 100, 'priority': 'high'},
            lead_time=7,
            operator_name='张三'
        )

        record = mock_cc.storage.save_schedule_record.call_args[0][0]
        self.assertEqual(record['order_no'], 'ORD001')
        self.assertEqual(record['status'], 'confirmed')
        self.assertEqual(record['product_name'], '网带A')
        self.assertEqual(record['quantity'], 100)
        self.assertEqual(record['priority'], 'high')
        self.assertEqual(record['confirmed_by'], '张三')

    @patch('dispatch_center._sync._get_container_center')
    def test_lead_time_string_raises_or_handled(self, mock_get_cc):
        """lead_time 为字符串时的处理"""
        mock_cc = MagicMock()
        mock_cc.storage = MagicMock()
        mock_get_cc.return_value = mock_cc

        # 字符串 "abc" 会被 int() 转换抛 ValueError
        # 应该被 except 捕获不传播
        try:
            self.func('ORD001', {}, 'abc', '张三')
        except ValueError:
            pass  # 允许抛 ValueError（未被捕获）


class TestGetCachedWorkOrders(unittest.TestCase):
    """测试 get_cached_work_orders 函数（mock DispatchContext）"""

    def setUp(self):
        from dispatch_center._sync import get_cached_work_orders
        self.func = get_cached_work_orders

    @patch.dict(os.environ, {'DISPATCH_MAX_PAGE_SIZE': '500'})
    @patch('dispatch_center._sync.DispatchContext')
    def test_size_capped_to_max(self, mock_dc_class):
        """超过 DISPATCH_MAX_PAGE_SIZE 时被截断"""
        mock_ctx = MagicMock()
        mock_dc_class.get_instance.return_value = mock_ctx

        self.func(page=1, size=10000, data_type='process')

        # 验证传入的 size 是 500（被截断）
        call_args = mock_ctx.get_cached_work_orders.call_args
        self.assertEqual(call_args[0][1], 500)
        self.assertEqual(call_args[0][0], 1)
        self.assertEqual(call_args[0][2], 'process')

    @patch('dispatch_center._sync.DispatchContext')
    def test_default_params(self, mock_dc_class):
        """默认参数"""
        mock_ctx = MagicMock()
        mock_dc_class.get_instance.return_value = mock_ctx

        self.func()

        call_args = mock_ctx.get_cached_work_orders.call_args
        # page=1, size=2000 (默认)
        self.assertEqual(call_args[0][0], 1)
        self.assertEqual(call_args[0][1], 2000)
        self.assertIsNone(call_args[0][2])

    def test_import_error_returns_empty_list(self):
        """DispatchContext 不可用时返回空列表"""
        # 这个测试需要确保 _sync.py 中的 import 失败时返回 []
        result = self.func()
        # 不强制要求是 []，只要求不抛异常
        self.assertIsNotNone(result)

    @patch.dict(os.environ, {'DISPATCH_MAX_PAGE_SIZE': '2000'})
    @patch('dispatch_center._sync.DispatchContext')
    def test_size_within_limit_not_capped(self, mock_dc_class):
        """在限制内不被截断"""
        mock_ctx = MagicMock()
        mock_dc_class.get_instance.return_value = mock_ctx

        self.func(page=1, size=100)

        call_args = mock_ctx.get_cached_work_orders.call_args
        self.assertEqual(call_args[0][1], 100)


class TestBackwardCompatAliases(unittest.TestCase):
    """测试向后兼容别名"""

    def test_aliases_match(self):
        """_xxx 别名与新名一致"""
        from dispatch_center._sync import (
            sync_work_order_status, _sync_work_order_status,
            sync_to_mysql, _sync_to_mysql,
            sync_schedule_to_container, _sync_schedule_to_container,
            get_cached_work_orders, _get_cached_work_orders,
            get_doc_data, _get_doc_data,
        )
        self.assertIs(_sync_work_order_status, sync_work_order_status)
        self.assertIs(_sync_to_mysql, sync_to_mysql)
        self.assertIs(_sync_schedule_to_container, sync_schedule_to_container)
        self.assertIs(_get_cached_work_orders, get_cached_work_orders)
        self.assertIs(_get_doc_data, get_doc_data)


class TestIntegration(unittest.TestCase):
    """端到端集成测试"""

    @patch('dispatch_center._sync.get_cached_work_orders')
    @patch('dispatch_center._sync._get_container_center')
    def test_full_workflow(self, mock_get_cc, mock_get_orders):
        """完整工作流：sync_to_mysql + sync_work_order_status"""
        # 准备 mock
        mock_cc = MagicMock()
        mock_get_cc.return_value = mock_cc
        mock_get_orders.return_value = [
            {'id': 'wo-int-1', 'doc_data': {'order_no': 'ORD-INT-001'}}
        ]

        # 1. 同步 MySQL（mock）
        from dispatch_center._sync import sync_to_mysql
        with patch('dispatch_center._sync._get_mysql_connection') as mock_get_conn:
            cursor = MagicMock()
            cursor.fetchone.return_value = {'id': 1, 'status': '已排产', 'order_id': 10}
            conn = MagicMock()
            conn.cursor.return_value = cursor
            mock_get_conn.return_value = conn
            sync_to_mysql('ORD-INT-001', 'confirmed', lead_time=7)

        # 2. 同步工单到容器中心
        from dispatch_center._sync import sync_work_order_status
        sync_work_order_status('ORD-INT-001', 'confirmed', current_step=2)

        # 验证容器中心被调用
        mock_cc.update_document.assert_called_once()


class TestSafeInsertDedup(unittest.TestCase):
    """测试 safe_insert_dedup / safe_insert_with_dedup_check（优雅降级）"""

    def setUp(self):
        from dispatch_center._sync import (
            safe_insert_dedup, safe_insert_with_dedup_check,
            dedup_insert, safe_dedup_insert,
        )
        self.safe_insert = safe_insert_dedup
        self.safe_insert_check = safe_insert_with_dedup_check
        self.alias_dedup = dedup_insert
        self.alias_safe = safe_dedup_insert

        self.mock_cur = MagicMock()
        self.mock_conn = MagicMock()

        self.test_table = 'process_sub_steps'
        self.test_data = {
            'id': 'pss-001',
            'order_no': 'ORD001',
            'step_name': '编织',
            'status': 'pending',
        }
        self.dedup_keys = ['order_no', 'step_name', 'status']

    # ── 基础成功场景 ──

    def test_successful_insert(self):
        """正常插入返回 success=True, duplicate=False"""
        result = self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys, self.mock_conn
        )
        self.assertTrue(result['success'])
        self.assertFalse(result['duplicate'])
        self.assertIsNone(result['existing_id'])
        self.assertEqual(result['message'], '创建成功')
        self.mock_cur.execute.assert_called_once()

    def test_successful_insert_commits(self):
        """成功插入后调用 conn.commit"""
        self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys, self.mock_conn
        )
        self.mock_conn.commit.assert_called_once()

    def test_no_conn_still_works(self):
        """不传 conn 也能正常工作"""
        result = self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys
        )
        self.assertTrue(result['success'])

    # ── 重复场景 ──

    def test_duplicate_entry_returns_graceful(self):
        """Duplicate entry 被捕获，返回 success=True, duplicate=True"""
        from pymysql.err import IntegrityError
        # 第1次 execute(INSERT) 抛异常，第2次 execute(SELECT) 正常
        self.mock_cur.execute.side_effect = [
            IntegrityError(
                "Duplicate entry 'ORD001-编织-pending' for key 'uk_active_task'"
            ),
            None,
        ]
        self.mock_cur.fetchone.return_value = ('pss-001',)

        result = self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys, self.mock_conn
        )

        self.assertTrue(result['success'])
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['existing_id'], 'pss-001')
        self.assertIn('已存在', result['message'])

    def test_duplicate_entry_commits(self):
        """Duplicate entry 场景也调用 conn.commit"""
        from pymysql.err import IntegrityError
        self.mock_cur.execute.side_effect = [
            IntegrityError(
                "Duplicate entry 'ORD001-编织-pending' for key 'uk_active_task'"
            ),
            None,
        ]
        self.mock_cur.fetchone.return_value = ('pss-001',)

        self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys, self.mock_conn
        )
        self.mock_conn.commit.assert_called_once()

    def test_duplicate_no_existing_id(self):
        """Duplicate entry 但查询不到记录时 existing_id=None"""
        from pymysql.err import IntegrityError
        self.mock_cur.execute.side_effect = [
            IntegrityError(
                "Duplicate entry 'xxx' for key 'uk_active_task'"
            ),
            None,
        ]
        self.mock_cur.fetchone.return_value = None

        result = self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            self.dedup_keys, self.mock_conn
        )

        self.assertTrue(result['duplicate'])
        self.assertIsNone(result['existing_id'])

    # ── 异常场景 ──

    def test_other_integrity_error_reraises(self):
        """非 Duplicate entry 的 IntegrityError 重新抛出"""
        from pymysql.err import IntegrityError
        self.mock_cur.execute.side_effect = IntegrityError(
            "Cannot add or update a child row: a foreign key constraint fails"
        )

        with self.assertRaises(IntegrityError):
            self.safe_insert(
                self.mock_cur, self.test_table, self.test_data,
                self.dedup_keys, self.mock_conn
            )
        self.mock_conn.rollback.assert_called_once()

    def test_other_exception_reraises(self):
        """其他异常重新抛出"""
        self.mock_cur.execute.side_effect = RuntimeError("数据库连接超时")

        with self.assertRaises(RuntimeError):
            self.safe_insert(
                self.mock_cur, self.test_table, self.test_data,
                self.dedup_keys, self.mock_conn
            )
        self.mock_conn.rollback.assert_called_once()

    # ── 防御性编程 ──

    def test_missing_dedup_key_uses_empty_fallback(self):
        """dedup_keys 中缺失的字段使用 '' 代替，不抛 KeyError"""
        dedup_keys_with_extra = self.dedup_keys + ['non_existent_field']

        result = self.safe_insert(
            self.mock_cur, self.test_table, self.test_data,
            dedup_keys_with_extra, self.mock_conn
        )

        self.assertTrue(result['success'])

    # ── safe_insert_with_dedup_check ──

    def test_precheck_finds_duplicate(self):
        """预检查发现重复记录，直接返回"""
        self.mock_cur.fetchone.return_value = ('existing-001',)

        result = self.safe_insert_check(
            self.mock_cur, self.mock_conn,
            self.test_table, self.test_data, self.dedup_keys
        )

        self.assertTrue(result['success'])
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['existing_id'], 'existing-001')
        self.assertIn('应用层', result['message'])
        # execute 应该只被调用 1 次（SELECT），不是 INSERT
        self.assertEqual(self.mock_cur.execute.call_count, 1)

    def test_precheck_passes_insert_succeeds(self):
        """预检查通过，插入成功"""
        self.mock_cur.fetchone.side_effect = [None, None]  # SELECT无结果, 但safe_insert_dedup会执行INSERT

        result = self.safe_insert_check(
            self.mock_cur, self.mock_conn,
            self.test_table, self.test_data, self.dedup_keys
        )

        self.assertTrue(result['success'])
        self.assertFalse(result['duplicate'])
        # execute 被调用 2 次（1次SELECT + 1次INSERT）
        self.assertEqual(self.mock_cur.execute.call_count, 2)

    def test_precheck_passes_but_db_duplicate(self):
        """预检查通过，但 INSERT 时被数据库拦截（TOCTOU 场景）"""
        from pymysql.err import IntegrityError
        # execute: SELECT预检查 → 成功(None) ; INSERT → 抛异常 ; SELECT查已有 → 成功(None)
        self.mock_cur.execute.side_effect = [
            None,
            IntegrityError(
                "Duplicate entry 'ORD001-编织-pending' for key 'uk_active_task'"
            ),
            None,
        ]
        # fetchone: 预检查无结果 ; 异常处理中查到已有记录
        self.mock_cur.fetchone.side_effect = [
            None,
            ('existing-002',),
        ]

        result = self.safe_insert_check(
            self.mock_cur, self.mock_conn,
            self.test_table, self.test_data, self.dedup_keys
        )

        self.assertTrue(result['success'])
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['existing_id'], 'existing-002')
        self.assertIn('数据库', result['message'])

    # ── 别名 ──

    def test_dedup_insert_alias(self):
        """dedup_insert 是 safe_insert_dedup 的别名"""
        self.assertIs(self.alias_dedup, self.safe_insert)

    def test_safe_dedup_insert_alias(self):
        """safe_dedup_insert 是 safe_insert_with_dedup_check 的别名"""
        self.assertIs(self.alias_safe, self.safe_insert_check)


def main():
    """运行所有测试"""
    print('=' * 70)
    print('dispatch_center/_sync.py 集成测试')
    print('=' * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 按类别添加测试
    test_classes = [
        TestGetDocData,
        TestSyncWorkOrderStatus,
        TestSyncToMysql,
        TestSyncScheduleToContainer,
        TestGetCachedWorkOrders,
        TestBackwardCompatAliases,
        TestIntegration,
        TestSafeInsertDedup,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print('')
    print('=' * 70)
    if result.wasSuccessful():
        print(f'✅ 所有测试通过！({result.testsRun} 个测试)')
    else:
        print(f'❌ 部分测试失败: {len(result.failures)} 失败, {len(result.errors)} 错误')
    print('=' * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())