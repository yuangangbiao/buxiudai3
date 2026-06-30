# -*- coding: utf-8 -*-
"""
测试数据清除脚本

执行步骤:
1. 备份测试数据到 CSV
2. 删除 process_sub_steps 中的测试数据
3. 重新计算 process_records.completed_qty
4. 清理 report_queue
5. 验证清除结果

执行方式:
  python scripts/cleanup_test_data.py

安全措施:
- 所有删除操作在事务中执行
- 删除前完整备份
- 提供 --dry-run 模式预览影响
"""
import os
import csv
import sys
import time
import json
import datetime
import pymysql

CC_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'container_center', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

STEEL_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backup')
DRY_RUN = '--dry-run' in sys.argv

# 测试操作员匹配模式（用于 WHERE 条件）
TEST_OPERATOR_CONDITIONS = [
    "operator LIKE 'stress-%%'",
    "operator LIKE '8008-stress-%%'",
    "operator LIKE '5008-stress-%%'",
    "operator LIKE '5srv-%%'",
    "operator LIKE 'dup-test-%%'",
    "operator LIKE '8008-test-%%'",
    "operator LIKE 'E2E%%'",
    "operator LIKE '4服务%%'",
    "operator LIKE '5008-100-%%'",
    "operator LIKE '跨服务%%'",
    "operator = '小明'",
    "operator = 'X-2'",
    "operator = '' OR operator IS NULL",
]


def get_test_where_clause(table_alias=''):
    prefix = f'{table_alias}.' if table_alias else ''
    return ' OR '.join([f"{prefix}{cond.replace('%%', '%')}" for cond in TEST_OPERATOR_CONDITIONS])


