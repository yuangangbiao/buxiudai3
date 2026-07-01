-- ============================================================
-- data_packages 拆表迁移脚本
-- 时间: 2026-06-20
-- 说明: 将 data_packages 表按 data_type 拆分为独立表
-- ============================================================

-- 1. 创建 material_records 表 (物料任务)
CREATE TABLE IF NOT EXISTS container_center.material_records (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255),
    content JSON,
    source VARCHAR(128),
    priority VARCHAR(32) DEFAULT 'normal',
    status VARCHAR(32),
    order_no VARCHAR(64),
    related_order VARCHAR(64),
    completed_qty INT DEFAULT 0,
    actual_qty INT DEFAULT 0,
    target_operator VARCHAR(64),
    operator_id VARCHAR(64),
    planned_qty INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    distributed_at DATETIME,
    acknowledged_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_order_no (order_no),
    INDEX idx_target_operator (target_operator)
);

-- 2. 创建 process_packages 表 (生产任务)
CREATE TABLE IF NOT EXISTS container_center.process_packages (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255),
    content JSON,
    source VARCHAR(128),
    priority VARCHAR(32) DEFAULT 'normal',
    status VARCHAR(32),
    flow_type VARCHAR(20),
    order_no VARCHAR(64),
    related_order VARCHAR(64),
    related_process VARCHAR(64),
    process_code VARCHAR(10),
    process_name VARCHAR(128),
    process_seq INT DEFAULT 0,
    completed_qty INT DEFAULT 0,
    actual_qty INT DEFAULT 0,
    planned_qty INT DEFAULT 0,
    target_operator VARCHAR(64),
    operator_id VARCHAR(64),
    target_device VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    distributed_at DATETIME,
    acknowledged_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_order_no (order_no),
    INDEX idx_process_code (process_code),
    INDEX idx_target_operator (target_operator)
);

-- 3. 创建 quality_packages 表 (质检任务)
CREATE TABLE IF NOT EXISTS container_center.quality_packages (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255),
    content JSON,
    source VARCHAR(128),
    priority VARCHAR(32) DEFAULT 'normal',
    status VARCHAR(32),
    flow_type VARCHAR(20) DEFAULT 'quality',
    order_no VARCHAR(64),
    related_order VARCHAR(64),
    related_process VARCHAR(64),
    process_code VARCHAR(10),
    process_name VARCHAR(128),
    completed_qty INT DEFAULT 0,
    actual_qty INT DEFAULT 0,
    planned_qty INT DEFAULT 0,
    target_operator VARCHAR(64),
    operator_id VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    distributed_at DATETIME,
    acknowledged_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_order_no (order_no),
    INDEX idx_target_operator (target_operator)
);

-- 4. 迁移数据 (已完成)
-- material_request -> material_records: 4 条
-- INSERT INTO container_center.material_records (...) SELECT ... FROM data_packages WHERE data_type='material_request';

-- process_task/process_report/report -> process_packages: 82 条
-- INSERT INTO container_center.process_packages (...) SELECT ... FROM data_packages WHERE data_type IN ('process_task', 'process_report', 'report');

-- quality_task -> quality_packages: 13 条
-- INSERT INTO container_center.quality_packages (...) SELECT ... FROM data_packages WHERE data_type='quality_task';

-- 5. 保留的数据 (不需要迁移)
-- config: 2 条 (系统配置)
-- flow_production: 1 条 (流程定义)
-- flow_step: 7 条 (流程步骤)
-- production: 1 条 (生产数据)

-- 6. 验证查询
-- SELECT COUNT(*) FROM container_center.material_records; -- 应为 4
-- SELECT COUNT(*) FROM container_center.process_packages; -- 应为 82
-- SELECT COUNT(*) FROM container_center.quality_packages; -- 应为 13
-- SELECT COUNT(*) FROM container_center.data_packages WHERE data_type IN ('config', 'flow_production', 'flow_step', 'production'); -- 应为 11
