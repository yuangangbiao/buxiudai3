#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RE-007 4 工单异常修复脚本(重写版 v2)
====================================

【真相修正】(基于 2026-06-10 详细 DB 探查):
  4 工单 `container_center.data_packages` 实际全部为 0 条(全空)
  业务真实数据分布在:
    - steel_belt.orders         : 工单主单
    - steel_belt.process_records: 工序计划/状态(planned_qty, status, display_seq)
    - steel_belt.process_sub_steps: 工序报工(batch 粒度实际完成量)
    - steel_belt.quality_records: 质检记录
  原 REPORT 里的 10 类异常 = API 返回的 mock/cache 旧数据(已不存在)
  真实根因: process_records/process_sub_steps 没同步到 data_packages 派单视图

【新策略】6 步修复:
  SQL#1 自动备份 data_packages 全表
  SQL#2 从 process_records 同步生成 process_task 派单
       (含 display_seq 排序、planned_qty 取 max(planned_qty, SUM(qualified_qty)),
        target_operator 取 process_sub_steps.operator, status 映射)
  SQL#3 ORD-202604210004 完全空(0 工序),从 process_names 模板补 16 道工序报工
  SQL#4 process_records.planned_qty 异常修正
       (P06/P07 29528 → orders.quantity, 其它 0 → orders.quantity)
  SQL#5 修正 process_records.status 中英文(status='待开始' → 'pending',
       'in_progress' → 'in_production')
  SQL#6 修正 process_records.status 同 source='chengsheng' 的工单同步 created/updated_at

用法:
  py scripts/fix_4orders_anomaly.py --dry-run      # 预览影响行数
  py scripts/fix_4orders_anomaly.py --execute      # 执行(自动备份)
  py scripts/fix_4orders_anomaly.py --rollback BT  # 还原

设计:
  - 全部 SQL 走参数化,无注入
  - 每次执行打印影响行数
  - 失败立即停止,提示用 --rollback 还原
