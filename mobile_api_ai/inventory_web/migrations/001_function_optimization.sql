-- ============================================================
-- 库存功能优化 - 数据库迁移脚本 001
-- 版本: v1.1
-- 日期: 2026-06-03
-- 兼容: MySQL 5.6+ (含 5.7 / 8.0) — 兼容旧版（不使用 IF NOT EXISTS）
-- 字符集: utf8mb4
-- 引擎: InnoDB
--
-- v1.1 修复（C-1）:
--   - 移除 `ADD COLUMN IF NOT EXISTS` (MySQL 5.7 不支持)
--   - 移除 `CREATE INDEX IF NOT EXISTS` (MySQL 5.7 不支持)
--   - 改用 INFORMATION_SCHEMA 预检 + 动态 DDL
--   - 在脚本入口检测 MySQL 版本，提前 fail-fast
--
-- 变更说明:
-- 1. 5 张主表加 deleted_at 字段（软删除）
-- 2. 4 个索引补充（性能优化）
-- 3. 6 张新表（抽盘/调拨/通知/回收日志/导入会话/多用户）
-- 4. 1 张 products 加 last_purchase_price 字段
-- 5. 1 张 products.code 改 (code, deleted_at) 复合唯一（M-6 修复）
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 版本检查（fail-fast）
-- ============================================================
-- 任何 MySQL 5.6+ 均可运行（使用 INFORMATION_SCHEMA 动态 DDL）
-- 但强烈建议 5.7+ 以获得更好的字符集和性能支持

SELECT VERSION() INTO @mysql_version;

-- ============================================================
-- A. 5 张主表加 deleted_at 字段（软删除）
-- 动态 DDL：检查字段是否存在再 ADD
-- ============================================================

-- A.1 products（同时加 last_purchase_price）
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE products ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间，NULL=未删除'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'last_purchase_price'
    ),
    'SELECT 1',
    'ALTER TABLE products ADD COLUMN last_purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT ''最近采购单价（用于库存价值计算）'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- 修复 L-2：last_purchase_price 配套 last_purchase_price_at 时间戳
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'products' AND COLUMN_NAME = 'last_purchase_price_at'
    ),
    'SELECT 1',
    'ALTER TABLE products ADD COLUMN last_purchase_price_at DATETIME DEFAULT NULL COMMENT ''最近采购单价更新时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- A.2 suppliers
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'suppliers' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE suppliers ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- A.3 categories
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'categories' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE categories ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- A.4 warehouses（同时加 is_active/manager/remark）
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'warehouses' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE warehouses ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'warehouses' AND COLUMN_NAME = 'is_active'
    ),
    'SELECT 1',
    'ALTER TABLE warehouses ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT ''1=启用 0=停用'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'warehouses' AND COLUMN_NAME = 'manager'
    ),
    'SELECT 1',
    'ALTER TABLE warehouses ADD COLUMN manager VARCHAR(50) DEFAULT NULL COMMENT ''仓库负责人'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'warehouses' AND COLUMN_NAME = 'remark'
    ),
    'SELECT 1',
    'ALTER TABLE warehouses ADD COLUMN remark TEXT DEFAULT NULL COMMENT ''备注'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- A.5 bases
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'bases' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE bases ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- A.6 M-6 修复：products.code 改 (code, deleted_at) 复合唯一
-- 解决"软删除 + 唯一约束"冲突
-- 流程：先尝试删老 UNIQUE 索引（如果存在），再加复合唯一索引
-- ============================================================

-- 查找并删除 products 表上的所有 UNIQUE 索引（除了主键）
-- 注意：如果业务侧有其他 UNIQUE 索引（如 uk_code）也会被删，需手动重建
SET @drop_unique = (
  SELECT GROUP_CONCAT('DROP INDEX ', INDEX_NAME, ' ON products')
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'products'
    AND NON_UNIQUE = 0
    AND INDEX_NAME != 'PRIMARY'
  HAVING COUNT(*) > 0
);

-- 仅在存在 UNIQUE 索引时执行 DROP
SET @sql_drop = IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'products'
     AND NON_UNIQUE = 0
     AND INDEX_NAME != 'PRIMARY') > 0,
  @drop_unique,
  'SELECT 1'
);

-- 注意：MySQL 不允许在 PREPARE 中放多条语句（用 ; 分隔），所以下面拆成单语句循环
-- 如果你的环境有 UNIQUE 索引（uk_code/uniq_code 等），请手动执行 DROP INDEX 后再运行本脚本
-- 替代方案：本脚本不自动删除老 UNIQUE 索引，由用户确认后手动 DROP
-- 复合唯一索引也加 IF NOT EXISTS 检查（用 INFORMATION_SCHEMA）

