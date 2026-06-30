# -*- coding: utf-8 -*-
"""
排产调度服务单元测试 — ScheduleDispatchService
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from unittest.mock import patch, MagicMock, call, PropertyMock
import pytest
from datetime import datetime, date
import json
import threading
import time

from services.schedule_dispatch_service import ScheduleDispatchService


# ── 辅助函数 ──────────────────────────────────────────────

def _ci(fetchone_value=None, fetchall_value=None, rowcount=1):
    """创建 cursor mock 并设置 return values"""
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    if fetchall_value is not None:
        cursor.fetchall.return_value = fetchall_value
    cursor.rowcount = rowcount
    cursor.lastrowid = 42
    return cursor


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def mock_log_ui():
    with patch('services.schedule_dispatch_service.log_ui') as m:
        yield m


@pytest.fixture
def mock_requests():
    with patch('services.schedule_dispatch_service.requests') as m:
        yield m


@pytest.fixture
def mock_deps():
    """Create mock connection and cursor fixtures"""
    with patch('services.schedule_dispatch_service.get_connection') as mock_get_conn:
        with patch('services.schedule_dispatch_service.log_status_change') as mock_log:
            with patch('services.schedule_dispatch_service.CONTAINER_CENTER_URL', 'http://test:5000'):
                mock_conn = MagicMock()
                mock_get_conn.return_value = mock_conn
                yield {
                    'get_connection': mock_get_conn,
                    'conn': mock_conn,
                    'cursor': None,
                    'log_status_change': mock_log,
                }


@pytest.fixture
def mock_retry_connections():
    """For retry_dead_letter which uses 2 connections"""
    with patch('services.schedule_dispatch_service.get_connection') as mock_get_conn:
        with patch('services.schedule_dispatch_service.log_status_change') as mock_log:
            with patch('services.schedule_dispatch_service.CONTAINER_CENTER_URL', 'http://test:5000'):
                conn1 = MagicMock()
                conn2 = MagicMock()
                mock_get_conn.side_effect = [conn1, conn2]
                yield {
                    'get_connection': mock_get_conn,
                    'conn': conn1,
                    'conn2': conn2,
                    'log_status_change': mock_log,
                }


# ── 样本数据 ──────────────────────────────────────────────

def _sample_order(**overrides):
    """构建样本订单字典"""
    order = {
        'product_type_id': 1,
        'customer_group': '测试客户',
        'customer_name': '测试客户',
        'product_type': '冷冻网带',
        'material': '304不锈钢',
        'mesh_size': '10*10',
        'wire_diameter': '1.0',
        'width': '1000',
        'length': '2000',
        'quantity': 50,
        'unit': '平方米',
        'surface_treatment': '抛光',
        'special_requirements': '特殊要求',
        'delivery_date': '2026-02-15',
        'remark': '测试备注',
        'extra_params': {},
    }
    order.update(overrides)
    return order


def _sample_callback_data(**overrides):
    """构建样本回调数据"""
    data = {
        'order_no': 'ORD001',
        'prod_id': 10,
        'plan_start': '2026-01-15',
        'plan_end': '2026-02-15',
        'operator': '张三',
        'remark': '确认排产',
    }
    data.update(overrides)
    return data


# ============================================================
# 1. 静态/类方法基础测试
# ============================================================

class TestSafe:
    """_safe 静态方法"""

    def test_safe_datetime(self):
        """datetime → 'YYYY-MM-DD HH:MM:SS'"""
        val = datetime(2026, 1, 15, 10, 30, 0)
        assert ScheduleDispatchService._safe(val) == '2026-01-15 10:30:00'

    def test_safe_date(self):
        """date → 'YYYY-MM-DD'"""
        val = date(2026, 1, 15)
        assert ScheduleDispatchService._safe(val) == '2026-01-15'

    def test_safe_other(self):
        """int/str/None → as-is"""
        assert ScheduleDispatchService._safe(42) == 42
        assert ScheduleDispatchService._safe("hello") == "hello"
        assert ScheduleDispatchService._safe(None) is None


class TestGetContainerCenterUrl:
    """_get_container_center_url 类方法"""

    def test_get_container_center_url(self, mock_deps):
        """返回配置的 URL"""
        url = ScheduleDispatchService._get_container_center_url()
        assert url == 'http://test:5000'


class TestGetContainerApiKey:
    """_get_container_api_key 类方法"""

    def test_get_container_api_key_with_key(self):
        """os.getenv 返回 key"""
        with patch('services.schedule_dispatch_service.os.getenv', return_value='my-api-key'):
            key = ScheduleDispatchService._get_container_api_key()
            assert key == 'my-api-key'

    def test_get_container_api_key_no_key(self):
        """os.getenv 返回空"""
        with patch('services.schedule_dispatch_service.os.getenv', return_value=''):
            key = ScheduleDispatchService._get_container_api_key()
            assert key == ''


# ============================================================
# 2. _build_payload
# ============================================================

class TestBuildPayload:
    """_build_payload 构建请求体"""

    def test_build_payload_basic(self):
        """标准订单字典，验证所有字段"""
        order = _sample_order()
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '2026-01-15', '2026-02-15')

        assert payload['order_no'] == 'ORD001'
        assert payload['prod_id'] == 10
        assert payload['plan_start'] == '2026-01-15'
        assert payload['plan_end'] == '2026-02-15'
        assert payload['product_type_id'] == 1
        assert payload['customer_group'] == '测试客户'
        assert payload['product_type'] == '冷冻网带'
        assert payload['material'] == '304不锈钢'
        assert payload['mesh_size'] == '10*10'
        assert payload['wire_diameter'] == '1.0'
        assert payload['width'] == '1000'
        assert payload['length'] == '2000'
        assert payload['quantity'] == 50
        assert payload['unit'] == '平方米'
        assert payload['surface_treatment'] == '抛光'
        assert payload['special_requirements'] == '特殊要求'
        assert payload['delivery_date'] == '2026-02-15'
        assert payload['remark'] == '测试备注'
        assert payload['extra_params'] == {}
        assert payload['source'] == 'desktop_schedule'

    def test_build_payload_extra_params_dict(self):
        """extra_params 本身就是 dict"""
        order = _sample_order(extra_params={'key1': 'val1', 'key2': 123})
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['extra_params'] == {'key1': 'val1', 'key2': 123}

    def test_build_payload_extra_params_json_string(self):
        """extra_params 是 JSON 字符串，应被解析"""
        order = _sample_order(extra_params='{"key1": "val1", "key2": 456}')
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['extra_params'] == {'key1': 'val1', 'key2': 456}

    def test_build_payload_extra_params_invalid_json(self, caplog):
        """extra_params 是无效 JSON，回退到 {}"""
        order = _sample_order(extra_params='{invalid json}')
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['extra_params'] == {}

    def test_build_payload_safe_calls(self):
        """_safe 在 datetime/date 字段上被调用"""
        dt = datetime(2026, 5, 1, 8, 0, 0)
        d = date(2026, 5, 1)
        order = _sample_order(delivery_date=d, customer_group=dt)
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['delivery_date'] == '2026-05-01'
        assert payload['customer_group'] == '2026-05-01 08:00:00'

    def test_build_payload_customer_group_fallback(self):
        """customer_group 为空时使用 customer_name"""
        order = _sample_order(customer_group='', customer_name='备用客户')
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['customer_group'] == '备用客户'

    def test_build_payload_default_values(self):
        """缺失的字段使用默认值"""
        order = {}
        payload = ScheduleDispatchService._build_payload('ORD001', order, 10, '', '')
        assert payload['product_type_id'] == 0
        assert payload['customer_group'] == ''
        assert payload['quantity'] == 0
        assert payload['unit'] == '米'
        assert payload['extra_params'] == {}


# ============================================================
# 3. _actually_send
# ============================================================

class TestActuallySend:
    """_actually_send 实际发送请求"""

    def test_actually_send_success(self, mock_requests, mock_log_ui):
        """POST 返回 200 且 code=0"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0, 'message': 'ok'}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is True
        mock_requests.post.assert_called_once()
        url = mock_requests.post.call_args[0][0]
        assert '/api/schedule/publish' in url

    def test_actually_send_success_no_code(self, mock_requests, mock_log_ui):
        """POST 返回 200 但用 success=true 而非 code=0"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'success': True, 'message': 'ok'}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})
        assert result['success'] is True

    def test_actually_send_duplicate(self, mock_requests, mock_log_ui):
        """POST 返回 200 但 data.duplicate=true"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            'code': 0, 'data': {'duplicate': True, 'message': '工单已存在，跳过'}
        }
        mock_requests.post.return_value = r

        result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is True
        assert result.get('duplicate') is True

    def test_actually_send_api_error(self, mock_requests, mock_log_ui):
        """POST 返回 200 但 code != 0 且 success 不真"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 1, 'message': '服务端错误'}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is False
        assert '服务端错误' in result['message']

    def test_actually_send_http_error(self, mock_requests, mock_log_ui):
        """POST 返回 500"""
        r = MagicMock()
        r.status_code = 500
        mock_requests.post.return_value = r

        result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is False
        assert 'HTTP 500' in result['message']

    def test_actually_send_connection_error(self, mock_log_ui):
        """POST 抛出 ConnectionError"""
        from requests.exceptions import ConnectionError as ReqConnError
        with patch('services.schedule_dispatch_service.requests.post',
                   side_effect=ReqConnError('connection refused')):
            result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is False
        assert '无法连接' in result['message']

    def test_actually_send_timeout(self, mock_log_ui):
        """POST 抛出 Timeout"""
        from requests.exceptions import Timeout as ReqTimeout
        with patch('services.schedule_dispatch_service.requests.post',
                   side_effect=ReqTimeout('timeout')):
            result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is False
        assert '超时' in result['message']

    def test_actually_send_generic_exception(self, mock_log_ui):
        """POST 抛出通用 Exception"""
        with patch('services.schedule_dispatch_service.requests.post',
                   side_effect=Exception('unknown error')):
            result = ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

        assert result['success'] is False
        assert 'unknown error' in result['message']

    def test_actually_send_with_api_key(self, mock_requests, mock_log_ui):
        """配置了 API Key 时在 Header 中传递"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        with patch.object(ScheduleDispatchService, '_get_container_api_key', return_value='secret-key'):
            ScheduleDispatchService._actually_send(1, {'order_no': 'ORD001'})

            call_kwargs = mock_requests.post.call_args[1]
            assert call_kwargs['headers']['X-API-Key'] == 'secret-key'


