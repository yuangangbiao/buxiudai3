# -*- coding: utf-8 -*-
"""集成测试: 辅助业务 Blueprint (ai, cost, message, scan, stats, reports).

每个测试类创建独立 Flask app 并注册对应 Blueprint，
验证 HTTP 路由、参数处理、返回值结构的正确性。
需要外部依赖的 Blueprint 通过 unittest.mock 进行打桩。
"""
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


class TestAiBlueprint:
    """AI模块 /api/ai/* 集成测试 — 使用内建数据，无需 mock"""

    @pytest.fixture
    def client(self):
        from api.ai import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_speech_to_report_success(self, client):
        """完整语音报工解析：工序+数量+状态全部识别"""
        resp = client.post('/api/ai/speech-to-report', json={'text': '裁剪200米完成了'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        data = result['data']
        assert data['needs_confirmation'] is False
        assert data['confirm_data']['process_name'] == '裁剪'
        assert data['confirm_data']['quantity'] == 200
        assert data['confirm_data']['status'] == '已完成'

    def test_speech_to_report_partial(self, client):
        """部分识别：仅有工序无数量，需人工确认"""
        resp = client.post('/api/ai/speech-to-report', json={'text': '质检'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['needs_confirmation'] is True

    def test_speech_to_report_empty_text(self, client):
        """空文本传入应返回错误"""
        resp = client.post('/api/ai/speech-to-report', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 3001

    def test_chat_order_progress(self, client):
        """查询订单进度"""
        resp = client.post('/api/ai/chat', json={'query': 'ORD202604001到哪一步了'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['type'] == 'order_progress'

    def test_chat_empty_query(self, client):
        """空查询应返回错误"""
        resp = client.post('/api/ai/chat', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 3003
        assert '问题内容不能为空' in result['message']

    def test_chat_history(self, client):
        """获取对话历史"""
        resp = client.get('/api/ai/chat/history')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'history' in result['data']
        assert 'total' in result['data']


class TestCostBlueprint:
    """成本模块 /api/cost/* 集成测试 — 需 mock cost_service"""

    @pytest.fixture
    def client(self):
        import sys
        mock_svc_mod = MagicMock()
        mock_get_svc = MagicMock()
        mock_svc_mod.get_cost_service = mock_get_svc
        sys.modules['services.cost_service'] = mock_svc_mod

        import api.cost
        with patch('api.cost.get_cost_service', mock_get_svc):
            mock_service = MagicMock()
            mock_get_svc.return_value = mock_service
            from api.cost import bp
            app = Flask(__name__)
            app.config['TESTING'] = True
            app.register_blueprint(bp)
            yield app.test_client(), mock_service

    def test_list_orders(self, client):
        test_client, mock_service = client
        mock_service.get_all_order_costs.return_value = {
            'orders': [], 'total': 0, 'page': 1, 'page_size': 20
        }
        resp = test_client.get('/api/cost/orders')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'orders' in result['data']

    def test_get_order_not_found(self, client):
        test_client, mock_service = client
        mock_service.get_order_cost.return_value = None
        resp = test_client.get('/api/cost/orders/ORD999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404
        assert '不存在' in result['message']

    def test_add_detail_missing_params(self, client):
        test_client, _ = client
        resp = test_client.post('/api/cost/detail', json={'only_field': 'value'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400
        assert 'order_no' in result['message']

    def test_summary(self, client):
        test_client, mock_service = client
        mock_service.get_summary.return_value = {
            'total_cost': 0, 'total_revenue': 0
        }
        resp = test_client.get('/api/cost/summary')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_material_prices(self, client):
        test_client, mock_service = client
        mock_service.get_material_prices.return_value = []
        resp = test_client.get('/api/cost/material-prices')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


class TestMessageBlueprint:
    """消息模块 /api/message/* 集成测试 — 内建数据，无需 mock"""

    @pytest.fixture
    def client(self):
        from api.message import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_message_list(self, client):
        resp = client.get('/api/message/list')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        data = result['data']
        assert 'messages' in data
        assert 'total' in data
        assert 'unread_count' in data

    def test_message_list_filter_by_receiver(self, client):
        resp = client.get('/api/message/list?receiver_id=OP001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']['messages']) >= 1

    def test_unread_count(self, client):
        resp = client.get('/api/message/unread-count')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'count' in result['data']

    def test_mark_read(self, client):
        resp = client.post('/api/message/1/read')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '已标记' in result['message']


class TestScanBlueprint:
    """扫码模块 /api/scan/* 集成测试 — 需 mock ContainerCenter"""

    @pytest.fixture
    def client(self):
        from api.scan import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_scan_worker(self, client):
        """扫码员工无外部依赖"""
        resp = client.get('/api/scan/worker/OP001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['worker_id'] == 'OP001'

    @patch('api.scan.get_container_center')
    def test_scan_workorder_container_unavailable(self, mock_get_cc, client):
        """容器中心不可用时返回指定错误码"""
        mock_get_cc.return_value = None
        resp = client.get('/api/scan/workorder/WO001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 5001

    def test_scan_task_no_qr_data(self, client):
        """缺少二维码数据返回指定错误码"""
        resp = client.post('/api/scan/task', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 4001


class TestStatsBlueprint:
    """统计模块 /api/stats/* 集成测试 — 需 mock stats_engine"""

    @pytest.fixture
    def client(self):
        import sys
        mock_eng_mod = MagicMock()
        mock_get_eng = MagicMock()
        mock_eng_mod.get_stats_engine = mock_get_eng
        sys.modules['services.stats_engine'] = mock_eng_mod

        import api.stats
        with patch('api.stats.get_stats_engine', mock_get_eng):
            mock_engine = MagicMock()
            mock_get_eng.return_value = mock_engine
            from api.stats import bp
            app = Flask(__name__)
            app.config['TESTING'] = True
            app.register_blueprint(bp)
            yield app.test_client(), mock_engine

    def test_dashboard(self, client):
        test_client, mock_engine = client
        mock_engine.get_dashboard.return_value = {}
        resp = test_client.get('/api/stats/dashboard')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_production_stats(self, client):
        test_client, mock_engine = client
        mock_engine.get_production_stats.return_value = {'overview': [], 'trend': [], 'top_products': []}
        resp = test_client.get('/api/stats/production')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_worker_stats(self, client):
        test_client, mock_engine = client
        mock_engine.get_worker_stats.return_value = {'efficiency': []}
        resp = test_client.get('/api/stats/worker')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


class TestReportsBlueprint:
    """报表模块 /api/reports/* 集成测试 — 需 mock stats_engine"""

    @pytest.fixture
    def client(self):
        import sys
        mock_eng_mod = MagicMock()
        mock_get_eng = MagicMock()
        mock_eng_mod.get_stats_engine = mock_get_eng
        sys.modules['services.stats_engine'] = mock_eng_mod

        import api.reports
        with patch('api.reports.get_stats_engine', mock_get_eng):
            mock_engine = MagicMock()
            mock_get_eng.return_value = mock_engine
            from api.reports import bp
            app = Flask(__name__)
            app.config['TESTING'] = True
            app.register_blueprint(bp)
            yield app.test_client(), mock_engine

    def test_list_definitions(self, client):
        test_client, mock_engine = client
        mock_engine.list_reports.return_value = []
        resp = test_client.get('/api/reports/definitions')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_get_definition_not_found(self, client):
        test_client, mock_engine = client
        mock_engine.get_report.return_value = None
        resp = test_client.get('/api/reports/definitions/nonexist')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_create_definition_missing_name(self, client):
        test_client, _ = client
        resp = test_client.post('/api/reports/definitions', json={'sql_template': 'SELECT 1'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400
        assert 'name' in result['message']

    def test_list_outputs(self, client):
        test_client, mock_engine = client
        mock_engine.list_outputs.return_value = []
        resp = test_client.get('/api/reports/outputs')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_scheduler_status(self, client):
        test_client, _ = client
        import sys, types
        scheduler_mod = types.ModuleType('services.scheduler')
        scheduler_mod._scheduler_instance = None
        sys.modules['services.scheduler'] = scheduler_mod
        resp = test_client.get('/api/reports/scheduler/status')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['running'] is False
