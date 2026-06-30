# -*- coding: utf-8 -*-
"""批量覆盖：json_safe / error_codes_structured / events"""
import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# json_safe.py
# ============================================================
class TestJsonSafe:
    def test_allows_json_content_type(self):
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        with app.test_request_context(
            '/api/test', method='POST',
            content_type='application/json',
            data='{"key":"val"}'
        ):
            @require_json_content_type
            def handler():
                return 'ok'
            result = handler()
            # handler returns ('ok',) or just 'ok' depending on Flask internals
            # The decorator passes through func() return which is 'ok'
            assert result == 'ok' or (isinstance(result, tuple) and result[0] == 'ok')

    def test_allows_text_plain(self):
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        with app.test_request_context(
            '/api/test', method='POST',
            content_type='text/plain',
            data='plain text'
        ):
            @require_json_content_type
            def handler():
                return 'ok'
            result = handler()
            assert result == 'ok' or (isinstance(result, tuple) and result[0] == 'ok')

    def test_rejects_form_data(self):
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        with app.test_request_context(
            '/api/test', method='POST',
            content_type='application/x-www-form-urlencoded',
            data='key=val'
        ):
            @require_json_content_type
            def handler():
                return 'ok'
            resp, status = handler()
            assert status == 415
            assert 'application/json' in resp.json['message']

    def test_skips_get_requests(self):
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        with app.test_request_context(
            '/api/test', method='GET'
        ):
            @require_json_content_type
            def handler():
                return 'ok'
            resp = handler()
            assert resp == 'ok'

    def test_skips_delete_requests(self):
        """DELETE 不在检查范围内"""
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        with app.test_request_context(
            '/api/test', method='DELETE',
            content_type='text/html'
        ):
            @require_json_content_type
            def handler():
                return 'ok'
            resp = handler()
            assert resp == 'ok'

    def test_no_content_type_header(self):
        from flask import Flask
        from core.json_safe import require_json_content_type

        app = Flask(__name__)
        # 测试 environ 中没有 CONTENT_TYPE
        with app.test_request_context('/api/test', method='POST', environ_base={}):
            @require_json_content_type
            def handler():
                return 'ok'
            resp, status = handler()
            assert status == 415


# ============================================================
# error_codes_structured.py
# ============================================================
class TestErrorCode:
    def test_basic_init(self):
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E9999", "测试错误", "test", "error", 400)
        assert ec.code == "E9999"
        assert ec.message == "测试错误"
        assert ec.domain == "test"
        assert ec.severity == "error"
        assert ec.http_status == 400

    def test_default_http_status(self):
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E0001", "msg", "system", "error")
        assert ec.http_status == 500

    def test_repr(self):
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E1001", "订单不存在", "order", "error", 404)
        r = repr(ec)
        assert "E1001" in r
        assert "订单不存在" in r

    def test_eq_same_code_true(self):
        from core.error_codes_structured import ErrorCode
        a = ErrorCode("E1001", "a", "x", "error")
        b = ErrorCode("E1001", "b", "y", "warning")
        assert a == b

    def test_eq_different_code_false(self):
        from core.error_codes_structured import ErrorCode
        a = ErrorCode("E1001", "a", "x", "error")
        b = ErrorCode("E1002", "a", "x", "error")
        assert a != b

    def test_eq_non_errorcode(self):
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E1001", "a", "x", "error")
        assert (ec == "E1001") is False


class TestErrorDomain:
    def test_constants(self):
        from core.error_codes_structured import ErrorDomain
        assert ErrorDomain.ORDER == "order"
        assert ErrorDomain.PRODUCTION == "production"
        assert ErrorDomain.QUALITY == "quality"
        assert ErrorDomain.INVENTORY == "inventory"
        assert ErrorDomain.SYSTEM == "system"
        assert ErrorDomain.AUTH == "auth"


class TestErrorSeverity:
    def test_constants(self):
        from core.error_codes_structured import ErrorSeverity
        assert ErrorSeverity.CRITICAL == "critical"
        assert ErrorSeverity.ERROR == "error"
        assert ErrorSeverity.WARNING == "warning"


