"""
清理端到端测试残留数据（2026-06-20 23:47 执行的 E2E 测试）
"""
import pymysql

STEEL_CFG = {'host': 'localhost', 'user': 'root', 'password': '88888888', 'database': 'steel_belt', 'charset': 'utf8mb4'}
CC_CFG = {'host': 'localhost', 'user': 'root', 'password': '88888888', 'database': 'container_center', 'charset': 'utf8mb4'}

# 1. 检查并清理 steel_belt
conn = pymysql.connect(**STEEL_CFG)
c = conn.cursor()

# 找到今天 E2E 测试新增的 process_sub_steps 记录 (created_at >= 23:40)
c.execute(
    "SELECT id, order_no, step_name, quantity, operator, batch_no, created_at "
    "FROM process_sub_steps WHERE created_at >= '2026-06-20 23:40:00' AND order_no='ORD-202604210002'")
rows = c.fetchall()
print(f'steel_belt.process_sub_steps 待清理: {len(rows)} 条')
for r in rows:
    print(f'  id={r[0]} qty={r[3]} op={r[4]} batch_no={r[5]} created_at={r[6]}')

if rows:
    c.execute(
        "DELETE FROM process_sub_steps WHERE created_at >= '2026-06-20 23:40:00' AND order_no='ORD-202604210002'")
    print(f'  已删除 {c.rowcount} 条')

# process_records 回滚 completed_qty 从 70→60
c.execute("SELECT id, completed_qty FROM process_records WHERE id=430")
row = c.fetchone()
if row:
    print(f'\nprocess_records id=430: completed_qty={row[1]} → 60 (回滚)')
    c.execute("UPDATE process_records SET completed_qty=60 WHERE id=430")
    print(f'  已更新 {c.rowcount} 条')
conn.commit()
conn.close()

# 2. 检查 container_center 是否有需要清理的
conn2 = pymysql.connect(**CC_CFG)
c2 = conn2.cursor()
c2.execute(
    "SELECT id, order_no, step_name, quantity, operator, batch_no, created_at "
    "FROM process_sub_steps WHERE order_no='ORD-202604210002' AND created_at >= '2026-06-20'")
rows2 = c2.fetchall()
print(f'\ncontainer_center.process_sub_steps 今天新增: {len(rows2)} 条（去重合并策略，无需清理）')
for r in rows2:
    print(f'  id={r[0]} qty={r[3]} op={r[4]} batch_no={r[5]} created_at={r[6]}')
conn2.close()

# 3. 验证清理结果
print('\n--- 清理后验证 ---')
conn3 = pymysql.connect(**STEEL_CFG)
c3 = conn3.cursor()
c3.execute("SELECT id, completed_qty FROM process_records WHERE id=430")
r = c3.fetchone()
print(f'process_records id=430: completed_qty={r[1]} (应为 60)')
c3.execute(
    "SELECT COUNT(*) FROM process_sub_steps WHERE created_at >= '2026-06-20 23:40:00' AND order_no='ORD-202604210002'")
cnt = c3.fetchone()[0]
print(f'steel_belt.process_sub_steps 残留: {cnt} 条 (应为 0)')
conn3.close()

print('\n✅ 清理完成')
