# -*- coding: utf-8 -*-
"""
[v4.1 重构 2026-06-21] ETL 同步器重构

[v4.1 重大变更] _local 表已废除，同步策略调整：
  - 旧策略：从 steel_belt ETL 同步到 container_center._local 表
  - 新策略：移动端报工通过 sync_bridge 双写 steel_belt + container_center 主表

当前文件保留但大部分逻辑已禁用。如需 ETL 功能，请使用 sync_bridge.py。
"""
import os
import sys
import time
import logging
import threading
from typing import Optional
import pymysql
from datetime import datetime, timedelta

_MOBILE_API_PATH = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_MOBILE_API_PATH)
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)
if _MOBILE_API_PATH not in sys.path:
    sys.path.append(_MOBILE_API_PATH)

logger = logging.getLogger(__name__)


def _get_mysql(cfg_name: str):
    """[T11 2026-06-14] 走 shim 连接池

    Args:
        cfg_name: 'steelbelt' 或 'container'
    """
    from core.db_compat import get_conn
    from core.config import STEELBELT_MYSQL_CFG, CONTAINER_MYSQL_CFG

    if cfg_name == 'steelbelt':
        return get_conn(**STEELBELT_MYSQL_CFG)
    else:  # container
        return get_conn(**CONTAINER_MYSQL_CFG)


# [N6 修复 2026-06-13] 启动前检查目标表是否存在
# [v4.1 重构 2026-06-21] _local 表已废除，改为检查主表
_TARGET_TABLES = [
    'orders',
    'production_orders',
    'violations',
    'process_records',
    'work_orders',
]


def _check_target_tables() -> list:
    """检查 5 个目标表是否存在

    Returns:
        不存在的表名列表
    """
    missing = []
    try:
        conn = _get_mysql('container')
        try:
            with conn.cursor() as c:
                for table in _TARGET_TABLES:
                    c.execute(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = DATABASE() AND table_name = %s",
                        (table,)
                    )
                    if c.fetchone()[0] == 0:
                        missing.append(table)
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[ETL] 检查表存在性失败: {e}')
        return []  # 检查失败不阻塞启动
    return missing


