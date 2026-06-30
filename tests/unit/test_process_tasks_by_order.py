# -*- coding: utf-8 -*-
"""
test_process_tasks_by_order.py
按订单显示合并工序任务 API 单元测试

覆盖 T3 验收标准 AC1-AC10
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import patch, MagicMock


class TestMergeSubSteps:
    """_merge_sub_steps 合并逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        """通过 Flask test_client 测试 API"""
        import os as _os
        _os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        # 清除缓存模块
        for _key in list(sys.modules.keys()):
            if _key.startswith('mobile_api_ai') or _key == 'app':
                sys.modules.pop(_key, None)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'mobile_api_ai'))
        from app import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        yield
        for _key in list(sys.modules.keys()):
            if _key.startswith('mobile_api_ai') or _key == 'app':
                sys.modules.pop(_key, None)

    def _mock_get_sub_steps(self, order_no, sub_steps):
        """Mock ContainerCenter.get_sub_steps"""
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_instance = MagicMock()
            mock_instance.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_instance
            return MockCC

    # -------------------------------------------------------------------------
    # T3-AC1: 同工序 2 条不同 operator → 合并 1 行，operators 有 2 人
    # -------------------------------------------------------------------------
    def test_merge_two_different_operators(self, setup_app):
        """同工序有 2 条不同 operator → 合并为 1 行，operators 数组有 2 人"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 9},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '李四', 'quantity': 8, 'qualified_qty': 8},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        assert data['code'] == 0
        processes = data['data']['processes']
        assert len(processes) == 1
        assert processes[0]['step_name'] == '焊接'
        assert processes[0]['process_code'] == 'WELD'
        names = [op['name'] for op in processes[0]['operators']]
        assert '张三' in names
        assert '李四' in names
        assert processes[0]['operators_str'] == '张三,李四'  # sorted by Unicode
        assert processes[0]['total_qty'] == 18.0
        assert processes[0]['qualified_qty'] == 17.0
        assert processes[0]['record_count'] == 2

    # -------------------------------------------------------------------------
    # T3-AC2: 同工序 2 条相同 operator → operators 只有 1 人（去重）
    # -------------------------------------------------------------------------
    def test_merge_same_operator_dedup(self, setup_app):
        """同 operator 重复报工 → 去重，operators 数组只有 1 人，数量累加"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 9},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        assert data['code'] == 0
        processes = data['data']['processes']
        assert len(processes) == 1
        assert len(processes[0]['operators']) == 1
        assert processes[0]['operators'][0]['name'] == '张三'
        assert processes[0]['operators'][0]['qty'] == 15.0   # 累加
        assert processes[0]['operators'][0]['qualified_qty'] == 14.0  # 累加
        assert processes[0]['total_qty'] == 15.0
        assert processes[0]['record_count'] == 2

    # -------------------------------------------------------------------------
    # T3-AC3: 不同 process_code 同一 step_name → 分属 2 个组
    # -------------------------------------------------------------------------
    def test_different_process_code_separate_groups(self, setup_app):
        """不同 process_code 同一 step_name → 分属不同组，不合并"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 10},
            {'step_name': '焊接', 'process_code': 'LASER', 'operator': '李四', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        assert data['code'] == 0
        processes = data['data']['processes']
        assert len(processes) == 2
        codes = {p['process_code'] for p in processes}
        assert 'WELD' in codes
        assert 'LASER' in codes

    # -------------------------------------------------------------------------
    # T3-AC4: 空 sub_steps → 返回空 processes[]
    # -------------------------------------------------------------------------
    def test_empty_sub_steps(self, setup_app):
        """空 sub_steps → 返回空 processes[]"""
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = []
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-EMPTY')
            data = resp.get_json()

        assert data['code'] == 0
        assert data['data']['processes'] == []

    # -------------------------------------------------------------------------
    # T3-AC5: process_code 为空字符串 → 走 '' 分组
    # -------------------------------------------------------------------------
    def test_empty_process_code_grouping(self, setup_app):
        """process_code 为空 → 按空字符串分组，不与其他 process_code 合并"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': '', 'operator': '张三', 'quantity': 10, 'qualified_qty': 10},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '李四', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        processes = data['data']['processes']
        assert len(processes) == 2
        codes = {p['process_code'] for p in processes}
        assert '' in codes
        assert 'WELD' in codes

    # -------------------------------------------------------------------------
    # T3-AC6: total_qty / qualified_qty 正确累加
    # -------------------------------------------------------------------------
    def test_qty_accumulation(self, setup_app):
        """多 operator 多条记录 → total_qty/qualified_qty 正确代数累加"""
        sub_steps = [
            {'step_name': '冲压', 'process_code': 'STAMP', 'operator': '张三', 'quantity': 10, 'qualified_qty': 9},
            {'step_name': '冲压', 'process_code': 'STAMP', 'operator': '李四', 'quantity': 8, 'qualified_qty': 7},
            {'step_name': '冲压', 'process_code': 'STAMP', 'operator': '王五', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        p = data['data']['processes'][0]
        assert p['total_qty'] == 23.0      # 10+8+5
        assert p['qualified_qty'] == 21.0   # 9+7+5
        assert p['record_count'] == 3

    # -------------------------------------------------------------------------
    # T3-AC7: record_count 正确计数
    # -------------------------------------------------------------------------
    def test_record_count(self, setup_app):
        """record_count = 原始 sub_steps 行数"""
        sub_steps = [
            {'step_name': '切割', 'process_code': 'CUT', 'operator': '张三', 'quantity': 10, 'qualified_qty': 10},
            {'step_name': '切割', 'process_code': 'CUT', 'operator': '李四', 'quantity': 5, 'qualified_qty': 5},
            {'step_name': '切割', 'process_code': 'CUT', 'operator': '王五', 'quantity': 3, 'qualified_qty': 3},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        assert data['data']['processes'][0]['record_count'] == 3

    # -------------------------------------------------------------------------
    # T3-AC8: status 非空（走真值源）
    # -------------------------------------------------------------------------
    def test_status_not_empty(self, setup_app):
        """status 字段非空（done/doing/wait 之一）"""
        sub_steps = [
            {'step_name': '打磨', 'process_code': 'POLISH', 'operator': '张三', 'quantity': 100, 'qualified_qty': 100},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        status = data['data']['processes'][0]['status']
        assert status in ('done', 'doing', 'wait'), f"status 应为 done/doing/wait，实际: {status}"

    # -------------------------------------------------------------------------
    # T3-AC9: order_no 大写归一化
    # -------------------------------------------------------------------------
    def test_order_no_uppercase(self, setup_app):
        """order_no 自动转大写"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 10},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ord-001')
            data = resp.get_json()

        assert data['data']['order_no'] == 'ORD-001'

    # -------------------------------------------------------------------------
    # T3-AC10: operators 中同名人只出现一次（追加去重）
    # -------------------------------------------------------------------------
    def test_operator_dedup_multiple_occurrences(self, setup_app):
        """同一 operator 出现 3 次 → 最终只出现在 operators 数组 1 次，数量累加"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 9},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 8, 'qualified_qty': 8},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        ops = data['data']['processes'][0]['operators']
        assert len(ops) == 1
        assert ops[0]['name'] == '张三'
        assert ops[0]['qty'] == 23.0      # 10+8+5
        assert ops[0]['qualified_qty'] == 22.0  # 9+8+5
        assert data['data']['processes'][0]['record_count'] == 3
        assert data['data']['processes'][0]['operators_str'] == '张三'

    # -------------------------------------------------------------------------
    # 边界: operator 为空字符串 → 跳过，不追加
    # -------------------------------------------------------------------------
    def test_empty_operator_skipped(self, setup_app):
        """operator 为空 → 跳过，operators 数组不含空字符串"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': 10, 'qualified_qty': 10},
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '', 'quantity': 5, 'qualified_qty': 5},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        ops = data['data']['processes'][0]['operators']
        names = [op['name'] for op in ops]
        assert '' not in names
        assert '张三' in names
        assert data['data']['processes'][0]['total_qty'] == 10.0  # 空 operator 的数量也累加（逻辑与写入侧一致）
        assert data['data']['processes'][0]['record_count'] == 2

    # -------------------------------------------------------------------------
    # 边界: quantity/qualified_qty 为 None → 当 0 处理
    # -------------------------------------------------------------------------
    def test_null_quantity_handled(self, setup_app):
        """quantity/qualified_qty 为 None → 当 0 处理，不崩溃"""
        sub_steps = [
            {'step_name': '焊接', 'process_code': 'WELD', 'operator': '张三', 'quantity': None, 'qualified_qty': None},
        ]
        with patch('container_center_v5.ContainerCenter') as MockCC:
            mock_cc = MagicMock()
            mock_cc.get_sub_steps.return_value = sub_steps
            MockCC.return_value = mock_cc

            resp = self.client.get('/api/process-tasks/by-order/ORD-001')
            data = resp.get_json()

        assert data['code'] == 0
        assert data['data']['processes'][0]['total_qty'] == 0.0
        assert data['data']['processes'][0]['qualified_qty'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
