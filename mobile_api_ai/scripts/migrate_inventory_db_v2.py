# -*- coding: utf-8 -*-
"""修复版迁移：每个 DDL 单独 execute()，避免多语句语法错"""
import os
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
cur = conn.cursor()
lines = []

# 工具函数
def add_column(tbl, col, ddl):
    cur.execute(f"SHOW COLUMNS FROM `{tbl}` LIKE %s", (col,))
    if cur.fetchone():
        lines.append(f'  [SKIP] {tbl}.{col}'); return False
    cur.execute(f"ALTER TABLE `{tbl}` {ddl}")
    lines.append(f'  [ADD] {tbl}.{col}'); return True

def add_index(tbl, idx_name, idx_def):
    cur.execute(f"SHOW INDEX FROM `{tbl}` WHERE Key_name=%s", (idx_name,))
    if cur.fetchone():
        lines.append(f'  [SKIP IDX] {idx_name}'); return False
    cur.execute(f"CREATE INDEX `{idx_name}` ON `{tbl}` {idx_def}")
    lines.append(f'  [CREATE IDX] {idx_name}'); return True

def create_table(tbl, ddl):
    cur.execute(f"SHOW TABLES LIKE %s", (tbl,))
    if cur.fetchone():
        lines.append(f'  [SKIP TBL] {tbl}'); return False
    cur.execute(ddl)
    lines.append(f'  [CREATE TBL] {tbl}'); return True

# ============ 1) deleted_at ============
for tbl in ['products', 'suppliers', 'categories', 'warehouses', 'inventory', 'inventory_transactions', 'inventory_alerts', 'operation_logs']:
    add_column(tbl, 'deleted_at', "ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT '软删除时间'")

# ============ 2) products 补字段 ============
add_column('products', 'last_purchase_price', "ADD COLUMN last_purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '最近采购单价'")
add_column('products', 'last_purchase_price_at', "ADD COLUMN last_purchase_price_at DATETIME DEFAULT NULL COMMENT '最近采购单价更新时间'")
# max_stock 和 categories.parent_id 上一轮已加，跳过

# ============ 3) warehouses 补字段 ============
add_column('warehouses', 'is_active', "ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=启用 0=停用'")
add_column('warehouses', 'manager', "ADD COLUMN manager VARCHAR(50) DEFAULT NULL COMMENT '仓库负责人'")

# ============ 4) inventory_transactions 补字段 ============
add_column('inventory_transactions', 'status', "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'")
add_column('inventory_transactions', 'cancel_reason', "ADD COLUMN cancel_reason TEXT DEFAULT NULL")
add_column('inventory_transactions', 'cancelled_at', "ADD COLUMN cancelled_at DATETIME DEFAULT NULL")
add_column('inventory_transactions', 'cancelled', "ADD COLUMN cancelled TINYINT(1) NOT NULL DEFAULT 0")
add_column('inventory_transactions', 'reason', "ADD COLUMN reason VARCHAR(500) DEFAULT NULL")
add_column('inventory_transactions', 'receiver', "ADD COLUMN receiver VARCHAR(50) DEFAULT NULL")

# ============ 5) CREATE 缺失表 ============
create_table('stocktakes', """
CREATE TABLE stocktakes (
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
""")
create_table('stocktake_items', """
CREATE TABLE stocktake_items (
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
""")
create_table('transfers', """
CREATE TABLE transfers (
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
""")
create_table('transfer_items', """
CREATE TABLE transfer_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  transfer_id INT NOT NULL,
  product_id INT NOT NULL,
  qty DECIMAL(12,2) NOT NULL,
  deleted_at DATETIME DEFAULT NULL,
  KEY idx_ti_transfer (transfer_id),
  KEY idx_ti_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")
create_table('notifications', """
CREATE TABLE notifications (
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
""")
create_table('import_sessions', """
CREATE TABLE import_sessions (
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
""")
create_table('users', """
CREATE TABLE users (
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
""")

# ============ 6) 索引 ============
add_index('products', 'idx_products_deleted', '(deleted_at)')
add_index('suppliers', 'idx_suppliers_deleted', '(deleted_at)')
add_index('categories', 'idx_categories_deleted', '(deleted_at)')
add_index('warehouses', 'idx_warehouses_deleted', '(deleted_at)')
add_index('inventory', 'idx_inv_wh_product', '(warehouse_id, product_id)')
add_index('inventory', 'idx_inv_qty', '(current_qty)')
add_index('inventory_transactions', 'idx_trans_created', '(created_at)')
# 复合唯一索引
cur.execute("SHOW INDEX FROM products WHERE Key_name='uk_products_code_active'")
if cur.fetchone():
    lines.append('  [SKIP IDX] uk_products_code_active')
else:
    try:
        cur.execute("ALTER TABLE products ADD UNIQUE INDEX uk_products_code_active (code, deleted_at)")
        lines.append('  [CREATE IDX] uk_products_code_active (code, deleted_at)')
    except Exception as e:
        lines.append(f'  [ERR IDX] uk_products_code_active: {e}')

conn.commit()
conn.close()
text = '\n'.join(lines)
Path(r'd:\yuan\migration_v2_result.txt').write_text(text, encoding='utf-8')
print(text)
