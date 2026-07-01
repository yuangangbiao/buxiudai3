# -*- coding: utf-8 -*-
"""执行迁移：
1. 备份关键表 (products, inventory, inventory_transactions, warehouses, suppliers, categories, inventory_alerts, operation_logs)
2. RENAME products.sku -> products.code  (代码 SQL 全用 code)
3. 给缺失表加 deleted_at
4. CREATE 缺失的表 (notifications, users, transfers, transfer_items, stocktakes, stocktake_items, import_sessions)
5. 创建索引
"""
import os
import time
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    database='inventory_db', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
ts = time.strftime('%Y%m%d_%H%M%S')
lines = [f'迁移开始: {ts}']

# ============ 1) 备份 ============
backup_tables = ['products', 'inventory', 'inventory_transactions', 'warehouses', 'suppliers', 'categories', 'inventory_alerts', 'operation_logs']
with conn.cursor() as cur:
    for t in backup_tables:
        try:
            cur.execute(f"SHOW TABLES LIKE '{t}'")
            if cur.fetchone():
                # 检查是否已经有 backup
                cur.execute(f"SHOW TABLES LIKE '{t}_backup_{ts}'")
                if not cur.fetchone():
                    cur.execute(f"CREATE TABLE `{t}_backup_{ts}` AS SELECT * FROM `{t}`")
                    lines.append(f'  [BACKUP] {t} -> {t}_backup_{ts}')
                else:
                    lines.append(f'  [SKIP] {t} 已有 backup')
            else:
                lines.append(f'  [SKIP] {t} 表不存在')
        except Exception as e:
            lines.append(f'  [ERR] backup {t}: {e}')

# ============ 2) RENAME products.sku -> code ============
with conn.cursor() as cur:
    cur.execute("SHOW COLUMNS FROM products LIKE 'code'")
    if cur.fetchone():
        lines.append('  [SKIP] products.code 已存在')
    else:
        cur.execute("SHOW COLUMNS FROM products LIKE 'sku'")
        if cur.fetchone():
            try:
                cur.execute("ALTER TABLE products CHANGE COLUMN sku code VARCHAR(50) NOT NULL")
                lines.append('  [RENAME] products.sku -> products.code')
            except Exception as e:
                lines.append(f'  [ERR] rename: {e}')
        else:
            # sku 也不存在，加 code 列
            cur.execute("ALTER TABLE products ADD COLUMN code VARCHAR(50) NOT NULL DEFAULT '' AFTER id")
            lines.append('  [ADD] products.code (默认空字符串)')

    # 处理 products.code 的 unique 冲突：可能已存在 uk_sku / idx_sku 等
    cur.execute("SHOW INDEX FROM products WHERE Key_name LIKE '%sku%'")
    sku_idx = cur.fetchall()
    for idx in sku_idx:
        try:
            cur.execute(f"ALTER TABLE products DROP INDEX `{idx['Key_name']}`")
            lines.append(f'  [DROP INDEX] {idx["Key_name"]}')
        except Exception as e:
            lines.append(f'  [ERR drop idx] {e}')