# ============================================================
# 4. _is_container_center_available
# ============================================================

class TestIsContainerCenterAvailable:
    """_is_container_center_available 健康检查"""

    def test_is_available_healthy(self, mock_requests):
        """GET /api/health 返回 200 → True"""
        r = MagicMock()
        r.status_code = 200
        mock_requests.get.return_value = r
        assert ScheduleDispatchService._is_container_center_available() is True

    def test_is_available_unhealthy(self, mock_requests):
        """GET /api/health 返回 500 → False"""
        r = MagicMock()
        r.status_code = 500
        mock_requests.get.return_value = r
        assert ScheduleDispatchService._is_container_center_available() is False

    def test_is_available_exception(self, mock_requests):
        """GET 抛出 Exception → False"""
        mock_requests.get.side_effect = Exception('network error')
        assert ScheduleDispatchService._is_container_center_available() is False

    def test_is_available_custom_timeout(self, mock_requests):
        """自定义 timeout 参数"""
        r = MagicMock()
        r.status_code = 200
        mock_requests.get.return_value = r
        ScheduleDispatchService._is_container_center_available(timeout=5)
        assert mock_requests.get.call_args[1]['timeout'] == 5


# ============================================================
# 5. _retry_single_queue_item
# ============================================================

class TestRetrySingleQueueItem:
    """_retry_single_queue_item 重试单条队列"""

    def test_retry_single_success(self, mock_requests):
        """POST 返回 200 且 code=0 → True"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r
        result = ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {})
        assert result is True

    def test_retry_single_success_alt(self, mock_requests):
        """POST 返回 200 且 success=true → True"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'success': True}
        mock_requests.post.return_value = r
        result = ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {})
        assert result is True

    def test_retry_single_fail_api(self, mock_requests):
        """POST 返回 200 但 code != 0 → False"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 1, 'message': 'error'}
        mock_requests.post.return_value = r
        result = ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {})
        assert result is False

    def test_retry_single_fail_http(self, mock_requests):
        """POST 返回 500 → False"""
        r = MagicMock()
        r.status_code = 500
        mock_requests.post.return_value = r
        result = ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {})
        assert result is False

    def test_retry_single_exception(self, mock_requests):
        """POST 抛出 Exception → False"""
        mock_requests.post.side_effect = Exception('any error')
        result = ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {})
        assert result is False


# ============================================================
# 6. publish_schedule
# ============================================================

class TestPublishSchedule:
    """publish_schedule 发布排产"""

    def _setup_mock_deps(self, deps, cursor):
        """将 cursor 注入到 mock_deps 中"""
        deps['conn'].cursor.return_value = cursor

    def test_publish_schedule_success_fresh(self, mock_deps, mock_requests, mock_log_ui):
        """无已存在记录，无失败记录，发送成功"""
        cursor = _ci()
        cursor.fetchone.side_effect = [None, None]  # existing=None, failed=None
        self._setup_mock_deps(mock_deps, cursor)

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is True

        # 验证执行了 INSERT
        insert_call = [c for c in cursor.execute.call_args_list if 'INSERT INTO schedule_queue' in c[0][0]]
        assert len(insert_call) == 1

        # 验证 UPDATE 为 success（注意：SELECT 查询也包含 "status='success'"，所以计为2）
        success_updates = [c for c in cursor.execute.call_args_list if "status='success'" in c[0][0]]
        assert len(success_updates) == 2  # 1个SELECT + 1个UPDATE

        # 验证 UPDATE orders
        order_updates = [c for c in cursor.execute.call_args_list if 'UPDATE orders' in c[0][0]]
        assert len(order_updates) == 1

        # 验证 commit
        assert mock_deps['conn'].commit.call_count >= 1

    def test_publish_schedule_success_reuse_failed(self, mock_deps, mock_requests, mock_log_ui):
        """已存在失败记录，复用该记录"""
        cursor = _ci()
        cursor.fetchone.side_effect = [None, {'id': 99}]  # existing=None, failed={'id': 99}
        self._setup_mock_deps(mock_deps, cursor)

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is True

        # 验证 UPDATE 而不是 INSERT（复用失败记录）
        update_calls = [c for c in cursor.execute.call_args_list
                        if 'UPDATE schedule_queue' in c[0][0] and "status='sending'" in c[0][0]]
        assert len(update_calls) == 1
        assert update_calls[0][0][1][-1] == 99  # WHERE id=99

        insert_calls = [c for c in cursor.execute.call_args_list if 'INSERT INTO schedule_queue' in c[0][0]]
        assert len(insert_calls) == 0

    def test_publish_schedule_already_published(self, mock_deps, mock_requests, mock_log_ui):
        """已存在成功记录，且容器中心验证通过"""
        cursor = _ci()
        cursor.fetchone.side_effect = [{'id': 5, 'status': 'success'}]  # existing
        self._setup_mock_deps(mock_deps, cursor)

        r_get = MagicMock()
        r_get.status_code = 200
        r_get.json.return_value = {'code': 0, 'data': {'order_no': 'ORD001'}}
        mock_requests.get.return_value = r_get

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is True
        assert '已发布，无需重复提交' in result['message']

        # 不应有任何 INSERT/UPDATE
        assert cursor.execute.call_count == 1  # 只有 SELECT 查询

    def test_publish_schedule_already_published_verify_fails(self, mock_deps, mock_requests, mock_log_ui):
        """已存在成功记录，但容器中心无数据，重新发送"""
        cursor = _ci()
        cursor.fetchone.side_effect = [
            {'id': 5, 'status': 'success'},  # existing
            None,  # failed
        ]
        self._setup_mock_deps(mock_deps, cursor)

        # 容器中心验证返回无 data
        r_get = MagicMock()
        r_get.status_code = 200
        r_get.json.return_value = {'code': 0, 'data': None}
        mock_requests.get.return_value = r_get

        r_post = MagicMock()
        r_post.status_code = 200
        r_post.json.return_value = {'code': 0}
        mock_requests.post.return_value = r_post

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is True

        # 验证 DELETE 旧记录被调用
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM schedule_queue' in c[0][0]]
        assert len(delete_calls) == 1

    def test_publish_schedule_already_published_verify_exception(self, mock_deps, mock_requests, mock_log_ui):
        """已存在成功记录，但容器中心请求异常，重发"""
        cursor = _ci()
        cursor.fetchone.side_effect = [
            {'id': 5, 'status': 'success'},  # existing
            None,  # failed
        ]
        self._setup_mock_deps(mock_deps, cursor)

        # 容器中心验证抛出异常
        mock_requests.get.side_effect = Exception('connection error')

        r_post = MagicMock()
        r_post.status_code = 200
        r_post.json.return_value = {'code': 0}
        mock_requests.post.return_value = r_post

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is True
        # 验证 DELETE 旧记录
        delete_calls = [c for c in cursor.execute.call_args_list if 'DELETE FROM schedule_queue' in c[0][0]]
        assert len(delete_calls) == 1

    def test_publish_schedule_actually_send_fails(self, mock_deps, mock_requests, mock_log_ui):
        """_actually_send 返回失败"""
        cursor = _ci()
        cursor.fetchone.side_effect = [None, None]  # existing=None, failed=None
        self._setup_mock_deps(mock_deps, cursor)

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 1, 'message': '服务端错误'}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is False
        assert '发布失败' in result['message']

        # 验证 UPDATE 为 failed 状态
        failed_updates = [c for c in cursor.execute.call_args_list if "status='failed'" in c[0][0]]
        assert len(failed_updates) >= 1

    def test_publish_schedule_db_exception(self, mock_deps, mock_log_ui):
        """数据库操作抛出异常"""
        cursor = MagicMock()
        cursor.execute.side_effect = Exception('DB connection lost')
        mock_deps['conn'].cursor.return_value = cursor

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is False
        assert '异常' in result['message'] or 'DB' in result['message']

        # verify conn.close is called in finally
        mock_deps['conn'].close.assert_called_once()


# ============================================================
# 7. get_dead_letters
# ============================================================

class TestGetDeadLetters:
    """get_dead_letters 获取死信"""

    def test_get_dead_letters_few(self, mock_deps, caplog):
        """返回 < 10 条，不触发告警"""
        cursor = _ci(fetchall_value=[
            {'id': 1, 'order_no': 'ORD001', 'retry_count': 5,
             'payload': '{}', 'last_error': None,
             'prod_id': 10, 'created_at': None, 'updated_at': None},
            {'id': 2, 'order_no': 'ORD002', 'retry_count': 5,
             'payload': '{}', 'last_error': None,
             'prod_id': 20, 'created_at': None, 'updated_at': None},
        ])
        mock_deps['conn'].cursor.return_value = cursor

        result = ScheduleDispatchService.get_dead_letters()

        assert len(result) == 2
        assert '死信告警' not in caplog.text

    def test_get_dead_letters_many(self, mock_deps, caplog):
        """返回 >= 10 条，触发告警"""
        rows = [{'id': i, 'order_no': f'ORD{i:03d}', 'retry_count': 5,
                 'payload': '{}', 'last_error': None,
                 'prod_id': i, 'created_at': None, 'updated_at': None}
                for i in range(10)]
        cursor = _ci(fetchall_value=rows)
        mock_deps['conn'].cursor.return_value = cursor

        with patch('services.schedule_dispatch_service.logger') as mock_logger:
            result = ScheduleDispatchService.get_dead_letters()

        assert len(result) == 10
        mock_logger.warning.assert_called_once()

    def test_get_dead_letters_empty(self, mock_deps):
        """返回空列表"""
        cursor = _ci(fetchall_value=[])
        mock_deps['conn'].cursor.return_value = cursor

        result = ScheduleDispatchService.get_dead_letters()

        assert result == []

    def test_get_dead_letters_conn_closed(self, mock_deps):
        """验证连接在 finally 中被关闭"""
        cursor = _ci(fetchall_value=[])
        mock_deps['conn'].cursor.return_value = cursor

        ScheduleDispatchService.get_dead_letters()
        mock_deps['conn'].close.assert_called_once()


# ============================================================
# 8. retry_dead_letter
# ============================================================

class TestRetryDeadLetter:
    """retry_dead_letter 重发死信"""

    def test_retry_dead_letter_skipped(self, mock_retry_connections):
        """原子更新 rowcount=0（已被处理）→ skipped=True"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=0)  # 原子抢占失败
        conn1.cursor.return_value = cursor1

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['skipped'] is True
        assert '已被其他进程处理' in result['message']

    def test_retry_dead_letter_payload_missing(self, mock_retry_connections):
        """原子更新成功，但 payload 为 None"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': None})
        conn1.cursor.return_value = cursor1

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert '数据缺失' in result['message']
        conn1.rollback.assert_called_once()

    def test_retry_dead_letter_payload_missing_row(self, mock_retry_connections):
        """原子更新成功，但查询无行"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value=None)
        conn1.cursor.return_value = cursor1

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert '数据缺失' in result['message']

    def test_retry_dead_letter_payload_invalid_json(self, mock_retry_connections):
        """payload 是无效 JSON"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{invalid json}'})
        conn1.cursor.return_value = cursor1

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert 'JSON解析失败' in result['message']
        conn1.rollback.assert_called_once()

    def test_retry_dead_letter_success_not_duplicate(self, mock_retry_connections, mock_requests, mock_log_ui):
        """重置成功，_actually_send 返回成功，非重复"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        conn2 = mock_retry_connections['conn2']
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is True

        # conn2 执行了 UPDATE status='success'
        success_updates = [c for c in cursor2.execute.call_args_list if "status='success'" in c[0][0]]
        assert len(success_updates) >= 1

    def test_retry_dead_letter_success_duplicate(self, mock_retry_connections, mock_requests, mock_log_ui):
        """重置成功，_actually_send 返回 duplicate=True"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        conn2 = mock_retry_connections['conn2']
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            'code': 0, 'data': {'duplicate': True, 'message': '已存在'}
        }
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is True
        assert result.get('duplicate') is True

    def test_retry_dead_letter_failure(self, mock_retry_connections, mock_requests, mock_log_ui):
        """重置成功，_actually_send 返回失败"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        conn2 = mock_retry_connections['conn2']
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 1, 'message': '服务端失败'}
        mock_requests.post.return_value = r

        result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        # conn2 执行了 UPDATE status='failed'
        fail_updates = [c for c in cursor2.execute.call_args_list if "status='failed'" in c[0][0]]
        assert len(fail_updates) >= 1

    def test_retry_dead_letter_connection_error(self, mock_retry_connections, mock_log_ui):
        """_actually_send 方法内部抛出 ConnectionError（service 内部 except）"""
        from requests.exceptions import ConnectionError as ReqConnError
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        conn2 = mock_retry_connections['conn2']
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch('services.schedule_dispatch_service.requests.post',
                   side_effect=ReqConnError('connection failed')):
            result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert '无法连接' in result['message']

    def test_retry_dead_letter_generic_exception(self, mock_retry_connections, mock_log_ui):
        """retry_dead_letter 外层捕获通用 Exception"""
        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        # 让 _actually_send 中 payload.get() 抛出异常（不依赖 requests）
        # 模拟 conn2.commit 抛出异常到外层 except
        conn2 = mock_retry_connections['conn2']
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2
        conn2.commit.side_effect = Exception('commit failed')

        with patch('services.schedule_dispatch_service.requests.post') as mock_post:
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = {'code': 0}
            mock_post.return_value = r

            result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert '异常' in result['message']


