# -*- coding: utf-8 -*-
"""桌面端 dry-run：模拟真实业务路径触发 6 参调用

业务流（修复前 vs 修复后）：
  1. 创建订单（id=9001, order_no=DRY-RUN-001）
  2. 排产 → 创建工单
  3. 工序 1-14 完成（含 QC 报工 +10）
  4. 工序 15（包装入库）报工 +5 → 触发：
     a) QC 强校验通过（10 >= 0+5）
     b) UPDATE process_records
     c) FinishedGoodsDAO.stock_in(qty=+5)
     d) UPDATE orders.status=包装入库
     e) POST 5008 warehousing
     f) log_status_change(6 参 + remark)
  5. 验证 finished_goods.quantity=5
  6. 部分发货 3 → 验证 finished_goods.quantity=2
  7. 清理测试数据
"""
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path("d:/yuan/不锈钢网带跟单3.0").resolve()
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=False)

import pymysql


def get_db():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"], port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"], charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def log(msg, ok=True):
    sym = "✅" if ok else "❌"
    print(f"{sym} {msg}")


def cleanup(conn, order_id, fg_ids):
    c = conn.cursor()
    for fg_id in fg_ids:
        c.execute("DELETE FROM finished_goods WHERE id=%s", (fg_id,))
    c.execute("DELETE FROM process_records WHERE order_id=%s", (order_id,))
    c.execute("DELETE FROM production_orders WHERE order_id=%s", (order_id,))
    c.execute("DELETE FROM orders WHERE id=%s", (order_id,))
    c.execute("DELETE FROM status_change_logs_current WHERE table_name='test_dry_run'")
    conn.commit()
    print("   cleanup done")


