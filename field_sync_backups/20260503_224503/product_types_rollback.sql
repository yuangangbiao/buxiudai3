-- 回滚脚本 2026-05-03 22:46:26
-- 表名: product_types
-- 新增字段: description

-- 回滚SQL:
ALTER TABLE `product_types` DROP COLUMN `description`;
