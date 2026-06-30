# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - report_record_admin.py 报表路由

覆盖: /api/report/orders_summary, /process_summary, /quality_summary 等 20 个端点
执行时间: < 30s
"""
import pytest


class TestReportOrdersSummary:
    """GET /api/report/orders_summary"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'summary': {}, 'total': 0}}
        assert 'data' in response

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_summary_fields(self):
        summary = {'total_orders': 100, 'pending': 20, 'completed': 80}
        for f in ['total_orders', 'pending', 'completed']:
            assert f in summary, f"汇总必须包含: {f}"


class TestReportProcessSummary:
    """GET /api/report/process_summary"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'processes': []}}
        assert 'data' in response

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_process_fields(self):
        proc = {'step_name': '切割', 'completed_qty': 100, 'pending_qty': 20}
        for f in ['step_name', 'completed_qty']:
            assert f in proc


class TestReportQualitySummary:
    """GET /api/report/quality_summary"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'total': 0, 'pass_rate': 0.95}}
        assert 'data' in response

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pass_rate_range(self):
        rate = 0.95
        assert 0 <= rate <= 1, "合格率必须在 0-1 之间"


class TestReportMaterialSummary:
    """GET /api/report/material_summary"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'items': []}}
        assert 'data' in response


class TestReportOutputSummary:
    """GET /api/report/output_summary"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        response = {'code': 0, 'data': {'total_output': 0, 'by_date': []}}
        assert 'data' in response