def main():
    print("=" * 60)
    print("桌面端 dry-run - 验证 log_status_change 6 参实际业务路径")
    print("=" * 60)

    conn = get_db()
    try:
        c = conn.cursor()
        order_id = 90010001
        # 清理历史测试数据
        c.execute("SELECT id FROM finished_goods WHERE order_id=%s", (order_id,))
        old_fg = c.fetchall()
        cleanup(conn, order_id, [r["id"] for r in old_fg])

        # ===== 1. 创建测试订单 =====
        print("\n[1] 创建测试订单")
        c.execute("""
            INSERT INTO orders (id, order_no, customer_name, quantity, product_type,
                                status, created_at, updated_at, is_deleted)
            VALUES (%s, %s, 'DRY-RUN-客户', 100, 'A型', '已排产', NOW(), NOW(), 0)
        """, (order_id, "DRY-RUN-001"))
        log("订单创建 OK")

        # ===== 2. 创建工单 =====
        print("\n[2] 排产 - 创建工单")
        c.execute("""
            INSERT INTO production_orders
            (order_id, order_no, priority, plan_start, plan_end, status, created_at, updated_at)
            VALUES (%s, %s, 5, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), '生产中', NOW(), NOW())
        """, (order_id, "DRY-RUN-001"))
        prod_id = c.lastrowid
        conn.commit()
        log(f"工单创建 OK (id={prod_id})")

        # ===== 3. QC 工序报工 +10 =====
        print("\n[3] QC 工序报工 +10 (触发 log_status_change 4 参 keyword)")
        from models.database import log_status_change
        from models.process import ProcessDAO
        from constants import ProcessStatus, ProcessNames

        # 找到 QC 工序模板
        c.execute("""SELECT id FROM process_records
                     WHERE order_id=%s AND process_name=%s
                     LIMIT 1""", (order_id, ProcessNames.QC.value))
        existing = c.fetchone()
        if existing:
            record_id = existing["id"]
            c.execute("""UPDATE process_records
                         SET qualified_qty=10, status='已完成', updated_at=NOW()
                         WHERE id=%s""", (record_id,))
        else:
            c.execute("""INSERT INTO process_records
                (order_id, production_id, process_name, process_seq, planned_qty, completed_qty,
                 qualified_qty, status, record_date, created_at, updated_at)
                VALUES (%s, %s, %s, 14, 10, 10, 10, '已完成', CURDATE(), NOW(), NOW())""",
                (order_id, prod_id, ProcessNames.QC.value))
            record_id = c.lastrowid
        conn.commit()
        # 4 参调用（keyword remark）
        log_status_change("process_records", record_id, "待开始", "已完成", operator="工人A")
        log("QC 报工 OK")

        # ===== 4. 包装入库报工 +5 (触发 6 参 + remark) =====
        print("\n[4] 包装入库报工 +5 (触发 log_status_change 6 参位置参数)")
        # 关键: process_records 初始 status=待开始, 报工后变为已完成
        # 这样 status 由"非已完成"→"已完成" 才会触发 finished_goods 联动
        c.execute("""SELECT id, status, completed_qty FROM process_records
                     WHERE order_id=%s AND process_name=%s
                     LIMIT 1""", (order_id, ProcessNames.PACKING.value))
        existing = c.fetchone()
        if existing:
            record_id = existing["id"]
            # 重置为初始状态以触发完整状态机
            c.execute("""UPDATE process_records
                         SET completed_qty=0, status='待开始', updated_at=NOW()
                         WHERE id=%s""", (record_id,))
        else:
            c.execute("""INSERT INTO process_records
                (order_id, production_id, process_name, process_seq, planned_qty, completed_qty,
                 qualified_qty, status, record_date, created_at, updated_at)
                VALUES (%s, %s, %s, 15, 5, 0, 0, '待开始', CURDATE(), NOW(), NOW())""",
                (order_id, prod_id, ProcessNames.PACKING.value))
            record_id = c.lastrowid
        conn.commit()

        # 调 ProcessDAO.update_record 模拟真实业务流
        try:
            ProcessDAO.update_record(record_id, {
                "completed_qty": 5,
                "qualified_qty": 5,
                "worker": "工人B",
                "work_hours": 1.0,
                "status": "已完成",
                "remark": "dry-run test",
            })
            log("包装入库 update_record OK (QC 强校验 + finished_goods 联动)")
        except Exception as e:
            log(f"包装入库 update_record 失败: {e}", ok=False)
            traceback.print_exc()
            return

        # 模拟 5008 同步失败 → 6 参位置参数
        try:
            log_status_change(
                "process_records", record_id, "生产中", "已完成",
                "工人B", "5008 同步失败: ConnectionError (dry-run 模拟)"
            )
            log("6 参位置参数 OK")
        except TypeError as e:
            log(f"6 参位置参数 TypeError: {e}", ok=False)
            return

        # ===== 5. 验证 finished_goods =====
        print("\n[5] 验证 finished_goods 仓库数量")
        c.execute("""SELECT id, quantity, unit, status FROM finished_goods
                     WHERE order_id=%s""", (order_id,))
        fg_rows = c.fetchall()
        if not fg_rows:
            log("finished_goods 无记录 (联动未触发)", ok=False)
        else:
            for fg in fg_rows:
                print(f"   finished_goods id={fg['id']} qty={fg['quantity']} unit={fg['unit']} status={fg['status']}")
            if fg_rows[0]["quantity"] == 5:
                log(f"finished_goods 数量=5 OK (符合预期)")
            else:
                log(f"finished_goods 数量={fg_rows[0]['quantity']} != 5", ok=False)
            fg_ids = [fg["id"] for fg in fg_rows]
        # ===== 6. 验证 status_change_logs_current 写入 remark =====
        print("\n[6] 验证 status_change_logs_current 写入 remark")
        c.execute("""SELECT table_name, old_status, new_status, operator, remark
                     FROM status_change_logs_current
                     WHERE record_id IN (
                        SELECT id FROM process_records WHERE order_id=%s
                     )
                     ORDER BY id DESC LIMIT 5""", (order_id,))
        log_rows = c.fetchall()
        if not log_rows:
            log("无 status_change_logs 记录 (可能 6 参调用未真实写入)", ok=False)
        else:
            for r in log_rows:
                rem = r.get("remark", "") or ""
                print(f"   table={r['table_name']} {r['old_status']}->{r['new_status']} "
                      f"op={r['operator']} remark='{rem[:60]}'")
            has_remark = any(r.get("remark") for r in log_rows)
            if has_remark:
                log("remark 字段写入 OK")
            else:
                log("remark 字段为空", ok=False)

        # ===== 7. 部分发货 3 =====
        print("\n[7] 部分发货 3 (验证 ship_out 减少库存)")
        from models.shipment import FinishedGoodsDAO
        if fg_rows:
            fg_id = fg_rows[0]["id"]
            try:
                FinishedGoodsDAO.ship_out(
                    order_id=order_id, qty=3, finished_goods_id=fg_id,
                    operator="工人C", remark="dry-run 部分发货"
                )
                c.execute("COMMIT")
                c.execute("SELECT quantity, status FROM finished_goods WHERE id=%s", (fg_id,))
                row = c.fetchone()
                print(f"   发货后 qty={row['quantity']} status={row['status']}")
                if float(row["quantity"]) == 2:
                    log("ship_out OK (5-3=2)")
                else:
                    log(f"ship_out 数量异常: {row['quantity']} (期望 2)", ok=False)
            except Exception as e:
                log(f"ship_out 失败: {e}", ok=False)
                traceback.print_exc()
        else:
            log("跳过 ship_out (无 finished_goods)", ok=False)

        # ===== 8. 清理 =====
        print("\n[8] 清理测试数据")
        c.execute("DELETE FROM finished_goods WHERE order_id=%s", (order_id,))
        c.execute("DELETE FROM process_records WHERE order_id=%s", (order_id,))
        c.execute("DELETE FROM production_orders WHERE order_id=%s", (order_id,))
        c.execute("DELETE FROM orders WHERE id=%s", (order_id,))
        c.execute(
            "DELETE FROM status_change_logs_current WHERE record_id IN "
            "(SELECT id FROM process_records WHERE order_id=%s)",
            (order_id,),
        )
        conn.commit()
        log("清理 OK")

        print("\n" + "=" * 60)
        print("dry-run 完成")
        print("=" * 60)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
