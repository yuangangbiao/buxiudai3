# -*- coding: utf-8 -*-
"""
考勤同步处理器
[F16 T16.4 修复] attendance 表已被 F6 P9 2026-06-10 DROP (跨库历史表清理, 详见 MEMORY.md L20)
    - steel_belt.attendance (1 行) 被清理
    - container_center.attendance 可能也已 DROP (需 auto_ensure_schema 重建)
    - 业务降级: 移动端签到/签退 → 写入失败时 SyncLog 记录 'f6p9_dropped' 状态
              容器中心自动尝试 CREATE TABLE IF NOT EXISTS 重建
              若 1146 持续失败, SyncLog 写入 'f6p9_failed' 触发监控
"""
import logging
import os
from .. import container_cursor
from contextlib import contextmanager
from datetime import datetime

from core.config import BASE_DIR
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)



@contextmanager


def _ensure_attendance_table():
    with container_cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                worker TEXT NOT NULL,
                check_in TEXT DEFAULT '',
                check_out TEXT DEFAULT '',
                status TEXT DEFAULT '未签到',
                date TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(worker, date)
            )
        ''')


def _is_f6p9_dropped_error(exc) -> bool:
    """[F16 T16.4 修复] 识别 F6 P9 DROP 触发的 1146 Table doesn't exist 错误
    返回 True 表示 attendance 表已 DROP, 业务降级
    """
    err_str = str(exc)
    return ('1146' in err_str or 'doesn\'t exist' in err_str
            or 'Table' in err_str and 'doesn' in err_str)


def handle_attendance_created(data: dict):
    """考勤签到同步 [F16 T16.4 修复] F6 P9 DROP 时业务降级"""
    worker = data.get('worker', '')
    date_val = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    check_in = data.get('check_in', '')
    status = data.get('status', '已签到')
    action = data.get('action', 'check-in')
    try:
        _ensure_attendance_table()
        with container_cursor() as cursor:
            cursor.execute(
                'REPLACE INTO attendance (worker, date, check_in, status) '
                'VALUES (%s, %s, %s, %s)',
                (worker, date_val, check_in, status)
            )
            logger.info('attendance synced to chengsheng.db: worker=%s date=%s action=%s',
                        worker, date_val, action)
            SyncLog.write('attendance.created', 'container_to_cs',
                          f'{worker}|{date_val}', 'success')
    except Exception as e:
        # [F16 T16.4 修复] F6 P9 DROP 识别 + 业务降级标记
        if _is_f6p9_dropped_error(e):
            logger.warning(
                '[F6 P9 DROP] attendance 表不存在 (1146), 业务降级: '
                '签到数据 %s|%s 无法持久化, 请改用 HR 系统。详细: %s',
                worker, date_val, e)
            SyncLog.write('attendance.created', 'container_to_cs',
                          f'{worker}|{date_val}', 'f6p9_dropped', str(e))
        else:
            logger.warning('sync attendance to chengsheng.db failed: %s', e)
            SyncLog.write('attendance.created', 'container_to_cs',
                          f'{worker}|{date_val}', 'failed', str(e))


def handle_attendance_updated(data: dict):
    """考勤签退同步 [F16 T16.4 修复] F6 P9 DROP 时业务降级"""
    worker = data.get('worker', '')
    date_val = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    check_out = data.get('check_out', '')
    status = data.get('status', '已签退')
    action = data.get('action', 'check-out')
    try:
        _ensure_attendance_table()
        with container_cursor() as cursor:
            cursor.execute(
                'REPLACE INTO attendance (worker, date, check_out, status) '
                'VALUES (%s, %s, %s, %s)',
                (worker, date_val, check_out, status)
            )
            logger.info('attendance synced to chengsheng.db: worker=%s date=%s action=%s',
                        worker, date_val, action)
            SyncLog.write('attendance.updated', 'container_to_cs',
                          f'{worker}|{date_val}', 'success')
    except Exception as e:
        # [F16 T16.4 修复] F6 P9 DROP 识别 + 业务降级标记
        if _is_f6p9_dropped_error(e):
            logger.warning(
                '[F6 P9 DROP] attendance 表不存在 (1146), 业务降级: '
                '签退数据 %s|%s 无法持久化, 请改用 HR 系统。详细: %s',
                worker, date_val, e)
            SyncLog.write('attendance.updated', 'container_to_cs',
                          f'{worker}|{date_val}', 'f6p9_dropped', str(e))
        else:
            logger.warning('sync attendance to chengsheng.db failed: %s', e)
            SyncLog.write('attendance.updated', 'container_to_cs',
                          f'{worker}|{date_val}', 'failed', str(e))