# ============ 3) 加 deleted_at 字段 ============
add_deleted_at = [
    ('products', "ALTER TABLE products ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT '软删除时间'"),
    ('suppliers', "ALTER TABLE suppliers ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('categories', "ALTER TABLE categories ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('warehouses', "ALTER TABLE warehouses ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('inventory', "ALTER TABLE inventory ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('inventory_transactions', "ALTER TABLE inventory_transactions ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('inventory_alerts', "ALTER TABLE inventory_alerts ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
    ('operation_logs', "ALTER TABLE operation_logs ADD COLUMN deleted_at DATETIME DEFAULT NULL"),
]
with conn.cursor() as cur:
    for tbl, ddl in add_deleted_at:
        cur.execute(f"SHOW COLUMNS FROM `{tbl}` LIKE 'deleted_at'")
        if cur.fetchone():
            lines.append(f'  [SKIP] {tbl}.deleted_at 已存在')
        else:
            try:
                cur.execute(f"USE inventory_db; {ddl}")
                lines.append(f'  [ADD] {tbl}.deleted_at')
            except Exception as e:
                lines.append(f'  [ERR] {tbl}.deleted_at: {e}')

# products 还要加 last_purchase_price / last_purchase_price_at
with conn.cursor() as cur:
    for col, ddl in [
        ('last_purchase_price', "ALTER TABLE products ADD COLUMN last_purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0"),
        ('last_purchase_price_at', "ALTER TABLE products ADD COLUMN last_purchase_price_at DATETIME DEFAULT NULL"),
    ]:
        cur.execute(f"SHOW COLUMNS FROM products LIKE '{col}'")
        if cur.fetchone():
            lines.append(f'  [SKIP] products.{col} 已存在')
        else:
            try:
                cur.execute(f"USE inventory_db; {ddl}")
                lines.append(f'  [ADD] products.{col}')
            except Exception as e:
                lines.append(f'  [ERR] products.{col}: {e}')

# warehouses 加 is_active / manager
with conn.cursor() as cur:
    for col, ddl in [
        ('is_active', "ALTER TABLE warehouses ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1"),
        ('manager', "ALTER TABLE warehouses ADD COLUMN manager VARCHAR(50) DEFAULT NULL"),
    ]:
        cur.execute(f"SHOW COLUMNS FROM warehouses LIKE '{col}'")
        if cur.fetchone():
            lines.append(f'  [SKIP] warehouses.{col} 已存在')
        else:
            try:
                cur.execute(f"USE inventory_db; {ddl}")
                lines.append(f'  [ADD] warehouses.{col}')
            except Exception as e:
                lines.append(f'  [ERR] warehouses.{col}: {e}')

# products 加 max_stock
with conn.cursor() as cur:
    cur.execute("SHOW COLUMNS FROM products LIKE 'max_stock'")
    if cur.fetchone():
        lines.append('  [SKIP] products.max_stock 已存在')
    else:
        try:
            cur.execute("ALTER TABLE products ADD COLUMN max_stock DECIMAL(15,3) NOT NULL DEFAULT 0 COMMENT '最大库存'")
            lines.append('  [ADD] products.max_stock')
        except Exception as e:
            lines.append(f'  [ERR] products.max_stock: {e}')

# categories 加 parent_id
with conn.cursor() as cur:
    cur.execute("SHOW COLUMNS FROM categories LIKE 'parent_id'")
    if cur.fetchone():
        lines.append('  [SKIP] categories.parent_id 已存在')
    else:
        try:
            cur.execute("ALTER TABLE categories ADD COLUMN parent_id INT DEFAULT NULL")
            lines.append('  [ADD] categories.parent_id')
        except Exception as e:
            lines.append(f'  [ERR] categories.parent_id: {e}')

# inventory_transactions 加 status / cancel_reason 等
with conn.cursor() as cur:
    for col, ddl in [
        ('status', "ALTER TABLE inventory_transactions ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'"),
        ('cancel_reason', "ALTER TABLE inventory_transactions ADD COLUMN cancel_reason TEXT DEFAULT NULL"),
        ('cancelled_at', "ALTER TABLE inventory_transactions ADD COLUMN cancelled_at DATETIME DEFAULT NULL"),
        ('cancelled', "ALTER TABLE inventory_transactions ADD COLUMN cancelled TINYINT(1) NOT NULL DEFAULT 0"),
        ('reason', "ALTER TABLE inventory_transactions ADD COLUMN reason VARCHAR(500) DEFAULT NULL"),
        ('receiver', "ALTER TABLE inventory_transactions ADD COLUMN receiver VARCHAR(50) DEFAULT NULL"),
    ]:
        cur.execute(f"SHOW COLUMNS FROM inventory_transactions LIKE '{col}'")
        if cur.fetchone():
            lines.append(f'  [SKIP] inventory_transactions.{col}')
        else:
            try:
                cur.execute(f"USE inventory_db; {ddl}")
                lines.append(f'  [ADD] inventory_transactions.{col}')
            except Exception as e:
                lines.append(f'  [ERR] inventory_transactions.{col}: {e}')

# ============ 4) CREATE 缺失表 ============
create_tables = [
    ('stocktakes', """
        CREATE TABLE IF NOT EXISTS stocktakes (
          id INT PRIMARY KEY AUTO_INCREMENT,
          warehouse_id INT NOT NULL,
          status VARCHAR(20) NOT NULL DEFAULT 'draft',
          tolerance_pct DECIMAL(5,2) NOT NULL DEFAULT 0.5,
          total_items INT NOT NULL DEFAULT 0,
          matched_items INT NOT NULL DEFAULT 0,
          diff_normal INT NOT NULL DEFAULT 0,
          diff_abnormal INT NOT NULL DEFAULT 0,
          operator VARCHAR(50) NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          submitted_at DATETIME DEFAULT NULL,
          adjusted_at DATETIME DEFAULT NULL,
          remark TEXT DEFAULT NULL,
          deleted_at DATETIME DEFAULT NULL,
          KEY idx_stocktake_wh (warehouse_id),
          KEY idx_stocktake_status (status),
          KEY idx_stocktake_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('stocktake_items', """
        CREATE TABLE IF NOT EXISTS stocktake_items (
          id INT PRIMARY KEY AUTO_INCREMENT,
          stocktake_id INT NOT NULL,
          product_id INT NOT NULL,
          expected_qty DECIMAL(12,2) NOT NULL DEFAULT 0,
          actual_qty DECIMAL(12,2) DEFAULT NULL,
          diff_qty DECIMAL(12,2) DEFAULT NULL,
          diff_status VARCHAR(20) NOT NULL DEFAULT 'pending',
          is_adjusted TINYINT(1) NOT NULL DEFAULT 0,
          KEY idx_si_stocktake (stocktake_id),
          KEY idx_si_product (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('transfers', """
        CREATE TABLE IF NOT EXISTS transfers (
          id INT PRIMARY KEY AUTO_INCREMENT,
          from_warehouse_id INT NOT NULL,
          to_warehouse_id INT NOT NULL,
          status VARCHAR(20) NOT NULL DEFAULT 'in_transit',
          total_items INT NOT NULL DEFAULT 0,
          operator VARCHAR(50) NOT NULL,
          receiver VARCHAR(50) DEFAULT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          completed_at DATETIME DEFAULT NULL,
          cancelled_at DATETIME DEFAULT NULL,
          cancel_reason VARCHAR(500) DEFAULT NULL,
          remark TEXT DEFAULT NULL,
          deleted_at DATETIME DEFAULT NULL,
          KEY idx_trans_from (from_warehouse_id),
          KEY idx_trans_to (to_warehouse_id),
          KEY idx_trans_status (status),
          KEY idx_trans_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('transfer_items', """
        CREATE TABLE IF NOT EXISTS transfer_items (
          id INT PRIMARY KEY AUTO_INCREMENT,
          transfer_id INT NOT NULL,
          product_id INT NOT NULL,
          qty DECIMAL(12,2) NOT NULL,
          deleted_at DATETIME DEFAULT NULL,
          KEY idx_ti_transfer (transfer_id),
          KEY idx_ti_product (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('notifications', """
        CREATE TABLE IF NOT EXISTS notifications (
          id INT PRIMARY KEY AUTO_INCREMENT,
          user_id INT DEFAULT NULL,
          type VARCHAR(30) NOT NULL,
          title VARCHAR(200) NOT NULL,
          body TEXT DEFAULT NULL,
          link VARCHAR(500) DEFAULT NULL,
          is_read TINYINT(1) NOT NULL DEFAULT 0,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          read_at DATETIME DEFAULT NULL,
          KEY idx_notif_user (user_id),
          KEY idx_notif_type (type),
          KEY idx_notif_read (is_read),
          KEY idx_notif_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('import_sessions', """
        CREATE TABLE IF NOT EXISTS import_sessions (
          id INT PRIMARY KEY AUTO_INCREMENT,
          token VARCHAR(64) NOT NULL UNIQUE,
          entity VARCHAR(50) NOT NULL,
          file_name VARCHAR(200) NOT NULL,
          file_size INT NOT NULL,
          total_rows INT NOT NULL DEFAULT 0,
          valid_rows INT NOT NULL DEFAULT 0,
          invalid_rows INT NOT NULL DEFAULT 0,
          status VARCHAR(20) NOT NULL DEFAULT 'pending',
          error_detail TEXT DEFAULT NULL,
          operator VARCHAR(50) NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          expires_at DATETIME NOT NULL,
          committed_at DATETIME DEFAULT NULL,
          KEY idx_import_token (token),
          KEY idx_import_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
    ('users', """
        CREATE TABLE IF NOT EXISTS users (
          id INT PRIMARY KEY AUTO_INCREMENT,
          username VARCHAR(50) NOT NULL UNIQUE,
          display_name VARCHAR(100) DEFAULT NULL,
          password_hash VARCHAR(255) NOT NULL,
          role VARCHAR(20) NOT NULL DEFAULT 'viewer',
          is_active TINYINT(1) NOT NULL DEFAULT 1,
          last_login_at DATETIME DEFAULT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          KEY idx_users_role (role),
          KEY idx_users_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """),
]
with conn.cursor() as cur:
    for tbl, ddl in create_tables:
        try:
            cur.execute(f"USE inventory_db; {ddl}")
            lines.append(f'  [CREATE] {tbl}')
        except Exception as e:
            lines.append(f'  [ERR] CREATE {tbl}: {e}')

# ============ 5) 索引 ============
indexes = [
    ('products', 'idx_products_deleted', 'products(deleted_at)'),
    ('suppliers', 'idx_suppliers_deleted', 'suppliers(deleted_at)'),
    ('categories', 'idx_categories_deleted', 'categories(deleted_at)'),
    ('warehouses', 'idx_warehouses_deleted', 'warehouses(deleted_at)'),
    ('inventory', 'idx_inv_wh_product', 'inventory(warehouse_id, product_id)'),
    ('inventory', 'idx_inv_qty', 'inventory(current_qty)'),
    ('inventory_transactions', 'idx_trans_created', 'inventory_transactions(created_at)'),
]
with conn.cursor() as cur:
    for tbl, idx_name, idx_def in indexes:
        cur.execute(f"SHOW INDEX FROM `{tbl}` WHERE Key_name='{idx_name}'")
        if cur.fetchone():
            lines.append(f'  [SKIP IDX] {idx_name}')
        else:
            try:
                cur.execute(f"USE inventory_db; CREATE INDEX {idx_name} ON `{tbl}`({idx_def.split('(', 1)[1]}")
                lines.append(f'  [CREATE IDX] {idx_name}')
            except Exception as e:
                lines.append(f'  [ERR IDX] {idx_name}: {e}')

# 复合唯一索引 uk_products_code_active
with conn.cursor() as cur:
    cur.execute("SHOW INDEX FROM products WHERE Key_name='uk_products_code_active'")
    if cur.fetchone():
        lines.append('  [SKID IDX] uk_products_code_active')
    else:
        try:
            cur.execute("ALTER TABLE products ADD UNIQUE INDEX uk_products_code_active (code, deleted_at)")
            lines.append('  [CREATE IDX] uk_products_code_active (code, deleted_at)')
        except Exception as e:
            lines.append(f'  [ERR IDX] uk_products_code_active: {e}')

conn.commit()
conn.close()

text = '\n'.join(lines)
Path(r'd:\yuan\migration_result.txt').write_text(text, encoding='utf-8')
print(text)
