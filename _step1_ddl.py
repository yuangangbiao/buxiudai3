"""
工序编号实施 第1步：MySQL DDL + 回填
"""
import pymysql

PCODE = {
    "原材料准备": "P01","焊接眼镜网": "P02","激光切板": "P03",
    "链板冲压孔": "P04","链板冲压成型": "P05","编制左旋": "P06",
    "编制右旋": "P07","穿曲轴": "P08","输送带组装穿杆": "P09",
    "安装链条": "P10","安装裙边": "P11","整形校直": "P12",
    "焊接输送带": "P13","表面处理": "P14","质量检验": "P15","包装入库": "P16",
}

c = pymysql.connect(host='localhost',port=3306,user='root',password='88888888',
                     database='steel_belt',charset='utf8mb4',autocommit=True)
cur = c.cursor()

# 1. 加列
try:
    cur.execute("ALTER TABLE process_records ADD COLUMN process_code VARCHAR(10) NOT NULL DEFAULT '' AFTER process_name")
    print('1. ADD COLUMN process_code: OK')
except pymysql.err.OperationalError as e:
    if 'Duplicate column' in str(e):
        print('1. process_code 列已存在, 跳过')
    else:
        raise

# 2. 回填预定义工序
import hashlib
for name, code in PCODE.items():
    cur.execute("UPDATE process_records SET process_code=%s WHERE process_name=%s AND process_code=''", (code, name))
    if cur.rowcount:
        print('2. 回填 %s -> %s (%s行)' % (name, code, cur.rowcount))

# 3. 回填非标工序（PX-动态）
cur.execute("SELECT DISTINCT process_name FROM process_records WHERE process_code=''")
odd = cur.fetchall()
for r in odd:
    name = r[0]
    code = 'PX' + hashlib.md5(name.encode()).hexdigest()[:4].upper()
    cur.execute("UPDATE process_records SET process_code=%s WHERE process_name=%s AND process_code=''", (code, name))
    print('3. 动态 %s -> %s (%s行)' % (name, code, cur.rowcount))

# 4. 加索引
try:
    cur.execute("CREATE INDEX idx_process_code ON process_records(order_id, process_code)")
    print('4. INDEX: OK')
except:
    print('4. INDEX: 已存在')

# 5. 验证
cur.execute("SELECT COUNT(*) FROM process_records WHERE process_code=''")
empty = cur.fetchone()[0]
print('\n5. 空process_code: %s条 (应为0)' % empty)
cur.execute("SELECT process_name, process_code, COUNT(*) as cnt FROM process_records GROUP BY process_name, process_code ORDER BY process_code")
print('\n全部工序编码:')
for r in cur.fetchall():
    print('  %-25s %-10s %s条' % (r[0], r[1], r[2]))

c.close()
print('\n✅ DDL完成')
