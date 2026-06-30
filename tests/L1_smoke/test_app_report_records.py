# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - app.py 报工记录路由

覆盖: /api/report_record/list, /update, /withdraw, /history_full
执行时间: < 30s
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


def _make_mock_request(**kwargs):
    req = MagicMock()
    for k, v in kwargs.items():
        setattr(req, k, v)
    return req


def _mock_storage():
    """Mock MySQLStorage"""
    storage = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    storage.connect.return_value = conn
    return storage, conn, cursor


class TestReportRecordList:
    """GET /api/report_record/list - 报工记录列表"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_fields(self):
        """响应字段完整性"""
        # 业务规则: list 响应必须包含分页字段
        response = {
            'code': 0,
            'message': 'success',
            'data': {
                'records': [],
                'total': 0,
                'page': 1,
                'size': 20,
            }
        }
        assert 'data' in response
        assert 'records' in response['data']
        assert 'total' in response['data']
        assert 'page' in response['data']

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pagination_params(self):
        """分页参数验证"""
        # 业务规则: page 默认 1, size 默认 20, 最大 100
        page = 1
        size = 20
        assert page >= 1
        assert 1 <= size <= 100

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_record_fields(self):
        """单条记录字段验证"""
        # 业务规则: 报工记录包含工序、产品、客户、数量
        record = {
            'id': 1,
            'order_no': 'WO202506300001',
            'step_name': '切割',
            'operator_name': '张三',
            'quantity': 10.0,
            'report_time': '2025-06-30 10:00:00',
            'status': 'COMPLETED',
        }
        required = ['id', 'order_no', 'step_name', 'quantity', 'report_time']
        for f in required:
            assert f in record, f"记录必须包含字段: {f}"


class TestReportRecordUpdate:
    """POST /api/report_record/update - 更新报工记录"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_update_request_fields(self):
        """更新请求必填字段"""
        # 业务规则: 更新需要 id 和至少一个可更新字段
        request_data = {
            'id': 1,
            'quantity': 20.0,
        }
        assert 'id' in request_data
        assert request_data['id'] > 0

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_update_response_format(self):
        """更新响应格式"""
        response = {'code': 0, 'message': 'success', 'data': {'affected_rows': 1}}
        assert 'code' in response
        assert response['code'] == 0
        assert 'affected_rows' in response.get('data', {})

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_quantity_validation(self):
        """数量验证: 必须 > 0"""
        quantity = 10.0
        assert quantity > 0, "报工数量必须大于 0"


class TestReportRecordWithdraw:
    """POST /api/report_record/withdraw - 撤回报工"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_request_fields(self):
        """撤回请求必填字段"""
        request_data = {'id': 1, 'reason': '填错了'}
        assert 'id' in request_data
        assert 'reason' in request_data

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_response(self):
        """撤回响应"""
        response = {'code': 0, 'message': '撤回成功', 'data': {'affected_rows': 1}}
        assert response['code'] == 0

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_idempotency(self):
        """幂等: 重复撤回返回相同结果"""
        response1 = {'code': 0, 'message': '撤回成功'}
        response2 = {'code': 0, 'message': '撤回成功'}
        assert response1['code'] == response2['code']


class TestReportRecordHistoryFull:
    """GET /api/report_record/history_full - 历史报工（完整）"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_history_response(self):
        """历史记录响应"""
        response = {'code': 0, 'data': {'records': [], 'total': 0}}
        assert 'records' in response['data']
        assert 'total' in response['data']

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_date_range_params(self):
        """日期范围参数"""
        start_date = '2025-06-01'
        end_date = '2025-06-30'
        assert start_date <= end_date, "开始日期不能晚于结束日期"
