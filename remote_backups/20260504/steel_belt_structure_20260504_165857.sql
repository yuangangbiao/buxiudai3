-- ===========================================================
-- 数据库结构备份
-- 备份时间: 2026-05-04 16:58:58
-- 远程服务器: 192.168.0.101:3306
-- 数据库: steel_belt
-- 表数量: 58
-- 警告: 此文件仅包含表结构，不包含任何数据！
-- ===========================================================

-- 表结构: steel_belt._migration_history
-- 字段数量: 9

DROP TABLE IF EXISTS `_migration_history`;
CREATE TABLE `_migration_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `migration_id` varchar(50) NOT NULL,
  `migration_name` varchar(200) DEFAULT NULL,
  `executed_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `sql_statements` text,
  `rollback_sql` text,
  `status` enum('success','failed','rolled_back') DEFAULT 'success',
  `error_message` text,
  `checksum` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `migration_id` (`migration_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt._upgrade_history
-- 字段数量: 5

DROP TABLE IF EXISTS `_upgrade_history`;
CREATE TABLE `_upgrade_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `upgrade_version` varchar(50) NOT NULL,
  `applied_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `description` text,
  `status` varchar(20) DEFAULT 'success',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.alert_records
-- 字段数量: 6

DROP TABLE IF EXISTS `alert_records`;
CREATE TABLE `alert_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `alert_type` varchar(50) NOT NULL,
  `record_id` int NOT NULL,
  `is_read` tinyint(1) DEFAULT '0',
  `is_dismissed` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.alert_rules
-- 字段数量: 10

DROP TABLE IF EXISTS `alert_rules`;
CREATE TABLE `alert_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_name` varchar(100) NOT NULL,
  `alert_type` varchar(50) NOT NULL,
  `condition_expr` text NOT NULL,
  `threshold_value` decimal(12,4) DEFAULT NULL,
  `message_template` text,
  `enabled` tinyint(1) DEFAULT '1',
  `priority` int DEFAULT '5',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_alert_type` (`alert_type`),
  KEY `idx_enabled` (`enabled`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.alerts
-- 字段数量: 13

DROP TABLE IF EXISTS `alerts`;
CREATE TABLE `alerts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_id` int DEFAULT NULL,
  `alert_type` varchar(50) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `message` text,
  `severity` varchar(20) DEFAULT 'info',
  `is_read` tinyint(1) DEFAULT '0',
  `is_resolved` tinyint(1) DEFAULT '0',
  `resolved_at` datetime DEFAULT NULL,
  `resolved_by` varchar(50) DEFAULT NULL,
  `related_table` varchar(50) DEFAULT NULL,
  `related_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rule_id` (`rule_id`),
  KEY `idx_is_read` (`is_read`),
  KEY `idx_is_resolved` (`is_resolved`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.approval_records
-- 字段数量: 15

DROP TABLE IF EXISTS `approval_records`;
CREATE TABLE `approval_records` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '审批ID',
  `approver_id` varchar(50) NOT NULL COMMENT '审批人',
  `approver_name` varchar(100) DEFAULT NULL COMMENT '审批人姓名',
  `applicant_id` varchar(50) DEFAULT NULL COMMENT '申请人',
  `approval_type` varchar(50) NOT NULL COMMENT '审批类型',
  `order_id` int NOT NULL COMMENT '关联订单ID',
  `production_id` int DEFAULT NULL COMMENT '关联生产工单ID',
  `process_record_id` int DEFAULT NULL COMMENT '关联工序记录ID',
  `title` varchar(200) NOT NULL COMMENT '标题',
  `content` text COMMENT '内容',
  `status` varchar(20) DEFAULT '待审批' COMMENT '状态',
  `result` varchar(20) DEFAULT NULL COMMENT '结果',
  `comment` varchar(500) DEFAULT NULL COMMENT '审批意见',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_approver` (`approver_id`),
  KEY `idx_applicant` (`applicant_id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='审批记录表';


-- 表结构: steel_belt.attendance
-- 字段数量: 8

DROP TABLE IF EXISTS `attendance`;
CREATE TABLE `attendance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator_id` varchar(50) NOT NULL COMMENT '员工工号',
  `work_order_no` varchar(50) DEFAULT NULL COMMENT '工单号',
  `check_in_time` datetime DEFAULT NULL COMMENT '签到时间',
  `check_out_time` datetime DEFAULT NULL COMMENT '签退时间',
  `work_hours` decimal(8,2) DEFAULT NULL COMMENT '工时',
  `status` varchar(20) DEFAULT '正常' COMMENT '状态',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator_id`),
  KEY `idx_work_order` (`work_order_no`),
  KEY `idx_check_in` (`check_in_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='考勤记录表';


-- 表结构: steel_belt.audit_logs
-- 字段数量: 16

DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action` text NOT NULL,
  `table_name` varchar(50) DEFAULT NULL,
  `record_id` int DEFAULT NULL,
  `old_data` text,
  `new_data` text,
  `operator` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `timestamp` text NOT NULL,
  `entity_type` text NOT NULL,
  `entity_id` text,
  `before_data` text,
  `after_data` text,
  `remark` text,
  `ip_address` text,
  `extra_info` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.bom_list
-- 字段数量: 28

DROP TABLE IF EXISTS `bom_list`;
CREATE TABLE `bom_list` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_type` varchar(50) NOT NULL,
  `material` varchar(50) NOT NULL,
  `steel_weight` decimal(10,2) DEFAULT '0.00',
  `steel_unit` varchar(10) DEFAULT 'kg/米',
  `packaging_materials` text,
  `surface_treatment` text,
  `production_process` text,
  `waste_rate` decimal(5,2) DEFAULT '5.00',
  `unit` varchar(10) DEFAULT '米',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `material_code` varchar(50) DEFAULT NULL COMMENT '物料编码',
  `material_type` varchar(50) DEFAULT NULL COMMENT '物料类型',
  `specification` varchar(100) DEFAULT NULL COMMENT '规格型号',
  `unit_weight` decimal(10,4) DEFAULT NULL COMMENT '单位重量(kg/米)',
  `standard_qty` decimal(10,4) DEFAULT NULL COMMENT '标准用量',
  `actual_qty` decimal(10,4) DEFAULT NULL COMMENT '实际用量',
  `price` decimal(10,2) DEFAULT NULL COMMENT '单价',
  `supplier` varchar(100) DEFAULT NULL COMMENT '供应商',
  `lead_time` int DEFAULT NULL COMMENT '采购周期(天)',
  `safety_stock` decimal(10,4) DEFAULT NULL COMMENT '安全库存',
  `location` varchar(50) DEFAULT NULL COMMENT '仓库位置',
  `batch_no` varchar(50) DEFAULT NULL COMMENT '批次号',
  `expiry_date` date DEFAULT NULL COMMENT '有效期',
  `draw_no` varchar(50) DEFAULT NULL COMMENT '图纸编号',
  `version` varchar(20) DEFAULT NULL COMMENT '版本号',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_product_material` (`product_type`,`material`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.custom_dim_params
-- 字段数量: 4

DROP TABLE IF EXISTS `custom_dim_params`;
CREATE TABLE `custom_dim_params` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `unit` varchar(20) NOT NULL DEFAULT 'mm',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.custom_mat_params
-- 字段数量: 3

DROP TABLE IF EXISTS `custom_mat_params`;
CREATE TABLE `custom_mat_params` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.custom_params
-- 字段数量: 4

DROP TABLE IF EXISTS `custom_params`;
CREATE TABLE `custom_params` (
  `id` int NOT NULL AUTO_INCREMENT,
  `params_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.custom_spec_fields
-- 字段数量: 6

DROP TABLE IF EXISTS `custom_spec_fields`;
CREATE TABLE `custom_spec_fields` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `display_name` varchar(100) DEFAULT NULL,
  `field_type` varchar(20) DEFAULT 'text',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_name` (`name`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.custom_surface_params
-- 字段数量: 7

DROP TABLE IF EXISTS `custom_surface_params`;
CREATE TABLE `custom_surface_params` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL COMMENT '参数名称',
  `display_name` varchar(100) DEFAULT NULL COMMENT '显示名称',
  `description` text COMMENT '描述',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='自定义表面参数表';


-- 表结构: steel_belt.customers
-- 字段数量: 18

DROP TABLE IF EXISTS `customers`;
CREATE TABLE `customers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_code` varchar(20) NOT NULL COMMENT '客户编码',
  `name` varchar(100) NOT NULL COMMENT '客户名称',
  `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
  `phone` varchar(20) DEFAULT NULL COMMENT '联系电话',
  `mobile` varchar(20) DEFAULT NULL COMMENT '手机',
  `address` varchar(255) DEFAULT NULL COMMENT '地址',
  `customer_group` varchar(50) DEFAULT NULL COMMENT '客户分组',
  `credit_limit` decimal(12,2) DEFAULT '0.00' COMMENT '信用额度',
  `payment_days` int DEFAULT '30' COMMENT '账期天数',
  `tax_rate` decimal(5,2) DEFAULT '0.00' COMMENT '税率',
  `bank_name` varchar(100) DEFAULT NULL COMMENT '开户银行',
  `bank_account` varchar(50) DEFAULT NULL COMMENT '银行账号',
  `salesperson` varchar(50) DEFAULT NULL COMMENT '负责业务员',
  `status` varchar(20) DEFAULT '正常' COMMENT '状态：正常/停用',
  `remark` text COMMENT '备注',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `customer_code` (`customer_code`),
  KEY `idx_customer_code` (`customer_code`),
  KEY `idx_customer_name` (`name`),
  KEY `idx_salesperson` (`salesperson`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='客户信息表';


-- 表结构: steel_belt.daily_summary
-- 字段数量: 9

DROP TABLE IF EXISTS `daily_summary`;
CREATE TABLE `daily_summary` (
  `id` int NOT NULL AUTO_INCREMENT,
  `summary_date` date NOT NULL COMMENT '汇总日期',
  `team_id` varchar(50) DEFAULT NULL COMMENT '班组ID',
  `total_orders` int DEFAULT '0' COMMENT '工单数',
  `total_qty` int DEFAULT '0' COMMENT '完成数量',
  `total_hours` decimal(10,2) DEFAULT '0.00' COMMENT '总工时',
  `worker_count` int DEFAULT '0' COMMENT '工人数量',
  `qualified_qty` int DEFAULT '0' COMMENT '合格数量',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_date_team` (`summary_date`,`team_id`),
  KEY `idx_date` (`summary_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='每日汇总表';


-- 表结构: steel_belt.devices
-- 字段数量: 8

DROP TABLE IF EXISTS `devices`;
CREATE TABLE `devices` (
  `device_id` varchar(100) NOT NULL COMMENT '设备ID',
  `device_name` varchar(200) NOT NULL COMMENT '设备名称',
  `device_type` varchar(50) DEFAULT NULL COMMENT '设备类型',
  `location` varchar(200) DEFAULT NULL COMMENT '位置',
  `status` varchar(20) DEFAULT 'normal' COMMENT '状态',
  `last_maintenance` date DEFAULT NULL COMMENT '最后保养日期',
  `next_maintenance` date DEFAULT NULL COMMENT '下次保养日期',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`device_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备表';


-- 表结构: steel_belt.finished_goods
-- 字段数量: 8

DROP TABLE IF EXISTS `finished_goods`;
CREATE TABLE `finished_goods` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `warehouse` varchar(50) DEFAULT '成品仓库',
  `quantity` decimal(10,2) DEFAULT '0.00',
  `unit` varchar(10) DEFAULT '米',
  `in_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `status` varchar(20) DEFAULT '在库',
  `remark` text,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `finished_goods_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.finished_products_stock
-- 字段数量: 12

DROP TABLE IF EXISTS `finished_products_stock`;
CREATE TABLE `finished_products_stock` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_code` varchar(50) NOT NULL COMMENT '产品编码',
  `product_name` varchar(100) NOT NULL COMMENT '产品名称',
  `specification` varchar(100) DEFAULT NULL COMMENT '规格',
  `unit` varchar(20) DEFAULT NULL COMMENT '单位',
  `quantity` decimal(12,2) DEFAULT '0.00' COMMENT '库存数量',
  `warning_threshold` decimal(12,2) DEFAULT '0.00' COMMENT '预警阈值',
  `location` varchar(50) DEFAULT NULL COMMENT '存放位置',
  `remark` text COMMENT '备注',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`product_code`),
  KEY `idx_name` (`product_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='成品库存表';


-- 表结构: steel_belt.inventory
-- 字段数量: 11

DROP TABLE IF EXISTS `inventory`;
CREATE TABLE `inventory` (
  `id` int NOT NULL AUTO_INCREMENT,
  `material_name` varchar(100) NOT NULL,
  `material_type` varchar(50) NOT NULL,
  `specification` varchar(100) DEFAULT NULL,
  `quantity` decimal(10,2) DEFAULT '0.00',
  `unit` varchar(10) DEFAULT 'kg',
  `unit_price` decimal(10,2) DEFAULT '0.00',
  `warehouse` varchar(50) DEFAULT '主仓库',
  `warning_qty` decimal(10,2) DEFAULT '50.00',
  `remark` text,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_material_name` (`material_name`),
  KEY `idx_material_type` (`material_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.inventory_records
-- 字段数量: 10

DROP TABLE IF EXISTS `inventory_records`;
CREATE TABLE `inventory_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `inventory_id` int NOT NULL,
  `order_id` int DEFAULT NULL,
  `record_type` varchar(20) NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `before_qty` decimal(10,2) DEFAULT NULL,
  `after_qty` decimal(10,2) DEFAULT NULL,
  `operator` varchar(50) DEFAULT NULL,
  `remark` text,
  `record_date` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `inventory_id` (`inventory_id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `inventory_records_ibfk_1` FOREIGN KEY (`inventory_id`) REFERENCES `inventory` (`id`),
  CONSTRAINT `inventory_records_ibfk_2` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.logistics_settings
-- 字段数量: 5

DROP TABLE IF EXISTS `logistics_settings`;
CREATE TABLE `logistics_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `setting_key` varchar(100) NOT NULL,
  `setting_value` text,
  `description` varchar(255) DEFAULT NULL,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `setting_key` (`setting_key`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_calc_rules
-- 字段数量: 11

DROP TABLE IF EXISTS `material_calc_rules`;
CREATE TABLE `material_calc_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_type` varchar(50) NOT NULL,
  `material_param` varchar(50) NOT NULL,
  `name` varchar(100) NOT NULL,
  `density` decimal(10,4) DEFAULT NULL,
  `spec_field` text,
  `spec_unit` varchar(20) DEFAULT NULL,
  `qty_formula` text,
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_product_material` (`product_type`,`material_param`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_densities
-- 字段数量: 6

DROP TABLE IF EXISTS `material_densities`;
CREATE TABLE `material_densities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `density` decimal(10,2) NOT NULL,
  `is_preset` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_history
-- 字段数量: 7

DROP TABLE IF EXISTS `material_history`;
CREATE TABLE `material_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `action` varchar(50) NOT NULL,
  `material_name` varchar(100) DEFAULT NULL,
  `detail` text,
  `operator` varchar(50) DEFAULT '系统',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `material_history_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_rules
-- 字段数量: 12

DROP TABLE IF EXISTS `material_rules`;
CREATE TABLE `material_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_type` varchar(50) NOT NULL,
  `material_param` varchar(50) NOT NULL,
  `material_name_template` varchar(100) NOT NULL,
  `spec_field` varchar(50) DEFAULT NULL,
  `spec_unit` varchar(20) DEFAULT NULL,
  `qty_field` varchar(50) DEFAULT NULL,
  `qty_formula` varchar(100) DEFAULT NULL,
  `qty_unit` varchar(20) DEFAULT NULL,
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_type_param` (`product_type`,`material_param`),
  UNIQUE KEY `idx_material_rules_unique` (`product_type`,`material_param`)
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_rules_templates
-- 字段数量: 6

DROP TABLE IF EXISTS `material_rules_templates`;
CREATE TABLE `material_rules_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` text,
  `rules_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.material_stock
-- 字段数量: 13

DROP TABLE IF EXISTS `material_stock`;
CREATE TABLE `material_stock` (
  `id` int NOT NULL AUTO_INCREMENT,
  `material_code` varchar(50) NOT NULL COMMENT '物料编码',
  `material_name` varchar(100) NOT NULL COMMENT '物料名称',
  `material_type` varchar(50) DEFAULT NULL COMMENT '物料类型',
  `specification` varchar(100) DEFAULT NULL COMMENT '规格',
  `unit` varchar(20) DEFAULT NULL COMMENT '单位',
  `quantity` decimal(12,2) DEFAULT '0.00' COMMENT '库存数量',
  `warning_threshold` decimal(12,2) DEFAULT '0.00' COMMENT '预警阈值',
  `location` varchar(50) DEFAULT NULL COMMENT '存放位置',
  `remark` text COMMENT '备注',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`material_code`),
  KEY `idx_name` (`material_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='原材料库存表';


-- 表结构: steel_belt.material_templates
-- 字段数量: 6

DROP TABLE IF EXISTS `material_templates`;
CREATE TABLE `material_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` text,
  `materials_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.messages
-- 字段数量: 9

DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '消息ID',
  `receiver_id` varchar(50) NOT NULL COMMENT '接收人',
  `title` varchar(200) NOT NULL COMMENT '标题',
  `content` text COMMENT '内容',
  `message_type` varchar(50) DEFAULT '通知' COMMENT '消息类型: 通知, 审批, 预警',
  `order_id` int DEFAULT NULL COMMENT '关联订单ID',
  `is_read` tinyint DEFAULT '0' COMMENT '是否已读: 0-未读, 1-已读',
  `read_time` datetime DEFAULT NULL COMMENT '阅读时间',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_receiver` (`receiver_id`),
  KEY `idx_is_read` (`is_read`),
  KEY `idx_order` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='消息通知表';


-- 表结构: steel_belt.operation_logs
-- 字段数量: 13

DROP TABLE IF EXISTS `operation_logs`;
CREATE TABLE `operation_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator` varchar(50) DEFAULT '系统',
  `action` varchar(50) NOT NULL,
  `entity_type` varchar(50) DEFAULT NULL COMMENT '实体类型',
  `entity_id` varchar(50) DEFAULT NULL COMMENT '实体ID',
  `before_data` text COMMENT '操作前数据',
  `after_data` text COMMENT '操作后数据',
  `ip_address` varchar(50) DEFAULT NULL COMMENT 'IP地址',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `order_id` int NOT NULL,
  `order_no` varchar(50) NOT NULL,
  `module` varchar(50) NOT NULL,
  `details` text,
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='操作日志表';


-- 表结构: steel_belt.operator_logs
-- 字段数量: 9

DROP TABLE IF EXISTS `operator_logs`;
CREATE TABLE `operator_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator_id` varchar(50) DEFAULT NULL,
  `operator_name` varchar(50) DEFAULT NULL,
  `action` varchar(100) DEFAULT NULL,
  `target_type` varchar(50) DEFAULT NULL,
  `target_id` varchar(50) DEFAULT NULL,
  `details` text,
  `ip_address` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.operators
-- 字段数量: 10

DROP TABLE IF EXISTS `operators`;
CREATE TABLE `operators` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator_id` varchar(50) NOT NULL,
  `name` varchar(50) NOT NULL,
  `role` varchar(20) DEFAULT '操作员',
  `password` varchar(255) NOT NULL,
  `password_salt` varchar(255) NOT NULL,
  `status` varchar(20) DEFAULT '正常',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `last_login` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `operator_id` (`operator_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.order_logs
-- 字段数量: 7

DROP TABLE IF EXISTS `order_logs`;
CREATE TABLE `order_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `order_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `operator` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '系统',
  `details` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `order_logs_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.order_materials
-- 字段数量: 14

DROP TABLE IF EXISTS `order_materials`;
CREATE TABLE `order_materials` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `material_name` varchar(100) NOT NULL,
  `material_type` varchar(50) DEFAULT '原材料',
  `spec` varchar(100) DEFAULT NULL,
  `required_qty` decimal(10,2) DEFAULT '0.00',
  `prepared_qty` decimal(10,2) DEFAULT '0.00',
  `unit` varchar(10) DEFAULT 'kg',
  `prep_status` varchar(20) DEFAULT '待备料',
  `warehouse` varchar(50) DEFAULT '主仓库',
  `locked` tinyint(1) DEFAULT '1',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_order_material` (`order_id`,`material_name`),
  UNIQUE KEY `idx_order_materials_unique` (`order_id`,`material_name`),
  CONSTRAINT `order_materials_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.order_templates
-- 字段数量: 7

DROP TABLE IF EXISTS `order_templates`;
CREATE TABLE `order_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_type` varchar(50) NOT NULL,
  `template_name` varchar(50) NOT NULL,
  `values_json` text,
  `order_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_type_template` (`product_type`,`template_name`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.orders
-- 字段数量: 41

DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_no` varchar(50) NOT NULL,
  `customer_name` varchar(100) NOT NULL,
  `customer_phone` varchar(20) DEFAULT NULL,
  `customer_address` varchar(255) DEFAULT NULL,
  `customer_group` varchar(50) DEFAULT NULL,
  `product_type` varchar(50) NOT NULL,
  `material` varchar(50) DEFAULT '',
  `mesh_size` decimal(10,2) DEFAULT NULL,
  `wire_diameter` decimal(10,2) DEFAULT NULL,
  `width` decimal(10,2) DEFAULT NULL,
  `length` decimal(10,2) DEFAULT NULL,
  `quantity` int DEFAULT '1',
  `unit` varchar(10) DEFAULT '米',
  `unit_price` decimal(10,2) DEFAULT '0.00',
  `total_amount` decimal(10,2) DEFAULT '0.00',
  `surface_treatment` varchar(50) DEFAULT NULL,
  `special_requirements` text,
  `delivery_date` datetime DEFAULT NULL,
  `status` varchar(20) DEFAULT '待确认',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `extra_params` text,
  `customer_id` int DEFAULT NULL COMMENT '客户ID',
  `salesperson` varchar(50) DEFAULT NULL COMMENT '业务员',
  `contact_person` varchar(50) DEFAULT NULL COMMENT '联系人',
  `priority_level` varchar(10) DEFAULT '中' COMMENT '优先级：高/中/低',
  `cancel_reason` text COMMENT '取消原因',
  `order_source` varchar(20) DEFAULT '线下' COMMENT '订单来源',
  `payment_method` varchar(20) DEFAULT NULL COMMENT '付款方式',
  `invoice_type` varchar(30) DEFAULT NULL COMMENT '发票类型',
  `invoice_status` varchar(20) DEFAULT '未开票' COMMENT '发票状态',
  `invoice_no` varchar(50) DEFAULT NULL COMMENT '发票号码',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  `deleted_by` varchar(50) DEFAULT NULL COMMENT '删除人',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `updated_by` varchar(50) DEFAULT NULL COMMENT '最后更新人',
  `version` int DEFAULT '1' COMMENT '版本号',
  `product_remark` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_no` (`order_no`),
  UNIQUE KEY `idx_orders_order_no` (`order_no`),
  KEY `idx_customer_name` (`customer_name`),
  KEY `idx_product_type` (`product_type`),
  KEY `idx_delivery_date` (`delivery_date`),
  KEY `idx_salesperson` (`salesperson`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.process_calc_rules
-- 字段数量: 11

DROP TABLE IF EXISTS `process_calc_rules`;
CREATE TABLE `process_calc_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `process_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `product_types_json` text COLLATE utf8mb4_unicode_ci,
  `condition_expr` text COLLATE utf8mb4_unicode_ci,
  `planned_qty_formula` text COLLATE utf8mb4_unicode_ci,
  `priority` int DEFAULT '5',
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `default_worker` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '默认负责人',
  `unit` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '件' COMMENT '工序单位',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.process_records
-- 字段数量: 46

DROP TABLE IF EXISTS `process_records`;
CREATE TABLE `process_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `production_id` int DEFAULT NULL,
  `process_name` varchar(50) NOT NULL,
  `process_seq` int DEFAULT '1',
  `planned_qty` int DEFAULT NULL,
  `completed_qty` int DEFAULT '0',
  `qualified_qty` int DEFAULT '0',
  `worker` varchar(50) DEFAULT NULL,
  `work_hours` decimal(10,2) DEFAULT '0.00',
  `status` varchar(20) DEFAULT '待开始',
  `remark` text,
  `record_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `is_outsource` tinyint(1) DEFAULT '0',
  `outsource_remark` text,
  `material_usage` decimal(12,2) DEFAULT '0.00',
  `material_unit` varchar(20) DEFAULT 'kg',
  `planned_start` datetime DEFAULT NULL COMMENT '计划开始时间',
  `planned_end` datetime DEFAULT NULL COMMENT '计划结束时间',
  `actual_pause_minutes` int DEFAULT '0' COMMENT '暂停总时长(分钟)',
  `pause_count` int DEFAULT '0' COMMENT '暂停次数',
  `rework_qty` int DEFAULT '0' COMMENT '返工数量',
  `scrap_qty` int DEFAULT '0' COMMENT '报废数量',
  `efficiency` decimal(5,2) DEFAULT NULL COMMENT '效率百分比',
  `machine_no` varchar(30) DEFAULT NULL COMMENT '机台编号',
  `batch_no` varchar(50) DEFAULT NULL COMMENT '生产批次号',
  `shift` varchar(20) DEFAULT NULL COMMENT '班次：早/中/晚',
  `standard_minutes` int DEFAULT NULL COMMENT '标准工时(分钟)',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `updated_by` varchar(50) DEFAULT NULL COMMENT '更新人',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  `deleted_by` varchar(50) DEFAULT NULL COMMENT '删除人',
  `calculated_qty` decimal(10,4) DEFAULT NULL COMMENT '计算用料量',
  `actual_used_qty` decimal(10,4) DEFAULT NULL COMMENT '实际使用量',
  `waste_rate` decimal(5,2) DEFAULT NULL COMMENT '废品率(%)',
  `setup_time` decimal(5,2) DEFAULT NULL COMMENT '准备时间(小时)',
  `defect_types` text COMMENT '缺陷类型记录',
  `rework_count` int DEFAULT '0' COMMENT '返工次数',
  `start_date` date DEFAULT NULL COMMENT '开始日期',
  `end_date` date DEFAULT NULL COMMENT '结束日期',
  `duration_days` int DEFAULT NULL COMMENT '工序用时(自然天数)',
  `operator` varchar(50) DEFAULT NULL,
  `unit` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `production_id` (`production_id`),
  KEY `idx_batch_no` (`batch_no`),
  KEY `idx_machine_no` (`machine_no`),
  CONSTRAINT `process_records_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=106 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.process_rules
-- 字段数量: 8

DROP TABLE IF EXISTS `process_rules`;
CREATE TABLE `process_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `condition_json` text COLLATE utf8mb4_unicode_ci,
  `action_json` text COLLATE utf8mb4_unicode_ci,
  `priority` int DEFAULT '5',
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.process_rules_templates
-- 字段数量: 9

DROP TABLE IF EXISTS `process_rules_templates`;
CREATE TABLE `process_rules_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `product_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '',
  `conditions_json` text COLLATE utf8mb4_unicode_ci,
  `actions_json` text COLLATE utf8mb4_unicode_ci,
  `priority` int DEFAULT '5',
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.process_templates
-- 字段数量: 5

DROP TABLE IF EXISTS `process_templates`;
CREATE TABLE `process_templates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `data_json` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.product_types
-- 字段数量: 5

DROP TABLE IF EXISTS `product_types`;
CREATE TABLE `product_types` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `is_preset` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.production
-- 字段数量: 12

DROP TABLE IF EXISTS `production`;
CREATE TABLE `production` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL COMMENT '订单ID',
  `process_name` varchar(100) DEFAULT NULL COMMENT '工序名称',
  `scheduled_date` date DEFAULT NULL COMMENT '计划日期',
  `actual_start` timestamp NULL DEFAULT NULL COMMENT '实际开始',
  `actual_end` timestamp NULL DEFAULT NULL COMMENT '实际结束',
  `status` varchar(30) DEFAULT '待开始' COMMENT '状态',
  `operator_id` varchar(50) DEFAULT NULL COMMENT '操作员ID',
  `output_quantity` decimal(10,2) DEFAULT '0.00' COMMENT '产出数量',
  `remark` text COMMENT '备注',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `production_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产记录表';


-- 表结构: steel_belt.production_orders
-- 字段数量: 23

DROP TABLE IF EXISTS `production_orders`;
CREATE TABLE `production_orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `work_order_no` varchar(50) NOT NULL,
  `order_id` int NOT NULL,
  `priority` int DEFAULT '5',
  `plan_start` datetime DEFAULT NULL,
  `plan_end` datetime DEFAULT NULL,
  `actual_start` datetime DEFAULT NULL,
  `actual_end` datetime DEFAULT NULL,
  `assigned_to` varchar(50) DEFAULT NULL,
  `status` varchar(20) DEFAULT '待开始',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  `deleted_by` varchar(50) DEFAULT NULL COMMENT '删除人',
  `created_by` varchar(50) DEFAULT NULL COMMENT '创建人',
  `updated_by` varchar(50) DEFAULT NULL COMMENT '最后更新人',
  `version` int DEFAULT '1' COMMENT '版本号',
  `planned_start_date` datetime DEFAULT NULL COMMENT '计划开始日期',
  `planned_end_date` datetime DEFAULT NULL COMMENT '计划结束日期',
  `actual_start_date` datetime DEFAULT NULL COMMENT '实际开始日期',
  `actual_end_date` datetime DEFAULT NULL COMMENT '实际结束日期',
  PRIMARY KEY (`id`),
  UNIQUE KEY `work_order_no` (`work_order_no`),
  KEY `idx_prod_order_id_new` (`order_id`),
  KEY `idx_production_orders_order_id` (`order_id`),
  CONSTRAINT `production_orders_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.production_stats
-- 字段数量: 32

DROP TABLE IF EXISTS `production_stats`;
CREATE TABLE `production_stats` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL COMMENT '订单ID',
  `production_id` int DEFAULT NULL COMMENT '生产单ID',
  `order_no` varchar(50) DEFAULT NULL COMMENT '订单号',
  `product_type` varchar(50) DEFAULT NULL COMMENT '产品类型',
  `confirm_time` datetime DEFAULT NULL COMMENT '订单确认时间',
  `ship_time` datetime DEFAULT NULL COMMENT '发货时间',
  `receive_time` datetime DEFAULT NULL COMMENT '客户签收时间',
  `order_cycle_days` int DEFAULT NULL COMMENT '订单确认到发货天数',
  `delivery_cycle_days` int DEFAULT NULL COMMENT '发货到签收天数',
  `total_cycle_days` int DEFAULT NULL COMMENT '订单确认到签收总天数',
  `plan_confirm_time` datetime DEFAULT NULL COMMENT '排产确认时间',
  `production_complete_time` datetime DEFAULT NULL COMMENT '生产完成时间',
  `production_cycle_days` int DEFAULT NULL COMMENT '排产到完成天数',
  `total_process_count` int DEFAULT NULL COMMENT '工序总数',
  `avg_process_duration_days` decimal(5,2) DEFAULT NULL COMMENT '平均工序用时(天)',
  `max_process_duration_days` int DEFAULT NULL COMMENT '最长工序用时(天)',
  `min_process_duration_days` int DEFAULT NULL COMMENT '最短工序用时(天)',
  `total_qty` int DEFAULT NULL COMMENT '总数量',
  `qualified_qty` int DEFAULT NULL COMMENT '合格数量',
  `total_qualified_rate` decimal(5,2) DEFAULT NULL COMMENT '总合格率(%)',
  `avg_process_qualified_rate` decimal(5,2) DEFAULT NULL COMMENT '平均工序合格率(%)',
  `total_calculated_qty` decimal(12,4) DEFAULT NULL COMMENT '总计算用料',
  `total_actual_qty` decimal(12,4) DEFAULT NULL COMMENT '总实际用料',
  `total_material_diff` decimal(12,4) DEFAULT NULL COMMENT '总用料差异',
  `avg_material_diff_rate` decimal(5,2) DEFAULT NULL COMMENT '平均用料差异率(%)',
  `total_work_hours` decimal(10,2) DEFAULT NULL COMMENT '总工时(小时)',
  `avg_efficiency` decimal(5,2) DEFAULT NULL COMMENT '平均效率(%)',
  `stats_status` varchar(20) DEFAULT '计算中' COMMENT '统计状态',
  `calculated_at` datetime DEFAULT NULL COMMENT '统计计算时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_production_id` (`production_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_calculated_at` (`calculated_at`),
  CONSTRAINT `production_stats_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `production_stats_ibfk_2` FOREIGN KEY (`production_id`) REFERENCES `production_orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='生产统计数据表';


-- 表结构: steel_belt.quality
-- 字段数量: 11

DROP TABLE IF EXISTS `quality`;
CREATE TABLE `quality` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL COMMENT '订单ID',
  `check_date` date DEFAULT NULL COMMENT '检验日期',
  `inspector` varchar(100) DEFAULT NULL COMMENT '检验员',
  `quantity_checked` decimal(10,2) DEFAULT '0.00' COMMENT '检验数量',
  `qualified_quantity` decimal(10,2) DEFAULT '0.00' COMMENT '合格数量',
  `defective_quantity` decimal(10,2) DEFAULT '0.00' COMMENT '不合格数量',
  `defect_type` varchar(200) DEFAULT NULL COMMENT '不合格类型',
  `result` varchar(20) DEFAULT '待检' COMMENT '检验结果',
  `remark` text COMMENT '备注',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  CONSTRAINT `quality_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质检记录表';


-- 表结构: steel_belt.quality_inspection_records
-- 字段数量: 15

DROP TABLE IF EXISTS `quality_inspection_records`;
CREATE TABLE `quality_inspection_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL COMMENT '订单ID',
  `order_no` varchar(50) DEFAULT NULL COMMENT '订单编号',
  `inspection_type` varchar(30) DEFAULT NULL COMMENT '检验类型',
  `inspection_item` varchar(100) DEFAULT NULL COMMENT '检验项目',
  `standard_value` decimal(10,3) DEFAULT NULL COMMENT '标准值',
  `measured_value` decimal(10,3) DEFAULT NULL COMMENT '实测值',
  `tolerance` decimal(10,3) DEFAULT NULL COMMENT '公差',
  `result` varchar(20) DEFAULT NULL COMMENT '检验结果',
  `inspector` varchar(50) DEFAULT NULL COMMENT '检验员',
  `inspection_time` datetime DEFAULT NULL COMMENT '检验时间',
  `remark` text COMMENT '备注',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '软删除标记',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_inspection_time` (`inspection_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='质量检验记录表';


-- 表结构: steel_belt.quality_record_items
-- 字段数量: 7

DROP TABLE IF EXISTS `quality_record_items`;
CREATE TABLE `quality_record_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `record_id` int NOT NULL,
  `inspection_item` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `measured_value` text COLLATE utf8mb4_unicode_ci,
  `standard_value` text COLLATE utf8mb4_unicode_ci,
  `tolerance` text COLLATE utf8mb4_unicode_ci,
  `is_passed` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `record_id` (`record_id`),
  CONSTRAINT `quality_record_items_ibfk_1` FOREIGN KEY (`record_id`) REFERENCES `quality_records` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.quality_records
-- 字段数量: 13

DROP TABLE IF EXISTS `quality_records`;
CREATE TABLE `quality_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `production_id` int DEFAULT NULL,
  `inspection_type` varchar(20) NOT NULL,
  `inspection_items` text,
  `result` varchar(20) NOT NULL,
  `defect_description` text,
  `defect_qty` int DEFAULT '0',
  `handling_method` text,
  `inspector` varchar(50) DEFAULT NULL,
  `remark` text,
  `record_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `process_name` varchar(50) DEFAULT NULL COMMENT '工序名称',
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `production_id` (`production_id`),
  CONSTRAINT `quality_records_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `quality_records_ibfk_2` FOREIGN KEY (`production_id`) REFERENCES `production_orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.quality_rule_items
-- 字段数量: 5

DROP TABLE IF EXISTS `quality_rule_items`;
CREATE TABLE `quality_rule_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_id` int NOT NULL,
  `inspection_item` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `check_formula` text COLLATE utf8mb4_unicode_ci,
  `tolerance` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `rule_id` (`rule_id`),
  CONSTRAINT `quality_rule_items_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `quality_rules` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.quality_rules
-- 字段数量: 11

DROP TABLE IF EXISTS `quality_rules`;
CREATE TABLE `quality_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `rule_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `process_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `product_types_json` text COLLATE utf8mb4_unicode_ci,
  `condition_expr` text COLLATE utf8mb4_unicode_ci,
  `inspection_items_json` text COLLATE utf8mb4_unicode_ci,
  `check_formula` text COLLATE utf8mb4_unicode_ci,
  `priority` int DEFAULT '5',
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.scan_logs
-- 字段数量: 7

DROP TABLE IF EXISTS `scan_logs`;
CREATE TABLE `scan_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `operator_id` varchar(50) DEFAULT NULL COMMENT '扫码人',
  `scan_type` varchar(20) NOT NULL COMMENT '扫码类型: WO, OP, ORD',
  `scan_content` varchar(200) NOT NULL COMMENT '扫码内容',
  `result` varchar(20) NOT NULL COMMENT '结果: success, fail',
  `error_message` varchar(200) DEFAULT NULL COMMENT '错误信息',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator_id`),
  KEY `idx_scan_type` (`scan_type`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='扫码日志表';


-- 表结构: steel_belt.shipment_tracks
-- 字段数量: 9

DROP TABLE IF EXISTS `shipment_tracks`;
CREATE TABLE `shipment_tracks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shipment_id` int NOT NULL,
  `tracking_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT '0',
  `state_text` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `traces` text COLLATE utf8mb4_unicode_ci,
  `company_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `query_time` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shipment_tracks_shipment_id` (`shipment_id`),
  KEY `idx_shipment_tracks_tracking_no` (`tracking_no`),
  CONSTRAINT `shipment_tracks_ibfk_1` FOREIGN KEY (`shipment_id`) REFERENCES `shipments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 表结构: steel_belt.shipments
-- 字段数量: 19

DROP TABLE IF EXISTS `shipments`;
CREATE TABLE `shipments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shipment_no` varchar(50) NOT NULL,
  `order_id` int NOT NULL,
  `finished_goods_id` int DEFAULT NULL,
  `warehouse` varchar(50) DEFAULT NULL,
  `ship_quantity` decimal(10,2) DEFAULT NULL,
  `unit` varchar(10) DEFAULT '米',
  `logistics_company` varchar(100) DEFAULT NULL,
  `tracking_no` varchar(100) DEFAULT NULL,
  `ship_date` datetime DEFAULT NULL,
  `recipient` varchar(100) DEFAULT NULL,
  `recipient_phone` varchar(20) DEFAULT NULL,
  `recipient_address` varchar(255) DEFAULT NULL,
  `freight` decimal(10,2) DEFAULT '0.00',
  `status` varchar(20) DEFAULT '待发货',
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `shipment_date` date DEFAULT NULL COMMENT '发货日期',
  PRIMARY KEY (`id`),
  UNIQUE KEY `shipment_no` (`shipment_no`),
  UNIQUE KEY `idx_shipments_shipment_no` (`shipment_no`),
  KEY `order_id` (`order_id`),
  KEY `finished_goods_id` (`finished_goods_id`),
  KEY `idx_ship_date` (`ship_date`),
  CONSTRAINT `shipments_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `shipments_ibfk_2` FOREIGN KEY (`finished_goods_id`) REFERENCES `finished_goods` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.status_logs
-- 字段数量: 8

DROP TABLE IF EXISTS `status_logs`;
CREATE TABLE `status_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `table_name` varchar(50) NOT NULL,
  `record_id` int NOT NULL,
  `old_status` varchar(50) DEFAULT NULL,
  `new_status` varchar(50) DEFAULT NULL,
  `operator` varchar(50) DEFAULT NULL,
  `remark` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.surface_treatment_options
-- 字段数量: 5

DROP TABLE IF EXISTS `surface_treatment_options`;
CREATE TABLE `surface_treatment_options` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `is_preset` tinyint(1) DEFAULT '0',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_name` (`name`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 表结构: steel_belt.workreport_records
-- 字段数量: 9

DROP TABLE IF EXISTS `workreport_records`;
CREATE TABLE `workreport_records` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `process_record_id` int NOT NULL COMMENT '工序记录ID',
  `worker_id` varchar(50) NOT NULL COMMENT '报工人工号',
  `report_type` varchar(20) NOT NULL COMMENT '报工类型: START, PROGRESS, COMPLETE',
  `completed_qty` int DEFAULT '0' COMMENT '完成数量',
  `qualified_qty` int DEFAULT '0' COMMENT '合格数量',
  `work_hours` decimal(8,2) DEFAULT '0.00' COMMENT '工时',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `report_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '报工时间',
  PRIMARY KEY (`id`),
  KEY `idx_worker` (`worker_id`),
  KEY `idx_process` (`process_record_id`),
  KEY `idx_report_time` (`report_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='报工记录表';
