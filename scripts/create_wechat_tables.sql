-- 微信报工回调日志表
CREATE TABLE IF NOT EXISTS wechat_callback_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(50) NOT NULL COMMENT '订单号',
    work_order_no VARCHAR(50) COMMENT '工单号',
    process_name VARCHAR(100) COMMENT '工序名称',
    status VARCHAR(20) COMMENT '状态',
    operator VARCHAR(50) COMMENT '操作员',
    remarks TEXT COMMENT '备注',
    received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
    processed TINYINT DEFAULT 0 COMMENT '是否已处理',
    INDEX idx_order_no (order_no),
    INDEX idx_work_order_no (work_order_no),
    INDEX idx_received_at (received_at),
    INDEX idx_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微信报工回调日志';

-- 工序状态变更记录表（用于去重和追溯）
CREATE TABLE IF NOT EXISTS process_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_id INT NOT NULL COMMENT '工序记录ID',
    old_status VARCHAR(20) COMMENT '原状态',
    new_status VARCHAR(20) COMMENT '新状态',
    completed_qty DECIMAL(10,2) DEFAULT 0 COMMENT '完成数量',
    qualified_qty DECIMAL(10,2) DEFAULT 0 COMMENT '合格数量',
    worker VARCHAR(50) COMMENT '操作员',
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
    source VARCHAR(20) DEFAULT 'wechat' COMMENT '来源：wechat/manual/system',
    INDEX idx_record_id (record_id),
    INDEX idx_changed_at (changed_at),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工序状态变更历史';
