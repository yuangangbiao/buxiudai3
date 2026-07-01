-- 迁移脚本：给 steel_belt.process_records 添加 record_type 字段
-- 时间：2026-06-20
-- 目的：与 container_center.process_records 保持结构一致，支持 record_type 过滤

-- 1. 添加 record_type 字段
ALTER TABLE steel_belt.process_records
ADD COLUMN record_type VARCHAR(20) DEFAULT NULL
COMMENT '记录类型: product=产品工序, workflow=工作流节点'
AFTER is_deleted;

-- 2. 为现有记录设置默认值（根据 flow_type 推断）
-- flow_type='production' 的记录 → product
-- 其他 → workflow
UPDATE steel_belt.process_records
SET record_type = CASE
    WHEN flow_type = 'production' THEN 'product'
    ELSE 'workflow'
END
WHERE record_type IS NULL;

-- 3. 添加索引（可选，用于加速 record_type 查询）
-- ALTER TABLE steel_belt.process_records ADD INDEX idx_record_type (record_type);

-- 4. 验证
-- SELECT record_type, COUNT(*) FROM steel_belt.process_records GROUP BY record_type;
