"""
诊断脚本：检查排产/任务列表加载慢的原因（简化版）
"""
import os
import sys
import time

# 直接用 pymysql 连接
try:
    import pymysql
    print("✅ pymysql 可用")
except ImportError:
    print("❌ pymysql 不可用")
    sys.exit(1)

# 读取环境变量
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    print(f"✅ 加载 .env: {env_file}")

# 数据库配置
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DB = os.environ.get('CONTAINER_MYSQL_DB', 'container_center')

print(f"\n📊 数据库: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")

def query(sql, params=None):
    """执行查询"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4'
    )
    try:
        c = conn.cursor()
        c.execute(sql, params)
        return c.fetchall()
    finally:
        conn.close()

print("\n" + "="*60)
print("📊 表数据量统计")
print("="*60)

# 1. data_packages 表
try:
    result = query("SELECT COUNT(*) FROM data_packages")
    pkg_count = result[0][0]
    print(f"\n📦 data_packages 表: {pkg_count} 条")
except Exception as e:
    print(f"\n❌ data_packages 查询失败: {e}")

# 2. process_records 表
try:
    result = query("SELECT COUNT(*) FROM process_records")
    rec_count = result[0][0]
    print(f"📋 process_records 表: {rec_count} 条")
except Exception as e:
    print(f"❌ process_records 查询失败: {e}")

# 3. 按 status 分布
print(f"\n📈 data_packages 按状态分布 (Top 5):")
try:
    result = query("""
        SELECT COALESCE(status, '(empty)'), COUNT(*) as cnt
        FROM data_packages
        GROUP BY status
        ORDER BY cnt DESC
        LIMIT 5
    """)
    for row in result:
        print(f"   {row[0]}: {row[1]} 条")
except Exception as e:
    print(f"❌ 查询失败: {e}")

# 4. 按 data_type 分布
print(f"\n📈 data_packages 按类型分布 (Top 5):")
try:
    result = query("""
        SELECT COALESCE(data_type, '(empty)'), COUNT(*) as cnt
        FROM data_packages
        GROUP BY data_type
        ORDER BY cnt DESC
        LIMIT 5
    """)
    for row in result:
        print(f"   {row[0]}: {row[1]} 条")
except Exception as e:
    print(f"❌ 查询失败: {e}")

# 5. 检查索引
print(f"\n🔍 索引检查:")
try:
    result = query("SHOW INDEX FROM data_packages")
    indexes = {}
    for row in result:
        Key_name = row[2]
        Column_name = row[4]
        if Key_name not in indexes:
            indexes[Key_name] = []
        indexes[Key_name].append(Column_name)

    for name, cols in indexes.items():
        print(f"   {name}: ({', '.join(cols)})")
except Exception as e:
    print(f"❌ 索引查询失败: {e}")

# 6. 查询性能测试
print(f"\n⏱️ 查询性能测试:")
try:
    start = time.time()
    result = query("SELECT * FROM data_packages ORDER BY created_at DESC LIMIT 100")
    elapsed = (time.time() - start) * 1000
    print(f"   SELECT 100条: {elapsed:.1f}ms")
except Exception as e:
    print(f"❌ 查询失败: {e}")

try:
    start = time.time()
    result = query("SELECT * FROM data_packages ORDER BY created_at DESC LIMIT 1000")
    elapsed = (time.time() - start) * 1000
    print(f"   SELECT 1000条: {elapsed:.1f}ms")
except Exception as e:
    print(f"❌ 查询失败: {e}")

try:
    start = time.time()
    result = query("SELECT * FROM data_packages WHERE related_order='ORD-202506120001' LIMIT 100")
    elapsed = (time.time() - start) * 1000
    print(f"   WHERE order_no 100条: {elapsed:.1f}ms")
except Exception as e:
    print(f"❌ 查询失败: {e}")

print("\n" + "="*60)
print("📝 诊断结论")
print("="*60)
print("""
根据诊断结果判断:

1. data_packages > 10000 条:
   → 数据量大，考虑分页

2. 查询 1000 条 > 500ms:
   → 数据库慢，需要索引优化

3. WHERE order_no 查询慢:
   → 缺少索引或索引失效

4. 查看日志中是否有 "回退到HTTP成功":
   → 确认是否触发了 HTTP 回退
""")