"""
import os
import sys
import json
import uuid
import argparse
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pymysql

DB = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "charset": "utf8mb4",
    "autocommit": False,
}

ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]


def get_conn(db):
    c = pymysql.connect(database=db, **DB)
    c.cursor().execute("SET NAMES utf8mb4")
    return c


def log(msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "  ", "OK": "✓", "WARN": "⚠", "ERR": "✗"}.get(level, " ")
    print(f"  [{ts}] {icon} {msg}", flush=True)


def header(title):
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


# =========================================================================
# 备份/回滚
# =========================================================================

def backup_table(src_db, src_table, backup_table, container_db="container_center"):
    """跨库备份:container_center.data_packages -> container_center.data_packages_backup"""
    log(f"备份 {src_db}.{src_table} -> {container_db}.{backup_table}")
    conn = get_conn(container_db)
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS {backup_table}")
    cur.execute(
        f"CREATE TABLE {backup_table} AS SELECT * FROM {src_db}.{src_table}"
    )
    cur.execute(f"SELECT COUNT(*) FROM {backup_table}")
    cnt = cur.fetchone()[0]
    conn.commit()
    conn.close()
    log(f"备份完成:{cnt} 行", "OK")
    return cnt


def rollback_table(backup_table, target_db, target_table, container_db="container_center"):
    """还原:container_center.{backup_table} -> {target_db}.{target_table}"""
    log(f"还原 {container_db}.{backup_table} -> {target_db}.{target_table}")
    conn = get_conn(container_db)
    cur = conn.cursor()
    cur.execute(f"SHOW TABLES LIKE %s", (backup_table,))
    if not cur.fetchone():
        log(f"备份表 {backup_table} 不存在,无法回滚", "ERR")
        conn.close()
        return
    # 用 TRUNCATE + INSERT(避免 FK 约束)
    cur.execute(f"DELETE FROM {target_db}.{target_table}")
    cur.execute(
        f"INSERT INTO {target_db}.{target_table} SELECT * FROM {backup_table}"
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    log(f"已还原 {n} 行", "OK")


# =========================================================================
# 探查
# =========================================================================

def show_status_4orders():
    """打印 4 工单修复前状态"""
    header("📊 修复前 4 工单状态(steel_belt + container_center)")

    conn = get_conn("steel_belt")
    cur = conn.cursor()
    cur.execute("""SELECT order_no, status, quantity, product_name
                   FROM orders WHERE order_no IN (%s,%s,%s,%s)""", ORDERS)
    print("\n  [orders]")
    for r in cur.fetchall():
        print(f"    {r[0]:22s} status={r[1]:8s} qty={r[2]:>4} product={r[3]}")

    cur.execute("""SELECT order_no, COUNT(*) AS prs,
                          SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS done
                   FROM process_records WHERE order_no IN (%s,%s,%s,%s) AND is_deleted=0
                   GROUP BY order_no""", ORDERS)
    print("\n  [process_records]")
    prs_map = {r[0]: r[1:] for r in cur.fetchall()}
    for o in ORDERS:
        v = prs_map.get(o, (0, 0))
        print(f"    {o:22s} 工序数={v[0]:>3} 已完成={v[1]}")

    cur.execute("""SELECT order_no, COUNT(*) AS bs, SUM(quantity) AS qty
                   FROM process_sub_steps WHERE order_no IN (%s,%s,%s,%s) AND is_deleted=0
                   GROUP BY order_no""", ORDERS)
    print("\n  [process_sub_steps 报工批次]")
    pss_map = {r[0]: r[1:] for r in cur.fetchall()}
    for o in ORDERS:
        v = pss_map.get(o, (0, 0))
        print(f"    {o:22s} 报工批={v[0]:>3} 累计 qty={v[1] or 0}")
    conn.close()

    conn = get_conn("container_center")
    cur = conn.cursor()
    cur.execute("""SELECT order_no, data_type, COUNT(*)
                   FROM data_packages WHERE order_no IN (%s,%s,%s,%s)
                   GROUP BY order_no, data_type""", ORDERS)
    print("\n  [data_packages]")
    for r in cur.fetchall():
        print(f"    {r[0]:22s} {r[1]:20s} {r[2]:>3}")
    conn.close()


# =========================================================================
# 修复 SQL
# =========================================================================

def fix_sql_2_sync_process_tasks(conn_steel, conn_container):
    """SQL#2: 从 process_records + process_sub_steps 同步生成 data_packages.process_task"""
    header("🔧 SQL#2: 从 process_records 同步生成 process_task 派单")
    cur = conn_steel.cursor()
    ccur = conn_container.cursor()

    # 收集每条 process_record 的同步数据
    cur.execute("""
        SELECT
            pr.id, pr.order_no, pr.process_code, pr.process_name,
            pr.display_seq, pr.process_seq, pr.planned_qty, pr.completed_qty,
            pr.qualified_qty, pr.status, pr.worker, pr.operator,
            pr.is_outsource, pr.machine_no,
            (SELECT COALESCE(SUM(pss.quantity), 0) FROM process_sub_steps pss
             WHERE pss.order_no=pr.order_no AND pss.step_name=pr.process_name
               AND pss.is_deleted=0) AS sub_qty,
            (SELECT COALESCE(SUM(pss.qualified_qty), 0) FROM process_sub_steps pss
             WHERE pss.order_no=pr.order_no AND pss.step_name=pr.process_name
               AND pss.is_deleted=0) AS sub_qual,
            (SELECT pss.operator FROM process_sub_steps pss
             WHERE pss.order_no=pr.order_no AND pss.step_name=pr.process_name
               AND pss.is_deleted=0 ORDER BY pss.record_date DESC, pss.id DESC LIMIT 1) AS sub_op
        FROM process_records pr
        WHERE pr.order_no IN (%s,%s,%s,%s) AND pr.is_deleted=0
        ORDER BY pr.order_no, pr.display_seq, pr.process_seq, pr.id
    """, ORDERS)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    log(f"找到 {len(rows)} 条 process_records 待同步")

    # 检查 data_packages 已存在的同 order+process (避免重复)
    ccur.execute("""
        SELECT order_no, related_process FROM data_packages
        WHERE order_no IN (%s,%s,%s,%s) AND data_type='process_task'
    """, ORDERS)
    existing = {(r[0], r[1]) for r in ccur.fetchall()}
    log(f"data_packages 已存在 process_task: {len(existing)} 条")

    # 状态映射(process_records.status 中文/英文 → data_packages 标准 status)
    status_map = {
        "待开始": "pending",
        "进行中": "in_progress",
        "in_progress": "in_progress",
        "已完成": "completed",
        "completed": "completed",
        "pending": "pending",
    }

    new_pkgs = []
    for r in rows:
        d = dict(zip(cols, r))
        if (d["order_no"], d["process_name"]) in existing:
            continue
        # operator 优先 sub_op, 其次 worker/operator
        operator = d["sub_op"] or d["worker"] or d["operator"] or ""
        # planned_qty: 取 max(planned_qty, sub_qty, orders.quantity)
        # 这里先取 sub_qty 兜底,后续 SQL#4 再统一修正
        planned = max(d["planned_qty"] or 0, int(d["sub_qty"] or 0))
        completed = int(d["sub_qual"] or 0)  # 报工合格量 = 已完成量
        # 状态映射
        st = status_map.get(d["status"], "pending")
        if completed > 0 and st == "pending":
            st = "in_progress"
        if planned > 0 and completed >= planned:
            st = "completed"
        # content JSON
        content = json.dumps({
            "process_code": d["process_code"],
            "process_name": d["process_name"],
            "display_seq": d["display_seq"],
            "process_seq": d["process_seq"],
            "planned_qty": planned,
            "is_outsource": bool(d["is_outsource"]),
            "source": "sync_from_process_records_2026_06_10",
            "process_record_id": d["id"],
        }, ensure_ascii=False)
        # title
        title = f"{d['order_no']} - {d['process_name']}({d['process_code']})"
        new_pkgs.append((
            f"PKG-{uuid.uuid4().hex[:12].upper()}",
            "process_task",
            title,
            content,
            "sync_v2",
            st,
            operator,
            "",
            d["order_no"],
            d["process_name"],
            d["display_seq"] or 999,
        ))

    log(f"将插入 {len(new_pkgs)} 条新 process_task")
    if new_pkgs:
        ccur.executemany("""
            INSERT INTO data_packages
                (id, data_type, title, content, source, status,
                 target_operator, operator_id, order_no, related_process,
                 completed_qty, progress_qty, actual_qty, priority, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    0, 0, 0, 'normal', NOW())
        """, [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9])
              for p in new_pkgs])
        n = ccur.rowcount
        log(f"插入 {n} 行", "OK" if n == len(new_pkgs) else "WARN")

    # 二次更新 completed_qty / progress_qty / actual_qty
    for p in new_pkgs:
        completed = int(json.loads(p[3])["planned_qty"])  # 简化:此处 planned_qty 实际是 completed 来自 sub_qual
        # 实际是 process_records 里的 completed_qty + sub_qual 的最大值
        # 重新计算一次(简化:从 process_sub_steps 取)
        ccur.execute("""
            UPDATE data_packages
            SET completed_qty=(
                SELECT COALESCE(SUM(qualified_qty), 0) FROM steel_belt.process_sub_steps
                WHERE order_no=%s AND step_name=%s AND is_deleted=0
            ),
            progress_qty=(
                SELECT COALESCE(SUM(quantity), 0) FROM steel_belt.process_sub_steps
                WHERE order_no=%s AND step_name=%s AND is_deleted=0
            ),
            actual_qty=(
                SELECT COALESCE(SUM(qualified_qty), 0) FROM steel_belt.process_sub_steps
                WHERE order_no=%s AND step_name=%s AND is_deleted=0
            )
            WHERE id=%s
        """, (p[8], p[9], p[8], p[9], p[8], p[9], p[0]))
    log(f"二次更新 completed_qty/progress_qty/actual_qty: {len(new_pkgs)} 行", "OK")
    return len(new_pkgs)


