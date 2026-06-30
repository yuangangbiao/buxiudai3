# -*- coding: utf-8 -*-
"""
[v3.7.1] DLQ retry worker 单元测试

覆盖 v3.7.0 实现的 _dlq_retry.py：
- start_dlq_retry_worker 幂等性
- 指数退避计算
- poison 标记逻辑
- message sender 注入
- 状态查询

完全 mock，不连接真实数据库。
"""
import os
import sys
import time
import threading
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# 测试期间禁用真实 DB 连接
os.environ['L1_TEST_MODE'] = 'true'


class TestDLQRetryWorker:
    """DLQ retry worker 测试"""

    @pytest.fixture(autouse=True)
    def reset_dlq_state(self):
        """每个测试前重置 worker 状态"""
        import importlib
        # [v3.7.6] 重置 sys.modules 中的缓存，强制 reload
        try:
            if 'mobile_api_ai.dispatch_center._dlq_retry' in importlib.import_module('sys').modules:
                mod = importlib.import_module('mobile_api_ai.dispatch_center._dlq_retry')
                importlib.reload(mod)
        except Exception:
            pass
        yield

    # ==================== start_dlq_retry_worker ====================

    def test_start_worker_first_time_returns_true(self):
        """首次启动返回 True"""
        from mobile_api_ai.dispatch_center._dlq_retry import start_dlq_retry_worker
        with patch('mobile_api_ai.dispatch_center._dlq_retry.threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            result = start_dlq_retry_worker()
            assert result is True
            mock_thread.assert_called_once()

    def test_start_worker_idempotent(self):
        """重复启动只生效一次"""
        from mobile_api_ai.dispatch_center._dlq_retry import start_dlq_retry_worker
        with patch('mobile_api_ai.dispatch_center._dlq_retry.threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            result1 = start_dlq_retry_worker()
            result2 = start_dlq_retry_worker()
            assert result1 is True
            assert result2 is False  # 第二次不启动
            mock_thread.assert_called_once()  # 只有一个线程

    # ==================== stop_dlq_retry_worker ====================

    def test_stop_worker_when_started(self):
        """worker 运行时停止"""
        from mobile_api_ai.dispatch_center._dlq_retry import start_dlq_retry_worker, stop_dlq_retry_worker
        with patch('mobile_api_ai.dispatch_center._dlq_retry.threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            start_dlq_retry_worker()
            result = stop_dlq_retry_worker()
            assert result is True

    def test_stop_worker_when_not_started(self):
        """worker 未启动时停止返回 False"""
        from mobile_api_ai.dispatch_center._dlq_retry import stop_dlq_retry_worker
        result = stop_dlq_retry_worker()
        assert result is False

    # ==================== get_dlq_stats ====================

    def test_get_dlq_stats_initial(self):
        """初始状态统计"""
        from mobile_api_ai.dispatch_center._dlq_retry import get_dlq_stats
        stats = get_dlq_stats()

        assert 'started' in stats
        assert 'last_run' in stats
        assert 'stats' in stats
        assert 'config' in stats
        assert stats['started'] is False
        assert stats['stats']['total_retries'] == 0
        assert stats['stats']['total_success'] == 0
        assert stats['stats']['total_failed'] == 0
        assert stats['stats']['total_poisoned'] == 0
        assert stats['config']['max_retries'] == 5

    def test_get_dlq_stats_after_start(self):
        """启动后统计"""
        from mobile_api_ai.dispatch_center._dlq_retry import start_dlq_retry_worker, get_dlq_stats
        with patch('mobile_api_ai.dispatch_center._dlq_retry.threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            start_dlq_retry_worker()
            stats = get_dlq_stats()
            assert stats['started'] is True

    # ==================== 指数退避 ====================

    def test_calc_next_retry_first_attempt(self):
        """第 1 次重试: 2^1=2 秒后"""
        from mobile_api_ai.dispatch_center._dlq_retry import _calc_next_retry
        before = int(time.time())
        result = _calc_next_retry(1)
        after = int(time.time())

        # 2 秒后
        assert before + 1 <= result <= after + 3

    def test_calc_next_retry_exponential_growth(self):
        """指数退避: 1→2→4→8→16→32"""
        from mobile_api_ai.dispatch_center._dlq_retry import _calc_next_retry

        now = int(time.time())
        assert _calc_next_retry(0) - now == 1   # 2^0 = 1
        assert _calc_next_retry(1) - now == 2   # 2^1 = 2
        assert _calc_next_retry(2) - now == 4   # 2^2 = 4
        assert _calc_next_retry(3) - now == 8   # 2^3 = 8
        assert _calc_next_retry(4) - now == 16  # 2^4 = 16
        assert _calc_next_retry(5) - now == 32  # 2^5 = 32

    def test_calc_next_retry_max_capped(self):
        """指数退避: 大于 5 次也持续增长（防雪崩）"""
        from mobile_api_ai.dispatch_center._dlq_retry import _calc_next_retry

        # 大于 5 次后，poison 标记介入，不再计算
        # 但函数本身仍能计算
        result = _calc_next_retry(10)
        now = int(time.time())
        # 2^10 = 1024 秒
        assert result - now == 1024

    # ==================== message sender 注入 ====================

    def test_register_message_sender(self):
        """注册 message sender"""
        from mobile_api_ai.dispatch_center._dlq_retry import (
            register_message_sender,
            _get_message_sender,
        )

        def my_sender(payload):
            return True

        register_message_sender(my_sender)
        assert _get_message_sender() is my_sender

    def test_get_message_sender_initial_none(self):
        """未注册时 sender 为 None"""
        # 重置模块状态
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry
        _dlq_retry._message_sender = None
        assert _dlq_retry._get_message_sender() is None

    # ==================== _resend_message ====================

    def test_resend_message_no_sender(self):
        """无 sender 时返回 False"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry
        _dlq_retry._message_sender = None

        result = _dlq_retry._resend_message({'key': 'value'})
        assert result is False

    def test_resend_message_success(self):
        """sender 返回 True"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def my_sender(payload):
            return True
        _dlq_retry._message_sender = my_sender

        result = _dlq_retry._resend_message({'key': 'value'})
        assert result is True

    def test_resend_message_failure(self):
        """sender 返回 False"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def my_sender(payload):
            return False
        _dlq_retry._message_sender = my_sender

        result = _dlq_retry._resend_message({'key': 'value'})
        assert result is False

    def test_resend_message_sender_raises(self):
        """sender 抛异常时返回 False（不中断 worker）"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def bad_sender(payload):
            raise RuntimeError('网络错误')

        _dlq_retry._message_sender = bad_sender

        result = _dlq_retry._resend_message({'key': 'value'})
        assert result is False  # 不应抛异常

    def test_resend_message_string_payload(self):
        """字符串 payload 自动解析 JSON"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        captured = []

        def my_sender(payload):
            captured.append(payload)
            return True

        _dlq_retry._message_sender = my_sender
        result = _dlq_retry._resend_message('{"key":"value"}')

        assert result is True
        assert len(captured) == 1
        assert captured[0] == {'key': 'value'}

    def test_resend_message_invalid_json(self):
        """无效 JSON 字符串返回 False"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def my_sender(payload):
            return True
        _dlq_retry._message_sender = my_sender

        result = _dlq_retry._resend_message('not valid json {')
        assert result is False

    # ==================== _dlq_retry_once ====================

    def test_dlq_retry_once_no_records(self):
        """无待重试记录时返回 0"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=[]):
            result = _dlq_retry._dlq_retry_once()
            assert result == 0

    def test_dlq_retry_once_all_success(self):
        """全部成功"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        records = [
            {'id': 1, 'payload': '{"k":"v1"}', 'retry_count': 0},
            {'id': 2, 'payload': '{"k":"v2"}', 'retry_count': 0},
        ]

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=records), \
             patch.object(_dlq_retry, '_try_retry_one', return_value=True), \
             patch.object(_dlq_retry, '_mark_as_poison') as mock_poison, \
             patch.object(_dlq_retry, '_delete_dlq_record') as mock_delete:

            result = _dlq_retry._dlq_retry_once()
            assert result == 2  # 2 个成功
            assert mock_poison.call_count == 0  # 无 poison
            assert _dlq_retry._DLQ_STATS['total_success'] == 2
            assert _dlq_retry._DLQ_STATS['total_failed'] == 0

    def test_dlq_retry_once_all_failed(self):
        """全部失败"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        records = [
            {'id': 1, 'payload': '{"k":"v1"}', 'retry_count': 0},
        ]

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=records), \
             patch.object(_dlq_retry, '_try_retry_one', return_value=False), \
             patch.object(_dlq_retry, '_mark_as_poison') as mock_poison:

            result = _dlq_retry._dlq_retry_once()
            assert result == 0  # 0 个成功
            assert _dlq_retry._DLQ_STATS['total_failed'] == 1

    def test_dlq_retry_once_poison_marking(self):
        """retry_count >= max 标记为 poison"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        # 第 6 次重试（>= max 5）
        records = [
            {'id': 1, 'payload': '{"k":"v1"}', 'retry_count': 5},
        ]

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=records), \
             patch.object(_dlq_retry, '_try_retry_one', return_value=False), \
             patch.object(_dlq_retry, '_mark_as_poison') as mock_poison:

            _dlq_retry._dlq_retry_once()
            mock_poison.assert_called_once_with(1)
            assert _dlq_retry._DLQ_STATS['total_poisoned'] == 1

    def test_dlq_retry_once_continue_on_exception(self):
        """单条失败不中断其他记录"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        records = [
            {'id': 1, 'payload': '{"k":"v1"}', 'retry_count': 0},
            {'id': 2, 'payload': '{"k":"v2"}', 'retry_count': 0},
        ]

        def side_effect(record):
            if record['id'] == 1:
                raise RuntimeError('单条失败')
            return True

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=records), \
             patch.object(_dlq_retry, '_try_retry_one', side_effect=side_effect), \
             patch.object(_dlq_retry, '_mark_as_poison'):

            result = _dlq_retry._dlq_retry_once()
            assert result == 1  # 第 2 条成功
            assert _dlq_retry._DLQ_STATS['total_failed'] == 1  # 第 1 条失败

    # ==================== _try_retry_one ====================

    def test_try_retry_one_empty_payload(self):
        """空 payload 返回 False"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        record = {'id': 1, 'payload': None, 'retry_count': 0}
        result = _dlq_retry._try_retry_one(record)
        assert result is False

    def test_try_retry_one_success(self):
        """成功重试"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def my_sender(payload):
            return True
        _dlq_retry._message_sender = my_sender

        record = {'id': 1, 'payload': '{"k":"v"}', 'retry_count': 0}

        with patch.object(_dlq_retry, '_delete_dlq_record') as mock_delete:
            result = _dlq_retry._try_retry_one(record)
            assert result is True
            mock_delete.assert_called_once_with(1)

    def test_try_retry_one_failure_increments_retry(self):
        """失败时增加 retry_count"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        def bad_sender(payload):
            return False
        _dlq_retry._message_sender = bad_sender

        record = {'id': 1, 'payload': '{"k":"v"}', 'retry_count': 2}

        with patch.object(_dlq_retry, '_update_dlq_retry_count') as mock_update:
            result = _dlq_retry._try_retry_one(record)
            assert result is False
            # 验证 retry_count 从 2 增加到 3
            args, kwargs = mock_update.call_args
            assert args[0] == 1  # record_id
            assert args[1] == 3  # retry_count + 1
            # 验证 next_retry_at = now + 2^3 = now + 8
            assert args[2] - int(time.time()) in (7, 8, 9)

    # ==================== 配置覆盖 ====================

    def test_environment_overrides_config(self):
        """环境变量可覆盖默认配置"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        # 修改环境变量
        os.environ['DLQ_RETRY_INTERVAL'] = '60'
        os.environ['DLQ_BATCH_SIZE'] = '200'
        os.environ['DLQ_MAX_RETRIES'] = '10'

        # 重新加载模块
        import importlib
        importlib.reload(_dlq_retry)

        # 验证配置
        assert _dlq_retry._DLQ_RETRY_INTERVAL == 60
        assert _dlq_retry._DLQ_BATCH_SIZE == 200
        assert _dlq_retry._DLQ_MAX_RETRIES == 10

        # 清理
        del os.environ['DLQ_RETRY_INTERVAL']
        del os.environ['DLQ_BATCH_SIZE']
        del os.environ['DLQ_MAX_RETRIES']


class TestDLQRetryStats:
    """DLQ retry 统计测试"""

    def test_stats_accumulate(self):
        """统计累加"""
        import mobile_api_ai.dispatch_center._dlq_retry as _dlq_retry

        # 重置
        _dlq_retry._DLQ_STATS = {
            'total_retries': 0,
            'total_success': 0,
            'total_failed': 0,
            'total_poisoned': 0,
        }

        records = [
            {'id': 1, 'payload': '{"k":"v1"}', 'retry_count': 0},
            {'id': 2, 'payload': '{"k":"v2"}', 'retry_count': 0},
        ]

        # 两次 _dlq_retry_once 调用，每次都有 2 条记录
        # 1 次成功 + 1 次失败 = 2 retries
        # 第 1 次: 成功 1, 失败 1
        # 第 2 次: 成功 1, 失败 1
        call_count = {'n': 0}

        def try_retry(record):
            call_count['n'] += 1
            return call_count['n'] % 2 == 1  # 奇数成功，偶数失败

        with patch.object(_dlq_retry, '_fetch_pending_dlq_records', return_value=records), \
             patch.object(_dlq_retry, '_try_retry_one', side_effect=try_retry), \
             patch.object(_dlq_retry, '_mark_as_poison'):

            _dlq_retry._dlq_retry_once()
            _dlq_retry._dlq_retry_once()

        assert _dlq_retry._DLQ_STATS['total_retries'] == 4
        assert _dlq_retry._DLQ_STATS['total_success'] == 2
        assert _dlq_retry._DLQ_STATS['total_failed'] == 2
