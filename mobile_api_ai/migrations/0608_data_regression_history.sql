-- ====== 统一数据回归审计表 DDL v1 ======
-- 库: container_center
-- 日期: 2026-06-08
-- 用途: 质检/物料/外协/排产四个模块共享同一个审计表，通过 data_type 字段区分

-- ============================================================
-- ↑ 创建审计表
-- ============================================================
CREATE TABLE IF NOT EXISTS container_center.data_regression_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    data_type VARCHAR(32) NOT NULL COMMENT '数据类型: quality|material|outsource|schedule',
    record_id VARCHAR(64) NOT NULL COMMENT '被审计记录ID',
    order_no VARCHAR(64) NOT NULL DEFAULT '' COMMENT '关联订单号',
    step_name VARCHAR(128) NOT NULL DEFAULT '' COMMENT '关联工序名',
    field_before JSON DEFAULT NULL COMMENT '修改前字段快照',
    field_after JSON DEFAULT NULL COMMENT '修改后字段快照',
    operator_before VARCHAR(64) NOT NULL DEFAULT '' COMMENT '原操作员',
    operator_after VARCHAR(64) NOT NULL DEFAULT '' COMMENT '新操作员/调度员',
    revert_reason VARCHAR(128) NOT NULL DEFAULT '' COMMENT '修改原因: admin_force|admin_withdraw|data_error|quality_redo|process_adjust',
    reverted_by VARCHAR(64) NOT NULL DEFAULT '' COMMENT '执行人',
    reverted_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    INDEX idx_drh_type (data_type),
    INDEX idx_drh_record (data_type, record_id),
    INDEX idx_drh_order (order_no),
    INDEX idx_drh_time (reverted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统一数据回归审计表（质检/物料/外协/排产）';

-- ============================================================
-- ↓ 回滚
-- ============================================================
-- DROP TABLE IF EXISTS container_center.data_regression_history;
