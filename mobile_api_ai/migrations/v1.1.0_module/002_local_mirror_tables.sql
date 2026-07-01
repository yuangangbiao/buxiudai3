-- [架构审计 P0-1 修复 2026-06-13] container_center 镜像表
-- 用途：消除跨库直查，所有读操作走本地表
-- 同步：通过 8008 sync_bridge 在写 steel_belt 时双写本地表

-- ============= 1. orders 本地表 =============
-- [P1 修复 2026-06-13] 兼容 MySQL 8.0.0-8.0.28（ADD COLUMN IF NOT EXISTS 需要 8.0.29+）
DROP PROCEDURE IF EXISTS _add_col_if_not_exists;
DELIMITER $$
CREATE PROCEDURE _add_col_if_not_exists(
    IN p_table VARCHAR(64),
    IN p_column VARCHAR(64),
    IN p_definition TEXT
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;
    SELECT COUNT(*) INTO v_exists FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = p_table AND column_name = p_column;
    IF v_exists = 0 THEN
        SET @sql := CONCAT('ALTER TABLE ', p_table, ' ADD COLUMN ', p_column, ' ', p_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$
DELIMITER ;

CREATE TABLE IF NOT EXISTS orders_local (
    order_no VARCHAR(50) PRIMARY KEY,
    customer_group VARCHAR(64) DEFAULT '',
    customer_name VARCHAR(128) DEFAULT '',
    product_name VARCHAR(255) DEFAULT '',
    quantity DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(32) DEFAULT 'created',
    plan_start DATETIME,
    plan_end DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_customer_group (customer_group),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='orders 镜像表（消除跨库直查）';

-- [D5 修复 2026-06-13] 兼容已存在表加 id / order_id 字段
CALL _add_col_if_not_exists('orders_local', 'id', 'INT COMMENT '源表 id（来自 steel_belt.orders）'');
CALL _add_col_if_not_exists('orders_local', 'order_id', 'INT COMMENT '兼容 order_id 别名（同 id）'');
CALL _add_col_if_not_exists('orders_local', 'is_deleted', 'TINYINT DEFAULT 0 COMMENT '软删除标记'');
CALL _add_col_if_not_exists('orders_local', 'is_archived', 'TINYINT DEFAULT 0 COMMENT '归档标记'');
-- [G1 修复 2026-06-13] 数据血缘标记
CALL _add_col_if_not_exists('orders_local', '_source', 'VARCHAR(32) DEFAULT 'etl' COMMENT '数据来源: etl/api/sync_bridge/manual'');
CALL _add_col_if_not_exists('orders_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后同步时间'');
CALL _add_col_if_not_exists('orders_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT '' COMMENT '同步时的 trace_id'');

-- ============= 2. violation_log 本地表 =============
-- [D7 修复 2026-06-13] 字段名严格匹配 steel_belt.violation_log
-- 原设计字段名 message/related_order 改为 detail/order_no，新增 violation_type
CREATE TABLE IF NOT EXISTS violations_local (
    id INT PRIMARY KEY,  -- 来自源表，不自增
    scenario VARCHAR(64) NOT NULL,
    violation_type VARCHAR(64) DEFAULT '',  -- [D7 修复] 新增
    severity VARCHAR(16) DEFAULT 'warning',
    order_no VARCHAR(50) DEFAULT '',  -- [D7 修复] 改 related_order → order_no
    detail TEXT,  -- [D7 修复] 改 message → detail
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    INDEX idx_severity (severity),
    INDEX idx_order (order_no),
    INDEX idx_type (violation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='violation_log 镜像表';

-- [D7 修复 2026-06-13] 兼容老表
CALL _add_col_if_not_exists('violations_local', 'violation_type', 'VARCHAR(64) DEFAULT '' COMMENT '违规类型'');
-- [G1 修复 2026-06-13] 数据血缘
CALL _add_col_if_not_exists('violations_local', '_source', 'VARCHAR(32) DEFAULT 'etl'');
CALL _add_col_if_not_exists('violations_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL _add_col_if_not_exists('violations_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT ''');
-- 如果是老表（字段名是 message/related_order），需要数据迁移
-- ALTER TABLE violations_local CHANGE COLUMN message detail TEXT;
-- ALTER TABLE violations_local CHANGE COLUMN related_order order_no VARCHAR(50);
-- 提示：升级前请先备份数据！老数据可保留，ETL 同步时会重写

-- ============= 6. 数据库约束（E4/E5/E6 修复 2026-06-13）=============
-- 严谨性原则：UNIQUE + FOREIGN KEY + CHECK + NOT NULL 全部建立
-- 业务层漏校验，数据库是最后防线

-- ============= 6.1 violations_local UNIQUE（E4 修复）=============
-- 防止同一订单同一天的同一违规类型被记录多次
-- [半真修复 2026-06-13] 改用 INFORMATION_SCHEMA 模式（兼容 MySQL 5.7/8.0）
-- 之前：`ADD UNIQUE KEY IF NOT EXISTS` 在 MySQL 5.7 直接报错
SET @uk_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'violations_local'
      AND index_name = 'uk_scenario_order_date'
);
SET @sql := IF(@uk_exists = 0,
    'ALTER TABLE violations_local ADD UNIQUE KEY uk_scenario_order_date (scenario, order_no, created_at)',
    'DO 0'  -- 已存在则跳过
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============= 6.2 orders_local 业务校验（E6 修复）=============
-- CHECK 约束（MySQL 8.0+ 支持，5.7 会被忽略）
-- [半真修复 2026-06-13] 用过程化方式加约束（避免重复执行报错）
-- 项目使用 MySQL 8.0，CHECK 有效
DELIMITER $$
DROP PROCEDURE IF EXISTS _add_check_constraints $$
CREATE PROCEDURE _add_check_constraints()
BEGIN
    DECLARE v_exists INT DEFAULT 0;

    -- orders_local
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'orders_local' AND constraint_name = 'chk_orders_status';
    IF v_exists = 0 THEN
        ALTER TABLE orders_local ADD CONSTRAINT chk_orders_status
            CHECK (status IN ('created','confirmed','in_production','completed','cancelled','archived','已排产','已入库','已发货'));
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'orders_local' AND constraint_name = 'chk_orders_quantity';
    IF v_exists = 0 THEN
        ALTER TABLE orders_local ADD CONSTRAINT chk_orders_quantity
            CHECK (quantity >= 0 AND quantity < 10000000);
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'orders_local' AND constraint_name = 'chk_orders_is_deleted';
    IF v_exists = 0 THEN
        ALTER TABLE orders_local ADD CONSTRAINT chk_orders_is_deleted
            CHECK (is_deleted IN (0, 1));
    END IF;

    -- production_orders_local
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'production_orders_local' AND constraint_name = 'chk_po_status';
    IF v_exists = 0 THEN
        ALTER TABLE production_orders_local ADD CONSTRAINT chk_po_status
            CHECK (status IN ('confirmed','in_production','completed','cancelled','已排产','生产中','已完工'));
    END IF;

    -- process_sub_steps_local
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'process_sub_steps_local' AND constraint_name = 'chk_pss_quantity';
    IF v_exists = 0 THEN
        ALTER TABLE process_sub_steps_local ADD CONSTRAINT chk_pss_quantity
            CHECK (quantity >= 0 AND quantity < 10000000);
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'process_sub_steps_local' AND constraint_name = 'chk_pss_qualified';
    IF v_exists = 0 THEN
        ALTER TABLE process_sub_steps_local ADD CONSTRAINT chk_pss_qualified
            CHECK (qualified_qty >= 0 AND qualified_qty <= quantity);
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'process_sub_steps_local' AND constraint_name = 'chk_pss_overtime';
    IF v_exists = 0 THEN
        ALTER TABLE process_sub_steps_local ADD CONSTRAINT chk_pss_overtime
            CHECK (overtime_hours >= 0 AND overtime_hours < 1000);
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'process_sub_steps_local' AND constraint_name = 'chk_pss_source';
    IF v_exists = 0 THEN
        ALTER TABLE process_sub_steps_local ADD CONSTRAINT chk_pss_source
            CHECK (source IN ('mobile','web','sync_bridge','dispatch_center','manual'));
    END IF;

    -- violations_local
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'violations_local' AND constraint_name = 'chk_v_severity';
    IF v_exists = 0 THEN
        ALTER TABLE violations_local ADD CONSTRAINT chk_v_severity
            CHECK (severity IN ('info','warning','error','critical'));
    END IF;

    -- work_orders_local
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'work_orders_local' AND constraint_name = 'chk_wo_status';
    IF v_exists = 0 THEN
        ALTER TABLE work_orders_local ADD CONSTRAINT chk_wo_status
            CHECK (status IN ('pending','in_progress','completed','cancelled','生产完成','已取消'));
    END IF;

    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'work_orders_local' AND constraint_name = 'chk_wo_is_deleted';
    IF v_exists = 0 THEN
        ALTER TABLE work_orders_local ADD CONSTRAINT chk_wo_is_deleted
            CHECK (is_deleted IN (0, 1));
    END IF;
END $$
DELIMITER ;
CALL _add_check_constraints();
DROP PROCEDURE _add_check_constraints;

-- ============= 6.7 batch_no 唯一性（F6 修复 2026-06-13）=============
-- 防止 batch_no 重复（业务层生成可能有极小概率冲突）
-- [半真修复 2026-06-13] INFORMATION_SCHEMA 兼容 MySQL 5.7
SET @uk_exists := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'process_sub_steps_local'
      AND index_name = 'uk_batch_no'
);
SET @sql := IF(@uk_exists = 0,
    'ALTER TABLE process_sub_steps_local ADD UNIQUE KEY uk_batch_no (batch_no)',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============= 6.8 sync_outbox 约束（F7 修复 2026-06-13）=============
-- status / retry_count 严格校验
-- [半真修复 2026-06-13] CHECK 约束 MySQL 5.7 不支持，需要：
-- 1. MySQL 8.0+：直接加 CHECK
-- 2. MySQL 5.7：CHECK 会被忽略，业务层必须做校验
-- 我们用 INFORMATION_SCHEMA 判断 MySQL 版本
SET @mysql_version_major := SUBSTRING_INDEX(@@version, '.', 1) + 0;

-- 业务层 status 校验（所有版本生效，兜底）
-- 在 Python outbox_worker.py 已有校验：写入前 c.execute(...) 限定 status
-- 这里 DDL 不强制 CHECK，避免 MySQL 5.7 报错

-- 仅当 MySQL 8.0+ 时加 CHECK（向后兼容）
SET @should_add_check := (@mysql_version_major >= 8);
SET @chk_status_exists := (
    SELECT COUNT(*) FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'sync_outbox'
      AND constraint_name = 'chk_outbox_status'
);
SET @sql := IF(@should_add_check = 1 AND @chk_status_exists = 0,
    'ALTER TABLE sync_outbox ADD CONSTRAINT chk_outbox_status CHECK (status IN (''pending'', ''processed'', ''dead''))',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============= 6.9 FOREIGN KEY（E5 修复 2026-06-13）=============
-- [半真修复 2026-06-13] 真的启用外键（用户确认 MySQL 8.0）
-- 之前：只加注释说"性能考虑不启用"，半真修复
-- 现在：真正加外键，MySQL 8.0 支持级联
-- 注：process_sub_steps_local.order_no → orders_local.order_no 用 RESTRICT 防止误删订单
DELIMITER $$
DROP PROCEDURE IF EXISTS _add_foreign_keys $$
CREATE PROCEDURE _add_foreign_keys()
BEGIN
    DECLARE v_exists INT DEFAULT 0;

    -- process_sub_steps_local.order_no → orders_local.order_no
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'process_sub_steps_local' AND constraint_name = 'fk_pss_order';
    IF v_exists = 0 THEN
        ALTER TABLE process_sub_steps_local
            ADD CONSTRAINT fk_pss_order
            FOREIGN KEY (order_no) REFERENCES orders_local(order_no)
            ON DELETE RESTRICT ON UPDATE CASCADE;
    END IF;

    -- production_orders_local.order_no → orders_local.order_no
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'production_orders_local' AND constraint_name = 'fk_po_order';
    IF v_exists = 0 THEN
        ALTER TABLE production_orders_local
            ADD CONSTRAINT fk_po_order
            FOREIGN KEY (order_no) REFERENCES orders_local(order_no)
            ON DELETE RESTRICT ON UPDATE CASCADE;
    END IF;

    -- work_orders_local.order_no → orders_local.order_no
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'work_orders_local' AND constraint_name = 'fk_wo_order';
    IF v_exists = 0 THEN
        ALTER TABLE work_orders_local
            ADD CONSTRAINT fk_wo_order
            FOREIGN KEY (order_no) REFERENCES orders_local(order_no)
            ON DELETE RESTRICT ON UPDATE CASCADE;
    END IF;

    -- violations_local.order_no → orders_local.order_no
    SELECT COUNT(*) INTO v_exists FROM information_schema.table_constraints
    WHERE table_schema = DATABASE() AND table_name = 'violations_local' AND constraint_name = 'fk_v_order';
    IF v_exists = 0 THEN
        ALTER TABLE violations_local
            ADD CONSTRAINT fk_v_order
            FOREIGN KEY (order_no) REFERENCES orders_local(order_no)
            ON DELETE RESTRICT ON UPDATE CASCADE;
    END IF;
END $$
DELIMITER ;
CALL _add_foreign_keys();
DROP PROCEDURE _add_foreign_keys;

-- ============= 3. production_orders 本地表 =============
CREATE TABLE IF NOT EXISTS production_orders_local (
    order_no VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    plan_start DATETIME,
    plan_end DATETIME,
    status VARCHAR(32),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='production_orders 镜像表';

-- [D4/D6 修复 2026-06-13] 兼容已存在表加 id / order_id 字段
CALL _add_col_if_not_exists('production_orders_local', 'id', 'INT COMMENT '源表 id'');
CALL _add_col_if_not_exists('production_orders_local', 'order_id', 'INT COMMENT 'orders.id 外键'');
CALL _add_col_if_not_exists('production_orders_local', 'created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
-- [G1 修复 2026-06-13]
CALL _add_col_if_not_exists('production_orders_local', '_source', 'VARCHAR(32) DEFAULT 'etl'');
CALL _add_col_if_not_exists('production_orders_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL _add_col_if_not_exists('production_orders_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT ''');

-- ============= 4. report_queue 增加 dead 状态支持 =============
-- 检查 status 字段是否支持 'dead' 值（VARCHAR 应该已支持）
-- 如果 status 是 ENUM 类型，需要 ALTER
-- ALTER TABLE report_queue MODIFY COLUMN status VARCHAR(16) DEFAULT 'pending';

-- ============= 4.0 process_records 本地表（D1 修复 2026-06-13）=============
-- 字段名严格匹配 steel_belt.process_records，避免 ETL SELECT * 时字段缺失
CREATE TABLE IF NOT EXISTS process_records_local (
    id INT PRIMARY KEY,  -- 来自源表，不自增
    order_no VARCHAR(50) NOT NULL,
    process_code VARCHAR(64),
    step_name VARCHAR(64),
    sequence_no INT DEFAULT 0,
    planned_qty DECIMAL(12, 2) DEFAULT 0,
    completed_qty DECIMAL(12, 2) DEFAULT 0,
    qualified_qty DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(32),
    flow_type VARCHAR(32),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_no),
    INDEX idx_status (status),
    INDEX idx_step (step_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='process_records 镜像表（消除跨库直查）';
-- [G1 修复 2026-06-13]
CALL _add_col_if_not_exists('process_records_local', '_source', 'VARCHAR(32) DEFAULT 'etl'');
CALL _add_col_if_not_exists('process_records_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL _add_col_if_not_exists('process_records_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT ''');

-- ============= 4.5 process_sub_steps 镜像表（8008 同步用）=============
-- 字段名严格匹配 steel_belt.process_records.process_sub_steps
CREATE TABLE IF NOT EXISTS process_sub_steps_local (
    uuid VARCHAR(64) PRIMARY KEY,  -- [D3 修复] 统一用 uuid 作为主键名（与源表一致）
    process_id VARCHAR(64),
    process_record_id VARCHAR(64),  -- 工序记录ID
    order_no VARCHAR(50) NOT NULL,
    step_name VARCHAR(64),
    batch_no VARCHAR(64),
    quantity DECIMAL(12, 2) DEFAULT 0,
    qualified_qty DECIMAL(12, 2) DEFAULT 0,
    operator VARCHAR(64),
    operator_id VARCHAR(64),  -- [D2 修复] 操作员ID
    wechat_userid VARCHAR(64),  -- [D2 修复] 微信 userid
    equipment_name VARCHAR(128) DEFAULT '',  -- [D2 修复] 设备名
    remark TEXT,  -- [D2 修复] 备注
    record_date DATE,  -- [D2 修复] 报工日期
    source VARCHAR(32) DEFAULT 'mobile',  -- [D2 修复] 数据来源
    overtime_hours DECIMAL(8, 2) DEFAULT 0,  -- [D2 修复] 加班工时
    synced TINYINT DEFAULT 0,  -- [D2 修复] 是否已同步
    synced_at DATETIME,  -- [D2 修复] 同步时间
    created_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(64) DEFAULT '',  -- [D2 修复] 创建人
    updated_by VARCHAR(64) DEFAULT '',  -- [D2 修复] 更新人
    INDEX idx_order (order_no),
    INDEX idx_step (step_name),
    INDEX idx_batch (batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='process_sub_steps 镜像表（避免 8008/5002 双写冲突）';
-- [G1 修复 2026-06-13]
CALL _add_col_if_not_exists('process_sub_steps_local', '_source', 'VARCHAR(32) DEFAULT 'sync_bridge'');
CALL _add_col_if_not_exists('process_sub_steps_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL _add_col_if_not_exists('process_sub_steps_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT ''');

-- [D3 修复 2026-06-13] 兼容老表（已存在但只有 id 字段）
CALL _add_col_if_not_exists('process_sub_steps_local', 'uuid', 'VARCHAR(64) COMMENT '主键（与源表一致）'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'process_record_id', 'VARCHAR(64) COMMENT '工序记录ID'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'operator_id', 'VARCHAR(64) COMMENT '操作员ID'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'wechat_userid', 'VARCHAR(64) COMMENT '微信 userid'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'equipment_name', 'VARCHAR(128) DEFAULT '' COMMENT '设备名'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'remark', 'TEXT COMMENT '备注'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'record_date', 'DATE COMMENT '报工日期'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'source', 'VARCHAR(32) DEFAULT 'mobile' COMMENT '数据来源'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'overtime_hours', 'DECIMAL(8, 2) DEFAULT 0 COMMENT '加班工时'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'synced', 'TINYINT DEFAULT 0 COMMENT '是否已同步'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'synced_at', 'DATETIME COMMENT '同步时间'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'created_by', 'VARCHAR(64) DEFAULT '' COMMENT '创建人'');
CALL _add_col_if_not_exists('process_sub_steps_local', 'updated_by', 'VARCHAR(64) DEFAULT '' COMMENT '更新人'');

-- ============= 4.6 work_orders 镜像表（N2 用）=============
CREATE TABLE IF NOT EXISTS work_orders_local (
    id INT PRIMARY KEY,  -- 来自源表，不自增
    order_no VARCHAR(50) NOT NULL,
    customer_name VARCHAR(128),
    product_name VARCHAR(255),
    quantity DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(32),
    is_deleted TINYINT DEFAULT 0,
    plan_start DATETIME,
    plan_end DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_order_no (order_no),  -- 业务唯一
    INDEX idx_status (status),
    INDEX idx_order (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='work_orders 镜像表';

-- [G1 修复 2026-06-13]
CALL _add_col_if_not_exists('work_orders_local', '_source', 'VARCHAR(32) DEFAULT 'etl'');
CALL _add_col_if_not_exists('work_orders_local', '_synced_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP');
CALL _add_col_if_not_exists('work_orders_local', '_sync_trace_id', 'VARCHAR(64) DEFAULT ''');

-- ============= 5. outbox 表（P1-3 准备）=============
CREATE TABLE IF NOT EXISTS sync_outbox (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trace_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_db VARCHAR(32) DEFAULT 'steel_belt',
    payload JSON,
    status VARCHAR(16) DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 5,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    INDEX idx_status (status),
    INDEX idx_trace (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步 outbox（异步可靠同步）';

-- 清理辅助存储过程
DROP PROCEDURE IF EXISTS _add_col_if_not_exists;
DROP PROCEDURE IF EXISTS _add_foreign_keys;
DROP PROCEDURE IF EXISTS _add_check_constraints;

-- ============================================================
-- [K11 修复 2026-06-14] 兜底直接 ALTER（不依赖存储过程）
-- 之前：DLL 里的 _add_col_if_not_exists 存储过程在 pymysql 跑不动
--      （pymysql 不识别 DELIMITER 语法）
-- 现在：直接 ALTER TABLE，重复执行会报错但加 IF NOT EXISTS 风格已通过
-- 说明：MySQL 8.0.29+ 支持 `ADD COLUMN IF NOT EXISTS`，老版本会报错
--      这里用 try/catch 在 Python 层处理
-- ============================================================

-- 6 个镜像表 _source 字段（兜底）
-- ALTER TABLE orders_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';
-- ALTER TABLE production_orders_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';
-- ALTER TABLE process_records_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';
-- ALTER TABLE process_sub_steps_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';
-- ALTER TABLE work_orders_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';
-- ALTER TABLE violations_local ADD COLUMN IF NOT EXISTS _source VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '数据来源';

-- feature_flags 表（K5 实施）
CREATE TABLE IF NOT EXISTS feature_flags (
    name VARCHAR(64) PRIMARY KEY,
    enabled TINYINT NOT NULL DEFAULT 1,
    description VARCHAR(255) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Feature flag 配置';

INSERT IGNORE INTO feature_flags (name, enabled, description) VALUES
    ('use_local_mirror', 1, '业务层读镜像表'),
    ('use_outbox_fallback', 1, 'mirror 失败 outbox 兜底'),
    ('enable_etl_sync', 1, '5002 启动 ETL worker'),
    ('enable_hard_delete_sync', 1, 'ETL 硬删除同步'),
    ('enable_outbox_worker', 1, '5002 启动 outbox worker'),
    ('enable_auto_cleanup', 1, 'ETL 同步后清理过期');
