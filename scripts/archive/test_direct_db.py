# -*- coding: utf-8 -*-
import mysql.connector
import os

print("=" * 50)
print("MySQL 直连数据库测试")
print("=" * 50)

configs = [
    ("本地", "localhost", "root", os.getenv('MYSQL_PASSWORD', ''), "inventory_db"),
    ("IP地址", os.getenv('INVENTORY_HOST', '127.0.0.1'), "root", os.getenv('MYSQL_PASSWORD', ''), "inventory_db"),
]

for name, host, user, password, db in configs:
    print(f"\n测试 {name} 连接 ({host})...")
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM inventory")
        inv_count = cursor.fetchone()[0]
        conn.close()
        print(f"  [OK] 连接成功! 商品: {count}, 库存记录: {inv_count}")
    except Exception as e:
        print(f"  [FAIL] {str(e)[:60]}")

print("\n" + "=" * 50)
print("配置说明:")
print("1. MySQL已配置 bind-address=0.0.0.0")
print("2. 已创建 root@'%' 用户支持远程连接")
print("3. 需要重启MySQL服务使配置生效")
print("4. 重启命令: 右键管理员运行 重启MySQL服务.bat")
print("=" * 50)
