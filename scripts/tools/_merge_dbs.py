"""
迁移 wechat_container.db 的数据到 container_center.db
将 wechat_container.db 中有但 container_center.db 中缺失的数据记录复制过去
"""
import sqlite3
import os

BASE = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
SRC = os.path.join(BASE, 'wechat_container.db')
DST = os.path.join(BASE, 'container_center.db')

if not os.path.exists(SRC):
    print(f'[ERROR] 源数据库不存在: {SRC}')
    exit(1)
if not os.path.exists(DST):
    print(f'[ERROR] 目标数据库不存在: {DST}')
    exit(1)

src = sqlite3.connect(SRC)
dst = sqlite3.connect(DST)

# 获取所有表
tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print(f'源数据库表数量: {len(tables)}')

total_copied = 0
for table in tables:
    # 获取表结构
    src_cols = [r[1] for r in src.execute(f'PRAGMA table_info({table})').fetchall()]
    # 获取目标表结构
    dst_cols = [r[1] for r in dst.execute(f'PRAGMA table_info({table})').fetchall()]

    common_cols = [c for c in src_cols if c in dst_cols]
    if not common_cols:
        print(f'  跳过 {table}: 无共同列')
        continue

    # 获取源数据
    col_list = ','.join(common_cols)
    src_rows = src.execute(f'SELECT {col_list} FROM {table}').fetchall()
    
    # 获取目标已存在的 id
    if 'id' in common_cols:
        existing_ids = set(r[0] for r in dst.execute(f'SELECT id FROM {table}').fetchall())
    else:
        existing_ids = set()

    copied = 0
    for row in src_rows:
        row_dict = dict(zip(common_cols, row))
        if 'id' in row_dict and row_dict['id'] in existing_ids:
            continue  # 已存在，跳过
        
        placeholders = ','.join(['?' for _ in common_cols])
        values = [row_dict[c] for c in common_cols]
        
        try:
            dst.execute(f'INSERT INTO {table} ({col_list}) VALUES ({placeholders})', values)
            copied += 1
        except Exception as e:
            print(f'  插入失败 [{table}]: id={row_dict.get("id","?")} 错误: {e}')

    dst.commit()
    print(f'  {table}: 源={len(src_rows)}条, 新增={copied}条')
    total_copied += copied

dst.close()
src.close()
print(f'\n迁移完成! 共新增 {total_copied} 条记录')
