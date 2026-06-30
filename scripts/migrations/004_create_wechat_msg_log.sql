-- R13 任务1: 创建 wechat_msg_log 表（含幂等约束）
-- 执行时间: 2026-06-11
-- 回滚: DROP TABLE IF EXISTS wechat_msg_log;

CREATE TABLE IF NOT EXISTS wechat_msg_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  scenario VARCHAR(64) NOT NULL COMMENT '场景:schedule_notify/workorder_created等',
  tmpl_id VARCHAR(64) NOT NULL,
  content TEXT NOT NULL COMMENT '实际发送内容(含变量替换后)',
  operators JSON DEFAULT NULL COMMENT '接收人列表["张三","李四"]',
  content_hash VARCHAR(64) DEFAULT NULL COMMENT 'SHA256(content)，用于幂等去重',
  msg_hash VARCHAR(64) DEFAULT NULL COMMENT 'SHA256(scenario+"|"+content_hash)，幂等键',
  send_status VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/success/fail',
  sent_at DATETIME DEFAULT NULL COMMENT '实际发送时间(成功后才填)',
  frontend_confirmed_at DATETIME DEFAULT NULL COMMENT '前端确认收到时间(可为空=未确认)',
  retry_count INT DEFAULT 0,
  err_msg TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE INDEX idx_msg_hash (msg_hash) COMMENT '幂等约束：同一scenario+content只允许一条记录',
  INDEX idx_scenario (scenario),
  INDEX idx_status (send_status),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='R13: 微信消息发送日志';
