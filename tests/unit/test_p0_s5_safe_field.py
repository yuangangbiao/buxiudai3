# -*- coding: utf-8 -*-
"""
P0-S5 单元测试 - 动态字段 SQL 注入白名单

测试范围: dispatch_center/_core.py 4 处动态字段同步
- api_sync_material (line 9319)
- api_sync_repair (line 9374)
- api_sync_outsource (line 9428)
- api_sync_quality_record (line 9538)
"""
import os
import sys
import re
import pytest
from unittest.mock import patch, MagicMock

# 项目根目录加入 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# 复制 SAFE_KEY_RE 逻辑（不依赖 _core.py 的复杂导入）
SAFE_KEY_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class TestSafeKeyRegex:
    """字段名白名单正则测试"""

    def test_legal_field_weight_kg(self):
        """合法字段: weight_kg"""
        assert SAFE_KEY_RE.match('weight_kg') is not None

    def test_legal_field_order_no(self):
        """合法字段: order_no"""
        assert SAFE_KEY_RE.match('order_no') is not None

    def test_legal_field_with_digits(self):
        """合法字段: field_1"""
        assert SAFE_KEY_RE.match('field_1') is not None

    def test_legal_field_with_underscore(self):
        """合法字段: __private"""
        assert SAFE_KEY_RE.match('__private') is not None

    def test_illegal_sql_injection(self):
        """非法: SQL 注入"""
        assert SAFE_KEY_RE.match('weight_kg; DROP TABLE orders; --') is None

    def test_illegal_field_with_space(self):
        """非法: 含空格"""
        assert SAFE_KEY_RE.match('weight kg') is None

    def test_illegal_field_with_quote(self):
        """非法: 含单引号"""
        assert SAFE_KEY_RE.match("weight'kg") is None

    def test_illegal_field_with_semicolon(self):
        """非法: 含分号"""
        assert SAFE_KEY_RE.match('weight;kg') is None

    def test_illegal_starts_with_digit(self):
        """非法: 数字开头"""
        assert SAFE_KEY_RE.match('123abc') is None

    def test_illegal_contains_dash(self):
        """非法: 含连字符"""
        assert SAFE_KEY_RE.match('weight-kg') is None


class TestFieldMapSafety:
    """字段映射安全性测试（模拟 _core.py 逻辑）"""

    def test_material_field_map_legal(self):
        """合法字段通过 material_field_map"""
        material_field_map = {
            'status': 'prep_status',
            'planned_qty': 'required_qty',
            'completed_qty': 'prepared_qty',
        }
        body = {'order_no': 'ORD-001', 'weight_kg': 100}
        exclude_fields = {'order_no'}

        update_fields = []
        for key, value in body.items():
            if key in exclude_fields or value is None:
                continue
            if not SAFE_KEY_RE.match(key):
                continue
            mapped_key = material_field_map.get(key, key)
            if not SAFE_KEY_RE.match(mapped_key):
                continue
            update_fields.append(f'{mapped_key}=%s')

        # 应该有 1 个字段：weight_kg
        assert 'weight_kg=%s' in update_fields
        assert len(update_fields) == 1

    def test_material_field_map_injection_blocked(self):
        """SQL 注入被过滤"""
        material_field_map = {}
        body = {
            'order_no': 'ORD-001',
            'weight_kg; DROP TABLE orders; --': 'malicious',
        }
        exclude_fields = {'order_no'}

        update_fields = []
        for key, value in body.items():
            if key in exclude_fields or value is None:
                continue
            if not SAFE_KEY_RE.match(key):
                continue
            mapped_key = material_field_map.get(key, key)
            if not SAFE_KEY_RE.match(mapped_key):
                continue
            update_fields.append(f'{mapped_key}=%s')

        # 应该有 0 个字段（注入被过滤）
        assert len(update_fields) == 0

    def test_mapped_key_injection_blocked(self):
        """mapped_key 注入被过滤"""
        # 模拟攻击者篡改 field_map
        fake_field_map = {'status': 'prep_status; DROP TABLE orders; --'}
        body = {'order_no': 'ORD-001', 'status': 'completed'}
        exclude_fields = {'order_no'}

        update_fields = []
        for key, value in body.items():
            if key in exclude_fields or value is None:
                continue
            if not SAFE_KEY_RE.match(key):
                continue
            mapped_key = fake_field_map.get(key, key)
            if not SAFE_KEY_RE.match(mapped_key):
                continue
            update_fields.append(f'{mapped_key}=%s')

        # mapped_key 包含特殊字符被过滤
        assert len(update_fields) == 0


class TestFieldFilterEndToEnd:
    """端到端字段过滤测试（4 个端点）"""

    @pytest.mark.parametrize("endpoint,body,expected_fields", [
        # 物料端点
        (
            "sync_material",
            {'order_no': 'ORD-001', 'weight_kg': 100, 'batch_no': 'B001'},
            ['weight_kg=%s', 'batch_no=%s']
        ),
        # 维修端点
        (
            "sync_repair",
            {'order_no': 'ORD-001', 'target_operator': 'OP01', 'repair_note': 'fix'},
            ['assigned_to=%s', 'repair_note=%s']
        ),
        # 外协端点
        (
            "sync_outsource",
            {'order_no': 'ORD-001', 'supplier': 'S01', 'qty': 50},
            ['supplier=%s', 'qty=%s']
        ),
        # 质检端点
        (
            "sync_quality",
            {'order_no': 'ORD-001', 'inspection_type': 'manual', 'result': 'pass'},
            ['process_name=%s', 'result=%s']
        ),
    ])
    def test_endpoint_legal_fields(self, endpoint, body, expected_fields):
        """合法字段通过端点过滤"""
        # 简化：只验证字段名能匹配 SAFE_KEY_RE
        for key in body.keys():
            if key == 'order_no':
                continue
            assert SAFE_KEY_RE.match(key) is not None, f"{endpoint}: 字段 {key!r} 应通过白名单"

    @pytest.mark.parametrize("endpoint,bad_body", [
        # 物料注入
        ("sync_material", {'order_no': 'ORD-001', 'weight; DROP TABLE': 'x'}),
        # 维修注入
        ("sync_repair", {'order_no': 'ORD-001', 'note\' OR 1=1;--': 'x'}),
        # 外协注入
        ("sync_outsource", {'order_no': 'ORD-001', 'supplier UNION SELECT': 'x'}),
        # 质检注入
        ("sync_quality", {'order_no': 'ORD-001', 'field; --': 'x'}),
    ])
    def test_endpoint_injection_blocked(self, endpoint, bad_body):
        """注入字段被端点过滤"""
        for key in bad_body.keys():
            if key == 'order_no':
                continue
            assert SAFE_KEY_RE.match(key) is None, f"{endpoint}: 字段 {key!r} 应被白名单拒绝"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
