# -*- coding: utf-8 -*-
"""
日志轮转配置 - 防止日志文件无限增长

使用 RotatingFileHandler：
- 单文件最大 100MB
- 保留最近 10 个备份
- 自动压缩旧日志

使用方式：
    from log_config import setup_logging_with_rotation

    setup_logging_with_rotation(
        log_file='app.log',
        max_bytes=100 * 1024 * 1024,  # 100MB
        backup_count=10
    )
"""
import os
import gzip
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


def setup_logging_with_rotation(
    log_file: str = 'app.log',
    max_bytes: int = 100 * 1024 * 1024,
    backup_count: int = 10,
    level: str = 'INFO',
    log_format: str = '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
    date_format: str = '%Y-%m-%d %H:%M:%S',
    console: bool = True
):
    """
    配置日志轮转

    Args:
        log_file: 日志文件路径
        max_bytes: 单文件最大字节数（默认100MB）
        backup_count: 保留的备份文件数量（默认10个）
        level: 日志级别
        log_format: 日志格式
        date_format: 日期格式
        console: 是否输出到控制台
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(log_format, datefmt='%H:%M:%S')

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger(__name__)
    logger.info(f"日志轮转已配置: {log_file} (max={max_bytes//1024//1024}MB, backup={backup_count})")

    return root_logger


def cleanup_old_logs(log_dir: str, days: int = 30):
    """
    清理旧日志文件

    Args:
        log_dir: 日志目录
        days: 保留天数
    """
    if not os.path.exists(log_dir):
        return

    import time
    cutoff = time.time() - days * 24 * 3600
    removed = 0

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            if filename.endswith('.log') or filename.endswith('.log.gz'):
                if os.path.getmtime(filepath) < cutoff:
                    try:
                        os.remove(filepath)
                        removed += 1
                    except OSError:
                        pass

    return removed


def compress_old_logs(log_dir: str, keep_latest: int = 3):
    """
    压缩旧日志文件（备份轮转产生的旧文件）

    Args:
        log_dir: 日志目录
        keep_latest: 保留最新的N个未压缩文件
    """
    if not os.path.exists(log_dir):
        return

    log_files = []
    for filename in os.listdir(log_dir):
        if filename.endswith('.log') and not filename.endswith('.gz'):
            filepath = os.path.join(log_dir, filename)
            log_files.append((os.path.getmtime(filepath), filepath))

    log_files.sort(reverse=True)

    for i, (_, filepath) in enumerate(log_files):
        if i >= keep_latest:
            try:
                with open(filepath, 'rb') as f_in:
                    with gzip.open(filepath + '.gz', 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(filepath)
            except Exception:
                pass


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

        print(f"清理 {log_dir} 中 {days} 天前的日志...")
        removed = cleanup_old_logs(log_dir, days)
        print(f"已删除 {removed} 个旧日志文件")
    else:
        print("使用方式: python log_rotation.py <日志目录> [保留天数]")
