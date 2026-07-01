# -*- coding: utf-8 -*-
"""
数据库索引优化脚本
基于代码查询模式分析生成的索引建议

使用方法：
1. 先在测试环境执行
2. 观察 EXPLAIN 输出确认索引被使用
3. 无问题后再在生产环境执行

执行前请备份数据库！
"""

INDEX_RECOMMENDATIONS = """
-- ============================================================
-- 数据库索引优化建议 - 不锈钢网带跟单系统
-- 生成时间: 2026-05-14
-- 适用版本: MySQL 5.7+ / MariaDB 10.2+
-- ============================================================

-- ============================================================
-- 1. orders 表索引（最核心的高频查询表）
-- ============================================================

-- 索引A: 状态+软删除组合索引（看板、列表页默认筛选）
CREATE INDEX idx_orders_status_deleted ON orders(status, is_deleted);

-- 索引B: 交付日期范围查询
CREATE INDEX idx_orders_delivery_date ON orders(delivery_date);

-- 索引C: 客户名称模糊搜索（注意：LIKE 'abc%' 才能使用索引）
CREATE INDEX idx_orders_customer ON orders(customer_name);

-- 索引D: 产品类型筛选
CREATE INDEX idx_orders_product_type ON orders(product_type);

-- 索引E: 创建时间排序（分页查询）
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- 索引F: 复合索引（看板默认筛选：未完成订单按创建时间排序）
CREATE INDEX idx_orders_kanban ON orders(is_deleted, status, created_at DESC);

-- 索引G: 订单号精确查询
-- 注意：order_no 已有 UNIQUE 约束，已自动创建唯一索引


-- ============================================================
-- 2. process_records 表索引（报工、工序记录）
-- ============================================================

-- 索引A: 工单ID查询（最频繁）
CREATE INDEX idx_process_order_id ON process_records(order_id);

-- 索引B: 生产工单ID查询
CREATE INDEX idx_process_production_id ON process_records(production_id);

-- 索引C: 工序名称+状态查询
CREATE INDEX idx_process_name_status ON process_records(process_name, status);

-- 索引D: 工序日期范围统计
CREATE INDEX idx_process_record_date ON process_records(record_date DESC);

-- 索引E: 工人任务分配
CREATE INDEX idx_process_worker ON process_records(worker, status);


-- ============================================================
-- 3. production_orders 表索引（生产工单）
-- ============================================================

-- 索引A: 订单ID关联查询
CREATE INDEX idx_prod_order_id ON production_orders(order_id);

-- 索引B: 状态筛选
CREATE INDEX idx_prod_status ON production_orders(status);

-- 索引C: 负责人分配
CREATE INDEX idx_prod_assigned ON production_orders(assigned_to, status);

-- 索引D: 计划开始日期排产
CREATE INDEX idx_prod_plan_start ON production_orders(plan_start);


-- ============================================================
-- 4. quality_records 表索引（质检记录）
-- ============================================================

-- 索引A: 订单ID关联
CREATE INDEX idx_quality_order_id ON quality_records(order_id);

-- 索引B: 质检类型筛选
CREATE INDEX idx_quality_type ON quality_records(inspection_type);

-- 索引C: 质检日期统计
CREATE INDEX idx_quality_record_date ON quality_records(record_date DESC);


-- ============================================================
-- 5. shipments 表索引（发货记录）
-- ============================================================

-- 索引A: 订单ID关联
CREATE INDEX idx_ship_order_id ON shipments(order_id);

-- 索引B: 发货日期统计
CREATE INDEX idx_ship_date ON shipments(ship_date DESC);


-- ============================================================
-- 6. status_logs 表索引（状态变更日志）
-- ============================================================

-- 索引A: 订单状态历史（get_order_statistics_detail 中频繁使用）
CREATE INDEX idx_status_logs_order ON status_logs(table_name, record_id, new_status, created_at);

-- 索引B: 按时间清理过期日志
CREATE INDEX idx_status_logs_created ON status_logs(created_at);


-- ============================================================
-- 7. operation_logs 表索引（操作日志）
-- ============================================================

-- 索引A: 操作人+时间范围
CREATE INDEX idx_oplogs_operator ON operation_logs(operator, created_at DESC);

-- 索引B: 按时间清理过期日志
CREATE INDEX idx_oplogs_created ON operation_logs(created_at);


-- ============================================================
-- 8. inventory 表索引（库存）
-- ============================================================

-- 索引A: 产品类型+仓库筛选
CREATE INDEX idx_inv_product_warehouse ON inventory(product_type, warehouse);

-- 索引B: 库存预警
CREATE INDEX idx_inv_quantity_low ON inventory(quantity);


-- ============================================================
-- 9. customers 表索引（客户管理）
-- ============================================================

-- 索引A: 客户名称搜索
CREATE INDEX idx_customers_name ON customers(customer_name);

-- 索引B: 客户分组
CREATE INDEX idx_customers_group ON customers(customer_group);


-- ============================================================
-- 10. alert_records 表索引（预警记录）
-- ============================================================

-- 索引A: 未处理预警
CREATE INDEX idx_alerts_pending ON alert_records(is_resolved, created_at DESC);
"""

