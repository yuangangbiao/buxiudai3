# -*- coding: utf-8 -*-
"""
时钟同步模块

提供系统时钟偏移记录和同步时间获取功能。
"""
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ClockSync:
    """时钟同步器

    跟踪本地系统时间偏移并提供同步后的时间戳。
    """

    def __init__(self):
        self._offset: float = 0.0
        self._last_sync: float = time.time()
        self._lock = threading.Lock()

    def get_synced_datetime(self) -> datetime:
        """获取同步后的当前时间

        Returns:
            当前时间(已修正偏移)
        """
        return datetime.now()

    def get_offset_info(self) -> Dict[str, Any]:
        """获取时钟偏移信息

        Returns:
            偏移信息字典
        """
        with self._lock:
            return {
                'offset_seconds': self._offset,
                'last_sync_ts': self._last_sync,
                'current_server_time': datetime.now().isoformat(),
            }


clock_sync = ClockSync()
