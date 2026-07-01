-- 容器中心缺失表补建脚本
-- 数据库: container_center
-- 日期: 2026-05-29（与 storage_mysql.py TABLES_DDL 保持一致）

-- 1. data_packages: 容器中心数据包（来自 SQLite 迁移）
CREATE TABLE IF NOT EXISTS data_packages (
    id VARCHAR(64) PRIMARY KEY,
    data_type VARCHAR(64) NOT NULL COMMENT '数据类型',
    title TEXT COMMENT '标题',
    content TEXT COMMENT '内容',
    source VARCHAR(128) DEFAULT '' COMMENT '数据来源',
    priority VARCHAR(32) DEFAULT 'normal' COMMENT '优先级',
    status VARCHAR(32) DEFAULT '' COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    distributed_at DATETIME DEFAULT NULL COMMENT '分发时间',
    acknowledged_at DATETIME DEFAULT NULL COMMENT '确认时间',
    last_reminded_at DATETIME DEFAULT NULL COMMENT '最后提醒时间',
    completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
    completed_qty INT DEFAULT 0 COMMENT '完成数量',
    progress_qty INT DEFAULT 0 COMMENT '进度数量',
    actual_qty INT DEFAULT 0 COMMENT '实际数量',
    target_operator VARCHAR(64) DEFAULT '' COMMENT '目标操作员',
    operator_id VARCHAR(64) DEFAULT '' COMMENT '操作员ID',
    target_device VARCHAR(64) DEFAULT '' COMMENT '目标设备',
    tags TEXT COMMENT '标签',
    related_order VARCHAR(64) DEFAULT '' COMMENT '关联订单',
    related_process VARCHAR(64) DEFAULT '' COMMENT '关联工序',
    INDEX idx_pkg_type (data_type),
    INDEX idx_pkg_status (status),
    INDEX idx_pkg_operator (target_operator),
    INDEX idx_pkg_created (created_at),
    INDEX idx_pkg_order (related_order),
    UNIQUE INDEX idx_pkg_unique_dispatch (data_type, related_order, related_process)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='容器中心数据包';

-- 2. process_records: 容器中心工序记录（同步自排产）
CREATE TABLE IF NOT EXISTS process_records (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    production_id INT UNSIGNED NOT NULL COMMENT '关联生产单ID',
    order_id INT UNSIGNED DEFAULT NULL COMMENT '关联订单ID',
    process_name VARCHAR(128) NOT NULL COMMENT '工序名称',
    process_code VARCHAR(32) DEFAULT '' COMMENT '工序编码',
    process_seq INT DEFAULT 0 COMMENT '工序顺序',
    display_seq INT DEFAULT 0 COMMENT '展示顺序',
    planned_qty DECIMAL(12,2) DEFAULT 0 COMMENT '计划数量',
    completed_qty DECIMAL(12,2) DEFAULT 0 COMMENT '完成数量',
    qualified_qty DECIMAL(12,2) DEFAULT 0 COMMENT '合格数量',
    status VARCHAR(32) DEFAULT 'pending' COMMENT '状态',
    worker VARCHAR(64) DEFAULT '' COMMENT '操作员',
    unit VARCHAR(20) DEFAULT '件' COMMENT '单位',
    device_remark TEXT COMMENT '设备备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_production_id (production_id),
    INDEX idx_order_id (order_id),
    INDEX idx_process_code (process_code),
    UNIQUE INDEX idx_prod_process (production_id, process_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='容器中心工序记录';

-- 3. enterprise_structure: 企业架构/操作员（单行配置表）
CREATE TABLE IF NOT EXISTS enterprise_structure (
    id INT UNSIGNED PRIMARY KEY DEFAULT 1,
    departments TEXT NOT NULL COMMENT '部门列表JSON',
    users TEXT NOT NULL COMMENT '用户列表JSON',
    operators TEXT DEFAULT NULL COMMENT '操作员配置JSON',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT chk_es_id CHECK (id = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='企业架构配置';

-- 4. process_sub_steps: 工序子步骤
CREATE TABLE IF NOT EXISTS process_sub_steps (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(64) NOT NULL UNIQUE COMMENT 'UUID',
    process_id INT UNSIGNED NOT NULL COMMENT '工序记录ID',
    process_record_id INT UNSIGNED DEFAULT NULL COMMENT '原始工序记录ID',
    order_no VARCHAR(64) DEFAULT '' COMMENT '订单号',
    step_name VARCHAR(128) NOT NULL COMMENT '子步骤名称',
    batch_no VARCHAR(64) DEFAULT '' COMMENT '批次号',
    quantity DECIMAL(12,2) DEFAULT 0 COMMENT '数量',
    qualified_qty DECIMAL(12,2) DEFAULT 0 COMMENT '合格数量',
    operator VARCHAR(64) DEFAULT '' COMMENT '操作员',
    operator_id VARCHAR(64) DEFAULT '' COMMENT '操作员ID',
    wechat_userid VARCHAR(64) DEFAULT '' COMMENT '微信用户ID',
    equipment_name VARCHAR(128) DEFAULT '' COMMENT '设备名称',
    remark TEXT COMMENT '备注',
    record_date DATE DEFAULT NULL COMMENT '记录日期',
    source VARCHAR(32) DEFAULT '' COMMENT '数据来源',
    synced TINYINT(1) DEFAULT 0 COMMENT '是否已同步',
    synced_at DATETIME DEFAULT NULL COMMENT '同步时间',
    overtime_hours DECIMAL(6,2) DEFAULT 0 COMMENT '加班时长',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    created_by VARCHAR(64) DEFAULT '' COMMENT '创建人',
    updated_by VARCHAR(64) DEFAULT '' COMMENT '更新人',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    deleted_at DATETIME DEFAULT NULL COMMENT '删除时间',
    deleted_by VARCHAR(64) DEFAULT '' COMMENT '删除人',
    version INT DEFAULT 1 COMMENT '版本号',
    INDEX idx_process_id (process_id),
    INDEX idx_order_no (order_no),
    INDEX idx_uuid (uuid),
    INDEX idx_is_deleted (is_deleted),
    INDEX idx_step_name (step_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序子步骤';

-- 5. sync_queue: 同步桥接消息队列（SyncBridge Worker 消费）
CREATE TABLE IF NOT EXISTS sync_queue (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(64) NOT NULL COMMENT '订单号',
    step_name VARCHAR(128) NOT NULL COMMENT '工序名称',
    quantity DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '报工数量',
    operator VARCHAR(64) DEFAULT '' COMMENT '操作员',
    process_code VARCHAR(32) DEFAULT '' COMMENT '工序编码',
    status VARCHAR(32) DEFAULT 'pending' COMMENT '状态: pending/retry/completed/failed',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    last_error TEXT COMMENT '最后错误信息',
    enqueued_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入队时间',
    processed_at DATETIME DEFAULT NULL COMMENT '处理完成时间',
    INDEX idx_sq_status (status),
    INDEX idx_sq_enqueued (enqueued_at),
    INDEX idx_sq_order_no (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='同步桥接消息队列';

-- 初始化企业架构默认行
INSERT IGNORE INTO enterprise_structure (id, departments, users, operators, updated_at)
VALUES (1, '[]', '[]', NULL, NOW());
