import os
import pymysql
c = pymysql.connect(host='127.0.0.1', user='root', password=os.environ.get('MYSQL_PASSWORD', ''), database='container_center')
cur = c.cursor()

# 1. 修正 process_sub_steps: 焊接眼镜网 -> M01
cur.execute("UPDATE process_sub_steps SET process_code='M01' WHERE step_name='焊接眼镜网' AND process_code='N/A'")
n1 = cur.rowcount
c.commit()
print(f'[1] process_sub_steps 焊接眼镜网 修正: {n1} 行 -> M01')

# 2. 备份 data_packages
cur.execute('CREATE TABLE data_packages_bak_20260612 AS SELECT id, process_code FROM data_packages')
n2 = cur.rowcount
c.commit()
print(f'[2] 备份 data_packages {n2} 行 -> data_packages_bak_20260612')

# 3. 回填 4 个 material_request (原材料准备 -> P01)
cases = [
    ('27B948C6', 'P01'),
    ('6165232F', 'P01'),
    ('72E29E2F', 'P01'),
    ('C79D9086', 'P01'),
]
for pkg_id, code in cases:
    cur.execute('UPDATE data_packages SET process_code=%s WHERE id=%s', (code, pkg_id))
    print(f'  {pkg_id} -> {code}')

# 4. 回填 1 个质检审核 (冷冻螺旋网-质检审核 -> P15)
cur.execute("UPDATE data_packages SET process_code='P15' WHERE id='80e608a5'")
print(f'  80e608a5 -> P15 (质检审核)')

c.commit()
print(f'[3] 回填完成')

# 5. 验证
cur.execute("SELECT id, data_type, process_code, title FROM data_packages WHERE (data_type='material_request' OR data_type='quality_task') ORDER BY data_type, id")
for r in cur.fetchall():
    print(f'  {r[0][:16]} {r[1]:20} code={r[2]!r:6} title={r[3]!r}')

cur.execute("SELECT COUNT(*) FROM data_packages WHERE data_type IN ('material_request','quality_task') AND (process_code IS NULL OR process_code=%s)", ('',))
rem = cur.fetchone()[0]
print(f'\n[4] material_request+quality_task 仍为空: {rem} 行')

cur.close()
c.close()
print('完成')