# ============================================================
# 9. handle_schedule_callback
# ============================================================

class TestHandleScheduleCallback:
    """handle_schedule_callback 处理回调"""

    def test_handle_callback_missing_fields(self):
        """缺少必需字段 → 错误响应"""
        data = {'order_no': 'ORD001'}  # 缺少 prod_id, plan_start, plan_end
        result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is False
        assert '缺少必需字段' in result['message']

    def test_handle_callback_pending(self, mock_deps, mock_log_ui):
        """old_status 已是 PENDING → 仅更新日期，不修改状态"""
        cursor = _ci(fetchone_value={
            'status': '待开始',
            'order_id': 5,
        })
        mock_deps['conn'].cursor.return_value = cursor

        data = _sample_callback_data(remark='')

        result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is True

        # 应当只有一条 UPDATE（更新日期）
        # 不应有 UPDATE orders（因为已经是 PENDING）
        prod_updates = [c for c in cursor.execute.call_args_list
                        if 'UPDATE production_orders' in c[0][0]]
        assert len(prod_updates) == 1

        order_updates = [c for c in cursor.execute.call_args_list
                         if 'UPDATE orders' in c[0][0]]
        assert len(order_updates) == 0

    def test_handle_callback_not_pending(self, mock_deps, mock_log_ui):
        """old_status 不是 PENDING → 更新状态为 PENDING，更新 orders"""
        cursor = _ci(fetchone_value={
            'status': '生产中',
            'order_id': 5,
        })
        mock_deps['conn'].cursor.return_value = cursor

        data = _sample_callback_data(remark='')

        with patch('core.event_bus.EventBus.publish') as mock_publish:
            result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is True

        # production_orders 更新（含 status）和 orders 更新
        prod_updates = [c for c in cursor.execute.call_args_list
                        if 'UPDATE production_orders' in c[0][0] and 'status' in c[0][0]]
        assert len(prod_updates) == 1

        order_updates = [c for c in cursor.execute.call_args_list
                         if 'UPDATE orders' in c[0][0]]
        assert len(order_updates) == 1

        # 验证 EventBus 被发布
        mock_publish.assert_called_once()

        # 验证 log_status_change 被调用（状态变更）
        mock_deps['log_status_change'].assert_called_once()

    def test_handle_callback_with_remark(self, mock_deps, mock_log_ui):
        """remark 不为空 → CONCAT_WS 更新"""
        cursor = _ci(fetchone_value={
            'status': '生产中',
            'order_id': 5,
        })
        mock_deps['conn'].cursor.return_value = cursor

        data = _sample_callback_data(remark='已确认排产，请注意交期')

        with patch('core.event_bus.EventBus.publish') as mock_publish:
            result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is True

        # 验证 CONCAT_WS 更新被调用
        concat_calls = [c for c in cursor.execute.call_args_list if 'CONCAT_WS' in str(c)]
        assert len(concat_calls) == 1

    def test_handle_callback_no_remark(self, mock_deps, mock_log_ui):
        """remark 为空 → 不触发 CONCAT_WS 更新"""
        cursor = _ci(fetchone_value={
            'status': '生产中',
            'order_id': 5,
        })
        mock_deps['conn'].cursor.return_value = cursor

        data = _sample_callback_data(remark='')

        with patch('core.event_bus.EventBus.publish') as mock_publish:
            result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is True

        # 不应有 CONCAT_WS
        concat_calls = [c for c in cursor.execute.call_args_list if 'CONCAT_WS' in str(c)]
        assert len(concat_calls) == 0

    def test_handle_callback_db_exception(self, mock_deps, mock_log_ui):
        """数据库异常 → rollback, 错误响应"""
        cursor = MagicMock()
        cursor.execute.side_effect = Exception('UPDATE failed')
        mock_deps['conn'].cursor.return_value = cursor

        data = _sample_callback_data()

        result = ScheduleDispatchService.handle_schedule_callback(data)

        assert result['success'] is False
        assert '失败' in result['message']

        mock_deps['conn'].rollback.assert_called_once()
        mock_deps['conn'].close.assert_called_once()


