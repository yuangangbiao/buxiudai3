# -*- coding: utf-8 -*-
"""
data_type 契约 v1.0 数据迁移脚本
==================================

将 ``container_center.data_packages`` 表中历史 data_type 重新打标签,
符合新契约(参见 docs/DATA_TYPE_CONTRACT.md)。

旧值 → 新值映射:
  report             → process_report / flow_step (按 related_process 判定)
  material           → material_pickup
  material_purchase  → material_request
  purchase           → material_buy
  quality            → quality_task
  quality_inspection → quality_task
  repair             → equipment_repair
  outsource          → outsource_task
  production         → flow_production
  config / 空        → config

用法::

    # 1. 干跑 (只看不改)
    python migrate_data_type_to_v1.py --dry-run

    # 2. 真正执行
    python migrate_data_type_to_v1.py --execute

    # 3. 回滚
    python migrate_data_type_to_v1.py --rollback <backup_table_name>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# 把项目根加入 path, 便于 import utils
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pymysql  # noqa: E402

from utils.data_type_contract import (  # noqa: E402
    LEGACY_TO_NEW,
    NEW_DATA_TYPES,
    PROCESS_FLOW_TEMPLATES,
    _parse_content,
    classify_payloads,
    get_flow_step_names_set,
)

# ────────────────────────────────────────────────────────────
# 数据库连接(从环境变量或 core.config 读)
# ────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "database": "container_center",
    "charset": "utf8mb4",
}

BACKUP_TABLE = f"data_packages_dt_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _connect():
    return pymysql.connect(**DB_CONFIG)


def _load_process_names(conn) -> set:
    """加载 process_names.process_name 全集
    [F16 T16.7 修复] process_names 表已 F6 P9 2026-06-10 DROP, 改用内存 PROCESS_CODES
    """
    # [F16 T16.7 修复] 改用 core.config PROCESS_CODES + _custom_process_codes
    try:
        from core.config import PROCESS_CODES, _custom_process_codes
        return set({**PROCESS_CODES, **_custom_process_codes}.keys())
    except Exception:
        return set()


def _classify_one(dt: str, related_process: str, process_set: set, flow_step_set: set, content: dict = None) -> str:
    """单条记录归类(支持 content 字段兜底判定)"""
    if dt in NEW_DATA_TYPES:
        return dt
    target = LEGACY_TO_NEW.get(dt)
    if target is None:
        return "__contract_violation__"
    if target == "__dynamic__":
        # 走完整的 content 兜底判定
        pkg = {
            "data_type": dt,
            "related_process": related_process,
            "content": content or {},
        }
        # 直接复用 _classify_legacy_report 逻辑(用 inline 实现避免循环引用)
        rp = related_process or ""
        c = content or {}
        flow_type = (c.get("flow_type") or "").strip()
        if flow_type == "production":
            return "flow_production"
        if rp.startswith("质检-") or c.get("inspection_type") or c.get("inspection_items"):
            return "quality_task"
        try:
            qty = float(c.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if (rp.startswith("备料-") or rp.startswith("物料") or "不锈钢" in rp) and qty > 0:
            return "material_request"
        if rp in process_set:
            return "process_report"
        if rp in flow_step_set:
            return "flow_step"
        return "__contract_violation__"
    return target


def _fetch_all(conn) -> List[Tuple]:
    """拉取所有 data_packages"""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, data_type, related_process, related_order, status, content "
        "FROM data_packages"
    )
    return cur.fetchall()


def _parse_content_str(s) -> dict:
    if not s:
        return {}
    try:
        return json.loads(s) if isinstance(s, str) else (s if isinstance(s, dict) else {})
    except Exception:
        return {}


def _backup(conn, dry_run: bool) -> str:
    """备份表,用于回滚"""
    if dry_run:
        return BACKUP_TABLE
    cur = conn.cursor()
    cur.execute(
        f"CREATE TABLE {BACKUP_TABLE} AS "
        f"SELECT id, data_type, related_process, related_order, status, created_at "
        f"FROM data_packages"
    )
    conn.commit()
    print(f"  ✓ 备份完成 → {BACKUP_TABLE}")
    return BACKUP_TABLE


def _rollback(backup_table: str) -> int:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE data_packages dp "
            f"JOIN {backup_table} b ON dp.id = b.id "
            f"SET dp.data_type = b.data_type"
        )
        affected = cur.rowcount
        conn.commit()
        print(f"  ✓ 已回滚 {affected} 条 → data_packages.data_type 恢复为备份值")
        return affected
    finally:
        conn.close()


def _build_plan(rows: List[Tuple], process_set: set, flow_step_set: set) -> Dict:
    """
    制定迁移计划,统计每种映射的条数
    Returns
    -------
    dict: {new_type: count}, plus 'violations': [(id, dt, rp)]
    """
    plan: Dict[str, int] = {dt: 0 for dt in NEW_DATA_TYPES}
    plan["__contract_violation__"] = 0
    plan["__unchanged__"] = 0
    violations: List[Tuple] = []

    for row in rows:
        pkg_id, dt, rp, order, status, content_str = row
        content = _parse_content_str(content_str)
        new_type = _classify_one(dt or "", rp or "", process_set, flow_step_set, content)
        if new_type in NEW_DATA_TYPES:
            plan[new_type] += 1
        elif new_type == "__contract_violation__":
            plan["__contract_violation__"] += 1
            violations.append((pkg_id, dt, rp, order))
        else:
            plan["__unchanged__"] += 1
    return {"plan": plan, "violations": violations}


def _print_plan(plan: Dict, total: int):
    print(f"\n  共 {total} 条记录,迁移计划:")
    for k, v in sorted(plan["plan"].items(), key=lambda x: -x[1]):
        if v == 0:
            continue
        print(f"    {k:30} : {v:4d} 条")
    if plan["violations"]:
        print(f"\n  ⚠ 契约违反 {len(plan['violations'])} 条:")
        for vid, vdt, vrp, vorder in plan["violations"][:10]:
            print(f"    id={vid} | data_type={vdt!r} | related_process={vrp!r} | order={vorder}")
        if len(plan["violations"]) > 10:
            print(f"    ... 另 {len(plan['violations']) - 10} 条")


def _execute_migration(conn, rows, process_set, flow_step_set) -> Tuple[int, int]:
    """执行 UPDATE,返回 (更新条数, 违反条数)"""
    cur = conn.cursor()
    updated = 0
    violations = 0
    for row in rows:
        pkg_id, dt, rp, order, status, content_str = row
        content = _parse_content_str(content_str)
        new_type = _classify_one(dt or "", rp or "", process_set, flow_step_set, content)
        if new_type in NEW_DATA_TYPES:
            cur.execute(
                "UPDATE data_packages SET data_type=%s WHERE id=%s",
                (new_type, pkg_id),
            )
            updated += cur.rowcount
        elif new_type == "__contract_violation__":
            violations += 1
    conn.commit()
    return updated, violations


def main():
    parser = argparse.ArgumentParser(description="data_type 契约 v1.0 数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划,不修改数据")
    parser.add_argument("--execute", action="store_true", help="实际执行迁移")
    parser.add_argument("--rollback", metavar="BACKUP_TABLE", help="回滚到指定备份表")
    args = parser.parse_args()

    if args.rollback:
        _rollback(args.rollback)
        return

    if not (args.dry_run or args.execute):
        parser.print_help()
        return

    conn = _connect()
    try:
        print("=" * 70)
        print(f"data_type 契约 v1.0 数据迁移  ({'DRY-RUN' if args.dry_run else 'EXECUTE'})")
        print("=" * 70)

        process_set = _load_process_names(conn)
        flow_step_set = get_flow_step_names_set()
        print(f"\n  process_names 物理工序集合: {len(process_set)} 条")
        print(f"  流程 step.name 集合: {len(flow_step_set)} 条 = {sorted(flow_step_set)}")

        rows = _fetch_all(conn)
        print(f"\n  data_packages 总记录: {len(rows)} 条")

        plan = _build_plan(rows, process_set, flow_step_set)
        _print_plan(plan, len(rows))

        if args.dry_run:
            print(f"\n  (dry-run 模式,未修改数据)")
            return

        # 真实执行
        print(f"\n>>> 创建备份表 {BACKUP_TABLE}")
        _backup(conn, dry_run=False)

        print(f"\n>>> 开始执行 UPDATE ...")
        updated, violations = _execute_migration(conn, rows, process_set, flow_step_set)
        print(f"  ✓ 已更新 {updated} 条;契约违反 {violations} 条 (未改动)")

        if violations:
            print(f"\n  ⚠ 仍有 {violations} 条契约违反未修复,请人工 review")
            print(f"     回滚命令: python {__file__} --rollback {BACKUP_TABLE}")

        print(f"\n  回滚命令(如需): python {__file__} --rollback {BACKUP_TABLE}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
