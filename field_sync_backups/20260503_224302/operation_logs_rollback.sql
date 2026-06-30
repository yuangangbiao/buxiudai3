-- 回滚脚本 2026-05-03 22:43:04
-- 表名: operation_logs
-- 新增字段: order_id, order_no, module, details
-- 变更字段: action, operator, created_at

-- 回滚SQL:
ALTER TABLE `operation_logs` DROP COLUMN `order_id`;
ALTER TABLE `operation_logs` DROP COLUMN `order_no`;
ALTER TABLE `operation_logs` DROP COLUMN `module`;
ALTER TABLE `operation_logs` DROP COLUMN `details`;
-- action 的变更需要手动回滚，请查看备份文件
-- operator 的变更需要手动回滚，请查看备份文件
-- created_at 的变更需要手动回滚，请查看备份文件