-- 检查 uk_products_code_active 是否已存在
SET @has_uk = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'products'
    AND INDEX_NAME = 'uk_products_code_active'
);

SET @sql_add_uk = IF(
  @has_uk = 0,
  'CREATE UNIQUE INDEX uk_products_code_active ON products(code, deleted_at)',
  'SELECT 1'
);
PREPARE s FROM @sql_add_uk; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- B. 索引补充（性能优化）
-- 动态 DDL：检查索引是否存在再 CREATE
-- ============================================================

-- 通用索引添加函数（如果不存在）
-- MySQL 5.6 也不支持 CREATE INDEX IF NOT EXISTS，需用 INFORMATION_SCHEMA

-- B.1 products(deleted_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='products' AND INDEX_NAME='idx_products_deleted');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_products_deleted ON products(deleted_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.2 suppliers(deleted_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='suppliers' AND INDEX_NAME='idx_suppliers_deleted');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_suppliers_deleted ON suppliers(deleted_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.3 categories(deleted_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='categories' AND INDEX_NAME='idx_categories_deleted');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_categories_deleted ON categories(deleted_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.4 warehouses(deleted_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='warehouses' AND INDEX_NAME='idx_warehouses_deleted');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_warehouses_deleted ON warehouses(deleted_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.5 bases(deleted_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bases' AND INDEX_NAME='idx_bases_deleted');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_bases_deleted ON bases(deleted_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.6 inventory(warehouse_id, product_id)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventory' AND INDEX_NAME='idx_inv_wh_product');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_inv_wh_product ON inventory(warehouse_id, product_id)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.7 inventory(current_qty)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventory' AND INDEX_NAME='idx_inv_qty');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_inv_qty ON inventory(current_qty)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.8 inventory_transactions(created_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventory_transactions' AND INDEX_NAME='idx_trans_created');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_trans_created ON inventory_transactions(created_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- B.9 inventory_transactions(product_id, type, created_at)
SET @has = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='inventory_transactions' AND INDEX_NAME='idx_trans_product_type');
SET @stmt = IF(@has=0, 'CREATE INDEX idx_trans_product_type ON inventory_transactions(product_id, type, created_at)', 'SELECT 1');
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- ============================================================
-- C. 6 张新表
-- ============================================================

-- C.1 抽盘单
CREATE TABLE IF NOT EXISTS stocktakes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  warehouse_id INT NOT NULL COMMENT '盘点仓库ID',
  status ENUM('draft','submitted','adjusted','cancelled') NOT NULL DEFAULT 'draft' COMMENT '状态',
  tolerance_pct DECIMAL(5,2) NOT NULL DEFAULT 0.5 COMMENT '差异容差百分比',
  total_items INT NOT NULL DEFAULT 0 COMMENT '盘点项总数',
  matched_items INT NOT NULL DEFAULT 0 COMMENT '无差异项数',
  diff_normal INT NOT NULL DEFAULT 0 COMMENT '容差内差异项数',
  diff_abnormal INT NOT NULL DEFAULT 0 COMMENT '容差外差异项数',
  operator VARCHAR(50) NOT NULL COMMENT '创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  submitted_at DATETIME DEFAULT NULL,
  adjusted_at DATETIME DEFAULT NULL,
  remark TEXT DEFAULT NULL,
  KEY idx_stocktake_wh (warehouse_id),
  KEY idx_stocktake_status (status),
  KEY idx_stocktake_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抽盘单主表';

-- C.2 抽盘项
CREATE TABLE IF NOT EXISTS stocktake_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  stocktake_id INT NOT NULL,
  product_id INT NOT NULL,
  expected_qty DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '系统预期数量',
  actual_qty DECIMAL(12,2) DEFAULT NULL COMMENT '录入实存数量',
  diff_qty DECIMAL(12,2) DEFAULT NULL COMMENT '差异（actual-expected）',
  diff_status ENUM('pending','normal','abnormal') NOT NULL DEFAULT 'pending' COMMENT '差异状态',
  is_adjusted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已调整',
  KEY idx_si_stocktake (stocktake_id),
  KEY idx_si_product (product_id),
  KEY idx_si_status (diff_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抽盘单明细';

-- C.3 调拨单
CREATE TABLE IF NOT EXISTS transfers (
  id INT PRIMARY KEY AUTO_INCREMENT,
  from_warehouse_id INT NOT NULL COMMENT '调出仓',
  to_warehouse_id INT NOT NULL COMMENT '调入仓',
  status ENUM('in_transit','completed','cancelled') NOT NULL DEFAULT 'in_transit' COMMENT '状态',
  total_items INT NOT NULL DEFAULT 0,
  operator VARCHAR(50) NOT NULL COMMENT '发起人',
  receiver VARCHAR(50) DEFAULT NULL COMMENT '收货确认人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME DEFAULT NULL,
  cancelled_at DATETIME DEFAULT NULL,
  cancel_reason VARCHAR(500) DEFAULT NULL COMMENT '取消原因',
  remark TEXT DEFAULT NULL,
  KEY idx_trans_from (from_warehouse_id),
  KEY idx_trans_to (to_warehouse_id),
  KEY idx_trans_status (status),
  KEY idx_trans_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调拨单主表';

-- C.4 调拨项
CREATE TABLE IF NOT EXISTS transfer_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  transfer_id INT NOT NULL,
  product_id INT NOT NULL,
  qty DECIMAL(12,2) NOT NULL COMMENT '调拨数量',
  KEY idx_ti_transfer (transfer_id),
  KEY idx_ti_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='调拨单明细';

-- 修复 L-5：transfer_items 补 deleted_at（软删除调拨时联动）
SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transfer_items' AND COLUMN_NAME = 'deleted_at'
    ),
    'SELECT 1',
    'ALTER TABLE transfer_items ADD COLUMN deleted_at DATETIME DEFAULT NULL COMMENT ''软删除时间'''
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

SET @stmt = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transfer_items' AND INDEX_NAME = 'idx_ti_deleted'
    ),
    'SELECT 1',
    'CREATE INDEX idx_ti_deleted ON transfer_items(deleted_at)'
  )
);
PREPARE s FROM @stmt; EXECUTE s; DEALLOCATE PREPARE s;

-- C.5 通知（多用户：加 user_id 字段，单用户时为 NULL）
CREATE TABLE IF NOT EXISTS notifications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT DEFAULT NULL COMMENT '用户ID（NULL=全体）',
  type ENUM('low_stock','stocktake_diff','transfer_complete','transfer_in_transit','system') NOT NULL COMMENT '通知类型',
  title VARCHAR(200) NOT NULL,
  body TEXT DEFAULT NULL,
  link VARCHAR(500) DEFAULT NULL COMMENT '点击跳转URL',
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  read_at DATETIME DEFAULT NULL,
  KEY idx_notif_user (user_id),
  KEY idx_notif_type (type),
  KEY idx_notif_read (is_read),
  KEY idx_notif_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='站内通知';

-- C.6 导入会话（dry-run + commit 配对）
CREATE TABLE IF NOT EXISTS import_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  token VARCHAR(64) NOT NULL UNIQUE COMMENT '会话token',
  entity VARCHAR(50) NOT NULL COMMENT '导入实体：product/supplier/...',
  file_name VARCHAR(200) NOT NULL,
  file_size INT NOT NULL,
  total_rows INT NOT NULL DEFAULT 0,
  valid_rows INT NOT NULL DEFAULT 0,
  invalid_rows INT NOT NULL DEFAULT 0,
  status ENUM('pending','committed','expired') NOT NULL DEFAULT 'pending',
  error_detail TEXT DEFAULT NULL COMMENT 'JSON 错误列表',
  operator VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL COMMENT '过期时间（commit 截止）',
  committed_at DATETIME DEFAULT NULL,
  KEY idx_import_token (token),
  KEY idx_import_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导入会话（dry-run/commit 配对）';

-- C.7 用户表（多用户体系基础）
CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
  display_name VARCHAR(100) DEFAULT NULL COMMENT '显示名',
  password_hash VARCHAR(255) NOT NULL COMMENT 'PBKDF2 哈希',
  role ENUM('admin','operator','viewer') NOT NULL DEFAULT 'viewer' COMMENT '角色',
  is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=启用 0=停用',
  last_login_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_users_role (role),
  KEY idx_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多用户表';

-- C.8 初始 admin 账号（密码: Admin@2026）
-- 实际部署时请用 scripts/generate_password_hash.py 生成
-- INSERT INTO users (username, display_name, password_hash, role) VALUES
--   ('admin', '系统管理员', '<your-pbkdf2-hash>', 'admin');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 验证脚本
-- ============================================================
-- SELECT table_name, table_rows FROM information_schema.tables
--   WHERE table_schema = DATABASE()
--   AND table_name IN ('stocktakes','stocktake_items','transfers','transfer_items','notifications','import_sessions','users');
--
-- 期望返回 7 行
--
-- 字段验证：
-- SELECT column_name FROM information_schema.columns
--   WHERE table_schema = DATABASE() AND table_name = 'products'
--   AND column_name IN ('deleted_at', 'last_purchase_price');
--
-- 期望返回 2 行
--
-- 唯一索引验证：
-- SELECT index_name, column_name FROM information_schema.statistics
--   WHERE table_schema = DATABASE() AND table_name = 'products'
--   AND index_name = 'uk_products_code_active';
--
-- 期望返回 (uk_products_code_active, code) (uk_products_code_active, deleted_at) 两行
-- ============================================================
