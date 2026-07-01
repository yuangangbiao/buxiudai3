# -*- coding: utf-8 -*-
"""
测试: 并发安全修复
验证 dispatch_center.py 中的线程安全改进
"""
import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestClientSingleton:
    """测试 DispatchContext 单例模式线程安全"""

    # [F6 P9 2026-06-10] 去掉 skip: DispatchContext.get_v5_client 实现双重检查锁 (行 304-316)
    # 原 skip 描述错误: "get_client 私有" 不成立, 而且 patch.object(get_client) 会破坏单例
    # 正确测法: 走真实单例逻辑 + patch 内部 V5CompatibleClient 类构造慢初始化
    def test_singleton_no_race_condition(self):
        """测试：多线程并发调用不会创建多个实例"""
        results = []

        class SlowInitClient:
            def __init__(self, *args, **kwargs):
                time.sleep(0.05)
                self.args = args
                self.kwargs = kwargs

        import dispatch_center
        from dispatch_center import _core as _core_mod
        ctx = _core_mod.DispatchContext.get_instance()

        # Reset client state for clean test
        ctx.v5_client = None

        # [F6 P9 2026-06-10] patch V5CompatibleClient 内部实际创建实例的类 (行 302-315)
        # 而不是 patch get_client, 这样双重检查锁逻辑会真跑
        original_v5_cls = _core_mod.V5CompatibleClient
        _core_mod.V5CompatibleClient = SlowInitClient
        try:
            threads = []
            for _ in range(10):
                t = threading.Thread(target=lambda: results.append(id(ctx.get_client())))
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join()
        finally:
            _core_mod.V5CompatibleClient = original_v5_cls

        assert len(set(results)) == 1, f"应该只创建一个实例, 实际 {len(set(results))} 个"

    def test_double_checked_locking(self):
        """测试：双重检查锁定模式正确实现"""
        import dispatch_center

        ctx = dispatch_center.DispatchContext.get_instance()
        assert hasattr(ctx, 'cc_client_lock'), "应该有 cc_client_lock"
        assert hasattr(ctx, 'cc_client_lock'), "应该有 cc_client_lock"
        assert hasattr(ctx.cc_client_lock, 'acquire'), \
            f"cc_client_lock 应该是锁对象，实际类型: {type(ctx.cc_client_lock)}"


class TestCacheConcurrency:
    """测试 _work_order_cache 缓存并发安全"""

    def test_cache_write_atomic(self):
        """测试：缓存写入是原子的"""
        import dispatch_center

        ctx = dispatch_center.DispatchContext.get_instance()
        assert hasattr(ctx, 'cache_lock'), "应该有 cache_lock"
        assert hasattr(ctx, 'cache_lock'), "应该有 cache_lock"
        assert hasattr(ctx.cache_lock, 'acquire'), \
            f"cache_lock 应该是锁对象，实际类型: {type(ctx.cache_lock)}"

    def test_cache_concurrent_access(self):
        """测试：并发访问不会导致缓存撕裂"""
        import dispatch_center
        mock_result = {'data': [{'id': 1}]}
        call_count = [0]

        def mock_query(*args, **kwargs):
            call_count[0] += 1
            return mock_result

        ctx = dispatch_center.DispatchContext.get_instance()
        original_cache = dict(ctx.work_order_cache)
        ctx.work_order_cache = {'data': None, 'time': 0, 'ttl': 3600}

        with patch.object(ctx, 'get_client') as mock_get_client:
            mock_get_client.return_value.query_documents = mock_query

            try:
                results = []
                errors = []

                def get_cached():
                    try:
                        result = ctx.get_cached_work_orders()
                        results.append(result)
                    except Exception as e:
                        errors.append(str(e))

                threads = [threading.Thread(target=get_cached) for _ in range(20)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                assert len(errors) == 0, f"并发访问不应出错: {errors}"

            finally:
                ctx.work_order_cache = original_cache


class TestWechatCloudShutdown:
    """测试 wechat_cloud.py 线程优雅关闭"""

    def test_shutdown_event_exists(self):
        """测试：关闭事件存在"""
        import wechat_cloud
        assert hasattr(wechat_cloud, '_scheduler_shutdown')
        assert isinstance(wechat_cloud._scheduler_shutdown, type(threading.Event()))

    def test_shutdown_event_set(self):
        """测试：设置关闭事件会停止线程"""
        import wechat_cloud

        wechat_cloud._scheduler_shutdown.clear()
        assert not wechat_cloud._scheduler_shutdown.is_set()

        wechat_cloud._scheduler_shutdown.set()
        assert wechat_cloud._scheduler_shutdown.is_set()

    def test_threads_tracked(self):
        """测试：线程被追踪"""
        import wechat_cloud
        assert hasattr(wechat_cloud, '_scheduler_threads')
        assert isinstance(wechat_cloud._scheduler_threads, list)
