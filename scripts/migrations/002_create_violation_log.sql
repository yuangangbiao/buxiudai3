-- R13 任务1: 创建 violation_log 表
-- 执行时间: 2026-06-11
-- 回滚: DROP TABLE IF EXISTS violation_log;

CREATE TABLE IF NOT EXISTS violation_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  scenario VARCHAR(128) NOT NULL COMMENT '触发场景',
  violation_type VARCHAR(64) NOT NULL
    COMMENT '11种违规类型:missing_template/no_scenario/msg_render_fail/send_timeout/retry_exhausted/invalid_receivers/db_write_fail/empty_content/parse_error/template_missing/cloud_api_error',
  severity VARCHAR(16) NOT NULL DEFAULT 'WARN' COMMENT 'WARN/ERROR/CRITICAL',
  order_no VARCHAR(64) DEFAULT NULL COMMENT '关联工单号',
  detail TEXT DEFAULT NULL COMMENT '详细描述',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME DEFAULT NULL COMMENT '处理时间',
  INDEX idx_violation_type (violation_type),
  INDEX idx_scenario (scenario),
  INDEX idx_severity (severity),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='R13: 违规日志';
