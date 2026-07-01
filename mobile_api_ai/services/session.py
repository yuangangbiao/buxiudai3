# -*- coding: utf-8 -*-
"""
会话管理模块

管理用户会话状态
"""

import threading
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from core.config import SESSION_TIMEOUT

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器

    管理用户会话状态，支持：
    - 创建会话
    - 获取会话
    - 更新会话状态
    - 自动过期清理
    """

    DEFAULT_TIMEOUT = SESSION_TIMEOUT

    def __init__(self, timeout: int = None):
        """
        初始化会话管理器

        Args:
            timeout: 会话超时时间（秒），默认300秒
        """
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._sessions: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_session(self, user_id: str, initial_data: Dict = None) -> str:
        """
        创建会话

        Args:
            user_id: 用户ID
            initial_data: 初始数据

        Returns:
            str: 会话ID
        """
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        with self._lock:
            self._sessions[session_id] = {
                'session_id': session_id,
                'user_id': user_id,
                'created_at': datetime.now(),
                'last_active': datetime.now(),
                'data': initial_data or {},
                'state': 'active',
            }

        logger.debug(f"[SessionManager] 会话创建: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            Dict: 会话数据，如果不存在或已过期则返回None
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return None

            if self._is_expired(session):
                del self._sessions[session_id]
                logger.debug(f"[SessionManager] 会话已过期: {session_id}")
                return None

            session['last_active'] = datetime.now()
            return session.copy()

    def get_session_by_user(self, user_id: str) -> Optional[Dict]:
        """
        获取用户最近一个会话

        Args:
            user_id: 用户ID

        Returns:
            Dict: 会话数据
        """
        with self._lock:
            user_sessions = [
                s for s in self._sessions.values()
                if s['user_id'] == user_id and not self._is_expired(s)
            ]

            if not user_sessions:
                return None

            latest = max(user_sessions, key=lambda s: s['last_active'])
            latest['last_active'] = datetime.now()
            return latest.copy()

    def update_session(self, session_id: str, data: Dict) -> bool:
        """
        更新会话数据

        Args:
            session_id: 会话ID
            data: 要更新的数据

        Returns:
            bool: 更新是否成功
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return False

            session['data'].update(data)
            session['last_active'] = datetime.now()
            return True

    def set_state(self, session_id: str, state: str) -> bool:
        """
        设置会话状态

        Args:
            session_id: 会话ID
            state: 状态

        Returns:
            bool: 设置是否成功
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return False

            session['state'] = state
            session['last_active'] = datetime.now()
            return True

    def get_state(self, session_id: str) -> Optional[str]:
        """
        获取会话状态

        Args:
            session_id: 会话ID

        Returns:
            str: 状态
        """
        session = self.get_session(session_id)
        return session['state'] if session else None

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 删除是否成功
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"[SessionManager] 会话删除: {session_id}")
                return True
            return False

    def cleanup_expired(self) -> int:
        """
        清理过期会话

        Returns:
            int: 清理的会话数量
        """
        with self._lock:
            expired = [
                sid for sid, s in self._sessions.items()
                if self._is_expired(s)
            ]

            for sid in expired:
                del self._sessions[sid]

            if expired:
                logger.info(f"[SessionManager] 清理过期会话: {len(expired)} 个")

            return len(expired)

    def _is_expired(self, session: Dict) -> bool:
        """检查会话是否过期"""
        last_active = session.get('last_active')
        if not last_active:
            return True

        elapsed = (datetime.now() - last_active).total_seconds()
        return elapsed > self._timeout

    def get_all_sessions(self) -> list:
        """获取所有会话"""
        with self._lock:
            return [s.copy() for s in self._sessions.values()]

    def get_session_count(self) -> int:
        """获取会话数量"""
        with self._lock:
            return len(self._sessions)

    def clear_all(self):
        """清空所有会话"""
        with self._lock:
            self._sessions.clear()
            logger.info("[SessionManager] 所有会话已清空")


_session_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    获取会话管理器单例

    Returns:
        SessionManager: 会话管理器实例
    """
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance


def get_storage():
    """
    获取存储实例（内存模式，供 services.factory 使用）

    Returns:
        BaseStorage: 存储器实例（优先内存模式，测试友好）
    """
    try:
        from storage_layer import StorageFactory, StorageType
        # 优先返回已缓存的 MEMORY 实例，否则创建新的
        storage = StorageFactory.get_instance(StorageType.MEMORY)
        if storage is not None:
            return storage
        return StorageFactory.create(StorageType.MEMORY)
    except ImportError:
        logger.warning("[Storage] storage_layer 不可用，返回 None")
        return None
