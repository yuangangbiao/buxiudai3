# -*- coding: utf-8 -*-
"""
[v3.7.8] publisher.py DB 模式单元测试

覆盖:
- _store_task_production INSERT (DB 模式)
- _store_task 双轨 + DB fallback 内存
- get_all_tasks / get_task_by_id / get_task_count (DB 模式)
- TaskRecallPublisher.recall (DB 模式)
- DB 错误 → 内存 fallback + ERROR 日志
- 内存模式回归 (USE_DB=False 默认行为)

策略:
- 直接 importlib 加载 publisher.py 模块（绕开 __init__.py pre-existing 问题）
- @patch.object(_fake_db_compat, 'get_conn') mock 整个连接入口
- 切换 _USE_DB 标志位控制路径
- tearDown 恢复 _USE_DB=False 避免污染其他测试
"""
import json
import os
import sys
import types
import importlib.util
from unittest.mock import MagicMock, patch

import pytest


# ============ fake core.db_compat 注入 ============
# 真实 core.db_compat 触发 core.config → core._config_domain → utils.data_type_contract
# 导入链预先存在 ImportError。本测试只关心 mock get_conn 行为，
# 用 sys.modules 注入 fake 模块跳过完整导入链。
# [v3.8.1] 命名加 publisher_v378 前缀避免与其他 fake_core_* 测试冲突
_fake_db_compat = types.ModuleType('publisher_v378_fake_db_compat')
_fake_db_compat.get_conn = MagicMock()
sys.modules['core.db_compat'] = _fake_db_compat
_fake_core = types.ModuleType('publisher_v378_fake_core')
_fake_core.db_compat = _fake_db_compat
sys.modules['core'] = _fake_core


# ============ 模块加载工具 ============