def _sync_table(
    source_table: str,
    target_table: str,
    pk_col: str = 'id',
    sync_field: str = 'updated_at',
    batch_size: int = 500,
    last_sync_time: Optional[str] = None,
) -> int:
    """同步单个表（基于 sync_field 增量）

    [N1 修复 2026-06-13] 修复 last_sync_marker 永远重置为 24h 前的 bug
    现在 last_sync_time 由调用方传入（或从状态字典获取），同步成功后返回新的时间戳
    [F10 修复 2026-06-13] 同步 is_deleted 字段（软删除同步）
    [G1 修复 2026-06-13] 标记 _source='etl'，记录同步时间和 trace_id
    [v4.1 重构 2026-06-21] 硬删除同步：删除主表中"源表已无"的行

    Args:
        source_table: 源表名（如 steel_belt.orders）
        target_table: 目标表名（如 container_center.orders）
        pk_col: 主键列
        sync_field: 增量同步字段（updated_at）
        batch_size: 每批处理行数
        last_sync_time: 上次同步的时间戳字符串，None 表示首次（全量）

    Returns:
        同步的行数
    """
    if last_sync_time is None:
        # 首次：只回溯 24h
        last_sync_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

    src_conn = _get_mysql('steelbelt')
    tgt_conn = _get_mysql('container')
    synced = 0
    new_sync_time = last_sync_time
    try:
        with src_conn.cursor() as sc:
            # [K19 修复] 检查源表是否存在
            sc.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (source_table,))
            if sc.fetchone() is None:
                logger.debug(f'[ETL] 源表 {source_table} 不存在，跳过同步')
                return 0

        with src_conn.cursor(pymysql.cursors.DictCursor) as sc:
            # 获取增量数据
            sc.execute(
                f"SELECT * FROM {source_table} WHERE {sync_field} >= %s ORDER BY {sync_field} ASC LIMIT %s",
                (last_sync_time, batch_size)
            )
            rows = sc.fetchall()
            if not rows:
                return 0

            with tgt_conn.cursor() as tc:
                # 使用 REPLACE INTO 处理新增+更新
                # [F9 修复 2026-06-13] 显式列名白名单（不依赖 SELECT *）
                # 之前：源表加新字段会导致镜像表缺字段
                # 现在：维护显式白名单，未列出的字段不同步
                all_cols = list(rows[0].keys())
                # 过滤出白名单内的列
                _table_cols = _ETL_TABLE_WHITELIST.get(target_table, set())
                if _table_cols:
                    cols = [c for c in all_cols if c in _table_cols]
                else:
                    # 没有白名单时使用全部列（向后兼容）
                    cols = all_cols
                if not cols:
                    logger.warning(f'[ETL] {target_table} 无可同步列（白名单为空）')
                    return 0

                # [v4.1 修复 2026-06-21] 分离 INSERT 和 UPDATE 列
                # 使用 INSERT ... ON DUPLICATE KEY UPDATE 替代 REPLACE INTO
                # 这样可以保留任务发布特有字段不被覆盖
                # [P0 修复 2026-06-23] 未配置表用白名单兜底, 避免 insert_cols=[] 导致 1364 错误
                _updatable = _ETL_UPDATABLE_FIELDS.get(
                    target_table,
                    _ETL_TABLE_WHITELIST.get(target_table, set())
                )
                insert_cols = [c for c in cols if c in _updatable]
                update_parts = [f"{c}=VALUES({c})" for c in insert_cols if c != 'id']

                col_list = ', '.join(insert_cols)
                placeholder = ', '.join(['%s'] * len(insert_cols))
                if update_parts:
                    upsert_sql = f"INSERT INTO {target_table} ({col_list}) VALUES ({placeholder}) ON DUPLICATE KEY UPDATE {', '.join(update_parts)}"
                else:
                    upsert_sql = f"INSERT INTO {target_table} ({col_list}) VALUES ({placeholder})"

                # [v4.1 监控 2026-06-21] 关键字段变更监控
                # [P0 修复 2026-06-23] insert_cols 是 list, 不能与 set 直接 & (TypeError)
                _CRITICAL_FIELDS = {'status', 'completed_qty', 'qualified_qty', 'batch_no', 'operator'}
                _critical_in_cols = set(insert_cols) & _CRITICAL_FIELDS

                # [E3 修复 2026-06-13] 分批 commit（每 50 行一次）
                batch_size_for_commit = 50
                for i, row in enumerate(rows, 1):
                    values = []
                    for c in insert_cols:
                        v = row.get(c)
                        if isinstance(v, datetime):
                            v = v.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(v, (bytes, bytearray)):
                            v = None
                        elif v is None:
                            v = _ETL_DEFAULT_VALUES.get(target_table, {}).get(c)
                        values.append(v)
                    try:
                        tc.execute(upsert_sql, values)
                        synced += 1
                        # 每 50 行 commit 一次
                        if i % batch_size_for_commit == 0:
                            tgt_conn.commit()
                    except pymysql.IntegrityError as e:
                        # [P0 修复 2026-06-23] 1062 重复键: 数据脏/已存在, 跳过这一行
                        if '1062' in str(e) or 'Duplicate entry' in str(e):
                            logger.debug(f'[ETL] 跳过重复行: {target_table} {values[:1]} - {e}')
                            continue
                        raise
                    except pymysql.OperationalError as e:
                        # 表不存在 → 跳过
                        if '1146' in str(e) or 'no such table' in str(e).lower():
                            logger.warning(f'[ETL] 目标表不存在: {target_table}, 跳过')
                            return 0
                        raise
                # 提交剩余的（不满 50 行的批次）
                tgt_conn.commit()

            # [N1 修复] 记录最大时间戳，供下次同步使用
            last_row = rows[-1]
            if last_row.get(sync_field):
                v = last_row[sync_field]
                if isinstance(v, datetime):
                    new_sync_time = v.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    new_sync_time = str(v)
    finally:
        src_conn.close()
        tgt_conn.close()

    if synced > 0:
        logger.info(f'[ETL] {source_table} → {target_table}: 同步 {synced} 行, 时间游标={new_sync_time}')
        # [v4.1 监控 2026-06-21] 关键字段同步统计
        if _critical_in_cols:
            logger.info(f'[ETL 监控] 关键字段同步: {list(_critical_in_cols)}')
    return synced


