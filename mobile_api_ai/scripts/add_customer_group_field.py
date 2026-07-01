# -*- coding: utf-8 -*-
"""
添加 customer_group 字段到数据库表中
"""
import os
import sqlite3

def add_customer_group_field(db_path):
    """为指定数据库添加 customer_group 字段"""
    if not os.path.exists(db_path):
        print(f"⚠️  数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(process_records)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'customer_group' not in columns:
            cursor.execute('ALTER TABLE process_records ADD COLUMN customer_group TEXT DEFAULT ""')
            conn.commit()
            print(f"✅ 成功为 {os.path.basename(db_path)} 的 process_records 表添加 customer_group 字段")
        else:
            print(f"ℹ️  {os.path.basename(db_path)} 的 process_records 表已存在 customer_group 字段")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return False

def add_customer_group_to_sync_records(db_path):
    """为 container_sync_records 表添加 customer_group 字段"""
    if not os.path.exists(db_path):
        print(f"⚠️  数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(container_sync_records)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'customer_group' not in columns:
            cursor.execute('ALTER TABLE container_sync_records ADD COLUMN customer_group TEXT DEFAULT ""')
            conn.commit()
            print(f"✅ 成功为 {os.path.basename(db_path)} 的 container_sync_records 表添加 customer_group 字段")
        else:
            print(f"ℹ️  {os.path.basename(db_path)} 的 container_sync_records 表已存在 customer_group 字段")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return False

if __name__ == '__main__':
    print("=== 开始添加 customer_group 字段 ===")
    
    # 处理 wechat_container.db
    container_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'wechat_container.db')
    add_customer_group_field(container_db)
    
    # 处理 chengsheng.db
    chengsheng_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '..', 'backend', 'data', 'chengsheng.db')
    add_customer_group_field(chengsheng_db)
    add_customer_group_to_sync_records(chengsheng_db)
    
    print("\n=== 字段添加完成 ===")