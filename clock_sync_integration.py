# -*- coding: utf-8 -*-
"""
时钟同步模块

为主系统提供与云端服务器的时间同步能力
基于 mobile_api_ai/modules/clock_sync.py 封装
"""

import os
import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

CHINA_TZ = timezone(timedelta(hours=8))


class ClockSync:
    """时钟同步器"""

    def __init__(
        self,
        ntp_server: str = "ntp.aliyun.com",
        ntp_port: int = 123,
        timeout: float = 5.0
    ):
        """
        初始化时钟同步器

        Args:
            ntp_server: NTP服务器地址
            ntp_port: NTP端口
            timeout: 超时时间（秒）
        """
        self.ntp_server = ntp_server
        self.ntp_port = ntp_port
        self.timeout = timeout
        self._offset = 0.0
        self._last_sync_time: Optional[float] = None
        self._sync_count = 0

    def get_offset(self) -> float:
        """获取时间偏移量（秒）"""
        return self._offset

    def get_local_time(self) -> datetime:
        """获取本地时间"""
        return datetime.now(CHINA_TZ)

    def get_synced_time(self) -> datetime:
        """获取同步后的时间"""
        return datetime.fromtimestamp(time.time() + self._offset, CHINA_TZ)

    def sync_with_ntp(self) -> Tuple[bool, float]:
        """
        与NTP服务器同步时间

        Returns:
            (是否成功, 时间偏移量)
        """
        try:
            import socket

            ntp_packet = self._build_ntp_packet()
            response_time = time.time()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)

            sock.sendto(ntp_packet, (self.ntp_server, self.ntp_port))
            response, _ = sock.recvfrom(1024)
            receive_time = time.time()

            sock.close()

            self._offset = self._calculate_offset(response, receive_time, response_time)
            self._last_sync_time = time.time()
            self._sync_count += 1

            logger.info(
                f"NTP同步成功: 服务器={self.ntp_server}, "
                f"偏移量={self._offset:.3f}秒, "
                f"同步次数={self._sync_count}"
            )

            return True, self._offset

        except ImportError:
            logger.warning("socket模块不可用，NTP同步失败")
            return False, 0.0
        except Exception as e:
            logger.error(f"NTP同步失败: {e}")
            return False, 0.0

    def _build_ntp_packet(self) -> bytes:
        """构建NTP请求包"""
        packet = bytearray(48)
        packet[0] = 0x1B
        return bytes(packet)

    def _calculate_offset(self, response: bytes, receive_time: float, transmit_time: float) -> float:
        """计算时间偏移量"""
        try:
            transmit_seconds = int.from_bytes(response[40:44], 'big')
            transmit_fraction = int.from_bytes(response[44:48], 'big')

            t1 = ((transmit_seconds & 0x7FFFFFFF) - 2208988800) + transmit_fraction / 2**32
            t2 = receive_time
            t3 = transmit_time

            round_trip = t3 - t1
            offset = ((t2 - t1) + (t3 - t2)) / 2

            return offset

        except Exception as e:
            logger.error(f"计算偏移量失败: {e}")
            return 0.0

    def sync_with_http(self) -> Tuple[bool, float]:
        """
        通过HTTP获取服务器时间

        Returns:
            (是否成功, 时间偏移量)
        """
        try:
            import urllib.request

            url = os.getenv('TIME_SERVER_URL', 'http://www.baidu.com')

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            start_time = time.time()

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                receive_time = time.time()
                date_header = response.headers.get('Date')

            if date_header:
                server_time = datetime.strptime(date_header, '%a, %d %b %Y %H:%M:%S GMT')
                server_timestamp = server_time.timestamp()

                self._offset = server_timestamp - (start_time + receive_time) / 2
                self._last_sync_time = time.time()
                self._sync_count += 1

                logger.info(
                    f"HTTP时间同步成功: 服务器={url}, "
                    f"偏移量={self._offset:.3f}秒"
                )

                return True, self._offset

        except ImportError:
            logger.warning("urllib不可用，HTTP时间同步失败")
        except Exception as e:
            logger.error(f"HTTP时间同步失败: {e}")

        return False, 0.0

    def sync(self) -> Tuple[bool, float]:
        """
        同步时间（优先NTP，失败则HTTP）

        Returns:
            (是否成功, 时间偏移量)
        """
        success, offset = self.sync_with_ntp()
        if not success:
            success, offset = self.sync_with_http()

        return success, offset

    def is_synced(self, max_age: float = 3600) -> bool:
        """
        检查是否已同步

        Args:
            max_age: 最大允许的时间间隔（秒），默认1小时

        Returns:
            是否已同步
        """
        if self._last_sync_time is None:
            return False

        return (time.time() - self._last_sync_time) < max_age

    def get_sync_info(self) -> dict:
        """获取同步信息"""
        return {
            'ntp_server': self.ntp_server,
            'offset_seconds': round(self._offset, 3),
            'last_sync_time': datetime.fromtimestamp(
                self._last_sync_time, CHINA_TZ
            ).isoformat() if self._last_sync_time else None,
            'sync_count': self._sync_count,
            'is_synced': self.is_synced(),
            'local_time': self.get_local_time().isoformat(),
            'synced_time': self.get_synced_time().isoformat()
        }


_clock_sync_instance = None


def get_clock_sync(
    ntp_server: str = "ntp.aliyun.com",
    ntp_port: int = 123
) -> ClockSync:
    """获取时钟同步器单例"""
    global _clock_sync_instance
    if _clock_sync_instance is None:
        _clock_sync_instance = ClockSync(ntp_server=ntp_server, ntp_port=ntp_port)
    return _clock_sync_instance


def now() -> datetime:
    """获取当前同步时间"""
    return get_clock_sync().get_synced_time()


def now_timestamp() -> float:
    """获取当前同步时间戳"""
    return time.time() + get_clock_sync().get_offset()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    sync = get_clock_sync()

    print("=" * 60)
    print("时钟同步模块测试")
    print("=" * 60)

    print("\n--- 本地时间 ---")
    print(f"本地时间: {sync.get_local_time().isoformat()}")

    print("\n--- NTP同步 ---")
    success, offset = sync.sync_with_ntp()
    print(f"NTP同步结果: {'成功' if success else '失败'}, 偏移量={offset:.3f}秒")

    print("\n--- 同步后时间 ---")
    print(f"同步后时间: {sync.get_synced_time().isoformat()}")

    print("\n--- 同步信息 ---")
    import json
    print(json.dumps(sync.get_sync_info(), indent=2, ensure_ascii=False))

    print("\n--- 时间戳对比 ---")
    print(f"本地时间戳: {time.time():.3f}")
    print(f"同步后时间戳: {now_timestamp():.3f}")

    print("\n" + "=" * 60)
