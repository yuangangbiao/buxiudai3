-- -*- coding: utf-8 -*-
-- 执行 stats_sync_log 建表脚本
-- 在 container_center 库执行
-- 日期: 2026-06-04
-- 用法: mysql -u root -p container_center < stats_sync_log.sql

-- 如果已存在则跳过（IF NOT EXISTS）
DROP TABLE IF EXISTS stats_sync_log;

CREATE TABLE stats_sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    table_type VARCHAR(64) NOT NULL COMMENT '统计表类型',
    period_key VARCHAR(64) NOT NULL COMMENT '周期键: 日期/周次/月份',
    record_count INT NOT NULL DEFAULT 0 COMMENT '本批记录数',
    record_hash VARCHAR(64) NOT NULL COMMENT '记录数据 SHA256（前64位）',
    batch_id VARCHAR(64) NOT NULL COMMENT '批次 UUID',
    sync_status ENUM('success', 'failed', 'pending') NOT NULL DEFAULT 'pending' COMMENT '同步状态',
    smart_sheet_record_ids TEXT COMMENT '智能表格返回的 record_id 列表',
    error_message TEXT COMMENT '失败原因',
    synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
    UNIQUE KEY uk_table_period_batch (table_type, period_key, batch_id),
    KEY idx_table_type (table_type),
    KEY idx_sync_status (sync_status),
    KEY idx_synced_at (synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统计表同步日志';

-- 验证
SELECT '✅ stats_sync_log 表创建成功' AS result;
