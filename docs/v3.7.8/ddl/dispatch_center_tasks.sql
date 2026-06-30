-- ============================================================================
-- [v3.7.8] dispatch_center_tasks 表 DDL
-- 创建日期: 2026-06-25
-- 用途: 替代 publisher.py 的内存 Dict 存储
-- 数据库: container_center (CONTAINER_MYSQL_CFG.database)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dispatch_center_tasks (
    id          VARCHAR(64)  NOT NULL                COMMENT '任务 ID (order_no + suffix 或 UUID)',
    type        VARCHAR(32)  NOT NULL                COMMENT '任务类型: report / material / quality / task_recall',
    payload     JSON         NOT NULL                COMMENT '任务完整 payload (json.dumps)',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            COMMENT '创建时间',
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP
                                            COMMENT '更新时间',

    PRIMARY KEY (id),
    INDEX idx_type (type),
    INDEX idx_created_at (created_at),
    INDEX idx_type_created (type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='dispatch_center 任务存储 (v3.7.8 替代内存 Dict)';

-- 验证:
--   SELECT id, type, created_at FROM dispatch_center_tasks ORDER BY created_at DESC LIMIT 10;
--   SELECT type, COUNT(*) FROM dispatch_center_tasks GROUP BY type;
