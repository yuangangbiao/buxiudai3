-- 回滚脚本 2026-05-03 22:43:05
-- 表名: orders
-- 新增字段: product_remark

-- 回滚SQL:
ALTER TABLE `orders` DROP COLUMN `product_remark`;