def log(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    print(f'[{ts}] {msg}')


def get_conn(config):
    return pymysql.connect(**config)


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_test_data():
    """备份测试数据到 CSV"""
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    log(f'{"="*60}')
    log(f'【步骤1】备份测试数据')
    log(f'{"="*60}')
    log(f'模式: {"DRY-RUN (仅预览)" if DRY_RUN else "实际执行"}')

    ensure_backup_dir()
    conn = get_conn(STEEL_CONFIG)
    try:
        with conn.cursor() as c:
            where = get_test_where_clause()
            sql = f"SELECT COUNT(*) as cnt FROM process_sub_steps WHERE {where}"
            c.execute(sql)
            total = c.fetchone()['cnt']
            log(f'  process_sub_steps 测试数据总数: {total} 条')

            if total == 0:
                log(f'  ⚠️ 无测试数据，跳过')
                return 0

            if not DRY_RUN:
                # 备份全部字段
                c.execute(f"SELECT * FROM process_sub_steps WHERE {where}")
                rows = c.fetchall()

                backup_file = os.path.join(BACKUP_DIR, f'process_sub_steps_test_data_{ts}.csv')
                if rows:
                    with open(backup_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)

                log(f'  备份完成: {backup_file}')
                log(f'  记录数: {len(rows)}')

                # 也保存一份 JSON 摘要
                summary = {
                    'backup_time': ts,
                    'table': 'process_sub_steps',
                    'total_records': len(rows),
                    'condition': TEST_OPERATOR_CONDITIONS,
                    'file': backup_file,
                }
                summary_file = os.path.join(BACKUP_DIR, f'cleanup_summary_{ts}.json')
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                log(f'  摘要保存: {summary_file}')

            return total
    finally:
        conn.close()


def delete_test_data():
    """删除测试数据"""
    log(f'')
    log(f'{"="*60}')
    log(f'【步骤2】删除测试数据')
    log(f'{"="*60}')

    if DRY_RUN:
        log(f'  DRY-RUN: 跳过实际删除')
        return 0

    conn = get_conn(STEEL_CONFIG)
    try:
        with conn.cursor() as c:
            where = get_test_where_clause()
            sql = f"DELETE FROM process_sub_steps WHERE {where}"
            log(f'  执行 SQL: {sql}')
            affected = c.execute(sql)
            conn.commit()
            log(f'  已删除: {affected} 条')
            return affected
    except Exception as e:
        conn.rollback()
        log(f'  ❌ 删除失败: {e}')
        raise
    finally:
        conn.close()


def recalculate_process_records():
    """重新计算 process_records.completed_qty"""
    log(f'')
    log(f'{"="*60}')
    log(f'【步骤3】重新计算 process_records.completed_qty')
    log(f'{"="*60}')

    conn = get_conn(STEEL_CONFIG)
    try:
        with conn.cursor() as c:
            not_test = " AND pss.operator NOT LIKE 'stress-%' AND pss.operator NOT LIKE '8008-stress-%'" \
                       " AND pss.operator NOT LIKE '5008-stress-%' AND pss.operator NOT LIKE '5srv-%'" \
                       " AND pss.operator NOT LIKE 'dup-test-%' AND pss.operator NOT LIKE '8008-test-%'" \
                       " AND pss.operator NOT LIKE 'E2E%' AND pss.operator NOT LIKE '4服务%'" \
                       " AND pss.operator NOT LIKE '5008-100-%' AND pss.operator NOT LIKE '跨服务%'" \
                       " AND pss.operator != '小明' AND pss.operator != 'X-2'" \
                       " AND pss.operator != '' AND pss.operator IS NOT NULL"

            # 找出所有 process_records 中有记录但数据可能被测试数据影响的工序
            c.execute(f"""
                SELECT pr.id, pr.order_no, pr.process_name, pr.completed_qty,
                       COALESCE((
                           SELECT SUM(pss.quantity)
                           FROM process_sub_steps pss
                           WHERE pss.order_no = pr.order_no
                             AND pss.step_name = pr.process_name
                             {not_test}
                       ), 0) as actual_qty
                FROM process_records pr
                ORDER BY pr.order_no, pr.process_name
            """)
            records = c.fetchall()
            log(f'  process_records 总记录数: {len(records)}')

            if DRY_RUN:
                changed = [r for r in records if r['completed_qty'] != r['actual_qty']]
                for r in changed:
                    log(f'    将更新: {r["order_no"]}/{r["process_name"]}: '
                        f'{r["completed_qty"]} → {r["actual_qty"]}')
                log(f'  需更新: {len(changed)} 条')
                return len(changed)

            updated = 0
            for r in records:
                if r['completed_qty'] != r['actual_qty']:
                    c.execute("""
                        UPDATE process_records
                        SET completed_qty = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (int(r['actual_qty']), r['id']))
                    updated += 1

            conn.commit()
            log(f'  已更新: {updated} 条')

            # 显示关键的修正
            for r in records:
                new_qty = int(r['actual_qty'])
                if r['completed_qty'] != new_qty:
                    log(f'    ✅ {r["order_no"]}/{r["process_name"]}: '
                        f'{r["completed_qty"]} → {new_qty}')

            return updated
    finally:
        conn.close()


def cleanup_report_queue():
    """清理 report_queue 中的测试相关记录"""
    log(f'')
    log(f'{"="*60}')
    log(f'【步骤4】清理 report_queue')
    log(f'{"="*60}')

    conn = get_conn(CC_CONFIG)
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, order_no, step_name, status, last_error, enqueued_at
                FROM report_queue
                ORDER BY id
            """)
            rows = c.fetchall()
            log(f'  report_queue 总记录数: {len(rows)}')

            if DRY_RUN:
                log(f'  DRY-RUN: 报告队列受影响记录:')
                for r in rows:
                    log(f'    #{r["id"]} {r["order_no"]}/{r["step_name"]} [{r["status"]}]')
                return 0

            c.execute("DELETE FROM report_queue WHERE status = 'failed'")
            failed = c.rowcount
            log(f'  已删除失败记录: {failed} 条')
            conn.commit()
            return failed
    finally:
        conn.close()


def verify_results(before_count):
    """验证清除结果"""
    log(f'')
    log(f'{"="*60}')
    log(f'【步骤5】验证清除结果')
    log(f'{"="*60}')

    conn_s = get_conn(STEEL_CONFIG)
    conn_c = get_conn(CC_CONFIG)
    try:
        with conn_s.cursor() as c:
            # process_sub_steps 验证
            where = get_test_where_clause()
            c.execute(f"SELECT COUNT(*) as cnt FROM process_sub_steps WHERE {where}")
            remaining_test = c.fetchone()['cnt']
            log(f'  剩余测试数据: {remaining_test} 条 (应=0，原={before_count})')

            c.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
            total = c.fetchone()['cnt']
            log(f'  process_sub_steps 总记录数: {total} 条')

            # ORD-20260416-0001/入库 验证
            c.execute("""
                SELECT SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE order_no = 'ORD-20260416-0001' AND step_name = '入库'
            """)
            in_qty = c.fetchone()['total_qty'] or 0
            log(f'  ORD-20260416-0001/入库 剩余报工量: {in_qty} 件')

            # process_records 验证
            c.execute("""
                SELECT order_no, process_name, completed_qty, status
                FROM process_records
                WHERE order_no = 'ORD-20260416-0001' AND process_name = '入库'
            """)
            pr = c.fetchone()
            if pr:
                log(f'  process_records: {pr["order_no"]}/{pr["process_name"]}'
                    f' completed_qty={pr["completed_qty"]} status={pr["status"]}')
                expected = int(in_qty)
                status = '✅' if pr['completed_qty'] == expected else '⚠️'
                log(f'  {status} completed_qty={pr["completed_qty"]}, 预期={expected}, '
                    f'差值={pr["completed_qty"] - expected}')

        with conn_c.cursor() as c:
            c.execute("SELECT status, COUNT(*) as cnt FROM report_queue GROUP BY status")
            rows = c.fetchall()
            log(f'  report_queue 分布:')
            for r in rows:
                log(f'    {r["status"]}: {r["cnt"]}')

        return remaining_test == 0

    finally:
        conn_s.close()
        conn_c.close()


def main():
    print(f'')
    print(f'{"#"*60}')
    print(f'# 测试数据清除脚本')
    print(f'# 时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'# 模式: {"DRY-RUN" if DRY_RUN else "实际执行"}')
    print(f'{"#"*60}')
    print(f'')

    if DRY_RUN:
        log(f'⚠️  注意: 这是 DRY-RUN 模式，不会实际修改数据')
        log(f'')

    # 步骤1: 备份
    before_count = backup_test_data()

    # 步骤2: 删除
    delete_test_data()

    # 步骤3: 重新计算
    recalculate_process_records()

    # 步骤4: 清理队列
    cleanup_report_queue()

    # 步骤5: 验证
    verify_results(before_count)

    log(f'')
    log(f'{"="*60}')
    if DRY_RUN:
        log(f'DRY-RUN 完成。移除 --dry-run 参数执行实际清除。')
    else:
        log(f'清除完成！')
    log(f'备份目录: {BACKUP_DIR}')
    log(f'{"="*60}')

    # 只在 dry-run 时输出 SQL 预览
    if DRY_RUN:
        log(f'')
        log(f'将要删除的 SQL WHERE 条件:')
        log(f'  WHERE {get_test_where_clause()}')
        log(f'')
        log(f'确认无误后执行:')
        log(f'  python scripts/cleanup_test_data.py')


if __name__ == '__main__':
    main()
