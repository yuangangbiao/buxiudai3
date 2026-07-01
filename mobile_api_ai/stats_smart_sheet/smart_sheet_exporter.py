# -*- coding: utf-8 -*-
"""
9 张统计表统一导出入口
- 定时任务 / 手动调用 / 事件触发 统一入口
- 含并发控制（H-5 修复）
- 含日志（M-1 修复）
- 含 metrics（M-3 修复）
"""
import logging
import threading
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Callable

from . import db_queries
from .smart_sheet_client import push_with_retry
from .config import SCHEDULE_CONFIG, TABLE_DISPLAY_NAMES, INVENTORY_CONFIG

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# 9 张表的导出函数
# ══════════════════════════════════════════════════════════
def export_production_daily() -> Dict[str, Any]:
    """生产日报 - 昨天"""
    target_date = date.today() - timedelta(days=1)
    records = db_queries.query_production_daily(target_date)
    return push_with_retry('production_daily_report', records, period_key=str(target_date))


def export_production_monthly() -> Dict[str, Any]:
    """生产月报 - 上月"""
    today = date.today()
    if today.month == 1:
        last_month = today.replace(year=today.year - 1, month=12)
    else:
        last_month = today.replace(month=today.month - 1)
    period_key = last_month.strftime('%Y-%m')
    records = db_queries.query_production_monthly(period_key)
    return push_with_retry('production_monthly_report', records, period_key=period_key)


def export_workshop_capacity() -> Dict[str, Any]:
    """车间产能分析 - 昨天"""
    target_date = date.today() - timedelta(days=1)
    records = db_queries.query_workshop_capacity(target_date)
    return push_with_retry('workshop_capacity', records, period_key=str(target_date))


def export_workorder_progress() -> Dict[str, Any]:
    """工单进度跟踪 - 实时"""
    records = db_queries.query_workorder_progress()
    period_key = datetime.now().strftime('%Y%m%d%H')
    return push_with_retry('workorder_progress', records, period_key=period_key)


def export_substep_recent() -> Dict[str, Any]:
    """工序报工 - 最近 1 小时"""
    since = datetime.now() - timedelta(hours=1)
    records = db_queries.query_substep_recent(since, limit=100)
    period_key = datetime.now().strftime('%Y%m%d%H%M')
    return push_with_retry('substep_report', records, period_key=period_key)


def export_inventory_weekly() -> Dict[str, Any]:
    """库存周报 - 本周"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 周一
    week_end = week_start + timedelta(days=6)             # 周日
    records = db_queries.query_inventory_weekly(week_start, week_end)
    period_key = f"{week_start}~{week_end}"
    return push_with_retry('inventory_weekly_report', records, period_key=period_key)


def export_inventory_monthly() -> Dict[str, Any]:
    """物料收发存 - 上月"""
    today = date.today()
    if today.month == 1:
        last_month = today.replace(year=today.year - 1, month=12)
    else:
        last_month = today.replace(month=today.month - 1)
    period_key = last_month.strftime('%Y-%m')
    records = db_queries.query_inventory_monthly(period_key)
    return push_with_retry('inventory_monthly_summary', records, period_key=period_key)


def export_inventory_alert() -> Dict[str, Any]:
    """库存预警 - 实时"""
    records = db_queries.query_inventory_alert(INVENTORY_CONFIG['safety_threshold'])
    period_key = datetime.now().strftime('%Y%m%d%H')
    return push_with_retry('inventory_alert', records, period_key=period_key)


def export_inventory_slow_moving() -> Dict[str, Any]:
    """呆滞料分析 - 本周"""
    records = db_queries.query_inventory_slow_moving(INVENTORY_CONFIG['slow_moving_days'])
    period_key = datetime.now().strftime('%Y%W')
    return push_with_retry('inventory_slow_moving', records, period_key=period_key)


# 9 张表的导出函数注册表
EXPORT_FUNCS: Dict[str, Callable] = {
    'production_daily_report':   export_production_daily,
    'production_monthly_report': export_production_monthly,
    'workshop_capacity':         export_workshop_capacity,
    'workorder_progress':        export_workorder_progress,
    'substep_report':            export_substep_recent,
    'inventory_weekly_report':   export_inventory_weekly,
    'inventory_monthly_summary': export_inventory_monthly,
    'inventory_alert':           export_inventory_alert,
    'inventory_slow_moving':     export_inventory_slow_moving,
}


# ══════════════════════════════════════════════════════════
# 并发控制 + Metrics（H-5 / M-3 修复）
# ══════════════════════════════════════════════════════════
_table_locks = {t: threading.Lock() for t in EXPORT_FUNCS}
_metrics = {
    'total_push': 0,
    'success_push': 0,
    'failed_push': 0,
    'last_push_time': '',
    'last_result': {},
}


def export_table(table_type: str) -> Dict[str, Any]:
    """统一导出入口（带并发控制）"""
    func = EXPORT_FUNCS.get(table_type)
    if not func:
        return {'code': -1, 'message': f'未知表类型: {table_type}'}

    # 同一表类型不能并发
    with _table_locks[table_type]:
        start = time.time()
        logger.info(f"[{table_type}] 开始导出 | 显示名={TABLE_DISPLAY_NAMES.get(table_type)}")
        try:
            result = func()
            elapsed = round(time.time() - start, 2)
            _metrics['total_push'] += 1
            if result.get('code') == 0:
                _metrics['success_push'] += 1
            else:
                _metrics['failed_push'] += 1
            _metrics['last_push_time'] = datetime.now().isoformat()
            _metrics['last_result'] = {'table_type': table_type, **result}
            logger.info(f"[{table_type}] 导出完成 | 耗时={elapsed}s | code={result.get('code')}")
            result['elapsed'] = elapsed
            return result
        except Exception as e:
            logger.exception(f"[{table_type}] 导出异常: {e}")
            _metrics['failed_push'] += 1
            return {'code': -1, 'message': f'异常: {e}'}


def export_all() -> Dict[str, Any]:
    """导出所有启用的表（顺序执行，避免数据库压力）"""
    results = {}
    for table_type, cfg in SCHEDULE_CONFIG.items():
        if not cfg.get('enabled', True):
            continue
        results[table_type] = export_table(table_type)
    return results


def get_metrics() -> Dict[str, Any]:
    """获取 metrics（M-3 修复）"""
    return dict(_metrics)


# ══════════════════════════════════════════════════════════
# APScheduler 定时任务入口
# ══════════════════════════════════════════════════════════
def register_scheduler(scheduler):
    """注册 9 张表的定时任务（需在启动时调用）"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler 未安装，定时任务未注册")
        return

    for table_type, cfg in SCHEDULE_CONFIG.items():
        if not cfg.get('enabled', True):
            continue
        cron_expr = cfg['cron']
        # 解析 cron 表达式
        parts = cron_expr.split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1],
                day=parts[2], month=parts[3], day_of_week=parts[4]
            )
            scheduler.add_job(
                export_table, trigger, args=[table_type],
                id=f'stats_{table_type}', replace_existing=True
            )
            logger.info(f"[定时任务] {table_type} cron='{cron_expr}'")


if __name__ == '__main__':
    # 命令行测试入口
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    if len(sys.argv) > 1:
        result = export_table(sys.argv[1])
    else:
        result = export_all()
    print(json.dumps(result, ensure_ascii=False, indent=2))
