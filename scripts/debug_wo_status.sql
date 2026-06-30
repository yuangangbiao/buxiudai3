-- 使用 MySQL 语法检查数据库
SELECT 'production_orders状态分布' as info;
SELECT status, COUNT(*) as cnt FROM production_orders GROUP BY status;

SELECT 'orders状态分布(非归档)' as info;
SELECT status, COUNT(*) as cnt FROM orders WHERE is_deleted=0 AND COALESCE(is_archived,0)=0 GROUP BY status;

SELECT 'orders状态分布(已归档)' as info;
SELECT status, COUNT(*) as cnt FROM orders WHERE is_deleted=0 AND is_archived=1 GROUP BY status;