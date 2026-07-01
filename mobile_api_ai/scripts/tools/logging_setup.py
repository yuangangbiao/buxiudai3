"""
每日轮转日志系统（日日志）

按日期自动分文件存储，支持自动清理过期日志。
所有服务统一使用此模块配置日志。

目录结构:
  logs/
    wechat_server/       # 微信服务日志
      2026-05-08.log
      2026-05-07.log
    container_api/       # 容器中心日志
      2026-05-08.log
    wechat_cloud/        # 云端服务日志
      2026-05-08.log
"""

import os
import glob
import logging
import threading
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from core.config import LOG_DIR, LOG_FORMAT, LOG_DATE_FORMAT, LOG_LEVEL, LOG_MAX_BYTES, LOG_RETENTION_DAYS


class DailyLogHandler(logging.Handler):
    """每日日志处理器 - 按日期分文件存储，自动轮转"""

    def __init__(self, service_name: str, log_dir: str = None, level=logging.NOTSET):
        super().__init__(level)
        self.service_name = service_name
        self.log_dir = log_dir or LOG_DIR
        self.service_log_dir = os.path.join(self.log_dir, service_name)
        os.makedirs(self.service_log_dir, exist_ok=True)
        self._today_str = None
        self._current_handler = None
        self._lock = threading.Lock()
        self._ensure_today_file()

    def _get_today_str(self):
        """获取今日日期字符串"""
        return datetime.now().strftime(LOG_DATE_FORMAT)

    def _get_today_path(self):
        """获取今日日志文件路径"""
        return os.path.join(self.service_log_dir, f"{self._get_today_str()}.log")

    def _ensure_today_file(self):
        """确保今日日志文件就绪"""
        today = self._get_today_str()
        if self._today_str == today and self._current_handler is not None:
            return
        self._today_str = today
        if self._current_handler is not None:
            self._current_handler.close()
        log_path = self._get_today_path()
        self._current_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=1,
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            LOG_FORMAT,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._current_handler.setFormatter(formatter)

    def emit(self, record):
        """写入日志记录"""
        try:
            with self._lock:
                self._ensure_today_file()
                self._current_handler.emit(record)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"日志写入失败: {e}")
            self.handleError(record)

    def close(self):
        """关闭处理器"""
        with self._lock:
            if self._current_handler is not None:
                self._current_handler.close()
                self._current_handler = None
        super().close()


def setup_daily_logger(
    service_name: str,
    log_level: str = None,
    console: bool = True,
    console_level: str = None
):
    """
    配置每日轮转日志

    Args:
        service_name: 服务名称（用于日志目录名）
        log_level: 日志级别，默认从Config获取
        console: 是否同时输出到控制台
        console_level: 控制台日志级别，默认与文件一致

    Returns:
        root logger
    """
    log_level = log_level or LOG_LEVEL
    console_level = console_level or log_level

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    file_handler = DailyLogHandler(service_name)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    return root_logger


def get_today_log_path(service_name: str) -> str:
    """获取今日日志文件路径"""
    log_dir = os.path.join(LOG_DIR, service_name)
    today = datetime.now().strftime(LOG_DATE_FORMAT)
    return os.path.join(log_dir, f"{today}.log")


def get_log_files(service_name: str) -> list:
    """获取某服务所有日志文件列表（按日期降序）"""
    log_dir = os.path.join(LOG_DIR, service_name)
    pattern = os.path.join(log_dir, "*.log")
    files = glob.glob(pattern)
    files.sort(reverse=True)
    return files


def read_log(
    service_name: str,
    date_str: str = None,
    tail_lines: int = None,
    level: str = None
) -> str:
    """
    读取日志内容

    Args:
        service_name: 服务名称
        date_str: 日期（YYYY-MM-DD），默认今日
        tail_lines: 只返回末尾N行
        level: 按级别过滤（INFO/WARNING/ERROR）

    Returns:
        日志内容
    """
    date_str = date_str or datetime.now().strftime(LOG_DATE_FORMAT)
    log_dir = os.path.join(LOG_DIR, service_name)
    log_path = os.path.join(log_dir, f"{date_str}.log")

    if not os.path.exists(log_path):
        return ""

    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if level:
        level_upper = level.upper()
        lines = [l for l in lines if level_upper in l]

    if tail_lines:
        lines = lines[-tail_lines:]

    return ''.join(lines)


def cleanup_old_logs(retention_days: int = None):
    """
    清理过期日志文件

    Args:
        retention_days: 保留天数，默认从Config获取

    Returns:
        清理的文件数量
    """
    retention_days = retention_days or LOG_RETENTION_DAYS
    cutoff = datetime.now() - timedelta(days=retention_days)
    count = 0

    log_dir = LOG_DIR
    if not os.path.exists(log_dir):
        return 0

    for service_name in os.listdir(log_dir):
        service_dir = os.path.join(log_dir, service_name)
        if not os.path.isdir(service_dir):
            continue
        for fname in os.listdir(service_dir):
            if not fname.endswith('.log'):
                continue
            try:
                file_date = datetime.strptime(fname.replace('.log', ''), '%Y-%m-%d')
                if file_date < cutoff:
                    os.remove(os.path.join(service_dir, fname))
                    count += 1
            except (ValueError, OSError):
                continue

    return count
