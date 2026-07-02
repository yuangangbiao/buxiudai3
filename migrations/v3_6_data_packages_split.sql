-- ============================================================================
-- [v3.6] data_packages 业务分表收敛 - 完整迁移脚本
--
-- 适用版本: v3.6
-- 执行时间: 凌晨 3-4 点（业务低峰）
-- 回滚方案: 见末尾 ROLLBACK 段
--
-- 内容:
-- 1. 备份（如未备份）
-- 2. status 字典统一（142 行）
-- 3. 9 业务表加 6 字段（is_deleted/created_by/updated_by/updated_at）
-- 4. approval_records 新建
-- 5. data_packages RENAME + 触发器
-- 6. DROP 2 张历史表
-- 7. 验证
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;
SET @backup_date = DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s');

-- ============================================================
-- 1. 备份
-- ============================================================
SELECT '[1/7] 备份...' AS step;
CREATE TABLE IF NOT EXISTS process_sub_steps_backup_20260702 AS SELECT * FROM process_sub_steps WHERE 1=0;
INSERT IGNORE INTO process_sub_steps_backup_20260702 SELECT * FROM process_sub_steps;
CREATE TABLE IF NOT EXISTS material_records_backup_20260702 AS SELECT * FROM material_records WHERE 1=0;
INSERT IGNORE INTO material_records_backup_20260702 SELECT * FROM material_records;
CREATE TABLE IF NOT EXISTS quality_records_backup_20260702 AS SELECT * FROM quality_records WHERE 1=0;
INSERT IGNORE INTO quality_records_backup_20260702 SELECT * FROM quality_records;
SELECT CONCAT('备份完成 @ ', @backup_date) AS msg;

-- ============================================================
-- 2. status 字典统一（142 行）
-- ============================================================
SELECT '[2/7] status 字典统一...' AS step;
UPDATE process_sub_steps SET status='pending' WHERE status='待开始';
UPDATE material_records SET status='pending' WHERE status='待备料';
UPDATE material_records SET status='shortage' WHERE status='缺料';
UPDATE quality_records SET status='in_progress' WHERE status='quality_reported';
UPDATE quality_records SET status='completed' WHERE status='quality_re_received';
UPDATE quality_records SET status='pending' WHERE status IS NULL;
SELECT 'status 字典迁移完成' AS msg;

-- ============================================================
-- 3. 9 业务表 + tbl_configs 加 6 字段
-- ============================================================
SELECT '[3/7] 9 业务表升级...' AS step;
-- process_sub_steps
ALTER TABLE process_sub_steps
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
-- material_records / quality_records / outsource_records / repair_records
ALTER TABLE material_records
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE quality_records
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE outsource_records
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE repair_records
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE production_orders
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE schedule_flow_logs
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE process_records
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE tbl_configs
  ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
SELECT '9 业务表 + tbl_configs 升级完成' AS msg;

-- ============================================================
-- 4. approval_records 新建
-- ============================================================
SELECT '[4/7] approval_records 新建...' AS step;
CREATE TABLE IF NOT EXISTS approval_records (
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    order_no VARCHAR(64),
    approval_type VARCHAR(32) NOT NULL,
    title VARCHAR(255),
    applicant VARCHAR(64),
    approver VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    content JSON,
    related_order VARCHAR(64),
    related_process VARCHAR(100),
    reject_reason TEXT,
    created_by VARCHAR(64) NOT NULL DEFAULT 'system',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    KEY idx_order_no (order_no),
    KEY idx_status (status),
    KEY idx_approver (approver),
    KEY idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SELECT 'approval_records 已创建' AS msg;

-- ============================================================
-- 5. data_packages RENAME + 触发器
-- ============================================================
SELECT '[5/7] data_packages RENAME + 触发器...' AS step;
ALTER TABLE data_packages RENAME TO data_packages_deprecated;
DROP TRIGGER IF EXISTS block_write_deprecated;
DELIMITER $$
CREATE TRIGGER block_write_deprecated
BEFORE INSERT ON data_packages_deprecated
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'data_packages 已废弃，请使用 11 业务表';
END$$
DELIMITER ;
SELECT 'data_packages 已 RENAME + 触发器' AS msg;

-- ============================================================
-- 6. DROP 2 张历史表
-- ============================================================
SELECT '[6/7] DROP 历史表...' AS step;
DROP TABLE IF EXISTS process_packages;
DROP TABLE IF EXISTS quality_packages;
SELECT '历史表已 DROP' AS msg;

-- ============================================================
-- 7. 验证
-- ============================================================
SELECT '[7/7] 验证...' AS step;
SELECT 'process_sub_steps status' AS table_name, status, COUNT(*) AS cnt
FROM process_sub_steps GROUP BY status
UNION ALL
SELECT 'material_records status', status, COUNT(*)
FROM material_records GROUP BY status
UNION ALL
SELECT 'quality_records status', status, COUNT(*)
FROM quality_records GROUP BY status;

SELECT 'data_packages 状态' AS info, COUNT(*) AS cnt
FROM information_schema.tables
WHERE TABLE_SCHEMA = 'container_center'
  AND TABLE_NAME IN ('data_packages', 'data_packages_deprecated');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- ROLLBACK 段（如需回滚）
-- ============================================================================
-- DROP TRIGGER IF EXISTS block_write_deprecated;
-- ALTER TABLE data_packages_deprecated RENAME TO data_packages;
-- DROP TABLE IF EXISTS approval_records;
-- ALTER TABLE process_sub_steps DROP COLUMN is_deleted;
-- ALTER TABLE process_sub_steps DROP COLUMN created_by;
-- ALTER TABLE process_sub_steps DROP COLUMN updated_by;
-- ALTER TABLE process_sub_steps DROP COLUMN updated_at;
-- -- ... 同样 DROP 其他 8 表的字段
-- UPDATE process_sub_steps SET status='待开始' WHERE status='pending';
-- UPDATE material_records SET status='待备料' WHERE status='pending';
-- UPDATE material_records SET status='缺料' WHERE status='shortage';
-- UPDATE quality_records SET status='quality_reported' WHERE status='in_progress';
-- UPDATE quality_records SET status='quality_re_received' WHERE status='completed';
