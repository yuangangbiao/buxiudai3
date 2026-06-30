"""P1-R2: 建 container_center.report_definition + report_output + report_schedule 表 (P1-20260623)

依据: docs/日志报错汇总_20260623.md
错误: 5008 [App] 统计引擎初始化失败: (1146, "Table 'container_center.report_definition' doesn't exist")

字段推断依据 stats_engine.py 写入字段:
- id (主键, 'builtin_*' 字符串)
- name, category, description
- sql_template (TEXT)
- params_config (TEXT, JSON)
- chart_config (TEXT, JSON)
- column_config (TEXT, JSON)
- created_at, updated_at
"""
import pymysql
import json

print('=== P1-R2: 建 3 个 reports 相关表 ===')

conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='88888888',
    database='container_center', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
try:
    with conn.cursor() as cur:
        # 1. report_definition
        cur.execute("SHOW TABLES LIKE 'report_definition'")
        if cur.fetchone():
            print('  ⚠️  report_definition 已存在')
        else:
            cur.execute("""
                CREATE TABLE `report_definition` (
                  `id` VARCHAR(100) NOT NULL,
                  `name` VARCHAR(200) NOT NULL,
                  `category` VARCHAR(50) NOT NULL,
                  `description` TEXT,
                  `sql_template` TEXT,
                  `params_config` TEXT,
                  `chart_config` TEXT,
                  `column_config` TEXT,
                  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_category` (`category`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表定义 (P1-20260623 创建)'
            """)
            print('  ✅ report_definition 创建成功')

        # 2. report_schedule (排程)
        cur.execute("SHOW TABLES LIKE 'report_schedule'")
        if cur.fetchone():
            print('  ⚠️  report_schedule 已存在')
        else:
            cur.execute("""
                CREATE TABLE `report_schedule` (
                  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  `report_id` VARCHAR(100) NOT NULL,
                  `name` VARCHAR(200),
                  `cron` VARCHAR(50),
                  `params` TEXT,
                  `format` VARCHAR(20) DEFAULT 'xlsx',
                  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
                  `last_run_at` DATETIME,
                  `next_run_at` DATETIME,
                  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_report_id` (`report_id`),
                  KEY `idx_enabled` (`enabled`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表排程 (P1-20260623 创建)'
            """)
            print('  ✅ report_schedule 创建成功')

        # 3. report_output (导出结果)
        cur.execute("SHOW TABLES LIKE 'report_output'")
        if cur.fetchone():
            print('  ⚠️  report_output 已存在')
        else:
            cur.execute("""
                CREATE TABLE `report_output` (
                  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  `report_id` VARCHAR(100) NOT NULL,
                  `report_name` VARCHAR(200),
                  `file_path` VARCHAR(500),
                  `format` VARCHAR(20) DEFAULT 'xlsx',
                  `params` TEXT,
                  `row_count` INT DEFAULT 0,
                  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_report_id` (`report_id`),
                  KEY `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表输出 (P1-20260623 创建)'
            """)
            print('  ✅ report_output 创建成功')

        # 4. 报告内容（看 stats_engine 是否能 list）
        print('\n=== 验证 stats_engine 接口 ===')
        cur.execute('SELECT COUNT(*) AS cnt FROM report_definition')
        print(f'  report_definition 行数: {cur.fetchone()["cnt"]}')

    conn.commit()
finally:
    conn.close()

# 重启 5008
print('\n=== 重启 5008 ===')
import subprocess
import time
for line in subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout.split('\n'):
    if ':5008' in line and 'LISTENING' in line:
        pid = line.split()[-1]
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True)
        print(f'killed {pid}')
time.sleep(3)
proc = subprocess.Popen(
    [r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe',
     r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'],
    cwd=r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'5008 PID {proc.pid}')
time.sleep(8)
import requests
r = requests.get('http://127.0.0.1:5008/api/health', timeout=5)
print(f'5008 health: {r.status_code}')

# 调 reports 接口
r2 = requests.get('http://127.0.0.1:5008/api/reports/definitions', timeout=5)
print(f'/api/reports/definitions: {r2.status_code} {r2.text[:200]}')

print('\n=== P1-R2 完成 ===')
