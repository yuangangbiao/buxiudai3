-- R13 任务1: 创建 process_code_registry 表
-- 执行时间: 2026-06-11
-- 回滚: DROP TABLE IF EXISTS process_code_registry;

CREATE TABLE process_code_registry (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL COMMENT '工序/物料/质检/外协名称',
  process_code VARCHAR(16) NOT NULL COMMENT '编码，如 P17/PWELD/M01',
  category VARCHAR(32) NOT NULL DEFAULT 'process'
    COMMENT 'process/material/quality/outsource/auxiliary',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_name_category (name, category) COMMENT '同名同类只允许一条',
  UNIQUE KEY uk_code (process_code) COMMENT '编码全局唯一',
  INDEX idx_category (category) COMMENT '按类型快速筛选'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT 'R13: 自定义工序/物料/质检/外协持久化注册表';
