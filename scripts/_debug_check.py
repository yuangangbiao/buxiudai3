import sys
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
from storage.mysql_storage import MySQLStorage

s = MySQLStorage()

# 检查 process_sub_steps 中的数据
rows = s.fetch_all(
    "SELECT id, order_no, operator, created_at, status "
    "FROM process_sub_steps WHERE order_no=%s LIMIT 10",
    ('ORD-202604210002',)
)
print(f'process_sub_steps 找到 {len(rows)} 条:')
for r in rows:
    print(f'  id={r["id"]}, operator={r["operator"]}, '
          f'created_at={r["created_at"]}, status={r["status"]}')

# 直接删除
s.execute(
    "DELETE FROM process_sub_steps WHERE order_no=%s",
    ('ORD-202604210002',)
)
print(f'已删除, 验证:')
rows2 = s.fetch_all(
    "SELECT COUNT(*) as cnt FROM process_sub_steps WHERE order_no=%s",
    ('ORD-202604210002',)
)
print(f'  remaining: {rows2[0]["cnt"]}')