# ============================================================
# 10. _process_failed_queue (single iteration)
# ============================================================

class TestProcessFailedQueue:
    """_process_failed_queue 后台队列处理"""

    def test_process_failed_queue_empty(self, mock_requests, mock_log_ui):
        """无失败条目，直接跳过"""
        # 让 _is_container_center_available 返回 True
        with patch.object(ScheduleDispatchService, '_is_container_center_available', return_value=True):
            # mock query 返回空
            cursor = _ci(fetchall_value=[])
            conn = MagicMock()
            conn.cursor.return_value = cursor
            with patch('services.schedule_dispatch_service.get_connection', return_value=conn):
                # 用 KeyboardInterrupt 跳出无限循环
                with patch('services.schedule_dispatch_service.time.sleep', side_effect=KeyboardInterrupt):
                    # 应不会抛出异常
                    with pytest.raises(KeyboardInterrupt):
                        ScheduleDispatchService._process_failed_queue()

                    # 验证没有执行任何 retry
                    mock_requests.post.assert_not_called()

    def test_process_failed_queue_processes_items(self, mock_requests, mock_log_ui):
        """有失败条目，部分成功、部分失败"""
        with patch.object(ScheduleDispatchService, '_is_container_center_available', return_value=True):
            # mock query 返回 2 个条目
            items = [
                {'id': 1, 'order_no': 'ORD001', 'payload': '{"order_no": "ORD001"}', 'retry_count': 1},
                {'id': 2, 'order_no': 'ORD002', 'payload': '{"order_no": "ORD002"}', 'retry_count': 2},
            ]
            cursor = _ci(fetchall_value=items)
            conn = MagicMock()
            conn.cursor.return_value = cursor
            with patch('services.schedule_dispatch_service.get_connection', return_value=conn):
                with patch.object(ScheduleDispatchService, '_retry_single_queue_item',
                                  side_effect=[True, False]):
                    with patch('services.schedule_dispatch_service.time.sleep', side_effect=KeyboardInterrupt):
                        with pytest.raises(KeyboardInterrupt):
                            ScheduleDispatchService._process_failed_queue()

                        # 验证两个条目都处理了
                        assert cursor.execute.call_count >= 2
                        # 验证 commit 被调用一次
                        conn.commit.assert_called_once()

    def test_process_failed_queue_not_available(self, mock_requests, mock_log_ui):
        """容器中心不可达，跳过不查询"""
        with patch.object(ScheduleDispatchService, '_is_container_center_available', return_value=False):
            with patch('services.schedule_dispatch_service.get_connection') as mock_get_conn:
                with patch('services.schedule_dispatch_service.time.sleep', side_effect=KeyboardInterrupt):
                    with pytest.raises(KeyboardInterrupt):
                        ScheduleDispatchService._process_failed_queue()

                    # 不应获取数据库连接
                    mock_get_conn.assert_not_called()


