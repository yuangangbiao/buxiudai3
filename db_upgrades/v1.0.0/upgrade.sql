-- 数据库升级脚本
-- 版本: 1.0.0
-- 时间: 2026-05-04 21:39:32
-- 描述: 添加订单归档功能字段（is_archived, archived_at, archived_by, original_status）
--======================================================================

-- 添加订单归档相关字段
ALTER TABLE orders ADD COLUMN is_archived TINYINT(1) DEFAULT 0 COMMENT '是否已归档' AFTER version;

ALTER TABLE orders ADD COLUMN archived_at DATETIME DEFAULT NULL COMMENT '归档时间' AFTER is_archived;

ALTER TABLE orders ADD COLUMN archived_by VARCHAR(50) DEFAULT NULL COMMENT '归档操作人' AFTER archived_at;

ALTER TABLE orders ADD COLUMN original_status VARCHAR(32) DEFAULT NULL COMMENT '归档前的原始状态' AFTER archived_by;

CREATE INDEX idx_orders_is_archived ON orders(is_archived);

CREATE INDEX idx_orders_archived_at ON orders(archived_at);