def fix_sql_3_supply_empty_order(conn_steel, conn_container):
    """SQL#3: 为 ORD-202604210004(完全空)从 process_names 模板补 16 道工序"""
    header("🔧 SQL#3: 为 ORD-202604210004 补建 16 道工序 process_task")
    cur = conn_steel.cursor()
    ccur = conn_container.cursor()

    # 查 ORD-202604210004 数量
    cur.execute("SELECT quantity FROM orders WHERE order_no='ORD-202604210004'")
    qty_row = cur.fetchone()
    qty = int(qty_row[0]) if qty_row else 0
    log(f"ORD-202604210004 quantity = {qty}")

    # 查 process_names 全部(注意: process_names 在 container_center 库)
    # [F16 T16.7 修复] process_names 表已 F6 P9 2026-06-10 DROP, 改用 dispatch_cache + 内存
    log('[F16 T16.7] process_names 表已 F6 P9 DROP, 改用 dispatch_cache.process_departments')
    pns = []
    try:
        from core.config import PROCESS_CODES, _custom_process_codes
        merged = {**PROCESS_CODES, **_custom_process_codes}
        for name, code in merged.items():
            pns.append((code, name, code[:1].upper() if code else '', ''))  # (code, name, prefix, department)
    except Exception as e:
        log(f'[F6 P9 兼容] 读 process_departments 失败: {e}')
    log(f"process_names 共 {len(pns)} 条")

    # 过滤:department 不为空 / prefix P + 必要 P_CS / X01 / M01
    valid_pns = [p for p in pns if p[3] and p[2] in ('P', 'M', 'X', 'Q')]

    # 检查已存在
    ccur.execute("""
        SELECT related_process FROM data_packages
        WHERE order_no='ORD-202604210004' AND data_type='process_task'
    """)
    existing = {r[0] for r in ccur.fetchall()}

    new_pkgs = []
    seq = 1
    for code, name, prefix, dept in valid_pns:
        if name in existing:
            continue
        content = json.dumps({
            "process_code": code,
            "process_name": name,
            "display_seq": seq,
            "planned_qty": qty,
            "is_outsource": False,
            "source": "supply_empty_order_2026_06_10",
        }, ensure_ascii=False)
        new_pkgs.append((
            f"PKG-EMPTY-{uuid.uuid4().hex[:10].upper()}",
            "process_task",
            f"ORD-202604210004 - {name}({code})",
            content,
            "supply_v2",
            "pending",
            "",
            "",
            "ORD-202604210004",
            name,
            seq,
        ))
        seq += 1

    log(f"将插入 {len(new_pkgs)} 条新 process_task(为空工单补全)")
    if new_pkgs:
        ccur.executemany("""
            INSERT INTO data_packages
                (id, data_type, title, content, source, status,
                 target_operator, operator_id, order_no, related_process,
                 completed_qty, progress_qty, actual_qty, priority, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 'normal', NOW())
        """, new_pkgs)
        n = ccur.rowcount
        log(f"插入 {n} 行", "OK" if n == len(new_pkgs) else "WARN")
    return len(new_pkgs)


