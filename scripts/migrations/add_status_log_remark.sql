-- v6.0.1 修补：status_change_logs_current 表加 remark 列
-- 配合 log_status_change 函数签名扩展（增加 remark="" 参数）

ALTER TABLE status_change_logs_current
ADD COLUMN remark VARCHAR(500) DEFAULT '' COMMENT '变更备注（v6.0.1）' AFTER operator;

-- 验证
SELECT COUNT(*) AS has_remark
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'status_change_logs_current'
  AND column_name = 'remark';
