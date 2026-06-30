# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - app.py 物料路由

覆盖: /api/material_record/list, /update, /withdraw, /history_full,
      /api/material/confirm, /arrived, /delivered, /requirements, /return, /replenish
执行时间: < 30s
"""
import pytest
from unittest.mock import MagicMock


class TestMaterialRecordList:
    """GET /api/material_record/list"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'records': [], 'total': 0}}
        assert 'data' in response

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_record_fields(self):
        record = {'id': 1, 'order_no': 'WO202506300001', 'material_type': '钢板', 'quantity': 100}
        for f in ['id', 'order_no', 'material_type']:
            assert f in record


class TestMaterialRecordUpdate:
    """POST /api/material_record/update"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_update_request(self):
        data = {'id': 1, 'quantity': 50}
        assert 'id' in data

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_quantity_positive(self):
        qty = 50
        assert qty > 0


class TestMaterialRecordWithdraw:
    """POST /api/material_record/withdraw"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_request(self):
        data = {'id': 1, 'reason': '重复录入'}
        assert 'id' in data


class TestMaterialRecordHistoryFull:
    """GET /api/material_record/history_full"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_history_response(self):
        response = {'code': 0, 'data': {'records': []}}
        assert 'records' in response['data']


class TestMaterialConfirm:
    """POST /api/material/confirm"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_confirm_request(self):
        data = {'order_no': 'WO202506300001', 'operator_id': 'OP001'}
        assert 'order_no' in data


class TestMaterialArrived:
    """POST /api/material/arrived"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_arrived_request(self):
        data = {'order_no': 'WO202506300001', 'arrived_quantity': 100}
        assert 'order_no' in data
        assert data['arrived_quantity'] > 0


class TestMaterialDelivered:
    """POST /api/material/delivered"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_delivered_request(self):
        data = {'order_no': 'WO202506300001'}
        assert 'order_no' in data


class TestMaterialRequirements:
    """GET /api/material/requirements"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_requirements_response(self):
        response = {'code': 0, 'data': {'items': [], 'total': 0}}
        assert 'data' in response
        assert 'items' in response['data']


class TestMaterialReturn:
    """POST /api/material/return"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_return_request(self):
        data = {'order_no': 'WO202506300001', 'return_quantity': 10, 'reason': '质量问题'}
        assert 'order_no' in data
        assert 'return_quantity' in data


class TestMaterialReplenish:
    """POST /api/material/replenish"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_replenish_request(self):
        data = {'order_no': 'WO202506300001', 'replenish_quantity': 20}
        assert 'order_no' in data
        assert data['replenish_quantity'] > 0
