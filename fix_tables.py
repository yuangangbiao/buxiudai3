import pymysql, sqlite3, os

os.chdir(r'D:\yuan\不锈钢网带跟单3.0')

c = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888',
                     database='container_center', charset='utf8mb4', autocommit=True)
cur = c.cursor()

# 1. 重建 data_packages
cur.execute('DROP TABLE IF EXISTS data_packages')
cur.execute('''CREATE TABLE data_packages (
    id VARCHAR(255) PRIMARY KEY, data_type VARCHAR(100), title VARCHAR(500),
    content LONGTEXT, source VARCHAR(100), priority VARCHAR(50), status VARCHAR(50),
    created_at VARCHAR(50), distributed_at VARCHAR(50), completed_at VARCHAR(50),
    target_operator VARCHAR(200), target_device VARCHAR(200), tags LONGTEXT,
    related_order VARCHAR(100), related_process VARCHAR(200), acknowledged_at VARCHAR(50),
    last_reminded_at VARCHAR(50), completed_qty DOUBLE DEFAULT 0, progress_qty DOUBLE DEFAULT 0,
    operator_id VARCHAR(200), actual_qty DOUBLE DEFAULT 0, display_seq INT DEFAULT NULL,
    process_code VARCHAR(200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

# 从备份复制数据
s = sqlite3.connect('mobile_api_ai/_migration_backups/wechat_container_final_backup.db')
rows = s.execute('SELECT * FROM data_packages').fetchall()
if rows:
    cols = [r[1] for r in s.execute('PRAGMA table_info(data_packages)').fetchall()]
    ph = ','.join(['%s'] * len(cols))
    for row in rows:
        vals = []
        for v in row:
            if v is None: vals.append(None)
            elif isinstance(v, (int, float)): vals.append(v)
            elif isinstance(v, bytes): vals.append(v.decode('utf-8', 'replace'))
            else: vals.append(str(v))
        cur.execute('INSERT INTO data_packages (' + ','.join(cols) + ') VALUES (' + ph + ')', vals)
    print('data_packages:', len(rows), 'rows')
s.close()

# 2. 重建 process_records
cur.execute('DROP TABLE IF EXISTS process_records')
cur.execute('''CREATE TABLE process_records (
    id VARCHAR(255) PRIMARY KEY, production_id VARCHAR(255), process_name VARCHAR(200),
    process_code VARCHAR(100), process_seq INT, display_seq INT,
    planned_qty DOUBLE, completed_qty DOUBLE, qualified_qty DOUBLE,
    status VARCHAR(50), worker VARCHAR(200), unit VARCHAR(50),
    order_no VARCHAR(100), product_name VARCHAR(200), quantity DOUBLE,
    customer_name VARCHAR(200), delivery_date VARCHAR(50), priority VARCHAR(50),
    flow_type VARCHAR(100), current_step INT, steps LONGTEXT, content LONGTEXT,
    created_at VARCHAR(50), updated_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

s2 = sqlite3.connect('mobile_api_ai/_migration_backups/wechat_container_final_backup.db')
rows = s2.execute('SELECT * FROM process_records').fetchall()
if rows:
    cols = [r[1] for r in s2.execute('PRAGMA table_info(process_records)').fetchall()]
    ph = ','.join(['%s'] * len(cols))
    for row in rows:
        vals = []
        for v in row:
            if v is None: vals.append(None)
            elif isinstance(v, (int, float)): vals.append(v)
            elif isinstance(v, bytes): vals.append(v.decode('utf-8', 'replace'))
            else: vals.append(str(v))
        cur.execute('INSERT INTO process_records (' + ','.join(cols) + ') VALUES (' + ph + ')', vals)
    print('process_records:', len(rows), 'rows')
s2.close()

cur.execute('SELECT COUNT(*) FROM data_packages')
print('data_packages rows:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM process_records')
print('process_records rows:', cur.fetchone()[0])
c.close()
print('Done')