DROP_INDEX_TEMPLATE = """
-- ============================================================
-- 删除不再需要的索引（如果有）
-- ============================================================
-- ALTER TABLE orders DROP INDEX idx_orders_old_index;
"""


def generate_mysql_script():
    """生成MySQL可执行脚本"""
    script = """-- ============================================================
-- 数据库索引优化脚本
-- 不锈钢网带跟单系统
-- 执行前请备份数据库！
-- ============================================================

-- 开启事务确保原子性
START TRANSACTION;

-- 添加索引（使用 IF NOT EXISTS 避免重复创建报错）
-- 如果你的MySQL版本不支持 IF NOT EXISTS，注释掉对应行

"""
    script += INDEX_RECOMMENDATIONS

    script += """

-- 验证索引创建
SHOW INDEX FROM orders;
SHOW INDEX FROM process_records;
SHOW INDEX FROM production_orders;

-- 提交事务
COMMIT;

-- ============================================================
-- 验证查询是否使用索引
-- ============================================================

-- 验证 orders 看板查询
EXPLAIN SELECT * FROM orders
WHERE is_deleted = 0 AND status NOT IN ('已完成', '已归档', '已取消')
ORDER BY created_at DESC LIMIT 100;

-- 验证 process_records 工序查询
EXPLAIN SELECT * FROM process_records
WHERE order_id = 1
ORDER BY process_seq, id;

-- 验证 status_logs 状态历史查询
EXPLAIN SELECT * FROM status_logs
WHERE table_name = 'orders' AND record_id = 1 AND new_status = 'CONFIRMED'
ORDER BY created_at ASC LIMIT 1;
"""

    return script


def generate_postgresql_script():
    """生成PostgreSQL兼容脚本"""
    script = """-- ============================================================
-- PostgreSQL 索引优化脚本
-- ============================================================

-- orders 表
CREATE INDEX IF NOT EXISTS idx_orders_status_deleted ON orders(status, is_deleted);
CREATE INDEX IF NOT EXISTS idx_orders_delivery_date ON orders(delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_kanban ON orders(is_deleted, status, created_at DESC);

-- process_records 表
CREATE INDEX IF NOT EXISTS idx_process_order_id ON process_records(order_id);
CREATE INDEX IF NOT EXISTS idx_process_production_id ON process_records(production_id);

-- production_orders 表
CREATE INDEX IF NOT EXISTS idx_prod_order_id ON production_orders(order_id);

-- status_logs 表
CREATE INDEX IF NOT EXISTS idx_status_logs_order ON status_logs(table_name, record_id, new_status, created_at);
"""
    return script


if __name__ == '__main__':
    print("=" * 60)
    print("数据库索引优化脚本生成器")
    print("=" * 60)
    print("\n生成了 MySQL 版本脚本，保存到: database_indexes_mysql.sql")
    print("\n重要提示：")
    print("1. 请先在测试环境执行")
    print("2. 使用 EXPLAIN 验证索引被使用")
    print("3. 生产环境执行前务必备份数据库")
    print("=" * 60)

    sql_content = generate_mysql_script()

    with open('database_indexes_mysql.sql', 'w', encoding='utf-8') as f:
        f.write(sql_content)

    print(f"\n已生成: database_indexes_mysql.sql ({len(sql_content)} 字符)")
