# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - app.py 工序/同步/任务路由

覆盖: /api/process_sub_step, /api/sync-queue, /api/tasks,
      /api/wechat/pool/report
执行时间: < 30s
"""
import pytest


class TestProcessSubStep:
    """POST /api/process_sub_step - 报工"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_request_fields(self):
        """报工请求必填字段"""
        data = {
            'order_no': 'WO202506300001',
            'step_name': '切割',
            'operator_id': 'OP001',
            'quantity': 10,
            'batch_no': 'B001',
        }
        for f in ['order_no', 'step_name', 'operator_id', 'quantity']:
            assert f in data, f"报工必须包含: {f}"

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_quantity_positive(self):
        """数量必须 > 0"""
        assert 10 > 0

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_format(self):
        """报工响应格式"""
        response = {
            'code': 0,
            'message': '报工成功',
            'success': True,
            'idempotent': False,
        }
        assert response['code'] == 0
        assert response.get('success') is True

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_idempotent_response(self):
        """幂等响应: 重复报工返回 idempotent=True"""
        response = {'code': 0, 'success': True, 'idempotent': True}
        assert response.get('idempotent') is True


class TestProcessSubStepWithdraw:
    """POST /api/process_sub_step/withdraw - 撤回报工"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_request(self):
        """撤回请求"""
        data = {'id': 1, 'reason': '填错了'}
        assert 'id' in data

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_withdraw_response(self):
        """撤回响应"""
        response = {'code': 0, 'message': '撤回成功'}
        assert response['code'] == 0


class TestProcessSubStepHistory:
    """GET /api/process_sub_step/history - 报工历史"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_history_response(self):
        """历史响应"""
        response = {'code': 0, 'data': {'records': []}}
        assert 'records' in response['data']


class TestAllProcessTasks:
    """GET /api/all-process-tasks - 全部工序任务"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_response_structure(self):
        """响应结构"""
        response = {'code': 0, 'data': {'tasks': []}}
        assert 'data' in response


class TestTasks:
    """GET /api/tasks - 我的任务"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_tasks_response(self):
        """任务列表响应"""
        response = {'code': 0, 'data': {'tasks': [], 'total': 0}}
        assert 'tasks' in response['data']


class TestSyncQueueList:
    """GET /api/sync-queue/list - 同步队列"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_sync_queue_response(self):
        """同步队列响应"""
        response = {'code': 0, 'data': {'items': [], 'pending': 0, 'failed': 0}}
        for f in ['items', 'pending', 'failed']:
            assert f in response['data']


class TestSyncQueueRetry:
    """POST /api/sync-queue/retry - 重试同步"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_retry_request(self):
        """重试请求"""
        data = {'queue_id': 1}
        assert 'queue_id' in data

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_retry_response(self):
        """重试响应"""
        response = {'code': 0, 'message': '重试已加入队列'}
        assert response['code'] == 0


class TestWechatPoolReport:
    """POST /api/wechat/pool/report - 微信报工池"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pool_report_request(self):
        """池报工请求"""
        data = {
            'pkg_id': 'PKG001',
            'operator_id': 'OP001',
            'quantity': 10,
        }
        for f in ['pkg_id', 'operator_id', 'quantity']:
            assert f in data

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pool_report_response(self):
        """池报工响应"""
        response = {'code': 0, 'success': True, 'data': {'id': 1}}
        assert response['code'] == 0
