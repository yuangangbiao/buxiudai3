"""
T1: process_sub_steps 合并去重迁移
- 库：container_center
- 日期：2026-06-09
- 来源：Phase 2 决策 D3 (SQL 一次性合并)
- 行为：
    1. 备份原表 → process_sub_steps_backup_20260609
    2. operator 字段从 VARCHAR(50) 扩到 VARCHAR(255)
    3. 按 (order_no, step_name) 分组：保留每组最早行作 anchor，
       operator 拼接去重（逗号分隔），process_code 取组内非空值
    4. 删除非 anchor 行
- 回滚：
    DROP TABLE process_sub_steps;
    RENAME TABLE process_sub_steps_backup_20260609 TO process_sub_steps;
- 验收：跑完后 (order_no, step_name) 无重复，operator 字段含所有原操作员
"""
import os
import sys
import pymysql
from datetime import datetime


def get_conn():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database="container_center",
        charset="utf8mb4",
        autocommit=False,
    )


def run():
    conn = get_conn()
    cur = conn.cursor()

    try:
        print("=" * 70)
        print("T1: process_sub_steps 合并去重迁移")
        print("=" * 70)
        print(f"开始时间: {datetime.now().isoformat()}")

        # 1. 备份
        cur.execute("SHOW TABLES LIKE 'process_sub_steps_backup_20260609'")
        if cur.fetchone():
            print("[1] 备份表已存在, 跳过备份步骤")
        else:
            cur.execute("CREATE TABLE process_sub_steps_backup_20260609 AS SELECT * FROM process_sub_steps")
            print("[1] 已创建备份表 process_sub_steps_backup_20260609")

        cur.execute("SELECT COUNT(*) FROM process_sub_steps_backup_20260609")
        bk_rows = cur.fetchone()[0]
        print(f"     备份行数: {bk_rows}")

        # 2. 扩宽 operator
        cur.execute("""
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA='container_center' AND TABLE_NAME='process_sub_steps'
              AND COLUMN_NAME='operator'
        """)
        col_type = cur.fetchone()[0]
        print(f"[2] operator 当前类型: {col_type}")
        if "varchar(50)" in col_type.lower():
            cur.execute("ALTER TABLE process_sub_steps MODIFY COLUMN operator VARCHAR(255) DEFAULT ''")
            print("     已扩宽到 VARCHAR(255)")
        else:
            print("     已是 VARCHAR(255) 或更宽, 跳过")

        # 3. 合并: 用临时表计算 anchor 和 merged operator
        cur.execute("DROP TEMPORARY TABLE IF EXISTS _merge_plan")
        cur.execute("""
            CREATE TEMPORARY TABLE _merge_plan AS
            SELECT
              order_no,
              step_name,
              SUBSTRING_INDEX(
                GROUP_CONCAT(id ORDER BY
                  CASE WHEN process_code IS NOT NULL AND process_code != '' THEN 0 ELSE 1 END,
                  created_at ASC, id ASC
                SEPARATOR ','),
              ',', 1
              ) AS anchor_id,
              SUBSTRING_INDEX(
                GROUP_CONCAT(
                  CASE WHEN process_code IS NOT NULL AND process_code != '' THEN process_code END
                  ORDER BY
                  CASE WHEN process_code IS NOT NULL AND process_code != '' THEN 0 ELSE 1 END,
                  created_at ASC, id ASC
                SEPARATOR ','),
              ',', 1
              ) AS canonical_process_code,
              GROUP_CONCAT(DISTINCT
                CASE WHEN operator IS NOT NULL AND TRIM(operator) != '' THEN TRIM(operator) END
                ORDER BY
                CASE WHEN operator IS NOT NULL AND TRIM(operator) != '' THEN TRIM(operator) END
                SEPARATOR ','
              ) AS merged_operator
            FROM process_sub_steps
            GROUP BY order_no, step_name
        """)
        print("[3] 已创建临时表 _merge_plan")

        # 4. 统计合并前 vs 合并后
        cur.execute("SELECT COUNT(*) FROM _merge_plan")
        plan_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM process_sub_steps")
        before_cnt = cur.fetchone()[0]
        print(f"     合并前: {before_cnt} 行, 预计合并后: {plan_cnt} 行")
        print(f"     预计删除: {before_cnt - plan_cnt} 行")

        # 5. 更新 anchor 行的 operator 和 process_code
        cur.execute("""
            UPDATE process_sub_steps pss
            JOIN _merge_plan mp ON pss.id = mp.anchor_id
            SET
              pss.operator = mp.merged_operator,
              pss.process_code = CASE
                WHEN mp.canonical_process_code IS NOT NULL AND mp.canonical_process_code != ''
                THEN mp.canonical_process_code
                ELSE pss.process_code
              END
        """)
        updated = cur.rowcount
        print(f"[5] 更新 anchor 行: {updated}")

        # 6. 删除非 anchor 行
        cur.execute("""
            DELETE pss
            FROM process_sub_steps pss
            JOIN _merge_plan mp
              ON pss.order_no = mp.order_no AND pss.step_name = mp.step_name
            WHERE pss.id != mp.anchor_id
        """)
        deleted = cur.rowcount
        print(f"[6] 删除非 anchor 行: {deleted}")

        # 7. 验证
        cur.execute("SELECT COUNT(*) FROM process_sub_steps")
        after_cnt = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM (
              SELECT order_no, step_name FROM process_sub_steps
              GROUP BY order_no, step_name HAVING COUNT(*) > 1
            ) t
        """)
        dup_after = cur.fetchone()[0]
        print(f"\n[7] 验证:")
        print(f"     迁移后行数: {after_cnt} (期望: {plan_cnt})")
        print(f"     重复组数: {dup_after} (期望: 0)")

        if after_cnt != plan_cnt:
            raise Exception(f"行数不符! 期望 {plan_cnt}, 实际 {after_cnt}")
        if dup_after != 0:
            raise Exception(f"仍有重复组! {dup_after}")

        # 8. 抽样验证: ORD-202604210002 / 原材料准备
        cur.execute("""
            SELECT id, order_no, step_name, process_code, operator, quantity, qualified_qty, status
            FROM process_sub_steps
            WHERE order_no='ORD-202604210002' AND step_name='原材料准备'
        """)
        print(f"\n[8] 抽样验证 - ORD-202604210002 / 原材料准备:")
        for row in cur.fetchall():
            print(f"     {row}")

        # 9. 提交
        conn.commit()
        print(f"\n[9] 已提交, 完成时间: {datetime.now().isoformat()}")
        print("=" * 70)
        print("✓ T1 迁移成功")
        print("=" * 70)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ T1 失败, 已回滚: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
