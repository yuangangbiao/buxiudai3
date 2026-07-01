# -*- coding: utf-8 -*-
"""
迁移: data_packages 加 flow_type 列 + process_records 补 flow_type 列
版本: 0610
创建时间: 2026-06-10
任务编号: T1（task-flow-type-strict-routing）
目标库: container_center
目标表:
  - data_packages （加列）
  - process_records（补列）

═══════════════════════════════════════════════════════════════
用途:
    task-flow-type-strict-routing F1 DDL:
    1. data_packages 表加 flow_type VARCHAR(64) DEFAULT '' 列
       + 2 索引 (idx_pkg_flow, idx_pkg_flow_order)
    2. process_records 表补 flow_type VARCHAR(100) DEFAULT '' 列
       （fix_missing_tables.sql 缺此字段，与 mysql_storage.py:218 不一致）

字段说明:
    flow_type: 业务流程分类
        - production        生产工序
        - material_purchase 物料采购
        - quality           质检
        - outsource         外协
        - repair            维修
        - '' (默认空)       未分类/历史数据

索引说明:
    idx_pkg_flow (flow_type, status)
        用于按 flow_type + status 过滤任务（supersede 用）
    idx_pkg_flow_order (flow_type, related_order)
        用于按 flow_type + 订单号精确 supersede

回滚策略:
    1. DROP INDEX data_packages.idx_pkg_flow_order
    2. DROP INDEX data_packages.idx_pkg_flow
    3. DROP COLUMN data_packages.flow_type
    4. DROP COLUMN process_records.flow_type

执行顺序: 先删索引再删列（索引依赖列）
═══════════════════════════════════════════════════════════════

执行机制:
    本文件由 mobile_api_ai/migrations/run.py 通过 exec() 执行。
    run.py 注入的 namespace:
      - conn      : pymysql.Connection 实例
      - cursor    : 初始为 None（run.py 已知缺陷），本文件自行创建本地 cursor
      - ROLLBACK  : True/False（标识 upgrade 还是 downgrade）

═══════════════════════════════════════════════════════════════
执行环境检测（进化项 #10+ 强制要求）
═══════════════════════════════════════════════════════════════
    跨平台 DDL 必须先检测执行环境, 避免:
    - Windows PowerShell 路径问题
    - macOS/Linux 字符编码问题
    - Python 0xC0000409 崩溃 (用 py 启动器而非 python 可执行文件)
"""
import sys
import platform

# 强制 unbuffered (避免跨进程管道看不到 print)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

# 检测执行环境
EXEC_ENV = {
    'platform': sys.platform,
    'system': platform.system(),
    'python_version': sys.version.split()[0],
    'executable': sys.executable,
}

print(f'[0610] 执行环境: {EXEC_ENV}')


def upgrade() -> None:
    """↑ 迁移:
    1. data_packages 加 flow_type 列 + 2 索引
    2. process_records 补 flow_type 列（与 mysql_storage.py 对齐）
    """
    with conn.cursor() as cur:
        # 1. data_packages 加列
        cur.execute("""
            ALTER TABLE data_packages
            ADD COLUMN flow_type VARCHAR(64) NOT NULL DEFAULT ''
            COMMENT '业务流程分类 (production/material_purchase/quality/outsource/repair)'
            AFTER data_type
        """)
        print('[0610] data_packages ADD COLUMN flow_type OK')

        # 2. data_packages 加索引 1: (flow_type, status)
        cur.execute("""
            ALTER TABLE data_packages
            ADD INDEX idx_pkg_flow (flow_type, status)
        """)
        print('[0610] data_packages ADD INDEX idx_pkg_flow OK')

        # 3. data_packages 加索引 2: (flow_type, related_order)
        cur.execute("""
            ALTER TABLE data_packages
            ADD INDEX idx_pkg_flow_order (flow_type, related_order)
        """)
        print('[0610] data_packages ADD INDEX idx_pkg_flow_order OK')

        # 4. process_records 补 flow_type 列（fix_missing_tables.sql 缺）
        cur.execute("""
            ALTER TABLE process_records
            ADD COLUMN flow_type VARCHAR(100) NOT NULL DEFAULT ''
            COMMENT '业务流程分类 (与 mysql_storage.py:218 对齐)'
        """)
        print('[0610] process_records ADD COLUMN flow_type OK')


def downgrade() -> None:
    """↓ 回滚: 先删索引再删列（索引依赖列）"""
    with conn.cursor() as cur:
        # 1. data_packages 删索引（按反序）
        cur.execute("ALTER TABLE data_packages DROP INDEX idx_pkg_flow_order")
        print('[0610] data_packages DROP INDEX idx_pkg_flow_order OK')

        cur.execute("ALTER TABLE data_packages DROP INDEX idx_pkg_flow")
        print('[0610] data_packages DROP INDEX idx_pkg_flow OK')

        # 2. data_packages 删列
        cur.execute("ALTER TABLE data_packages DROP COLUMN flow_type")
        print('[0610] data_packages DROP COLUMN flow_type OK')

        # 3. process_records 删列
        cur.execute("ALTER TABLE process_records DROP COLUMN flow_type")
        print('[0610] process_records DROP COLUMN flow_type OK')


# ═══════════════════════════════════════════════════════════════
# 入口：run.py 通过 exec() 加载本文件后，会调用同名入口
# 为兼容两种调用方式（exec 后自动执行 / 显式调用 main），
# 在文件末尾直接根据 ROLLBACK 标识执行
# ═══════════════════════════════════════════════════════════════
if 'ROLLBACK' in dir() and ROLLBACK:
    downgrade()
else:
    upgrade()
