# -*- coding: utf-8 -*-
"""
测试数据生成脚本：自定义工序功能测试

创建测试数据：
1. 在某个工单中添加自定义工序 P03-B, P03-C
2. 测试删除后编号回收
3. 测试插入后编号重用
"""
import sys
import os
import pymysql

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "88888888"),
    "database": os.getenv("MYSQL_DATABASE", "steel_belt"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def find_test_production():
    """找一个有多个工序的工单用于测试"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # 找一个有至少 5 个基准工序的生产工单
        cursor.execute("""
            SELECT p.id, p.order_id, o.order_no, COUNT(pr.id) as proc_count
            FROM production_orders p
            JOIN orders o ON p.order_id = o.id
            JOIN process_records pr ON pr.production_id = p.id
            WHERE pr.is_deleted_code = 0
            GROUP BY p.id
            HAVING proc_count >= 5
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    finally:
        conn.close()


def add_custom_process(production_id, order_id, order_no, process_name, process_code, worker="测试员"):
    """添加自定义工序"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 获取当前最大 process_seq
        cursor.execute("""
            SELECT COALESCE(MAX(process_seq), 0) + 1 AS next_seq
            FROM process_records WHERE production_id=%s
        """, (production_id,))
        next_seq = cursor.fetchone()['next_seq']

        cursor.execute("""
            INSERT INTO process_records
            (production_id, order_id, order_no, process_name, process_code, process_seq, worker, unit,
             planned_qty, status, is_deleted_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, '件', 100, '待开始', 0)
        """, (production_id, order_id, order_no, process_name, process_code, next_seq, worker))

        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id
    finally:
        conn.close()


def soft_delete_process(process_id):
    """软删除工序"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE process_records SET is_deleted_code=1
            WHERE id=%s
        """, (process_id,))
        conn.commit()
        cursor.close()
    finally:
        conn.close()


def show_processes(production_id, title="当前工序列表"):
    """显示工序列表（按 process_seq 排序）"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, process_seq, process_code, process_name, worker, is_deleted_code
            FROM process_records
            WHERE production_id=%s
            ORDER BY process_seq ASC
        """, (production_id,))
        rows = cursor.fetchall()
        cursor.close()

        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
        print(f"{'ID':<6} {'Seq':<4} {'Code':<10} {'Name':<20} {'Worker':<10} {'Deleted'}")
        print(f"{'-'*60}")
        for r in rows:
            del_mark = "✓" if r['is_deleted_code'] else ""
            print(f"{r['id']:<6} {r['process_seq']:<4} {r['process_code'] or '-':<10} "
                  f"{r['process_name']:<20} {r['worker'] or '-':<10} {del_mark}")
    finally:
        conn.close()


def run_test():
    """执行测试"""
    print("=" * 60)
    print("自定义工序功能测试")
    print("=" * 60)

    # 1. 找一个测试工单
    print("\n[1] 查找测试工单...")
    test_prod = find_test_production()
    if not test_prod:
        print("❌ 未找到合适的测试工单（需要至少5个基准工序）")
        return False

    production_id = test_prod['id']
    order_id = test_prod['order_id']
    order_no = test_prod['order_no']
    print(f"✅ 找到测试工单: {order_no} (production_id={production_id}, order_id={order_id})")

    # 2. 显示当前工序
    show_processes(production_id, "测试前 - 当前工序")

    # 3. 添加自定义工序 P03-B
    print("\n[2] 添加自定义工序 P03-B...")
    id_b = add_custom_process(production_id, order_id, order_no, "表面处理-精加工", "P03-B", "张三")
    print(f"✅ P03-B 添加成功 (id={id_b})")

    # 4. 添加自定义工序 P03-C
    print("\n[3] 添加自定义工序 P03-C...")
    id_c = add_custom_process(production_id, order_id, order_no, "表面处理-打磨", "P03-C", "李四")
    print(f"✅ P03-C 添加成功 (id={id_c})")

    # 5. 显示添加后工序
    show_processes(production_id, "添加 P03-B, P03-C 后")

    # 6. 软删除 P03-B
    print("\n[4] 软删除 P03-B...")
    soft_delete_process(id_b)
    print(f"✅ P03-B 已软删除 (id={id_b}, is_deleted_code=1)")

    # 7. 显示删除后工序
    show_processes(production_id, "删除 P03-B 后（is_deleted_code=1）")

    # 8. 总结
    print("\n" + "=" * 60)
    print("测试数据创建完成！")
    print("=" * 60)
    print(f"""
验证方式：
1. 在桌面端打开订单 {order_no}
2. 查看工序列表，应显示 P03-B, P03-C 为蓝色高亮
3. P03-B 已软删除（is_deleted_code=1），但仍显示在列表中
4. 下次在 P03 之后插入新工序时，应重用 P03-B 编号

清理测试数据：
DELETE FROM process_records WHERE id IN ({id_b}, {id_c});
    """)

    return True


if __name__ == "__main__":
    try:
        success = run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
