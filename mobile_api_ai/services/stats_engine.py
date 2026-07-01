# -*- coding: utf-8 -*-
"""
报表引擎核心 - 提供SQL模板渲染、内置统计查询、报表定义管理、模板化导出

设计说明：
  1. SQL模板引擎：使用 {param_name} 占位符，自动安全替换
  2. 内置预设报表：首次初始化时自动写入4大维度默认报表定义
  3. 可通过 report_definition 自定义 SQL，实现任意统计
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.db import get_direct_connection
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from data_export import DataExporter
from .interfaces import StatsServiceInterface

logger = logging.getLogger(__name__)


class StatsEngine(StatsServiceInterface):
    """
    报表引擎核心

    功能：
      - SQL模板引擎（安全参数注入）
      - 内置4大维度统计（生产/成本/人员/综合）
      - 报表定义的全生命周期管理
      - 按模板导出 Excel/CSV
    """

    def __init__(self, storage):
        self.storage = storage
        self._builtin_seeded = False

    # ── 初始化：写入内置预设报表 ──

    def seed_builtin_reports(self):
        """写入内置预设报表定义（幂等，仅在首次运行时执行）"""
        if self._builtin_seeded:
            return
        existing = self.storage.list_report_definitions()
        if existing:
            self._builtin_seeded = True
            return

        now = datetime.now().isoformat()
        builtins = self._get_builtin_definitions(now)
        for report in builtins:
            self.storage.save_report_definition(report)
        self._builtin_seeded = True
        logger.info(f"已写入 {len(builtins)} 个内置报表定义")

    def _get_builtin_definitions(self, now: str) -> List[Dict]:
        return [
            # ── Dashboard ──
            {
                'id': 'builtin_dashboard',
                'name': '综合仪表盘',
                'category': 'dashboard',
                'description': '生产/成本/效率综合看板',
                'sql_template': '',
                'params_config': '[]',
                'chart_config': json.dumps({
                    'type': 'dashboard',
                    'cards': [
                        {'key': 'today_reports', 'label': '今日报工', 'icon': 'file-text'},
                        {'key': 'quality_rate', 'label': '良品率', 'icon': 'check-circle'},
                        {'key': 'pending_approvals', 'label': '待审批', 'icon': 'clock'},
                        {'key': 'efficiency', 'label': '综合效率', 'icon': 'trending-up'}
                    ]
                }, ensure_ascii=False),
                'column_config': '[]',
                'created_at': now, 'updated_at': now
            },
            # ── 生产统计 ──
            {
                'id': 'builtin_production_overview',
                'name': '生产概况',
                'category': 'production',
                'description': '各状态订单数统计',
                'sql_template': 'SELECT COALESCE(status, "未知") AS 状态, COUNT(*) AS 数量 FROM process_records GROUP BY status ORDER BY 数量 DESC',
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'pie', 'title': '订单状态分布'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '状态', 'field': '状态'},
                    {'header': '数量', 'field': '数量'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            {
                'id': 'builtin_production_trend',
                'name': '近7天产量趋势',
                'category': 'production',
                'description': '最近7天每日报工趋势',
                'sql_template': "SELECT date(created_at) AS 日期, COUNT(*) AS 报工数 FROM data_packages WHERE date(created_at) >= date('now', '-7 days') GROUP BY date(created_at) ORDER BY 日期",
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'line', 'title': '产量趋势'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '日期', 'field': '日期'},
                    {'header': '报工数', 'field': '报工数'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            {
                'id': 'builtin_product_ranking',
                'name': '产品产量排行',
                'category': 'production',
                'description': '各产品累计产量排名',
                'sql_template': 'SELECT product_name AS 产品名称, SUM(quantity) AS 总数量, COUNT(*) AS 订单数 FROM order_cost WHERE quantity > 0 GROUP BY product_name ORDER BY 总数量 DESC LIMIT 20',
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'bar', 'title': '产品产量排行'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '产品名称', 'field': '产品名称'},
                    {'header': '总数量', 'field': '总数量'},
                    {'header': '订单数', 'field': '订单数'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            # ── 成本统计 ──
            {
                'id': 'builtin_cost_overview',
                'name': '成本概况',
                'category': 'cost',
                'description': '各订单成本与利润率',
                'sql_template': "SELECT order_no AS 订单号, customer_name AS 客户, revenue AS 收入, total_cost AS 总成本, profit AS 利润, margin_rate AS 利润率 FROM order_cost WHERE status != 'draft' ORDER BY margin_rate DESC",
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'table', 'title': '成本利润率排行'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '订单号', 'field': '订单号'},
                    {'header': '客户', 'field': '客户'},
                    {'header': '收入', 'field': '收入', 'formatter': 'amount'},
                    {'header': '总成本', 'field': '总成本', 'formatter': 'amount'},
                    {'header': '利润', 'field': '利润', 'formatter': 'amount'},
                    {'header': '利润率', 'field': '利润率', 'formatter': 'percent'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            {
                'id': 'builtin_cost_breakdown',
                'name': '成本构成汇总',
                'category': 'cost',
                'description': '料工费及其他成本占比',
                'sql_template': 'SELECT SUM(material_cost) AS 材料成本, SUM(labor_cost) AS 人工成本, SUM(overhead_cost) AS 制造费用, SUM(outsourcing_cost) AS 外协成本, SUM(other_cost) AS 其他成本, SUM(total_cost) AS 总成本合计 FROM order_cost',
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'pie', 'title': '成本构成'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '材料成本', 'field': '材料成本', 'formatter': 'amount'},
                    {'header': '人工成本', 'field': '人工成本', 'formatter': 'amount'},
                    {'header': '制造费用', 'field': '制造费用', 'formatter': 'amount'},
                    {'header': '外协成本', 'field': '外协成本', 'formatter': 'amount'},
                    {'header': '其他成本', 'field': '其他成本', 'formatter': 'amount'},
                    {'header': '总成本合计', 'field': '总成本合计', 'formatter': 'amount'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            {
                'id': 'builtin_loss_analysis',
                'name': '亏损订单分析',
                'category': 'cost',
                'description': '亏损订单明细',
                'sql_template': "SELECT order_no AS 订单号, customer_name AS 客户, profit AS 利润, margin_rate AS 利润率 FROM order_cost WHERE profit < 0 ORDER BY profit ASC",
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'table', 'title': '亏损订单'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '订单号', 'field': '订单号'},
                    {'header': '客户', 'field': '客户'},
                    {'header': '利润', 'field': '利润', 'formatter': 'amount'},
                    {'header': '利润率', 'field': '利润率', 'formatter': 'percent'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            # ── 人员效率 ──
            {
                'id': 'builtin_worker_efficiency',
                'name': '操作员效率排名',
                'category': 'worker',
                'description': '各操作员任务完成量与效率',
                'sql_template': "SELECT COALESCE(target_operator, '未分配') AS 操作员, COUNT(*) AS 总任务数, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS 已完成, ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END, 1) || '%' AS 完成率 FROM data_packages WHERE target_operator IS NOT NULL AND target_operator != '' GROUP BY target_operator ORDER BY 已完成 DESC",
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'bar', 'title': '操作员效率排行'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '操作员', 'field': '操作员'},
                    {'header': '总任务数', 'field': '总任务数'},
                    {'header': '已完成', 'field': '已完成'},
                    {'header': '完成率', 'field': '完成率'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
            {
                'id': 'builtin_worker_output',
                'name': '工序完成量排行',
                'category': 'worker',
                'description': '各工序完成数量排名',
                'sql_template': 'SELECT operator AS 操作员, step_name AS 工序, SUM(quantity) AS 完成总量, COUNT(*) AS 记录数 FROM process_sub_steps GROUP BY operator ORDER BY 完成总量 DESC LIMIT 20',
                'params_config': '[]',
                'chart_config': json.dumps({'type': 'bar', 'title': '工序完成量排行'}, ensure_ascii=False),
                'column_config': json.dumps([
                    {'header': '操作员', 'field': '操作员'},
                    {'header': '工序', 'field': '工序'},
                    {'header': '完成总量', 'field': '完成总量'},
                    {'header': '记录数', 'field': '记录数'}
                ], ensure_ascii=False),
                'created_at': now, 'updated_at': now
            },
        ]

    # ── SQL 模板引擎 ──

    def _render_sql(self, template: str, params: Dict = None) -> str:
        """渲染 SQL 模板：将 {param_name} 替换为安全参数值"""
        if not template.strip():
            return ''
        if not params:
            params = {}
        def _replacer(match):
            key = match.group(1)
            val = params.get(key, match.group(0))
            if isinstance(val, str):
                escaped = val.replace("'", "''")
                return f"'{escaped}'"
            if isinstance(val, (int, float)):
                return str(val)
            if val is None:
                return 'NULL'
            return match.group(0)
        return re.sub(r'\{(\w+)\}', _replacer, template)

    def _execute_raw_query(self, sql: str) -> List[Dict]:
        """直接执行原始 SQL 并返回字典列表"""
        if not sql.strip():
            return []
        conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return rows  # DictCursor 已返回字典
        finally:
            conn.close()

    # ── 内置统计（4大维度）──

    def get_dashboard(self) -> Dict:
        """综合仪表盘"""
        try:
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) AS c FROM data_packages WHERE DATE(created_at) = CURDATE()")
                    today_reports = cursor.fetchone()['c']

                    cursor.execute("SELECT COUNT(*) AS c, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS done FROM data_packages WHERE DATE(created_at) = CURDATE()")
                    row = cursor.fetchone()
                    today_done = row['done'] or 0
                    efficiency = round(100.0 * today_done / row['c'], 1) if row['c'] > 0 else 0

                    cursor.execute("SELECT COUNT(*) AS c FROM order_cost WHERE profit < 0")
                    loss_count = cursor.fetchone()['c']

                    cursor.execute("SELECT COUNT(*) AS c FROM process_records WHERE status = 'in_progress'")
                    in_progress = cursor.fetchone()['c']
            finally:
                conn.close()

            return {
                'today_reports': {'count': today_reports, 'change': None},
                'quality_rate': {'value': '--', 'change': None},
                'pending_approvals': {'count': in_progress, 'change': None},
                'efficiency': {'value': f'{efficiency}%', 'change': None},
                'loss_orders': loss_count
            }
        except Exception as e:
            logger.error(f"获取仪表盘数据失败: {e}")
            return {}

    def get_production_stats(self, params: Dict = None) -> Dict:
        """生产统计"""
        try:
            if params is None:
                params = {}
            report = self.storage.get_report_definition('builtin_production_overview')
            trend = self.storage.get_report_definition('builtin_production_trend')
            ranking = self.storage.get_report_definition('builtin_product_ranking')
            overview_data = self._execute_raw_query(report['sql_template']) if report else []
            trend_data = self._execute_raw_query(trend['sql_template']) if trend else []
            ranking_data = self._execute_raw_query(ranking['sql_template']) if ranking else []
            return {
                'overview': overview_data,
                'trend': trend_data,
                'product_ranking': ranking_data
            }
        except Exception as e:
            logger.error(f"获取生产统计失败: {e}")
            return {'overview': [], 'trend': [], 'product_ranking': []}

    def get_cost_stats(self, params: Dict = None) -> Dict:
        """成本统计"""
        try:
            if params is None:
                params = {}
            overview = self.storage.get_report_definition('builtin_cost_overview')
            breakdown = self.storage.get_report_definition('builtin_cost_breakdown')
            loss = self.storage.get_report_definition('builtin_loss_analysis')
            overview_data = self._execute_raw_query(overview['sql_template']) if overview else []
            breakdown_data = self._execute_raw_query(breakdown['sql_template']) if breakdown else []
            loss_data = self._execute_raw_query(loss['sql_template']) if loss else []
            return {
                'overview': overview_data,
                'breakdown': breakdown_data,
                'loss_analysis': loss_data
            }
        except Exception as e:
            logger.error(f"获取成本统计失败: {e}")
            return {'overview': [], 'breakdown': [], 'loss_analysis': []}

    def get_worker_stats(self, params: Dict = None) -> Dict:
        """人员效率统计"""
        try:
            if params is None:
                params = {}
            efficiency = self.storage.get_report_definition('builtin_worker_efficiency')
            output = self.storage.get_report_definition('builtin_worker_output')
            efficiency_data = self._execute_raw_query(efficiency['sql_template']) if efficiency else []
            output_data = self._execute_raw_query(output['sql_template']) if output else []
            return {
                'efficiency': efficiency_data,
                'output': output_data
            }
        except Exception as e:
            logger.error(f"获取人员统计失败: {e}")
            return {'efficiency': [], 'output': []}

    # ── 报表定义管理 ──

    def list_reports(self, category: str = None) -> List[Dict]:
        """列表报表定义"""
        self.seed_builtin_reports()
        return self.storage.list_report_definitions(category)

    def get_report(self, report_id: str) -> Optional[Dict]:
        """获取报表定义详情"""
        return self.storage.get_report_definition(report_id)

    def save_report(self, data: Dict) -> bool:
        """保存报表定义（自动生成 ID）"""
        if not data.get('id'):
            data['id'] = f"custom_{uuid4().hex[:12]}"
        return self.storage.save_report_definition(data)

    def delete_report(self, report_id: str) -> bool:
        """删除报表定义"""
        return self.storage.delete_report_definition(report_id)

    def execute_report(self, report_id: str, params: Dict = None) -> Dict:
        """
        执行指定报表（渲染 SQL → 执行查询 → 返回结果）

        返回结构：
          {
              'id': str,
              'name': str,
              'category': str,
              'chart_config': dict,
              'column_config': list,
              'data': [ { col: val, ... }, ... ],
              'row_count': int,
              'generated_at': str
          }
        """
        report = self.storage.get_report_definition(report_id)
        if not report:
            return {'error': f'报表定义不存在: {report_id}'}
        try:
            sql = report.get('sql_template', '')
            rendered_sql = self._render_sql(sql, params)
            data = self._execute_raw_query(rendered_sql)
            now = datetime.now().isoformat()
            return {
                'id': report['id'],
                'name': report['name'],
                'category': report['category'],
                'chart_config': json.loads(report.get('chart_config', '{}')),
                'column_config': json.loads(report.get('column_config', '[]')),
                'data': data,
                'row_count': len(data),
                'generated_at': now
            }
        except Exception as e:
            logger.error(f"执行报表 {report_id} 失败: {e}")
            return {'error': str(e), 'report_id': report_id}

    # ── 模板化导出 ──

    def export_report(self, report_id: str, format: str = 'xlsx',
                      profile_id: str = None, params: Dict = None) -> Dict:
        """
        按模板导出报表

        参数：
          report_id:  报表定义 ID
          format:     导出格式（xlsx/csv）
          profile_id: 导出配置 ID（如不传则使用 column_config 自动生成）
          params:     SQL 模板参数

        返回：
          {
              'success': bool,
              'file_path': str,
              'file_name': str,
              'row_count': int,
              'output_id': int
          }
        """
        result = self.execute_report(report_id, params)
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        data = result['data']
        if not data:
            return {'success': False, 'error': '无数据可导出'}

        profile = None
        if profile_id:
            profile = self.storage.get_export_profile(profile_id)

        exporter = DataExporter()
        report_name = result.get('name', report_id)
        exporter.set_title(report_name)

        if profile:
            profile_config = json.loads(profile.get('columns_config', '[]'))
            for col in profile_config:
                exporter.add_column(col['header'], col.get('field', col['header']))
        else:
            columns = result.get('column_config', [])
            for col in columns:
                exporter.add_column(col['header'], col.get('field', col['header']))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', report_name)
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
        os.makedirs(output_dir, exist_ok=True)
        file_name = f'{safe_name}_{timestamp}.{format}'
        file_path = os.path.join(output_dir, file_name)

        if format == 'csv':
            exporter.export_to_csv(data, file_path)
        else:
            if profile:
                exporter.export_to_xlsx(data, file_path, sheet_name=profile.get('sheet_name', report_name))
            else:
                exporter.export_to_xlsx(data, file_path, sheet_name=report_name)

        output_id = self.storage.save_report_output({
            'report_id': report_id,
            'report_name': report_name,
            'format': format,
            'file_path': file_path,
            'row_count': len(data),
            'status': 'generated',
            'params_snapshot': json.dumps(params or {}, ensure_ascii=False)
        })

        return {
            'success': True,
            'file_path': file_path,
            'file_name': file_name,
            'row_count': len(data),
            'output_id': output_id
        }

    # ── 导出配置管理 ──

    def list_export_profiles(self) -> List[Dict]:
        return self.storage.list_export_profiles()

    def get_export_profile(self, profile_id: str) -> Optional[Dict]:
        return self.storage.get_export_profile(profile_id)

    def save_export_profile(self, data: Dict) -> bool:
        if not data.get('id'):
            data['id'] = f"profile_{uuid4().hex[:12]}"
        return self.storage.save_export_profile(data)

    def delete_export_profile(self, profile_id: str) -> bool:
        return self.storage.delete_export_profile(profile_id)

    # ── 定时计划管理 ──

    def list_schedules(self, enabled_only: bool = False) -> List[Dict]:
        return self.storage.list_report_schedules(enabled_only)

    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        return self.storage.get_report_schedule(schedule_id)

    def save_schedule(self, data: Dict) -> bool:
        if not data.get('id'):
            data['id'] = f"schedule_{uuid4().hex[:12]}"
        return self.storage.save_report_schedule(data)

    def delete_schedule(self, schedule_id: str) -> bool:
        return self.storage.delete_report_schedule(schedule_id)

    def list_outputs(self, report_id: str = None, limit: int = 50) -> List[Dict]:
        return self.storage.list_report_outputs(report_id, limit)


def get_stats_engine():
    from storage_layer import StorageFactory, StorageType, resolve_storage_type
    default_st = resolve_storage_type()
    storage = StorageFactory.get_instance(default_st)
    if not storage:
        storage = StorageFactory.create(default_st)
    engine = StatsEngine(storage)
    engine.seed_builtin_reports()
    return engine
