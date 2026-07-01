import socket, sys, os

out = []

def log(msg):
    out.append(msg)
    print(msg, flush=True)

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'production_dispatch')

log("=== 诊断 MySQL 和队列 ===")

# 1. 网络连通性
log(f"\n[1] 检查 {MYSQL_HOST}:{MYSQL_PORT} 是否可达")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
result = sock.connect_ex((MYSQL_HOST, MYSQL_PORT))
sock.close()
log(f"  结果: {'可达' if result == 0 else '不可达 (code=' + str(result) + ')'}")

# 2. MySQL 查询
log("\n[2] 检查 schedule_queue")
try:
    import pymysql
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        connect_timeout=10
    )
    c = conn.cursor()
    c.execute("SHOW TABLES LIKE 'schedule_queue'")
    tables = c.fetchall()
    log(f"  schedule_queue 表: {'存在' if tables else '不存在'}")
    if tables:
        c.execute("SELECT COUNT(*) FROM schedule_queue")
        log(f"  总记录: {c.fetchone()[0]}")
        c.execute("""
            SELECT id, order_no, order_no, status, retry_count,
                   error_message, created_at, published_at
            FROM schedule_queue ORDER BY created_at DESC LIMIT 20
        """)
        for r in c.fetchall():
            log(f"  wo={r[1]} order={r[2]} status={r[3]} retry={r[4]} error={r[5]} created={r[6]} published={r[7]}")
    conn.close()
except Exception as e:
    log(f"  失败: {e}")

# 3. 检查 container_center 日志 (最近)
log("\n[3] container_center API 日志 (如果存在)")
try:
    log_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\logs'
    import os
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if 'container' in f.lower() or 'api' in f.lower()]
        log(f"  日志文件: {log_files[:5]}")
except Exception as e:
    log(f"  检查容器日志目录失败: {e}")

with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\mysql_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
log("\n结果已保存到 mysql_result.txt")
