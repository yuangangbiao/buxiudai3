-- 回滚脚本 2026-05-03 22:46:26
-- 表名: process_records
-- 新增字段: operator, unit

-- 回滚SQL:
ALTER TABLE `process_records` DROP COLUMN `operator`;
ALTER TABLE `process_records` DROP COLUMN `unit`;