def _load_publisher():
    """直接加载 publisher.py 模块"""
    if 'publisher_v378' in sys.modules:
        return sys.modules['publisher_v378']
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'mobile_api_ai', 'dispatch_center', 'publisher.py'
    )
    spec = importlib.util.spec_from_file_location("publisher_v378", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pub():
    """加载 publisher 模块（function scope，每个测试独立）"""
    return _load_publisher()


@pytest.fixture
def mock_shim():
    """Mock DB 连接 shim: with get_conn() as (conn, cur) -> (mock_conn, mock_cur)"""
    mock_cur = MagicMock()
    mock_conn = MagicMock()
    shim = MagicMock()
    shim.__enter__ = MagicMock(return_value=(mock_conn, mock_cur))
    shim.__exit__ = MagicMock(return_value=False)
    return shim, mock_conn, mock_cur


# ============ DB 模式: _store_task_production ============

class TestDbModeStorage:
    """DB 模式存储路径测试"""

    def test_store_production_insert_sql(self, pub, mock_shim):
        """INSERT SQL 正确性"""
        shim, mock_conn, mock_cur = mock_shim
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                pub._store_task_production(
                    'task-001', 'report',
                    {'order_no': 'WO-001', 'process_name': '拉丝'}
                )
            mock_cur.execute.assert_called_once()
            sql, params = mock_cur.execute.call_args[0]
            assert 'INSERT INTO dispatch_center_tasks' in sql
            assert 'ON DUPLICATE KEY UPDATE' in sql
            assert 'type=VALUES(type)' in sql
            assert params[0] == 'task-001'
            assert params[1] == 'report'
            assert json.loads(params[2]) == {
                'order_no': 'WO-001', 'process_name': '拉丝'
            }
        finally:
            pub._USE_DB = False

    def test_store_production_chinese_payload(self, pub, mock_shim):
        """中文 payload 正确序列化（ensure_ascii=False）"""
        shim, mock_conn, mock_cur = mock_shim
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                pub._store_task_production(
                    'task-cn', 'report',
                    {'customer_name': '张三不锈钢有限公司', 'note': '加急'}
                )
            params = mock_cur.execute.call_args[0][1]
            assert '张三不锈钢有限公司' in params[2]
            assert params[2].startswith('{')  # 不是 unicode escape
        finally:
            pub._USE_DB = False

    def test_store_task_dual_rail_db_first(self, pub, mock_shim):
        """_store_task 双轨: USE_DB=True 优先 DB 路径"""
        shim, mock_conn, mock_cur = mock_shim
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                pub._store_task('dual-001', 'material', {'order_no': 'WO-X'})
            mock_cur.execute.assert_called_once()
            assert 'dual-001' not in pub._task_store
        finally:
            pub._USE_DB = False

    def test_store_task_dual_rail_memory_default(self, pub):
        """_store_task 内存模式（USE_DB=False 默认）"""
        pub._USE_DB = False
        pub._store_task('mem-001', 'report', {'order_no': 'WO-M'})
        assert 'mem-001' in pub._task_store
        assert pub._task_store['mem-001']['type'] == 'report'


# ============ DB 模式: 查询方法 ============

class TestDbModeQuery:
    """DB 模式查询路径测试"""

    def _build_select_rows(self):
        """构造 SELECT 模拟返回行"""
        from datetime import datetime
        return [
            ('task-001', 'report', '{"order_no":"WO-001"}', datetime(2026, 6, 25, 10, 0), datetime(2026, 6, 25, 10, 5)),
            ('task-002', 'material', '{"order_no":"WO-002"}', datetime(2026, 6, 25, 11, 0), datetime(2026, 6, 25, 11, 5)),
        ]

    def test_get_all_tasks_db(self, pub, mock_shim):
        """get_all_tasks DB 路径: 返回列表 + payload JSON 反序列化"""
        shim, mock_conn, mock_cur = mock_shim
        mock_cur.fetchall.return_value = self._build_select_rows()
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                result = pub.get_all_tasks()
            assert len(result) == 2
            assert result[0]['id'] == 'task-001'
            assert result[0]['type'] == 'report'
            assert result[0]['payload'] == {'order_no': 'WO-001'}
            assert result[0]['created_at'] == '2026-06-25T10:00:00'
            mock_cur.execute.assert_called_once()
            assert 'ORDER BY created_at DESC' in mock_cur.execute.call_args[0][0]
        finally:
            pub._USE_DB = False

    def test_get_task_by_id_db_found(self, pub, mock_shim):
        """get_task_by_id DB 路径: 命中"""
        shim, mock_conn, mock_cur = mock_shim
        from datetime import datetime
        mock_cur.fetchone.return_value = (
            'task-001', 'report', '{"order_no":"WO-001"}',
            datetime(2026, 6, 25), datetime(2026, 6, 25)
        )
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                result = pub.get_task_by_id('task-001')
            assert result is not None
            assert result['id'] == 'task-001'
            assert result['payload'] == {'order_no': 'WO-001'}
            assert 'WHERE id=%s' in mock_cur.execute.call_args[0][0]
        finally:
            pub._USE_DB = False

    def test_get_task_by_id_db_not_found(self, pub, mock_shim):
        """get_task_by_id DB 路径: 未命中"""
        shim, mock_conn, mock_cur = mock_shim
        mock_cur.fetchone.return_value = None
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                result = pub.get_task_by_id('nonexistent')
            assert result is None
        finally:
            pub._USE_DB = False

    def test_get_task_count_db(self, pub, mock_shim):
        """get_task_count DB 路径: COUNT + GROUP BY"""
        shim, mock_conn, mock_cur = mock_shim
        mock_cur.fetchone.return_value = (5,)
        mock_cur.fetchall.return_value = [('report', 3), ('material', 2)]
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                result = pub.get_task_count()
            assert result == {'total': 5, 'report': 3, 'material': 2}
            sqls = [c[0][0] for c in mock_cur.execute.call_args_list]
            assert any('COUNT(*) FROM dispatch_center_tasks' in s for s in sqls)
            assert any('GROUP BY type' in s for s in sqls)
        finally:
            pub._USE_DB = False


# ============ DB 模式: 撤回 ============

class TestDbModeRecall:
    """TaskRecallPublisher DB 模式"""

    def test_recall_db_hit(self, pub, mock_shim):
        """DB 撤回: rowcount > 0 返回 True"""
        shim, mock_conn, mock_cur = mock_shim
        mock_cur.rowcount = 1
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                p = pub.get_publisher('task_recall')
                result = p.recall('task-001')
            assert result is True
            assert 'DELETE FROM dispatch_center_tasks' in mock_cur.execute.call_args[0][0]
        finally:
            pub._USE_DB = False

    def test_recall_db_miss_then_memory(self, pub, mock_shim):
        """DB 撤回: rowcount=0 后 fallback 内存命中"""
        shim, mock_conn, mock_cur = mock_shim
        mock_cur.rowcount = 0
        pub._USE_DB = True
        pub._task_store['mem-only'] = {'id': 'mem-only', 'type': 'report', 'payload': {}}
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                p = pub.get_publisher('task_recall')
                result = p.recall('mem-only')
            assert result is True
            assert 'mem-only' not in pub._task_store
        finally:
            pub._USE_DB = False


# ============ Fallback 行为 ============

class TestDbFallback:
    """DB 错误时 fallback 内存 + ERROR 日志"""

    def test_store_task_fallback_on_db_error(self, pub):
        """DB 写失败 → 内存 fallback + 业务不中断"""
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', side_effect=Exception('connection refused')):
                pub._store_task('fail-001', 'report', {'order_no': 'WO-F'})
            assert 'fail-001' in pub._task_store
            assert pub._task_store['fail-001']['type'] == 'report'
        finally:
            pub._USE_DB = False

    def test_get_all_tasks_fallback_on_db_error(self, pub):
        """DB 查询失败 → 内存 fallback 返回当前内存数据"""
        pub._USE_DB = False
        pub._store_task('mem-A', 'report', {'order_no': 'WO-A'})
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', side_effect=Exception('timeout')):
                result = pub.get_all_tasks()
            assert any(t['id'] == 'mem-A' for t in result)
        finally:
            pub._USE_DB = False

    def test_get_task_count_fallback_on_db_error(self, pub):
        """DB 统计失败 → 内存 fallback"""
        pub._USE_DB = False
        pub._store_task('c-1', 'report', {})
        pub._store_task('c-2', 'material', {})
        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', side_effect=Exception('boom')):
                result = pub.get_task_count()
            assert result['total'] == 2
            assert result['report'] == 1
            assert result['material'] == 1
        finally:
            pub._USE_DB = False


# ============ 内存模式回归（保护旧测试）============

class TestMemoryModeRegression:
    """DISPATCH_CENTER_USE_DB 未设置时所有功能照旧"""

    def test_default_use_db_is_false(self, pub):
        """默认 USE_DB=False（保护单元测试）"""
        assert pub._USE_DB is False

    def test_publish_report_task_works_in_memory_mode(self, pub):
        """publish_report_task 兼容层 + 内存存储"""
        p = pub.get_publisher('report')
        result = p.publish_report_task(
            order_no='WO-REG-001',
            process_name='拉丝',
            customer_name='客户A',
            quantity=100
        )
        assert result == 'WO-REG-001'
        assert 'WO-REG-001' in pub._task_store
        assert pub._task_store['WO-REG-001']['type'] == 'report'

    def test_publish_material_task_works_in_memory_mode(self, pub):
        """publish_material_task 兼容层 + 内存存储"""
        p = pub.get_publisher('material')
        result = p.publish_material_task(
            order_no='WO-MAT-001',
            materials=[{'name': '钢丝', 'qty': 50}]
        )
        assert result == 'WO-MAT-001'
        assert 'WO-MAT-001' in pub._task_store

    def test_publish_quality_task_works_in_memory_mode(self, pub):
        """publish_quality_task 兼容层 + 内存存储"""
        p = pub.get_publisher('quality')
        result = p.publish_quality_task(
            order_no='WO-Q-001',
            customer_name='客户B'
        )
        assert result == 'WO-Q-001'
        assert 'WO-Q-001' in pub._task_store

    def test_get_task_count_memory_mode(self, pub):
        """内存模式 get_task_count"""
        pub._store_task('m1', 'report', {})
        pub._store_task('m2', 'material', {})
        pub._store_task('m3', 'report', {})
        result = pub.get_task_count()
        assert result == {'total': 3, 'report': 2, 'material': 1}

    def test_recall_memory_mode(self, pub):
        """内存模式撤回"""
        pub._store_task('rec-001', 'report', {})
        p = pub.get_publisher('task_recall')
        result = p.recall('rec-001')
        assert result is True
        assert 'rec-001' not in pub._task_store


# ============ DB 模式下 publisher 完整链路 ============

class TestPublisherFullFlowDb:
    """publish → store → recall → query 完整链路（DB 模式）"""

    def test_full_flow_db(self, pub, mock_shim):
        """ReportPublisher.publish → DB INSERT → DB SELECT → DB DELETE"""
        shim, mock_conn, mock_cur = mock_shim
        from datetime import datetime

        pub._USE_DB = True
        try:
            with patch.object(_fake_db_compat, 'get_conn', return_value=shim):
                # 1) publish report
                p = pub.get_publisher('report')
                ok = p.publish({'order_no': 'FLOW-001', 'process_name': '焊接'})
                assert ok is True
                mock_cur.execute.assert_called_once()
                assert 'INSERT INTO' in mock_cur.execute.call_args[0][0]

                # 2) query - reset mock for SELECT
                mock_cur.reset_mock()
                mock_cur.fetchone.return_value = (
                    'FLOW-001', 'report', '{"order_no":"FLOW-001","process_name":"焊接"}',
                    datetime(2026, 6, 25), datetime(2026, 6, 25)
                )
                task = pub.get_task_by_id('FLOW-001')
                assert task is not None
                assert task['payload']['process_name'] == '焊接'

                # 3) recall
                mock_cur.reset_mock()
                mock_cur.rowcount = 1
                recall_p = pub.get_publisher('task_recall')
                assert recall_p.recall('FLOW-001') is True
                assert 'DELETE FROM dispatch_center_tasks' in mock_cur.execute.call_args[0][0]
        finally:
            pub._USE_DB = False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
