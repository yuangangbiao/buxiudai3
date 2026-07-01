-- ============================================================================
-- [v3.7.9] MySQL 初始化脚本 — docker-entrypoint-initdb.d
-- 创建日期: 2026-06-25
-- 用途: 容器启动时自动建库 + 关键表
-- 执行时机: MySQL 容器首次启动时（仅当 /var/lib/mysql 空时）
--
-- 业务表（orders, process_records, data_packages 等）由 utils/auto_schema.py
-- 在应用启动时自动创建（IF NOT EXISTS），此处只需建：
--   1. container_center 库
--   2. dispatch_center_tasks 表（v3.7.8 引入）
-- ============================================================================

-- 1. 创建 container_center 库（如果不存在）
CREATE DATABASE IF NOT EXISTS `container_center`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `container_center`;

-- 2. dispatch_center_tasks 表（v3.7.8 publisher.py 双轨化）
-- 替代 publisher.py 的内存 Dict 存储
-- 详细 DDL 同步见 docs/v3.7.8/ddl/dispatch_center_tasks.sql
CREATE TABLE IF NOT EXISTS `dispatch_center_tasks` (
    `id`         VARCHAR(64)  NOT NULL
        COMMENT '任务 ID (order_no + suffix 或 UUID)',
    `type`       VARCHAR(32)  NOT NULL
        COMMENT '任务类型: report / material / quality / task_recall',
    `payload`    JSON         NOT NULL
        COMMENT '任务完整 payload (json.dumps)',
    `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT '创建时间',
    `updated_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        COMMENT '更新时间',

    PRIMARY KEY (`id`),
    INDEX `idx_type` (`type`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_type_created` (`type`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='dispatch_center 任务存储 (v3.7.8 替代内存 Dict)';

-- 3. 验证
SELECT 'container_center.dispatch_center_tasks created/verified' AS status;
