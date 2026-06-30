# -*- coding: utf-8 -*-
"""
process_tracker.py 单元测试
"""

import os
import tempfile

import pytest

# 设置有效路径，避免 ModularConfig.get_container_db_path() 返回 MySQL URL 被误当路径
os.environ['CONTAINER_DB_PATH'] = os.path.join(tempfile.gettempdir(), 'test_container.db')


class TestProcessTracker:

    def setup_method(self):
        """每个测试前重置 process_tracker 全局实例"""
        from process_tracker import reset_process_tracker
        reset_process_tracker()

    def test_tracker_init(self):
        """验证追踪器初始化"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        assert tracker is not None
        assert hasattr(tracker, 'track_process')
        assert hasattr(tracker, 'get_order_processes')
        assert hasattr(tracker, 'get_current_process')

    def test_track_process_pending(self):
        """验证记录待处理工序"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        result = tracker.track_process(
            order_no='TEST001',
            process_name='编织',
            status='pending',
            operator_id='OP001'
        )
        assert isinstance(result, bool)

    def test_track_process_in_progress(self):
        """验证记录进行中工序"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        result = tracker.track_process(
            order_no='TEST002',
            process_name='质检',
            status='in_progress',
            operator_id='OP002'
        )
        assert isinstance(result, bool)

    def test_track_process_invalid_status(self):
        """验证无效状态处理"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        result = tracker.track_process(
            order_no='TEST003',
            process_name='包装',
            status='invalid_status'
        )
        assert not result

    def test_get_order_processes(self):
        """验证获取订单工序列表"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        tracker.track_process('TEST004', '工序1', 'pending')
        tracker.track_process('TEST004', '工序2', 'in_progress')

        processes = tracker.get_order_processes('TEST004')
        assert isinstance(processes, list)

    def test_get_current_process(self):
        """验证获取当前工序"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        tracker.track_process('TEST005', '编织', 'pending')
        tracker.track_process('TEST005', '质检', 'in_progress')

        current = tracker.get_current_process('TEST005')
        assert current is not None
        assert current.get('process_name') == '质检'
        assert current.get('status') == 'in_progress'

    def test_get_current_process_none(self):
        """验证无当前工序时返回None"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        processes = tracker.get_order_processes('NONEXISTENT')
        current = tracker.get_current_process('NONEXISTENT')
        assert current is None

    def test_complete_process(self):
        """验证完成工序"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        tracker.track_process('TEST006', '编织', 'in_progress')
        result = tracker.complete_process('TEST006', '编织', completed_qty=100)
        assert isinstance(result, bool)

    def test_start_process(self):
        """验证开始工序"""
        from process_tracker import ProcessTracker

        tracker = ProcessTracker()
        result = tracker.start_process(
            order_no='TEST007',
            process_name='编织',
            operator_id='OP001',
            quantity=100
        )
        assert result


class TestProcessTrackerSingleton:

    def setup_method(self):
        from process_tracker import reset_process_tracker
        reset_process_tracker()

    def test_get_process_tracker(self):
        """验证获取全局实例"""
        from process_tracker import get_process_tracker, reset_process_tracker

        reset_process_tracker()
        tracker1 = get_process_tracker()
        tracker2 = get_process_tracker()
        assert tracker1 is tracker2

    def test_reset_process_tracker(self):
        """验证重置功能"""
        from process_tracker import get_process_tracker, reset_process_tracker

        tracker1 = get_process_tracker()
        reset_process_tracker()
        tracker2 = get_process_tracker()
        assert tracker1 is not tracker2
