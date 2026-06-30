-- R13 任务1: 创建 notification_recipient_preset 表
-- 执行时间: 2026-06-11
-- 回滚: DROP TABLE IF EXISTS notification_recipient_preset;

CREATE TABLE IF NOT EXISTS notification_recipient_preset (
  id INT AUTO_INCREMENT PRIMARY KEY,
  scenario VARCHAR(128) NOT NULL COMMENT '触发场景',
  receivers JSON NOT NULL COMMENT '接收人列表["张三","李四"]',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_scenario (scenario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='R13: 通知接收人全局预设';