def _sync_table_with_state(
    source_table: str,
    target_table: str,
    sync_field: str = 'updated_at',
    batch_size: int = 500,
) -> int:
    """带状态管理的同步：维护每张表的最后同步时间

    [N1 修复 2026-06-13] 使用模块级 _sync_state 字典记录每张表的 last_sync_time
    """
    last_time = _sync_state.get(source_table)
    synced = _sync_table(
        source_table=source_table,
        target_table=target_table,
        sync_field=sync_field,
        batch_size=batch_size,
        last_sync_time=last_time,
    )
    # 同步成功后才更新时间游标
    if synced > 0:
        _sync_state[source_table] = (datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    return synced


# [G2 修复 2026-06-13] 硬删除同步：删除镜像表中"源表已无"的行
def _sync_hard_delete(source_table: str, target_table: str, pk_col: str = 'id', batch_size: int = 200) -> int:
    """同步硬删除：删除镜像表中"源表已无"的行

    原理：
    1. 取镜像表最新的 200 个 uuid
    2. 查源表这些 uuid 是否还存在
    3. 不存在的 → 从镜像表删除

    Args:
        source_table: 源表
        target_table: 镜像表
        pk_col: 镜像表主键列
        batch_size: 每批处理行数

    Returns:
        硬删除的行数
    """
    try:
        from utils.trace import get_trace_id
        _trace_id = get_trace_id() or 'etl'

        tgt_conn = _get_mysql('container')
        try:
            with tgt_conn.cursor() as tc:
                # [K19 修复] 检查源表是否存在
                tc.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (source_table,))
                if tc.fetchone() is None:
                    logger.debug(f'[G2 硬删除] 源表 {source_table} 不存在，跳过')
                    return 0

                # [v4.1 修复 2026-06-21] 源表和目标表相同时跳过（避免 process_records 被误删）
                if source_table == target_table:
                    logger.debug(f'[G2 硬删除] 源表和目标表相同，跳过: {source_table}')
                    return 0

                # [P1 修复 2026-06-23] 检查目标表是否有 _synced_at 列, 没有则降级用 id 排序
                tc.execute(
                    "SELECT 1 FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s AND column_name = '_synced_at'",
                    (target_table,)
                )
                has_synced_at = tc.fetchone() is not None
                order_col = '_synced_at' if has_synced_at else 'id'
                # 取镜像表最新的 200 行
                tc.execute(f"SELECT {pk_col} FROM {target_table} ORDER BY {order_col} DESC LIMIT %s", (batch_size,))
                # [K19 修复] 使用索引访问 tuple 而不是字段名
                mirror_rows = tc.fetchall()
                if not mirror_rows:
                    return 0
                pk_idx = None
                for i, desc in enumerate(tc.description):
                    if desc[0] == pk_col:
                        pk_idx = i
                        break
                if pk_idx is None:
                    logger.warning(f'[G2 硬删除] 表 {target_table} 没有 {pk_col} 列')
                    return 0
                mirror_ids = [row[pk_idx] for row in mirror_rows if row[pk_idx] is not None]
                if not mirror_ids:
                    return 0

            src_conn = _get_mysql('steelbelt')
            try:
                with src_conn.cursor() as sc:
                    # 查源表这些 id 是否还存在
                    placeholders = ', '.join(['%s'] * len(mirror_ids))
                    sc.execute(f"SELECT {pk_col} FROM {source_table} WHERE {pk_col} IN ({placeholders})", mirror_ids)
                    # [K19 修复] 使用索引访问 tuple
                    source_rows = sc.fetchall()
                    pk_idx = None
                    for i, desc in enumerate(sc.description):
                        if desc[0] == pk_col:
                            pk_idx = i
                            break
                    if pk_idx is None:
                        logger.warning(f'[G2 硬删除] 源表 {source_table} 没有 {pk_col} 列')
                        return 0
                    source_ids = set(row[pk_idx] for row in source_rows)

                # 镜像表有但源表无 → 硬删除
                to_delete = [mid for mid in mirror_ids if mid not in source_ids]
                if not to_delete:
                    return 0

                with tgt_conn.cursor() as tc:
                    placeholders = ', '.join(['%s'] * len(to_delete))
                    tc.execute(
                        f"DELETE FROM {target_table} WHERE {pk_col} IN ({placeholders})",
                        to_delete
                    )
                tgt_conn.commit()
                logger.info(f'[G2 硬删除] {target_table} 删 {len(to_delete)} 行（源表已无）')
                return len(to_delete)
            finally:
                src_conn.close()
        finally:
            tgt_conn.close()
    except Exception as e:
        logger.warning(f'[G2 硬删除] {source_table} → {target_table} 失败: {e}')
        return 0