# ============================================================
# 11. start_queue_recovery
# ============================================================

class TestStartQueueRecovery:
    """start_queue_recovery 启动队列恢复线程"""

    def _reset_global_flag(self):
        """重置全局标志（用于测试清理）"""
        import services.schedule_dispatch_service as sds
        sds._QUEUE_RECOVERY_STARTED = False

    def test_start_queue_recovery_first_call(self):
        """全局标志为 False → 启动线程"""
        self._reset_global_flag()

        mock_thread = MagicMock()
        with patch('services.schedule_dispatch_service.threading.Thread', return_value=mock_thread) as mock_thread_cls:
            with patch('services.schedule_dispatch_service.logger') as mock_logger:
                ScheduleDispatchService.start_queue_recovery()

                # 验证线程被创建（daemon=True）
                mock_thread_cls.assert_called_once()
                kwargs = mock_thread_cls.call_args[1]
                assert kwargs['daemon'] is True
                assert kwargs['name'] == 'schedule-queue-recovery'

                # 验证线程启动
                mock_thread.start.assert_called_once()

                # 验证 logger.info 被调用
                mock_logger.info.assert_called_once()

        self._reset_global_flag()

    def test_start_queue_recovery_already_started(self):
        """全局标志为 True → 直接返回，不启动线程"""
        self._reset_global_flag()

        # 先调用一次，将标志设为 True
        mock_thread1 = MagicMock()
        with patch('services.schedule_dispatch_service.threading.Thread', return_value=mock_thread1):
            ScheduleDispatchService.start_queue_recovery()

        # 第二次调用应直接返回
        mock_thread2 = MagicMock()
        with patch('services.schedule_dispatch_service.threading.Thread', return_value=mock_thread2) as mock_thread_cls:
            with patch('services.schedule_dispatch_service.logger') as mock_logger:
                ScheduleDispatchService.start_queue_recovery()

                # 不应创建新线程
                mock_thread_cls.assert_not_called()
                mock_logger.info.assert_not_called()

        self._reset_global_flag()

    def test_start_queue_recovery_concurrent_calls(self):
        """并发调用时只有第一个启动线程"""
        self._reset_global_flag()

        import services.schedule_dispatch_service as sds

        # 模拟 Thread，防止后台线程实际运行
        mock_thread = MagicMock()
        barrier = threading.Barrier(2, timeout=3)

        def call_with_barrier():
            barrier.wait()
            ScheduleDispatchService.start_queue_recovery()

        # 关键：子线程必须在 patch 作用域之外创建，
        # 因为 threading 是单例模块，patch 会影响 threading.Thread 类本身
        t1 = threading.Thread(target=call_with_barrier)
        t2 = threading.Thread(target=call_with_barrier)

        with patch('services.schedule_dispatch_service.threading.Thread',
                    return_value=mock_thread) as mock_thread_cls:
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # 验证 flag 被设置（第一个线程通过了 lock 并设为 True）
            # 第二个线程看到 flag 为 True 后直接 return
            assert sds._QUEUE_RECOVERY_STARTED is True
            # Thread 应该只被调用一次（只有第一个线程创建 Thread 对象）
            assert mock_thread_cls.call_count == 1

        self._reset_global_flag()


