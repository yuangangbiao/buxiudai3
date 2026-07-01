import socket, os

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'production_dispatch')

sock = socket.socket()
sock.settimeout(10)
r = sock.connect_ex((MYSQL_HOST, MYSQL_PORT))
sock.close()
print(f"socket: {r}")
if r == 0:
    try:
        import pymysql
        conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
            password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
            charset='utf8mb4', connect_timeout=15)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM schedule_queue")
        print(f"total: {c.fetchone()[0]}")
        c.execute("SELECT id, order_no, status, retry_count, last_error, created_at FROM schedule_queue ORDER BY id DESC LIMIT 10")
        for r in c.fetchall():
            print(f"id={r[0]} wo={r[1]} status={r[2]} retry={r[3]} err={str(r[4])[:50]} created={r[5]}")
        c.execute("SELECT id, order_no, status FROM schedule_queue WHERE order_no LIKE '%202605008%'")
        for r in c.fetchall():
            print(f"008: id={r[0]} wo={r[1]} status={r[2]}")
        conn.close()
    except Exception as e:
        print(f"mysql error: {e}")
else:
    print(f"port not reachable, code={r}")
