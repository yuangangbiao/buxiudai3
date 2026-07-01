# -*- coding: utf-8 -*-
"""
迁移: work_order_history（产品类型变更审计表）
版本: 0609
创建时间: 2026-06-09
任务编号: T1（workorder-product-type-fix）
目标库: container_center
目标表: work_order_history（新增）

═══════════════════════════════════════════════════════════════
用途:
    记录 work_order 的 product_name / product_type 字段变更历史。
    用于：
    1. 追溯"产品类型被偷偷改"等异常行为
    2. 为 data_regression_history 提供同源审计上下文
    3. 为 C 方案 change_product_type 显式 API 提供落库支撑

字段说明:
    - id              : 自增主键
    - order_no        : 关联工单号（必填，可索引）
    - field_name      : 被审计的字段名（product_name / product_type / customer_name ...）
    - old_value       : 修改前的值（TEXT，兼容任意长度）
    - new_value       : 修改后的值
    - changed_by      : 修改人（operator_id / system / schedule_bot）
    - change_reason   : 修改原因（必填，建议 ≥10 字符的语义化说明）
    - change_source   : 修改来源（api / script / mobile_confirm / register / fix_script ...）
    - changed_at      : 修改时间（DATETIME(3) 毫秒精度）

回滚策略:
    DROP TABLE container_center.work_order_history;
    注：单表新增，rollback 仅 drop table 即可；不会影响其他表。

设计依据:
    - SPEC §2C：work_order_history 表 DDL
    - 借鉴 0608_data_regression_history.sql 的索引模式
    - 使用 IF NOT EXISTS 保证幂等（重复执行不报错）
═══════════════════════════════════════════════════════════════

执行机制:
    本文件由 mobile_api_ai/migrations/run.py 通过 exec() 执行。
    run.py 注入的 namespace:
      - conn      : pymysql.Connection 实例
      - cursor    : 初始为 None（run.py 已知缺陷），本文件自行创建本地 cursor
      - ROLLBACK  : True/False（标识 upgrade 还是 downgrade）
"""


def upgrade() -> None:
    """↑ 迁移：创建 work_order_history 表（MySQL 容器中心库）"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS container_center.work_order_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                order_no VARCHAR(64) NOT NULL COMMENT '关联工单号',
                field_name VARCHAR(64) NOT NULL COMMENT '被审计字段名（product_name 等）',
                old_value TEXT COMMENT '修改前的值',
                new_value TEXT COMMENT '修改后的值',
                changed_by VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人/系统标识',
                change_reason TEXT NOT NULL COMMENT '修改原因（必填，语义化）',
                change_source VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改来源',
                changed_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT '修改时间（毫秒精度）',
                INDEX idx_woh_order_no (order_no),
                INDEX idx_woh_field_name (field_name),
                INDEX idx_woh_changed_at (changed_at),
                INDEX idx_woh_order_field (order_no, field_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='work_order 字段变更审计（产品类型/客户名等）'
        """)


def downgrade() -> None:
    """↓ 回滚：删除 work_order_history 表"""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS container_center.work_order_history")


# ═══════════════════════════════════════════════════════════════
# 入口：run.py 通过 exec() 加载本文件后，会调用同名入口
# 为兼容两种调用方式（exec 后自动执行 / 显式调用 main），
# 在文件末尾直接根据 ROLLBACK 标识执行
# ═══════════════════════════════════════════════════════════════
if 'ROLLBACK' in dir() and ROLLBACK:
    downgrade()
else:
    upgrade()