class TestErrorsDict:
    def test_keys_exist(self):
        from core.error_codes_structured import ERRORS
        assert "ORDER_NOT_FOUND" in ERRORS
        assert "DATABASE_ERROR" in ERRORS
        assert "AUTH_FAILED" in ERRORS
        assert "INVENTORY_SHORTAGE" in ERRORS

    def test_order_not_found_details(self):
        from core.error_codes_structured import ERRORS
        ec = ERRORS["ORDER_NOT_FOUND"]
        assert ec.code == "E1001"
        assert ec.http_status == 404
        assert ec.domain == "order"

    def test_module_level_aliases(self):
        from core.error_codes_structured import (
            ORDER_NOT_FOUND, ORDER_STATUS_INVALID, ORDER_CREATE_FAILED,
            VALIDATION_FAILED, DATABASE_ERROR
        )
        assert ORDER_NOT_FOUND.code == "E1001"
        assert ORDER_STATUS_INVALID.code == "E1002"
        assert ORDER_CREATE_FAILED.code == "E1003"
        assert VALIDATION_FAILED.code == "E2001"
        assert DATABASE_ERROR.code == "E3001"


# ============================================================
# events.py 补充覆盖率 (77% → ~95%)
# ============================================================
class TestEvents:
    def test_event_types_defined(self):
        from core.events import EventType
        assert EventType.ORDER_CREATED == 'order:created'
        assert EventType.PROCESS_COMPLETED == 'process:completed'
        assert EventType.QC_PASSED == 'qc:passed'
        assert EventType.INVENTORY_LOW == 'inventory:low'
        assert EventType.SYSTEM_READY == 'system:ready'

    def test_get_all_events(self):
        from core.events import EventType
        events = EventType.get_all_events()
        assert isinstance(events, list)
        assert 'ORDER_CREATED' in events
        assert 'PROCESS_COMPLETED' in events
        assert 'SYSTEM_READY' in events

    def test_is_valid_event_name(self):
        from core.events import EventType
        assert EventType.is_valid_event('ORDER_CREATED') is True
        assert EventType.is_valid_event('NONEXISTENT') is False

    def test_is_valid_event_value(self):
        from core.events import EventType
        assert EventType.is_valid_event('order:created') is True
        assert EventType.is_valid_event('bogus:stuff') is False

    def test_get_event_category(self):
        from core.events import EventType
        assert EventType.get_event_category('order:created') == 'order'
        assert EventType.get_event_category('process:completed') == 'process'
        assert EventType.get_event_category('no_colon') == 'unknown'

    def test_event_data_basic(self):
        from core.events import EventData
        ed = EventData('order:created', {'id': 1})
        assert ed.event == 'order:created'
        assert ed.data == {'id': 1}
        assert ed.timestamp is None

    def test_event_data_default_data(self):
        from core.events import EventData
        ed = EventData('system:ready')
        assert ed.data == {}

    def test_event_data_get_set(self):
        from core.events import EventData
        ed = EventData('test:event', {'a': 1})
        assert ed.get('a') == 1
        assert ed.get('missing', 'default') == 'default'
        ed.set('b', 2)
        assert ed.data['b'] == 2

    def test_event_data_to_dict(self):
        from core.events import EventData
        ed = EventData('order:created', {'id': 5})
        d = ed.to_dict()
        assert d['event'] == 'order:created'
        assert d['data'] == {'id': 5}
        assert 'timestamp' in d

    def test_event_data_repr(self):
        from core.events import EventData
        ed = EventData('order:created', {'id': 1})
        r = repr(ed)
        assert 'order:created' in r
        assert 'id' in r

    def test_create_event_factory(self):
        from core.events import create_event, EventType
        ed = create_event(
            EventType.ORDER_CREATED,
            order_id=123,
            order_no='WB-2025-0501',
        )
        assert ed.event == 'order:created'
        assert ed.data['order_id'] == 123
        assert ed.data['order_no'] == 'WB-2025-0501'