# ============================================================
# 12. 补充覆盖: publish_schedule 异常处理内层commit (L154)
# ============================================================

class TestPublishScheduleInnerExceptionHandler:
    """publish_schedule 异常 — 到达 except 内层的 conn.commit() (L154)"""

    def test_publish_schedule_exception_in_success_path_causes_inner_commit(self, mock_deps, mock_requests, mock_log_ui):
        """_actually_send 返回 success=True, 但后续 cursor.execute 抛出异常，触发外层 except 进入内层 try"""
        cursor = _ci()
        # 使用无限 None 生成器，确保 fetchone 始终返回 None（existing/failed 均为 None）
        # 避免有限 list 耗尽后 MagicMock 自动返回 truthy 对象导致无限循环
        def always_none(*args, **kwargs):
            return None
        cursor.fetchone.side_effect = always_none
        mock_deps['conn'].cursor.return_value = cursor

        # _actually_send 返回成功
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        # 让 success 路径上的某个 cursor.execute 抛出异常
        # 注意: side_effect 中不能调用 cursor.execute (real_execute)，
        # 因为 cursor.execute 有 side_effect，也会触发 side_effect_execute 导致递归无限循环
        execute_log = []
        call_count = [0]

        def side_effect_execute(*args, **kwargs):
            call_count[0] += 1
            sql_preview = args[0][:80] if args else '?'
            execute_log.append(f"#{call_count[0]}: {sql_preview}")
            if call_count[0] == 5:
                raise Exception('orders update failed')
            # 返回 MagicMock 而非调用 real_execute，避免触发 side_effect 递归
            return MagicMock()

        cursor.execute.side_effect = side_effect_execute

        result = ScheduleDispatchService.publish_schedule(
            'ORD001', _sample_order(), 10, '2026-01-15', '2026-02-15'
        )

        assert result['success'] is False

        # 验证内层的 conn.commit() (L154) 被调用
        import sys
        print("\n[DEBUG] execute calls:", execute_log, file=sys.stderr)
        mock_deps['conn'].commit.assert_called()
        # 验证 conn.close (finally 块) 被调用
        mock_deps['conn'].close.assert_called_once()


