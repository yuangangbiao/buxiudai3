#!/usr/bin/env python3
"""等待 MySQL 服务就绪（CI 用）"""
import sys
import time

def wait_for_mysql(host='127.0.0.1', port=3306, user='root',
                    password='88888888', database='container_center',
                    max_attempts=60, interval=2):
    """最多尝试 max_attempts 次，每次间隔 interval 秒"""
    for attempt in range(1, max_attempts + 1):
        try:
            import pymysql
            conn = pymysql.connect(
                host=host, port=port, user=user,
                password=password, database=database,
                connect_timeout=2
            )
            conn.close()
            print(f"MySQL ready after {attempt} attempt(s)")
            return 0
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(interval)
            else:
                print(f"ERROR: MySQL not ready after {max_attempts} attempts: {e}")
                return 1
    return 1

if __name__ == '__main__':
    sys.exit(wait_for_mysql())
