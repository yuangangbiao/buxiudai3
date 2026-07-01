# -*- coding: utf-8 -*-
"""
定时任务调度器 - 按计划自动生成报表

设计说明：
  使用 threading.Thread 后台线程，借鉴 dispatch_center 的 daemon 线程模式
  cron_expression 支持: daily / weekly / monthly / hourly
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .stats_engine import StatsEngine
from .interfaces import SchedulerServiceInterface

logger = logging.getLogger(__name__)


class ReportScheduler(SchedulerServiceInterface):
    """
    报表定时调度器

    在后台线程中周期性检查所有启用的计划，
    根据 cron_expression 判断是否到达执行时间。
    """

    def __init__(self, engine: StatsEngine, check_interval: int = 60):
        """

        参数：
          engine:         StatsEngine 实例
          check_interval: 检查周期（秒）
        """
        self.engine = engine
        self.check_interval = check_interval
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """启动后台调度线程"""
        if self._thread and self._thread.is_alive():
            logger.warning('[ReportScheduler] 调度器已在运行')
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name='report-scheduler'
        )
        self._thread.start()
        logger.info(f'[ReportScheduler] 调度器已启动，检查周期={self.check_interval}s')

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self):
        """停止调度器"""
        self._running = False
        logger.info('[ReportScheduler] 调度器已停止')

    def _run_loop(self):
        """调度主循环"""
        while self._running:
            try:
                self._check_schedules()
            except Exception as e:
                logger.error(f'[ReportScheduler] 检查计划异常: {e}')
            time.sleep(self.check_interval)

    def _check_schedules(self):
        """检查并执行到期计划"""
        schedules = self.engine.list_schedules(enabled_only=True)
        now = datetime.now()
        for schedule in schedules:
            try:
                if self._is_due(schedule, now):
                    self._execute_schedule(schedule)
            except Exception as e:
                logger.error(f'[ReportScheduler] 执行计划 {schedule.get("id")} 失败: {e}')

    def _is_due(self, schedule: Dict, now: datetime) -> bool:
        """判断计划是否到期"""
        last_run = schedule.get('last_run_at')
        if not last_run:
            return True
        last_dt = datetime.fromisoformat(last_run)
        expr = schedule.get('cron_expression', 'daily')
        if expr == 'hourly':
            return (now - last_dt).total_seconds() >= 3600
        if expr == 'daily':
            return now.date() > last_dt.date()
        if expr == 'weekly':
            return (now - last_dt).days >= 7
        if expr == 'monthly':
            return (now - last_dt).days >= 28
        if expr == 'every_30min':
            return (now - last_dt).total_seconds() >= 1800
        return False

    def _execute_schedule(self, schedule: Dict):
        """执行单个定时计划"""
        report_id = schedule.get('report_id', '')
        profile_id = schedule.get('export_profile_id', '')
        export_format = schedule.get('export_format', 'xlsx')
        params = {}
        try:
            raw = schedule.get('params', '{}')
            if raw:
                params = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            params = {}

        export_params = {}
        if profile_id:
            export_params['profile_id'] = profile_id
        result = self.engine.export_report(
            report_id=report_id,
            format=export_format,
            params=params,
            **export_params
        )

        now_str = datetime.now().isoformat()
        if result.get('success'):
            self.engine.save_schedule({
                'id': schedule['id'],
                'report_id': report_id,
                'name': schedule.get('name', ''),
                'cron_expression': schedule.get('cron_expression', 'daily'),
                'params': schedule.get('params', '{}'),
                'export_profile_id': profile_id,
                'export_format': export_format,
                'enabled': 1,
                'last_run_at': now_str,
                'updated_at': now_str
            })
            logger.info(f'[ReportScheduler] 报表已生成: {result.get("file_name")}')
        else:
            self.engine.storage.save_report_output({
                'report_id': report_id,
                'report_name': schedule.get('name', report_id),
                'format': export_format,
                'status': 'failed',
                'error_message': result.get('error', '未知错误'),
                'params_snapshot': json.dumps(params, ensure_ascii=False)
            })
            logger.warning(f'[ReportScheduler] 报表生成失败: {result.get("error")}')


_scheduler_instance: Optional[ReportScheduler] = None


def get_scheduler(engine: StatsEngine = None) -> Optional[ReportScheduler]:
    """获取调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None and engine is not None:
        _scheduler_instance = ReportScheduler(engine)
    return _scheduler_instance


def start_scheduler(engine: StatsEngine, check_interval: int = 60):
    """启动全局调度器"""
    scheduler = get_scheduler(engine)
    if scheduler:
        scheduler.start()
    return scheduler