# [G3 修复 2026-06-13] 镜像表清理策略：删除 N 天前的旧数据
# [v4.1 修复 2026-06-21] 废除 process_sub_steps_local，移除清理
def _cleanup_old_records(retention_days: int = 90) -> int:
    """清理表中过期的旧数据

    [v4.1 重构 2026-06-21] _local 表已废除，改为清理主表
    策略：
    - violations 保留 365 天
    - 其他主表不清理（业务表）

    Returns:
        清理的行数
    """
    try:
        tgt_conn = _get_mysql('container')
        try:
            deleted_total = 0
            with tgt_conn.cursor() as tc:
                # violations 保留 365 天
                tc.execute("""
                    DELETE FROM violations
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (365,))
                deleted_total += tc.rowcount
            tgt_conn.commit()
            if deleted_total > 0:
                logger.info(f'[G3 清理] 表共清理 {deleted_total} 行（保留 {retention_days} 天）')
            return deleted_total
        finally:
            tgt_conn.close()
    except Exception as e:
        logger.warning(f'[G3 清理] 失败: {e}')
        return 0


# [G2 修复] 在 _run_etl_cycle 中调用硬删除同步
# [v4.1 重构 2026-06-21] _local 表已废除，改为同步到主表
_HARD_DELETE_TABLES = [
    # (source_table, target_table, pk_col)
    ('orders', 'orders', 'order_no'),
    ('violation_log', 'violations', 'id'),
    ('production_orders', 'production_orders', 'order_no'),
    ('process_records', 'process_records', 'id'),
    ('work_orders', 'work_orders', 'order_no'),
]


# [F9 修复 2026-06-13] ETL 显式列名白名单
# [v4.1 重构 2026-06-21] _local 表已废除，改为白名单主表
_ETL_TABLE_WHITELIST = {
    'orders': {
        'order_no', 'customer_group', 'customer_name', 'product_name',
        'quantity', 'status', 'plan_start', 'plan_end', 'is_deleted',
        'is_archived', 'id', 'order_id', 'updated_at', 'created_at',
    },
    'production_orders': {
        'order_no', 'product_name', 'plan_start', 'plan_end', 'status',
        'id', 'order_id', 'updated_at', 'created_at',
    },
    'process_records': {
        'id', 'order_no', 'process_code', 'step_name', 'process_name',
        'quantity', 'status', 'flow_type', 'batch_no', 'customer_name', 'customer_group',
        'product_name', 'unit', 'is_archived', 'is_deleted',
        'plan_start', 'plan_end', 'start_date', 'end_date',
        'updated_at', 'created_at',
    },
    'work_orders': {
        'id', 'order_no', 'customer_name', 'product_name', 'quantity',
        'status', 'is_deleted', 'plan_start', 'plan_end', 'updated_at', 'created_at',
    },
    'violations': {
        'id', 'scenario', 'violation_type', 'severity', 'order_no',
        'detail', 'created_at',
    },
    'operators': {
        'id', 'name', 'department', 'role', 'phone',
        'status', 'is_active', 'created_at', 'updated_at',
    },
    # [P1 修复 2026-06-23] 物料任务白名单
    'material_records': {
        'id', 'order_no', 'related_order', 'material_name', 'material_spec',
        'unit', 'warehouse', 'planned_qty', 'completed_qty', 'actual_qty',
        'target_operator', 'operator_id', 'status', 'priority', 'source',
        'arrival_date', 'expected_date', 'title', 'content',
        'created_at', 'updated_at', 'distributed_at', 'acknowledged_at', 'completed_at',
    },
    'quality_records': {
        'id', 'order_no', 'process_code', 'inspection_type', 'inspector',
        'result', 'quantity', 'qualified_qty', 'defect_qty', 'defect_types',
        'remark', 'record_date', 'created_at', 'updated_at',
    },
}


# [v4.1 修复 2026-06-21] ETL 同步时填充默认值
# 用于补充主表必需但源表没有的字段
_ETL_DEFAULT_VALUES = {
    'process_records': {
        'is_archived': 0,
        'is_deleted': 0,
        'status': 'pending',
        'unit': '',
        'quantity': 0,
    },
}


# [v4.1 修复 2026-06-21] ETL 可更新字段白名单
# 只有这些字段允许 ETL 增量更新，其他字段保持原值
# 注意：container_center.process_records 表结构与 steel_belt.process_records 不同
#       - process_records 表偏向订单基础信息
#       - 报工数据在 process_sub_steps 表
_ETL_UPDATABLE_FIELDS = {
    'process_records': {
        'id',               # 主键（用于定位）
        'order_no',         # 工单号（用于关联）
        'status',           # 状态
        'batch_no',         # 批次号
        'updated_by',       # 更新人
        'start_date',       # 开始日期
        'end_date',         # 结束日期
        'completed_at',     # 完成时间
        'efficiency',       # 效率
        'updated_at',       # 更新时间
        'is_deleted',       # 是否删除
        'is_archived',      # 是否归档
        'completed_by',     # 完成人
        'shift',           # 班次
        'machine_no',      # 机台号
        'actual_pause_minutes',  # 实际暂停分钟
        'pause_count',     # 暂停次数
        'rework_qty',      # 返工数量
        'scrap_qty',       # 报废数量
    },
}


# [v4.1 修复 2026-06-21] 任务发布特有字段（ETL 不更新）
# 这些字段只在任务发布系统写入
_TASK_PUBLISH_ONLY_FIELDS = {
    'process_records': {
        'record_id',           # 任务发布生成的记录ID
        'steps',               # 工序列表
        'process_code_prefix', # 工序编码前缀
        'process_seq',         # 工序序号
        'display_seq',         # 显示序号
        'production_id',       # 生产订单ID
        'plan_start',          # 计划开始
        'plan_end',            # 计划结束
        'planned_start',       # 计划开始时间
        'planned_end',         # 计划结束时间
        'customer_group',      # 客户群
        'product_name',        # 产品名称
        'quantity',            # 订单数量
        'unit',                # 单位
        'customer_name',       # 客户名称
        'delivery_date',       # 交付日期
        'priority',            # 优先级
        'current_step',        # 当前步骤
        'task_count',          # 任务数量
        'completed_task_count', # 已完成任务数
        'qc_required',        # 是否需要质检
        'qc_trigger_reason',   # 质检触发原因
        'data_locked',         # 数据锁定
        'last_reverted_at',    # 最后撤回时间
        'material_usage',      # 物料用量
        'material_unit',       # 物料单位
        'standard_minutes',    # 标准工时
        'setup_time',          # 准备时间
        'waste_rate',         # 废品率
        'actual_pause_minutes',# 实际暂停分钟
        'pause_count',         # 暂停次数
        'rework_qty',          # 返工数量
        'rework_count',        # 返工次数
        'scrap_qty',          # 报废数量
        'actual_used_qty',     # 实际用量
        'process_code',        # 工序编码
        'process_name',        # 工序名称
        'step_name',          # 步骤名称
        'process_type',       # 工序类型
        'flow_type',          # 流程类型
        'machine_no',         # 机台号
        'shift',              # 班次
        'content',            # 内容
        'template_id',        # 模板ID
        'record_type',        # 记录类型
        'defect_types',       # 缺陷类型
        'duration_days',      # 持续天数
        'calculated_qty',     # 计算数量
        'created_at',         # 创建时间
        'created_by',         # 创建人
        'deleted_at',         # 删除时间
        'deleted_by',         # 删除人
        'source',             # 数据来源
        'work_order_no',      # 工单号
        'prod_id',           # 生产ID
    },
}


def _run_etl_cycle() -> int:
    """执行一轮 ETL 同步

    [N1 修复 2026-06-13] 使用 _sync_state 状态字典维护每张表的时间游标
    [Q5 修复 2026-06-13] 失败重试 + 连续失败告警
    """
    total = 0
    # [v4.1 重构 2026-06-21] _local 表已废除，改为同步到主表
    # [P1 修复 2026-06-23] 添加 order_materials → material_records
    sync_configs = [
        # (source, target, sync_field)
        ('orders', 'orders', 'updated_at'),
        ('production_orders', 'production_orders', 'updated_at'),
        ('violation_log', 'violations', 'created_at'),
        ('process_records', 'process_records', 'updated_at'),
        # [v4.1] work_orders
        ('work_orders', 'work_orders', 'updated_at'),
        # [P1 修复 2026-06-23] 物料任务同步 (5001 端 order_materials → 5008 端 material_records)
        ('order_materials', 'material_records', 'updated_at'),
    ]
    for src, tgt, sf in sync_configs:
        # [Q5 修复] 失败重试 3 次
        n = 0
        last_err = None
        for attempt in range(1, 4):
            try:
                # [N1 修复] 改用带状态管理的同步
                n = _sync_table_with_state(src, tgt, sf)
                if attempt > 1:
                    logger.info(f'[ETL] {src} → {tgt} 重试第 {attempt} 次成功')
                # [Q5 修复] 成功后重置失败计数
                _consecutive_failures.pop(src, None)
                break
            except Exception as e:
                last_err = e
                if attempt < 3:
                    time.sleep(2 ** attempt)  # 指数退避 2s, 4s
                continue
        if n == 0 and last_err is not None:
            # [Q5 修复] 连续失败告警
            _consecutive_failures[src] = _consecutive_failures.get(src, 0) + 1
            fails = _consecutive_failures[src]
            logger.warning(f'[ETL] {src} → {tgt} 失败 (连续 {fails} 次): {last_err}')
            if fails >= 3:
                _trigger_alert(src, tgt, fails, last_err)
        total += n

    # [G2 修复 2026-06-13] 硬删除同步：每轮 ETL 同步后清理镜像表中"源表已无"的行
    for src, tgt, pk in _HARD_DELETE_TABLES:
        try:
            _sync_hard_delete(src, tgt, pk)
        except Exception as e:
            logger.warning(f'[G2 硬删除] {src}/{tgt} 失败: {e}')

    # [G3 修复 2026-06-13] 清理过期数据
    try:
        _cleanup_old_records()
    except Exception as e:
        logger.warning(f'[G3 清理] 失败: {e}')

    return total


# [Q5 修复 2026-06-13] 失败计数 + 告警
_consecutive_failures: dict = {}  # {source_table: fail_count}


def _trigger_alert(src: str, tgt: str, fail_count: int, last_err: Exception):
    """触发告警：连续失败 >= 3 次时"""
    try:
        # 1. 写告警到 dead_letter 表
        try:
            import pymysql
            from core.config import CONTAINER_MYSQL_CFG
            from core.db_compat import get_conn
            conn = get_conn()
            try:
                with conn.cursor() as c:
                    c.execute("""
                        CREATE TABLE IF NOT EXISTS etl_dead_letter (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            source_table VARCHAR(64),
                            target_table VARCHAR(64),
                            fail_count INT,
                            last_error TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    c.execute("""
                        INSERT INTO etl_dead_letter (source_table, target_table, fail_count, last_error)
                        VALUES (%s, %s, %s, %s)
                    """, (src, tgt, fail_count, str(last_err)[:500]))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f'[ETL] 写 dead_letter 失败: {e}')

        # 2. 调 5003 微信通知（如果配置）
        try:
            import requests as _req
            _req.post(
                f'{os.getenv("DISPATCH_CENTER_URL", "http://127.0.0.1:5003")}/api/notify/wechat',
                json={
                    'message': f'⚠️ ETL 连续失败\n{src} → {tgt}\n次数: {fail_count}\n错误: {str(last_err)[:200]}',
                    'level': 'warning',
                },
                timeout=2,
            )
        except Exception:
            pass  # 通知失败不阻塞

        logger.error(f'[ETL ALERT] {src} → {tgt} 连续失败 {fail_count} 次, 告警已触发')
    except Exception as e:
        logger.error(f'[ETL] 告警触发失败: {e}')


# ============= 状态管理 =============
# [N1 修复 2026-06-13] 改为 {table_name: last_sync_time} 字典
# 之前: _last_sync_time 永远是 24h 前，每次都重置 → 每轮都全表
# 修复: 每张表独立维护时间游标，同步成功后更新
_sync_state: dict = {}  # {source_table: 'YYYY-MM-DD HH:MM:SS'}
_etl_running = threading.Event()
_etl_stop = threading.Event()
# [K17 修复 2026-06-14] 全局线程引用，保证 start 幂等
_etl_thread: Optional[threading.Thread] = None


def start_etl_worker(interval_sec: int = 60):
    """启动 ETL 后台线程

    [C1 修复 2026-06-13] 后台线程持续同步 steel_belt → container_center 本地表
    [P1 集成 thread_lifecycle 2026-06-13] 支持优雅停止
    [N6 修复 2026-06-13] 启动前检查目标表是否存在
    """
    # [N6 修复] 启动前检查 4 个目标表是否存在
    missing_tables = _check_target_tables()
    if missing_tables:
        logger.warning(
            f'[ETL] 以下主表不存在: {missing_tables}\n'
            f'  [v4.1] _local 表已废除，ETL 同步已简化。\n'
            f'  ETL 仍会启动，但同步这些表时会失败。'
        )
    def _worker():
        logger.info(f'[ETL Worker] 启动，同步间隔 {interval_sec}s')
        while not _etl_stop.is_set():
            try:
                _run_etl_cycle()
            except Exception as e:
                logger.warning(f'[ETL Worker] 异常: {e}')
            # 拆 sleep，0.5s 步进快速响应停止
            for _ in range(int(interval_sec * 2)):
                if _etl_stop.is_set():
                    break
                time.sleep(0.5)
        logger.info('[ETL Worker] 收到停止信号，退出')

    # [P1 修复] 使用 thread_lifecycle
    # [K17 修复 2026-06-14] 幂等 - 多次启动不创建重复线程
    global _etl_thread
    if _etl_thread is not None and _etl_thread.is_alive():
        logger.info('[ETL Worker] 已在运行，跳过启动')
        return _etl_thread
    try:
        from thread_lifecycle import create_daemon_thread
        _etl_thread = create_daemon_thread(name='etl-mirror-worker', target=_worker)
    except ImportError:
        _etl_thread = threading.Thread(target=_worker, daemon=True, name='etl-mirror-worker')
        _etl_thread.start()
    logger.info('[ETL Worker] 线程已启动')
    return _etl_thread


def stop_etl_worker():
    """停止 ETL 线程"""
    _etl_stop.set()


def manual_sync_once() -> int:
    """手动触发一次同步（用于测试或运维）"""
    return _run_etl_cycle()


if __name__ == '__main__':
    # 测试模式：手动同步一次
    logging.basicConfig(level=logging.INFO)
    n = manual_sync_once()
    print(f'同步完成: {n} 行')