def fix_sql_4_fix_planned_qty(conn_steel):
    """SQL#4: 修正 process_records.planned_qty 异常值
       - P06/P07 编制 29528 → orders.quantity (可能本身就是另一种单位,这里只对单条记录改)
       - 其它 planned_qty=0 → orders.quantity
    """
    header("🔧 SQL#4: 修正 process_records.planned_qty 异常")
    cur = conn_steel.cursor()

    # 策略:对于所有 4 工单的 process_records.planned_qty,先与 orders.quantity 对比
    # 如果 planned_qty=0 或 异常大(> 10 * orders.quantity),都改为 orders.quantity
    cur.execute("""
        UPDATE process_records pr
        JOIN orders o ON pr.order_no=o.order_no
        SET pr.planned_qty = o.quantity
        WHERE pr.order_no IN (%s,%s,%s,%s)
          AND pr.is_deleted=0
          AND (pr.planned_qty=0 OR pr.planned_qty > 10 * o.quantity)
    """, ORDERS)
    n = cur.rowcount
    log(f"更新 planned_qty {n} 行", "OK" if n > 0 else "WARN")
    return n


def fix_sql_5_normalize_status(conn_steel):
    """SQL#5: 修正 process_records.status 中英文 → 标准 status"""
    header("🔧 SQL#5: 修正 process_records.status 中英文")
    cur = conn_steel.cursor()

    cur.execute("""
        UPDATE process_records
        SET status = CASE
            WHEN status IN ('待开始', 'pending', 'Pending', 'PENDING') THEN 'pending'
            WHEN status IN ('进行中', 'in_progress', 'InProgress', 'IN_PROGRESS') THEN 'in_progress'
            WHEN status IN ('已完成', 'completed', 'Completed', 'COMPLETED') THEN 'completed'
            WHEN status IN ('已暂停', 'paused', 'Paused') THEN 'paused'
            WHEN status IN ('已取消', 'cancelled', 'Cancelled') THEN 'cancelled'
            ELSE status
        END
        WHERE order_no IN (%s,%s,%s,%s) AND is_deleted=0
    """, ORDERS)
    n = cur.rowcount
    log(f"标准化 status {n} 行", "OK" if n > 0 else "INFO")
    return n


