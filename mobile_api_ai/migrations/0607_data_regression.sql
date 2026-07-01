-- ====== 报工数据回归系统 DDL v2 ======
-- 库: container_center
-- 日期: 2026-06-08

-- ============================================================
-- ↑ M1：审计表
-- ============================================================
CREATE TABLE IF NOT EXISTS process_sub_steps_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    original_id VARCHAR(50) NOT NULL COMMENT '被覆盖的 sub_steps.id (UUID)',
    order_no VARCHAR(50) NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    batch_no VARCHAR(100) NOT NULL DEFAULT '',
    operator_before VARCHAR(64) NOT NULL DEFAULT '' COMMENT '旧操作员',
    operator_after VARCHAR(64) NOT NULL DEFAULT '' COMMENT '新操作员',
    old_quantity DECIMAL(14,4) NOT NULL DEFAULT 0,
    new_quantity DECIMAL(14,4) NOT NULL DEFAULT 0,
    delta_quantity DECIMAL(14,4) GENERATED ALWAYS AS (new_quantity - old_quantity) STORED,
    revert_reason VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'self_correct|self_withdraw|admin_force|admin_withdraw|other_override|desktop_sync',
    reverted_by VARCHAR(64) NOT NULL DEFAULT '',
    reverted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_history_order (order_no),
    INDEX idx_history_time (reverted_at),
    INDEX idx_history_reason (revert_reason)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报工数据回归审计';

-- ============================================================
-- ↑ M2：process_records 扩展
-- ============================================================
ALTER TABLE process_records ADD COLUMN qc_required TINYINT(1) DEFAULT 0;
ALTER TABLE process_records ADD COLUMN qc_trigger_reason VARCHAR(32) DEFAULT '';
ALTER TABLE process_records ADD COLUMN data_locked TINYINT(1) DEFAULT 0;
ALTER TABLE process_records ADD COLUMN last_reverted_at DATETIME DEFAULT NULL;

-- ============================================================
-- ↓ 回滚
-- ============================================================
-- DROP TABLE IF EXISTS process_sub_steps_history;
-- ALTER TABLE process_records DROP COLUMN qc_required, DROP COLUMN qc_trigger_reason, DROP COLUMN data_locked, DROP COLUMN last_reverted_at;
