-- 回滚脚本 2026-05-03 22:45:04
-- 表名: orders
-- 新增字段: product_remark

-- 回滚SQL:
ALTER TABLE `orders` DROP COLUMN `product_remark`;