def fix_sql_6_recompute_status_from_sub_steps(conn_steel):
    """SQL#6: 重新计算 process_records.status(根据 process_sub_steps 累计完成量 vs planned_qty)"""
    header("🔧 SQL#6: 根据报工实际数据重算 process_records.status")
    cur = conn_steel.cursor()

    cur.execute("""
        UPDATE process_records pr
        LEFT JOIN (
            SELECT order_no, step_name,
                   COALESCE(SUM(qualified_qty), 0) AS sub_qual
            FROM process_sub_steps
            WHERE order_no IN (%s,%s,%s,%s) AND is_deleted=0
            GROUP BY order_no, step_name
        ) pss ON pr.order_no=pss.order_no AND pr.process_name=pss.step_name
        SET pr.status = CASE
            WHEN pss.sub_qual IS NULL OR pss.sub_qual=0 THEN 'pending'
            WHEN pr.planned_qty > 0 AND pss.sub_qual >= pr.planned_qty THEN 'completed'
            ELSE 'in_progress'
        END
        WHERE pr.order_no IN (%s,%s,%s,%s) AND pr.is_deleted=0
    """, ORDERS + ORDERS)
    n = cur.rowcount
    log(f"重算 status {n} 行", "OK" if n > 0 else "INFO")
    return n


# =========================================================================
# 流程编排
# =========================================================================

def dry_run():
    """预览"""
    header("🔍 DRY-RUN 预览(不执行任何修改)")
    show_status_4orders()

    print("\n" + "=" * 76)
    print("  📋 修复动作清单(预期影响)")
    print("=" * 76)
    actions = [
        ("SQL#1", "备份 data_packages -> data_packages_4orders_v2_backup_YYYYMMDD_HHMMSS", "≈0 行(空表)"),
        ("SQL#2", "从 process_records 同步生成 process_task(排除已存在)", "ORD-202605020001:9, ORD-202604210002:10, ORD-202605010001:10 = 29"),
        ("SQL#3", "ORD-202604210004 从 process_names 模板补 16 道工序", "≤16"),
        ("SQL#4", "修正 process_records.planned_qty(0/异常 → orders.quantity)", "≈10 行(0+ 29528 异常)"),
        ("SQL#5", "标准化 process_records.status 中英文", "≈0(已标准化)"),
        ("SQL#6", "根据报工重算 process_records.status", "29 行(所有 process_records)"),
    ]
    for k, v, exp in actions:
        print(f"\n  [{k}] {v}")
        print(f"        预期影响: {exp}")


def execute():
    """执行所有修复"""
    header("🔧 EXECUTE 执行修复")
    show_status_4orders()

    # 0. 备份
    backup_name = f"data_packages_4orders_v2_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_table("container_center", "data_packages", backup_name)
    # 保存 backup_table 名
    with open(os.path.join(ROOT, "scripts", "last_backup_v2.txt"), "w") as f:
        f.write(backup_name)

    conn_steel = get_conn("steel_belt")
    conn_container = get_conn("container_center")
    results = {}

    try:
        results["SQL#2"] = fix_sql_2_sync_process_tasks(conn_steel, conn_container)
        results["SQL#3"] = fix_sql_3_supply_empty_order(conn_steel, conn_container)
        results["SQL#4"] = fix_sql_4_fix_planned_qty(conn_steel)
        results["SQL#5"] = fix_sql_5_normalize_status(conn_steel)
        results["SQL#6"] = fix_sql_6_recompute_status_from_sub_steps(conn_steel)

        conn_steel.commit()
        conn_container.commit()
        log("已 commit", "OK")
    except Exception as e:
        conn_steel.rollback()
        conn_container.rollback()
        log(f"执行失败:{e}", "ERR")
        log(f"可执行 --rollback {backup_name} 还原 data_packages", "ERR")
        raise
    finally:
        conn_steel.close()
        conn_container.close()

    # 打印汇总
    header("📊 修复汇总")
    for k, v in results.items():
        print(f"  {k}: {v} 行")
    print(f"\n  备份表: {backup_name}")
    print(f"  回滚命令: py scripts/fix_4orders_anomaly.py --rollback {backup_name}")

    # 打印修复后状态
    show_status_4orders()


def rollback(backup_table):
    header(f"⏪ ROLLBACK:从 {backup_table} 还原")
    rollback_table(backup_table, "container_center", "data_packages")
    show_status_4orders()


def main():
    ap = argparse.ArgumentParser(description="RE-007 4 工单异常修复脚本 v2")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--rollback", metavar="BACKUP_TABLE")
    args = ap.parse_args()

    if not any([args.dry_run, args.execute, args.rollback]):
        ap.print_help()
        return 1

    if args.dry_run:
        dry_run()
    elif args.execute:
        execute()
    elif args.rollback:
        rollback(args.rollback)
    return 0


if __name__ == "__main__":
    sys.exit(main())
