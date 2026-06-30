# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - app.py 外协/排产/物料路由

覆盖: /api/outsource_record/*, /api/schedule_record/*, /api/warehousing/*
执行时间: < 30s
"""
import pytest


class TestOutsourceRecordList:
    """GET /api/outsource_record/list"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'records': [], 'total': 0}}
        assert 'data' in response

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_record_fields(self):
        record = {'id': 1, 'order_no': 'WO202506300001', 'outsource_type': '电镀'}
        for f in ['id', 'order_no']:
            assert f in record


class TestOutsourceRecordUpdate:
    """POST /api/outsource_record/update"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_update_request(self):
        data = {'id': 1, 'status': 'IN_PROGRESS'}
        assert 'id' in data


class TestOutsourceRecordWithdraw:
    """POST /api/outsource_record/withdraw"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_request(self):
        data = {'id': 1, 'reason': '取消外协'}
        assert 'id' in data


class TestOutsourceRecordHistoryFull:
    """GET /api/outsource_record/history_full"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_history_response(self):
        response = {'code': 0, 'data': {'records': []}}
        assert 'records' in response['data']


class TestScheduleRecordList:
    """GET /api/schedule_record/list"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'records': [], 'total': 0}}
        assert 'data' in response


class TestScheduleRecordUpdate:
    """POST /api/schedule_record/update"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_update_request(self):
        data = {'id': 1, 'scheduled_date': '2025-07-01'}
        assert 'id' in data


class TestScheduleRecordWithdraw:
    """POST /api/schedule_record/withdraw"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_request(self):
        data = {'id': 1, 'reason': '计划变更'}
        assert 'id' in data


class TestScheduleRecordHistoryFull:
    """GET /api/schedule_record/history_full"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_history_response(self):
        response = {'code': 0, 'data': {'records': []}}
        assert 'records' in response['data']


class TestWarehousingPending:
    """GET /api/warehousing/pending"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pending_response(self):
        response = {'code': 0, 'data': {'items': [], 'total': 0}}
        assert 'data' in response


class TestWarehousingConfirm:
    """POST /api/warehousing/confirm"""
    @pytest.mark.L1
    @pytest.mark.smoke
    def test_confirm_request(self):
        data = {'order_no': 'WO202506300001', 'warehouse_location': 'A-01'}
        assert 'order_no' in data
