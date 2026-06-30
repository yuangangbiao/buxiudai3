-- 回滚脚本 2026-05-03 22:43:02
-- 表名: audit_logs
-- 新增字段: timestamp, entity_type, entity_id, before_data, after_data, remark, ip_address, extra_info
-- 变更字段: operator, action

-- 回滚SQL:
ALTER TABLE `audit_logs` DROP COLUMN `timestamp`;
ALTER TABLE `audit_logs` DROP COLUMN `entity_type`;
ALTER TABLE `audit_logs` DROP COLUMN `entity_id`;
ALTER TABLE `audit_logs` DROP COLUMN `before_data`;
ALTER TABLE `audit_logs` DROP COLUMN `after_data`;
ALTER TABLE `audit_logs` DROP COLUMN `remark`;
ALTER TABLE `audit_logs` DROP COLUMN `ip_address`;
ALTER TABLE `audit_logs` DROP COLUMN `extra_info`;
-- operator 的变更需要手动回滚，请查看备份文件
-- action 的变更需要手动回滚，请查看备份文件
