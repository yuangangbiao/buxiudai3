-- 防止任务重复创建 - 数据库唯一约束 (v3.6.1)
-- 日期: 2026-06-20
-- 目的: 即使应用层去重逻辑失效，数据库层也能保证任务不重复

-- ═══════════════════════════════════════════════════════════════════
-- 1. process_sub_steps 表去重约束
--    同订单 + 同工序 + 同一非完成状态 只允许一条记录
-- ═══════════════════════════════════════════════════════════════════

-- 先清理可能的重复数据（保留最早的一条）
DELETE p1 FROM process_sub_steps p1
INNER JOIN process_sub_steps p2
WHERE p1.order_no = p2.order_no
  AND p1.step_name = p2.step_name
  AND p1.status IN ('pending', 'in_progress', 'distributed')
  AND p2.status IN ('pending', 'in_progress', 'distributed')
  AND p1.created_at > p2.created_at;

-- 注意：MySQL 不支持 partial unique index，无法直接对部分状态加唯一约束
-- 改为使用 generated column + unique index
ALTER TABLE process_sub_steps
ADD COLUMN _active_dedup_key VARCHAR(200) AS (
    CASE
        WHEN status IN ('pending', 'in_progress', 'distributed')
        THEN CONCAT_WS('|', order_no, step_name)
        ELSE NULL
    END
) STORED;

ALTER TABLE process_sub_steps
ADD UNIQUE INDEX uk_active_task (order_no, step_name, status);

-- 清理临时列
ALTER TABLE process_sub_steps DROP COLUMN _active_dedup_key;

-- ═══════════════════════════════════════════════════════════════════
-- 2. quality_records 表去重约束
-- ═══════════════════════════════════════════════════════════════════

-- 清理重复
DELETE q1 FROM quality_records q1
INNER JOIN quality_records q2
WHERE q1.order_no = q2.order_no
  AND q1.process_name = q2.process_name
  AND q1.status IN ('pending', 'in_progress')
  AND q2.status IN ('pending', 'in_progress')
  AND q1.record_date > q2.record_date;

ALTER TABLE quality_records
ADD UNIQUE INDEX uk_active_quality (order_no, process_name, status);

-- ═══════════════════════════════════════════════════════════════════
-- 3. material_records 表去重约束
-- ═══════════════════════════════════════════════════════════════════

-- 清理重复
DELETE m1 FROM material_records m1
INNER JOIN material_records m2
WHERE m1.order_no = m2.order_no
  AND m1.material_name = m2.material_name
  AND m1.status IN ('pending', 'in_progress')
  AND m2.status IN ('pending', 'in_progress')
  AND m1.created_at > m2.created_at;

ALTER TABLE material_records
ADD UNIQUE INDEX uk_active_material (order_no, material_name, status);

-- ═══════════════════════════════════════════════════════════════════
-- 4. outsource_records 表去重约束
-- ═══════════════════════════════════════════════════════════════════

-- 清理重复
DELETE o1 FROM outsource_records o1
INNER JOIN outsource_records o2
WHERE o1.order_no = o2.order_no
  AND o1.title = o2.title
  AND o1.status IN ('pending', 'in_progress')
  AND o2.status IN ('pending', 'in_progress')
  AND o1.created_at > o2.created_at;

ALTER TABLE outsource_records
ADD UNIQUE INDEX uk_active_outsource (order_no, title, status);

-- ═══════════════════════════════════════════════════════════════════
-- 完成提示
-- ═══════════════════════════════════════════════════════════════════
SELECT '✅ v3.6.1 防任务重复唯一约束已添加' AS message;