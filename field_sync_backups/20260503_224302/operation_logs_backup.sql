-- 表结构备份 2026-05-03 22:43:04
-- 表名: operation_logs

CREATE TABLE `operation_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator` varchar(100) DEFAULT NULL COMMENT '操作员',
  `action` varchar(100) NOT NULL COMMENT '操作类型',
  `entity_type` varchar(50) DEFAULT NULL COMMENT '实体类型',
  `entity_id` varchar(50) DEFAULT NULL COMMENT '实体ID',
  `before_data` text COMMENT '操作前数据',
  `after_data` text COMMENT '操作后数据',
  `ip_address` varchar(50) DEFAULT NULL COMMENT 'IP地址',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='操作日志表';
