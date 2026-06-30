-- 回滚脚本 2026-05-03 22:46:25
-- 表名: process_calc_rules
-- 新增字段: default_worker, unit

-- 回滚SQL:
ALTER TABLE `process_calc_rules` DROP COLUMN `default_worker`;
ALTER TABLE `process_calc_rules` DROP COLUMN `unit`;
