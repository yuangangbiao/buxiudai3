# -*- coding: utf-8 -*-
"""
数据完整性及漂移检测模块

提供数据完整性校验(checksum)和时间/数量漂移检测功能。
"""
import hashlib
import json
import time
import logging
import threading
from typing import Any, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class DataIntegrity:
    """数据完整性校验器

    为请求载荷计算校验和，确保数据传输完整性。
    """

    def calculate_hash(self, payload: Dict[str, Any]) -> str:
        """计算载荷的 SHA256 校验和

        Args:
            payload: 需要计算校验和的字典数据

        Returns:
            十六进制 SHA256 哈希字符串
        """
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class DriftDetector:
    """漂移检测器

    检测客户端与服务端之间的时间漂移和数量漂移。
    """

    def __init__(self, tolerance_seconds: float = 5.0):
        """初始化漂移检测器

        Args:
            tolerance_seconds: 时间漂移容忍阈值(秒)
        """
        self.tolerance_seconds = tolerance_seconds
        self._total_checks = 0
        self._drift_count = 0
        self._max_drift = 0.0
        self._lock = threading.Lock()

    def detect_time_drift(self, client_timestamp: float) -> Tuple[bool, float]:
        """检测时间漂移

        Args:
            client_timestamp: 客户端时间戳(秒)

        Returns:
            (has_drift, offset_seconds): 是否存在漂移、偏移秒数
        """
        server_ts = time.time()
        offset = abs(server_ts - client_timestamp)
        has_drift = offset > self.tolerance_seconds

        with self._lock:
            self._total_checks += 1
            if has_drift:
                self._drift_count += 1
            if offset > self._max_drift:
                self._max_drift = offset

        return has_drift, round(offset, 3)

    def detect_quantity_drift(
        self, original_quantity: float, reported_quantity: float
    ) -> Tuple[bool, float]:
        """检测数量漂移

        Args:
            original_quantity: 原始数量
            reported_quantity: 上报数量

        Returns:
            (has_drift, drift_percent): 是否存在漂移、漂移百分比
        """
        if original_quantity == 0:
            return False, 0.0

        drift_percent = abs(reported_quantity - original_quantity) / original_quantity * 100
        has_drift = drift_percent > 10.0

        return has_drift, round(drift_percent, 2)

    def get_statistics(self) -> Dict[str, Any]:
        """获取漂移检测统计信息

        Returns:
            统计字典
        """
        with self._lock:
            return {
                'total_checks': self._total_checks,
                'drift_count': self._drift_count,
                'max_drift_seconds': round(self._max_drift, 3),
                'tolerance_seconds': self.tolerance_seconds,
            }


drift_detector = DriftDetector()
