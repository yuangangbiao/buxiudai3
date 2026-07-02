# -*- coding: utf-8 -*-
"""
[C.5] DROP data_packages_deprecated + 触发器
"""
import pymysql
c = pymysql.connect(host='localhost', port=3306, user='root',
                    password='88888888', database='container_center', autocommit=True)
cur = c.cursor()
# 1. DROP 触发器
cur.execute("DROP TRIGGER IF EXISTS block_write_deprecated")
print('✅ 触发器已 DROP')
# 2. DROP 表
cur.execute("DROP TABLE IF EXISTS data_packages_deprecated")
print('✅ data_packages_deprecated 已 DROP')
# 3. 验证
cur.execute("SHOW TABLES LIKE 'data_packages%'")
print(f'  剩余 data_packages% 表: {cur.fetchall()}')
c.close()
print('\n🎉 data_packages 已彻底物理删除！')
