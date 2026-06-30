# -*- coding: utf-8 -*-
"""
备份系统模块
"""
import os
import stat
import shutil
import time
import threading
from datetime import datetime, timedelta
from config import MYSQL_CONFIG

def backup_database():
    """备份数据库"""
    try:
        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"steel_belt_backup_{timestamp}.sql")
        
        import pymysql
        from core.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SHOW TABLES")
        tables = [row['Tables_in_steel_belt'] for row in cursor.fetchall()]
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f"-- ===========================================================\n")
            f.write(f"-- 钢带订单追踪系统 - 数据库备份\n")
            f.write(f"-- 备份时间: {timestamp}\n")
            f.write(f"-- 数据库: {MYSQL_CONFIG['database']}\n")
            f.write(f"-- ===========================================================\n")
            f.write(f"-- 警告: 此文件包含敏感数据，请妥善保管！\n")
            f.write(f"-- 建议: 备份完成后立即转移到安全存储位置\n")
            f.write(f"-- ===========================================================\n\n")
            
            for table in tables:
                f.write(f"-- 表: {table}\n")
                cursor.execute("SELECT * FROM %s", (table,))
                rows = cursor.fetchall()
                
                cursor.execute("SHOW COLUMNS FROM %s", (table,))
                columns = [col['Field'] for col in cursor.fetchall()]
                
                f.write(f"DELETE FROM {table};\n")
                
                if rows:
                    f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n")
                    for i, row in enumerate(rows):
                        values = []
                        for col in columns:
                            val = row[col]
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                escaped_val = val.replace("\\", "\\\\").replace("'", "''")
                                values.append(f"'{escaped_val}'")
                            else:
                                values.append(str(val))
                        line = f"    ({', '.join(values)})"
                        if i < len(rows) - 1:
                            line += ","
                        f.write(line + "\n")
                f.write("\n")
        
        conn.close()
        
        # 设置备份文件权限为仅所有者可读写（0600）
        try:
            os.chmod(backup_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            print(f"[备份] 设置文件权限失败: {e}")
        
        print(f"[备份] 数据库备份成功: {backup_file}")
        
        # 保留最近7天的备份
        cleanup_old_backups(backup_dir, days=7)
        
    except Exception as e:
        print(f"[备份] 备份失败: {e}")

def cleanup_old_backups(backup_dir, days=7):
    """清理旧备份"""
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    for filename in os.listdir(backup_dir):
        filepath = os.path.join(backup_dir, filename)
        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"[备份] 删除旧备份失败 {filename}: {e}")

def backup_scheduler():
    """备份调度器"""
    while True:
        # 每天凌晨2点执行备份
        now = datetime.now()
        next_backup = datetime(now.year, now.month, now.day, 2, 0, 0)
        if now >= next_backup:
            next_backup = next_backup + timedelta(days=1)
        
        sleep_seconds = (next_backup - now).total_seconds()
        time.sleep(min(sleep_seconds, 3600))
        
        if datetime.now().hour == 2:
            backup_database()

def start_backup_scheduler():
    """启动备份调度器"""
    backup_thread = threading.Thread(target=backup_scheduler, daemon=True)
    backup_thread.start()
    print("[备份系统] 自动备份已启动")

if __name__ == "__main__":
    backup_database()