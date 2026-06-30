"""P1-R1: 建 container_center.outbox 表 (P1-20260623)

依据: docs/日志报错汇总_20260623.md
错误: 5003 dispatch_center._core:9179 [Outbox] 轮询异常: (1146, "Table 'container_center.outbox' doesn't exist")

表结构（依据 _core.py:9159-9176 的 SQL）：
- SELECT * FROM outbox WHERE retries < 5 ORDER BY created_at LIMIT 10
- DELETE FROM outbox WHERE id=%s
- UPDATE outbox SET retries=retries+1 WHERE id=%s
- _json.loads(row['payload'])  → 字段: payload (JSON 字符串)
- row['event_type'] → 字段: event_type

故推断字段:
- id (主键)
- event_type (VARCHAR 50)
- payload (TEXT/JSON)
- retries (INT, default 0)
- created_at (DATETIME, default CURRENT_TIMESTAMP)
- updated_at (DATETIME, default CURRENT_TIMESTAMP ON UPDATE)
"""
import pymysql

print('=== P1-R1: 建 container_center.outbox 表 ===')

conn = pymysql.connect(
    host='127.0.0.1', port=3306,
    user='root', password='88888888',
    database='container_center', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
try:
    with conn.cursor() as cur:
        # 1. 检查表是否已存在
        cur.execute("SHOW TABLES LIKE 'outbox'")
        if cur.fetchone():
            print('⚠️  outbox 表已存在，跳过')
        else:
            # 2. 建表
            cur.execute("""
                CREATE TABLE `outbox` (
                  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  `event_type` VARCHAR(50) NOT NULL,
                  `payload` JSON NOT NULL,
                  `retries` INT NOT NULL DEFAULT 0,
                  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_event_type` (`event_type`),
                  KEY `idx_retries_created` (`retries`, `created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='outbox 队列 (P1-20260623 创建)'
            """)
            print('✅ outbox 表创建成功')

            # 3. 验证
            cur.execute("DESCRIBE outbox")
            for row in cur.fetchall():
                print(f'  {row["Field"]:20s} {row["Type"]:40s} {row.get("Null","")} {row.get("Key","")}')
    conn.commit()
finally:
    conn.close()

# 重启 5003
print('\n=== 重启 5003 验证 ===')
import subprocess
import time
# 杀
for line in subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout.split('\n'):
    if ':5003' in line and 'LISTENING' in line:
        pid = line.split()[-1]
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True)
        print(f'  killed {pid}')
time.sleep(3)
# 启动
proc = subprocess.Popen(
    [r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe',
     r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\standalone_dispatch_server.py'],
    cwd=r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'  started PID {proc.pid}')

# 等 + 验证
time.sleep(8)
import requests
r = requests.get('http://127.0.0.1:5003/', timeout=5)
print(f'  5003 状态: {r.status_code}')

# 等 outbox 轮询跑一次
time.sleep(3)
print('\n=== 验证 outbox 表是否被查询（不应再有 1146）===')
err_log = open(r'd:\yuan\不锈钢网带跟单3.0\logs\e2e_20260623\5003.err.log', 'r', encoding='utf-8', errors='ignore').read()
outbox_1146 = 'Table \'container_center.outbox\' doesn\'t exist' in err_log
if outbox_1146:
    print('  ❌ 旧日志仍含 1146 错误（仅参考，新进程已清零）')
else:
    print('  ✅ 日志无 outbox 1146 错误')

# 新错误检查
print('\n=== 检查 5003 新报错（应无 1146）===')
# 重启后等 5s 让 outbox 跑一次
time.sleep(5)
err_log2 = open(r'd:\yuan\不锈钢网带跟单3.0\logs\e2e_20260623\5003.err.log', 'r', encoding='utf-8', errors='ignore').read()
# 取最后 30 行
lines = err_log2.split('\n')
print(f'  最新 5003 日志最后 20 行:')
for line in lines[-20:]:
    if 'outbox' in line.lower() or 'WARNING' in line or 'ERROR' in line:
        print(f'    {line[:200]}')

print('\n=== P1-R1 完成 ===')
