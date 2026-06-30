import pymysql
import sys

def migrate():
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root',
                            password='88888888', database='container_center', charset='utf8mb4')
    cur = conn.cursor()

    # 1. 先看哪些需要重算
    cur.execute("""
        SELECT dp.id, dp.order_no, dp.related_process, dp.completed_qty AS old_qty,
               COALESCE(SUM(ss.quantity), 0) AS new_qty
        FROM data_packages dp
        LEFT JOIN process_sub_steps ss
            ON ss.order_no = dp.order_no
            AND ss.step_name = dp.related_process
        WHERE dp.order_no IS NOT NULL AND dp.order_no != ''
          AND dp.related_process IS NOT NULL AND dp.related_process != ''
        GROUP BY dp.id, dp.order_no, dp.related_process, dp.completed_qty
        ORDER BY ABS(dp.completed_qty - COALESCE(SUM(ss.quantity), 0)) DESC
    """)
    rows = cur.fetchall()
    print(f'=== 需要重算的记录 ({len(rows)} 条) ===')
    diff_count = 0
    for r in rows:
        diff = r[3] != r[4]
        if diff:
            diff_count += 1
            mark = '  \u26a0\ufe0f 需要更新!'
        else:
            mark = '  \u2713 无需改动'
        print(f'  id={r[0]}, order={r[1]}, process={r[2]}, 当前={r[3]}, 应为={r[4]}{mark}')

    print(f'\n共 {len(rows)} 条，其中 {diff_count} 条需要更新')

    if diff_count == 0:
        print('[INFO] 无需更新，退出')
        conn.close()
        return True

    # 2. 执行 UPDATE（MySQL 兼容写法）
    update_sql = """
        UPDATE data_packages dp
        INNER JOIN (
            SELECT order_no, step_name,
                   CAST(SUM(quantity) AS SIGNED) AS total_qty
            FROM process_sub_steps
            WHERE order_no IS NOT NULL AND order_no != ''
              AND step_name IS NOT NULL AND step_name != ''
            GROUP BY order_no, step_name
        ) ss_sum
        ON ss_sum.order_no = dp.order_no AND ss_sum.step_name = dp.related_process
        SET dp.completed_qty = ss_sum.total_qty
        WHERE dp.order_no IS NOT NULL AND dp.order_no != ''
          AND dp.related_process IS NOT NULL AND dp.related_process != ''
    """
    cur.execute(update_sql)
    affected = cur.rowcount
    conn.commit()
    print(f'\n[OK] 更新了 {affected} 条')

    # 3. 验证
    cur.execute("SELECT COUNT(*) FROM data_packages WHERE completed_qty > 0")
    total_positive = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM data_packages dp
        LEFT JOIN (
            SELECT order_no, step_name, CAST(SUM(quantity) AS SIGNED) AS total_qty
            FROM process_sub_steps
            WHERE order_no IS NOT NULL AND order_no != ''
              AND step_name IS NOT NULL AND step_name != ''
            GROUP BY order_no, step_name
        ) ss_sum
        ON ss_sum.order_no = dp.order_no AND ss_sum.step_name = dp.related_process
        WHERE dp.order_no IS NOT NULL AND dp.order_no != ''
          AND dp.related_process IS NOT NULL AND dp.related_process != ''
          AND dp.completed_qty != COALESCE(ss_sum.total_qty, 0)
    """)
    mismatches = cur.fetchone()[0]
    print(f'[INFO] completed_qty>0 共 {total_positive} 条')
    print(f'[INFO] 重算后不一致: {mismatches} 条')

    conn.close()
    return mismatches == 0

if __name__ == '__main__':
    ok = migrate()
    sys.exit(0 if ok else 1)
