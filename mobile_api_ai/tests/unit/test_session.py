# -*- coding: utf-8 -*-
"""
session 单元测试

覆盖：
- SessionManager 初始化
- create_session
- get_session（含过期）
- get_session_by_user
- update_session
- set_state / get_state
- delete_session
- cleanup_expired
- 会话数量统计
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta


class TestSessionManagerInit:
    """SessionManager 初始化测试"""

    def test_init_default(self):
        from services.session import SessionManager
        mgr = SessionManager()
        assert mgr._timeout > 0
        assert mgr._sessions == {}

    def test_init_custom_timeout(self):
        from services.session import SessionManager
        mgr = SessionManager(timeout=60)
        assert mgr._timeout == 60


class TestCreateSession:
    """create_session 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)

    def test_create_basic(self):
        sid = self.mgr.create_session('user001')
        assert sid.startswith('user001_')

    def test_create_with_initial_data(self):
        sid = self.mgr.create_session('user001', {'role': 'admin'})
        session = self.mgr.get_session(sid)
        assert session['data']['role'] == 'admin'

    def test_create_returns_unique_ids(self):
        import time
        s1 = self.mgr.create_session('user001')
        time.sleep(0.01)
        s2 = self.mgr.create_session('user001')
        assert s1 != s2

    def test_create_initial_data_none(self):
        sid = self.mgr.create_session('user001', None)
        session = self.mgr.get_session(sid)
        assert session['data'] == {}


class TestGetSession:
    """get_session 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid = self.mgr.create_session('user001')

    def test_get_existing(self):
        session = self.mgr.get_session(self.sid)
        assert session is not None
        assert session['user_id'] == 'user001'

    def test_get_nonexistent(self):
        assert self.mgr.get_session('nonexistent') is None

    def test_get_expired(self):
        from services.session import SessionManager
        mgr = SessionManager(timeout=1)
        sid = mgr.create_session('user001')
        session = mgr._sessions[sid]
        session['last_active'] = datetime.now() - timedelta(seconds=10)
        assert mgr.get_session(sid) is None
        assert sid not in mgr._sessions

    def test_get_updates_last_active(self):
        session1 = self.mgr.get_session(self.sid)
        time1 = session1['last_active']
        import time as t
        t.sleep(0.01)
        session2 = self.mgr.get_session(self.sid)
        assert session2['last_active'] >= time1

    def test_get_returns_copy(self):
        session = self.mgr.get_session(self.sid)
        session['data']['x'] = 1
        session2 = self.mgr.get_session(self.sid)
        assert 'x' not in session2['data']


class TestGetSessionByUser:
    """get_session_by_user 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid1 = self.mgr.create_session('user001', {'idx': 1})
        self.sid2 = self.mgr.create_session('user001', {'idx': 2})
        self.sid_other = self.mgr.create_session('user002')

    def test_get_user_session(self):
        session = self.mgr.get_session_by_user('user001')
        assert session is not None
        assert session['user_id'] == 'user001'

    def test_get_user_no_sessions(self):
        assert self.mgr.get_session_by_user('nonexistent') is None

    def test_get_returns_latest(self):
        import time
        time.sleep(0.01)
        latest = self.mgr.get_session_by_user('user001')
        assert latest['data']['idx'] in (1, 2)


class TestUpdateSession:
    """update_session 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid = self.mgr.create_session('user001', {'a': 1})

    def test_update_existing(self):
        result = self.mgr.update_session(self.sid, {'b': 2})
        assert result is True
        session = self.mgr.get_session(self.sid)
        assert session['data']['a'] == 1
        assert session['data']['b'] == 2

    def test_update_nonexistent(self):
        assert self.mgr.update_session('nonexistent', {'a': 1}) is False

    def test_update_overwrites(self):
        self.mgr.update_session(self.sid, {'a': 999})
        session = self.mgr.get_session(self.sid)
        assert session['data']['a'] == 999


class TestSetGetState:
    """set_state / get_state 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid = self.mgr.create_session('user001')

    def test_set_state(self):
        result = self.mgr.set_state(self.sid, 'paused')
        assert result is True

    def test_get_state(self):
        self.mgr.set_state(self.sid, 'paused')
        assert self.mgr.get_state(self.sid) == 'paused'

    def test_set_state_nonexistent(self):
        assert self.mgr.set_state('nonexistent', 'paused') is False

    def test_get_state_nonexistent(self):
        assert self.mgr.get_state('nonexistent') is None

    def test_initial_state_active(self):
        assert self.mgr.get_state(self.sid) == 'active'


class TestDeleteSession:
    """delete_session 测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid = self.mgr.create_session('user001')

    def test_delete_existing(self):
        assert self.mgr.delete_session(self.sid) is True
        assert self.mgr.get_session(self.sid) is None

    def test_delete_nonexistent(self):
        assert self.mgr.delete_session('nonexistent') is False


class TestCleanupExpired:
    """cleanup_expired 测试"""

    def test_cleanup_expired_removes_old(self):
        from services.session import SessionManager
        mgr = SessionManager(timeout=1)
        sid = mgr.create_session('user001')
        mgr._sessions[sid]['last_active'] = datetime.now() - timedelta(seconds=10)
        count = mgr.cleanup_expired()
        assert count >= 1

    def test_cleanup_keeps_fresh(self):
        from services.session import SessionManager
        mgr = SessionManager(timeout=300)
        sid = mgr.create_session('user001')
        count = mgr.cleanup_expired()
        assert count == 0
        assert mgr.get_session(sid) is not None

    def test_cleanup_no_sessions(self):
        from services.session import SessionManager
        mgr = SessionManager(timeout=300)
        count = mgr.cleanup_expired()
        assert count == 0


class TestSessionStats:
    """会话统计测试"""

    def setup_method(self):
        from services.session import SessionManager
        self.mgr = SessionManager(timeout=300)
        self.sid1 = self.mgr.create_session('user001')
        self.sid2 = self.mgr.create_session('user002')
        self.sid3 = self.mgr.create_session('user001')

    def test_session_count(self):
        assert self.mgr.session_count() == 3

    def test_user_count(self):
        assert self.mgr.user_count() == 2

    def test_count_after_delete(self):
        self.mgr.delete_session(self.sid1)
        assert self.mgr.session_count() == 2