# ============================================================
# 13. 补充覆盖: _retry_single_queue_item X-API-Key header (L278)
# ============================================================

class TestRetrySingleQueueItemApiKey:
    """_retry_single_queue_item 设置了 API Key 时传递 X-API-Key header (L278)"""

    def test_retry_single_with_api_key(self, mock_requests):
        """配置了 API Key 时在 Header 中传递 X-API-Key"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        with patch.object(ScheduleDispatchService, '_get_container_api_key', return_value='retry-secret'):
            ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {'order_no': 'ORD001'})

            call_kwargs = mock_requests.post.call_args[1]
            assert call_kwargs['headers']['X-API-Key'] == 'retry-secret'

    def test_retry_single_without_api_key(self, mock_requests):
        """未配置 API Key 时 Header 中不包含 X-API-Key"""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {'code': 0}
        mock_requests.post.return_value = r

        with patch.object(ScheduleDispatchService, '_get_container_api_key', return_value=''):
            ScheduleDispatchService._retry_single_queue_item(1, 'ORD001', {'order_no': 'ORD001'})

            call_headers = mock_requests.post.call_args[1]['headers']
            assert 'X-API-Key' not in call_headers


# ============================================================
# 14. 补充覆盖: _process_failed_queue continue (L310) 和 logger.error (L357)
# ============================================================

class TestProcessFailedQueueContinueAndError:
    """_process_failed_queue — 容器中心不可达的 continue (L310) 和通用异常 (L357)"""

    def test_process_failed_queue_continue_when_unavailable(self, mock_requests, mock_log_ui):
        """容器中心不可达 → sleep → continue → 下一轮循环被 KeyboardInterrupt 中断"""
        with patch.object(ScheduleDispatchService, '_is_container_center_available', return_value=False):
            with patch('services.schedule_dispatch_service.get_connection') as mock_get_conn:
                # 第一次 sleep(15) 正常执行, 第二次抛出 KeyboardInterrupt 退出循环
                sleep_side_effect = [None, KeyboardInterrupt]
                with patch('services.schedule_dispatch_service.time.sleep', side_effect=sleep_side_effect):
                    with pytest.raises(KeyboardInterrupt):
                        ScheduleDispatchService._process_failed_queue()

                    # continue 后不应获取数据库连接
                    mock_get_conn.assert_not_called()

    def test_process_failed_queue_generic_exception(self, mock_requests, mock_log_ui):
        """_process_failed_queue try 块中抛出通用异常 → L357 logger.error"""
        with patch.object(ScheduleDispatchService, '_is_container_center_available', return_value=True):
            # get_connection 抛出异常触发外层 except
            with patch('services.schedule_dispatch_service.get_connection',
                       side_effect=Exception('DB connection pool exhausted')):
                with patch('services.schedule_dispatch_service.logger') as mock_logger:
                    with patch('services.schedule_dispatch_service.time.sleep', side_effect=KeyboardInterrupt):
                        with pytest.raises(KeyboardInterrupt):
                            ScheduleDispatchService._process_failed_queue()

                        # 验证 logger.error 被调用 (L357)
                        mock_logger.error.assert_called_once()
                        args, _ = mock_logger.error.call_args
                        assert '队列处理异常' in args[0]


# ============================================================
# 15. 补充覆盖: resend_dead_letter ConnectionError (L458)
# ============================================================

class TestRetryDeadLetterConnectionError:
    """retry_dead_letter — 外层 except requests.ConnectionError (L457-458)"""

    def test_retry_dead_letter_outer_connection_error(self, mock_retry_connections, mock_log_ui):
        """_actually_send 抛出 ConnectionError → 外层 except (L457-458) 捕获并返回"""
        from requests.exceptions import ConnectionError as ReqConnError

        conn1 = mock_retry_connections['conn']
        cursor1 = _ci(rowcount=1, fetchone_value={'payload': '{"order_no": "ORD001"}'})
        conn1.cursor.return_value = cursor1

        # _actually_send 在外层 retry_dead_letter 内部被调用 (L426: cls._actually_send(queue_id, payload))
        # patch 类方法直接 raise ConnectionError（绕过 _actually_send 内部的 except）
        with patch.object(ScheduleDispatchService, '_actually_send',
                          side_effect=ReqConnError('connection refused')):
            result = ScheduleDispatchService.retry_dead_letter(99)

        assert result['success'] is False
        assert '连接失败' in result['message']