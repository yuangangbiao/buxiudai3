# 数据库字典

**生成时间**: 2026-06-20
**来源**: 代码中 CREATE TABLE 语句扫描（SQL/Python DDL）
**说明**: 本文档由 scan_ddl.py 自动生成，如有出入请以实际 DDL 文件为准

---

### attendance

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| worker | VARCHAR(200) | NO |  |  |
| check_in | VARCHAR(200) | YES |  |  |
| check_out | VARCHAR(200) | YES |  |  |
| status | VARCHAR(100) | YES | 未签到 |  |
| date | VARCHAR(200) | NO |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### data_collection_records

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| record_type | VARCHAR(64) | NO |  |  |
| data_type | VARCHAR(64) | YES |  |  |
| source_id | VARCHAR(128) | YES |  |  |
| collected_at | DATETIME | YES |  |  |
| data | JSON | YES |  |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### data_flow_logs

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| event_type | VARCHAR(64) | NO |  |  |
| flow_type | VARCHAR(64) | YES |  |  |
| source | VARCHAR(128) | YES |  |  |
| target | VARCHAR(128) | YES |  |  |
| status | VARCHAR(32) | YES |  |  |
| detail | JSON | YES |  |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### data_packages

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | VARCHAR(64) | NO |  |  |
| data_type | VARCHAR(64) | NO |  |  |
| title | TEXT, content TEXT | YES |  |  |
| source | VARCHAR(128) | YES |  |  |
| priority | VARCHAR(32) | YES | normal |  |
| status | VARCHAR(32) | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| distributed_at | DATETIME | YES |  |  |
| acknowledged_at | DATETIME | YES |  |  |
| completed_at | DATETIME | YES |  |  |
| completed_qty | INT | YES | 0 |  |
| actual_qty | INT | YES | 0 |  |
| target_operator | VARCHAR(64) | YES |  |  |
| operator_id | VARCHAR(64) | YES |  |  |
| target_device | VARCHAR(64) | YES |  |  |
| tags | TEXT | YES |  |  |
| related_order | VARCHAR(64) | YES |  |  |
| related_process | VARCHAR(64) | YES |  |  |

---

### enterprise_structure

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | NO |  |  |
| departments | LONGTEXT | YES |  |  |
| users | LONGTEXT | YES |  |  |
| updated_at | DATETIME | YES |  |  |

---

### feature_flags

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| name | VARCHAR(64) | YES |  |  |
| enabled | TINYINT | NO | 1 |  |
| description | VARCHAR(255) | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### import_sessions

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| token | VARCHAR(64) | NO |  | 会话token |
| entity | VARCHAR(50) | NO |  | 导入实体：product/supplier/... |
| file_name | VARCHAR(200) | NO |  |  |
| file_size | INT | NO |  |  |
| total_rows | INT | NO | 0 |  |
| valid_rows | INT | NO | 0 |  |
| invalid_rows | INT | NO | 0 |  |
| status | ENUM('pending','committed','expired') | NO | pending |  |
| error_detail | TEXT DEFAULT | YES | NULL | JSON 错误列表 |
| operator | VARCHAR(50) | NO |  |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| expires_at | DATETIME | NO |  | 过期时间（commit 截止） |
| committed_at | DATETIME DEFAULT | YES | NULL |  |

---

### notification_recipient_preset

**来源**: `003_create_notification_recipient_preset.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| CREATE | TABLE IF | YES |  |  |
| id | INT | YES |  |  |
| scenario | VARCHAR(128) | NO |  | 触发场景 |
| receivers | JSON | NO |  | 接收人列表[ |
| enabled | TINYINT(1) | NO | 1 | 1=启用 0=禁用 |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### notifications

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| user_id | INT DEFAULT | YES | NULL | 用户ID（NULL=全体） |
| type | ENUM('low_stock','stocktake_diff','transfer_complete','transfer_in_transit','system') | NO |  | 通知类型 |
| title | VARCHAR(200) | NO |  |  |
| body | TEXT DEFAULT | YES | NULL |  |
| link | VARCHAR(500) DEFAULT | YES | NULL | 点击跳转URL |
| is_read | TINYINT(1) | NO | 0 |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| read_at | DATETIME DEFAULT | YES | NULL |  |

---

### orders_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| order_no | VARCHAR(50) | YES |  |  |
| customer_group | VARCHAR(64) | YES |  |  |
| customer_name | VARCHAR(128) | YES |  |  |
| product_name | VARCHAR(255) | YES |  |  |
| quantity | DECIMAL(12, 2) | YES | 0 |  |
| status | VARCHAR(32) | YES | created |  |
| plan_start | DATETIME | YES |  |  |
| plan_end | DATETIME | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_code_registry

**来源**: `001_create_process_code_registry.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| name | VARCHAR(128) | NO |  | 工序/物料/质检/外协名称 |
| process_code | VARCHAR(16) | NO |  | 编码，如 P17/PWELD/M01 |
| category | VARCHAR(32) | NO | process |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_records

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | VARCHAR(64) | NO |  |  |
| process_type | VARCHAR(50) | YES | production |  |
| order_no | VARCHAR(100) | YES |  |  |
| product_name | VARCHAR(200) | YES |  |  |
| quantity | DOUBLE | YES | 0 |  |
| unit | VARCHAR(50) | YES |  |  |
| customer_name | VARCHAR(200) | YES |  |  |
| delivery_date | DATE | YES |  |  |
| priority | VARCHAR(50) | YES | normal |  |
| status | VARCHAR(50) | YES | created |  |
| current_step | INT | YES | 0 |  |
| steps | JSON | YES |  |  |
| task_count | INT | YES | 0 |  |
| completed_task_count | INT | YES | 0 |  |
| flow_type | VARCHAR(100) | YES |  |  |
| plan_start | DATE | YES |  |  |
| plan_end | DATE | YES |  |  |
| customer_group | VARCHAR(100) | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_records_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| order_no | VARCHAR(50) | NO |  |  |
| process_code | VARCHAR(64) | YES |  |  |
| step_name | VARCHAR(64) | YES |  |  |
| sequence_no | INT | YES | 0 |  |
| planned_qty | DECIMAL(12, 2) | YES | 0 |  |
| completed_qty | DECIMAL(12, 2) | YES | 0 |  |
| qualified_qty | DECIMAL(12, 2) | YES | 0 |  |
| status | VARCHAR(32) | YES |  |  |
| flow_type | VARCHAR(32) | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_sub_steps

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | VARCHAR(50) | NO |  |  |
| order_no | VARCHAR(50) | YES |  |  |
| process_code | VARCHAR(10) | YES |  |  |
| step_name | VARCHAR(100) | YES |  |  |
| quantity | DECIMAL(10,2) | YES | 0.00 |  |
| operator | VARCHAR(50) | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_sub_steps_history

**来源**: `0607_data_regression.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | BIGINT | YES |  |  |
| original_id | VARCHAR(50) | NO |  | 被覆盖的 sub_steps.id (UUID) |
| order_no | VARCHAR(50) | NO |  |  |
| step_name | VARCHAR(100) | NO |  |  |
| batch_no | VARCHAR(100) | NO |  |  |
| operator_before | VARCHAR(64) | NO |  | 旧操作员 |
| operator_after | VARCHAR(64) | NO |  | 新操作员 |
| old_quantity | DECIMAL(14,4) | NO | 0 |  |
| new_quantity | DECIMAL(14,4) | NO | 0 |  |
| delta_quantity | DECIMAL(14,4) GENERATED ALWAYS AS (new_quantity - old_quantity) STORED | YES |  |  |
| revert_reason | VARCHAR(64) | NO |  | self_correct|self_withdraw|admin_force|admin_withdraw|other_override|desktop_sync |
| reverted_by | VARCHAR(64) | NO |  |  |
| reverted_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### process_sub_steps_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| uuid | VARCHAR(64) | YES |  |  |
| process_id | VARCHAR(64) | YES |  |  |
| process_record_id | VARCHAR(64),  -- 工序记录ID | YES |  |  |
| order_no | VARCHAR(50) | NO |  |  |
| step_name | VARCHAR(64) | YES |  |  |
| batch_no | VARCHAR(64) | YES |  |  |
| quantity | DECIMAL(12, 2) | YES | 0 |  |
| qualified_qty | DECIMAL(12, 2) | YES | 0 |  |
| operator | VARCHAR(64) | YES |  |  |
| operator_id | VARCHAR(64),  -- [D2 修复] 操作员ID | YES |  |  |
| wechat_userid | VARCHAR(64),  -- [D2 修复] 微信 userid | YES |  |  |
| equipment_name | VARCHAR(128) | YES |  |  |
| remark | TEXT,  -- [D2 修复] 备注 | YES |  |  |
| record_date | DATE,  -- [D2 修复] 报工日期 | YES |  |  |
| source | VARCHAR(32) | YES | mobile |  |
| overtime_hours | DECIMAL(8, 2) | YES | 0 |  |
| synced | TINYINT | YES | 0 |  |
| synced_at | DATETIME,  -- [D2 修复] 同步时间 | YES |  |  |
| created_at | DATETIME | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| created_by | VARCHAR(64) | YES |  |  |
| updated_by | VARCHAR(64) | YES |  |  |

---

### production_orders_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| order_no | VARCHAR(50) | YES |  |  |
| product_name | VARCHAR(255) | YES |  |  |
| plan_start | DATETIME | YES |  |  |
| plan_end | DATETIME | YES |  |  |
| status | VARCHAR(32) | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### quality_records

**来源**: `quality_handler.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INTEGER PRIMARY KEY | YES |  |  |
| package_id | TEXT | NO |  |  |
| order_no | TEXT | NO |  |  |
| result | TEXT | YES | pass |  |
| inspection_type | TEXT | YES | 巡检 |  |
| defect_description | TEXT | YES |  |  |
| inspector | TEXT | YES |  |  |
| inspection_items | TEXT | YES | [] |  |
| created_at | TEXT | NO |  |  |
| synced_at | TEXT | YES | (datetime('now |  |

---

### report_queue

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| order_no | VARCHAR(64) | NO |  |  |
| step_name | VARCHAR(128) | NO |  |  |
| quantity | DECIMAL(10,2) | NO |  |  |
| operator | VARCHAR(64) | YES |  |  |
| process_id | VARCHAR(64) | YES |  |  |
| status | VARCHAR(32) | NO | pending |  |
| retry_count | INT | YES | 0 |  |
| max_retries | INT | YES | 3 |  |
| last_error | TEXT | YES |  |  |
| enqueued_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| processed_at | DATETIME | YES |  |  |

---

### return_records

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| order_id | VARCHAR(64) | NO |  |  |
| reason | TEXT | YES |  |  |
| returned_qty | DECIMAL(10,2) | YES | 0.00 |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### scheduler_configs

**来源**: `_core.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| name | TEXT | YES |  |  |
| enabled | INTEGER | NO | 1 |  |
| interval_seconds | INTEGER | NO | 3600 |  |
| updated_at | TEXT | NO | (datetime('now')) |  |

---

### stocktake_items

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| stocktake_id | INT | NO |  |  |
| product_id | INT | NO |  |  |
| expected_qty | DECIMAL(12,2) | NO | 0 | 系统预期数量 |
| actual_qty | DECIMAL(12,2) DEFAULT | YES | NULL | 录入实存数量 |
| diff_qty | DECIMAL(12,2) DEFAULT | YES | NULL | 差异（actual-expected） |
| diff_status | ENUM('pending','normal','abnormal') | NO | pending | 差异状态 |
| is_adjusted | TINYINT(1) | NO | 0 | 是否已调整 |

---

### stocktakes

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| warehouse_id | INT | NO |  | 盘点仓库ID |
| status | ENUM('draft','submitted','adjusted','cancelled') | NO | draft | 状态 |
| tolerance_pct | DECIMAL(5,2) | NO | 0.5 | 差异容差百分比 |
| total_items | INT | NO | 0 | 盘点项总数 |
| matched_items | INT | NO | 0 | 无差异项数 |
| diff_normal | INT | NO | 0 | 容差内差异项数 |
| diff_abnormal | INT | NO | 0 | 容差外差异项数 |
| operator | VARCHAR(50) | NO |  | 创建人 |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| submitted_at | DATETIME DEFAULT | YES | NULL |  |
| adjusted_at | DATETIME DEFAULT | YES | NULL |  |
| remark | TEXT DEFAULT | YES | NULL |  |

---

### sync_log

**来源**: `sync_log.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| event_type | VARCHAR(64) | YES |  |  |
| direction | VARCHAR(16) | YES |  |  |
| record_id | VARCHAR(128) | YES |  |  |
| status | VARCHAR(32) | YES | success |  |
| error_msg | TEXT | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### sync_logs

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| action | VARCHAR(64) | YES |  |  |
| package_id | VARCHAR(64) | YES |  |  |
| detail | TEXT | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### sync_outbox

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| trace_id | VARCHAR(64) | NO |  |  |
| action | VARCHAR(64) | NO |  |  |
| target_db | VARCHAR(32) | YES | steel_belt |  |
| payload | JSON | YES |  |  |
| status | VARCHAR(16) | YES | pending |  |
| retry_count | INT | YES | 0 |  |
| max_retries | INT | YES | 5 |  |
| last_error | TEXT | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| processed_at | DATETIME | YES |  |  |

---

### tbl_alerts

**来源**: `alert_store.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | VARCHAR(64) | YES |  |  |
| alert_type | VARCHAR(255) | NO |  |  |
| doc_id | VARCHAR(255) | YES |  |  |
| title | VARCHAR(255) | NO |  |  |
| content | LONGTEXT | NO |  |  |
| level | VARCHAR(32) | NO | WARNING |  |
| dismissed | INT | YES | 0 |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### tbl_configs

**来源**: `config_store.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| config_name | VARCHAR(128) | YES |  |  |
| config_data | LONGTEXT | NO |  |  |
| version | INTEGER | YES | 1 |  |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### tbl_documents

**来源**: `document_store.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | VARCHAR(64) | YES |  |  |
| doc_type | VARCHAR(64) | NO |  |  |
| doc_data | LONGTEXT | NO |  |  |
| status | VARCHAR(32) | YES | pending |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### tbl_indexes

**来源**: `index_store.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| doc_type | VARCHAR(255) | NO |  |  |
| doc_id | VARCHAR(255) | NO |  |  |
| key_name | VARCHAR(255) | NO |  |  |
| key_value | VARCHAR(255) | NO |  |  |

---

### transfer_items

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| transfer_id | INT | NO |  |  |
| product_id | INT | NO |  |  |
| qty | DECIMAL(12,2) | NO |  | 调拨数量 |

---

### transfers

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| from_warehouse_id | INT | NO |  | 调出仓 |
| to_warehouse_id | INT | NO |  | 调入仓 |
| status | ENUM('in_transit','completed','cancelled') | NO | in_transit | 状态 |
| total_items | INT | NO | 0 |  |
| operator | VARCHAR(50) | NO |  | 发起人 |
| receiver | VARCHAR(50) DEFAULT | YES | NULL | 收货确认人 |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| completed_at | DATETIME DEFAULT | YES | NULL |  |
| cancelled_at | DATETIME DEFAULT | YES | NULL |  |
| cancel_reason | VARCHAR(500) DEFAULT | YES | NULL | 取消原因 |
| remark | TEXT DEFAULT | YES | NULL |  |

---

### users

**来源**: `001_function_optimization.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT PRIMARY KEY | YES |  |  |
| username | VARCHAR(50) | NO |  | 用户名 |
| display_name | VARCHAR(100) DEFAULT | YES | NULL | 显示名 |
| password_hash | VARCHAR(255) | NO |  | PBKDF2 哈希 |
| role | ENUM('admin','operator','viewer') | NO | viewer | 角色 |
| is_active | TINYINT(1) | NO | 1 | 1=启用 0=停用 |
| last_login_at | DATETIME DEFAULT | YES | NULL |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |

---

### violation_log

**来源**: `002_create_violation_log.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | BIGINT | YES |  |  |
| scenario | VARCHAR(128) | NO |  | 触发场景 |
| violation_type | VARCHAR(64) | NO |  |  |
| severity | VARCHAR(16) | NO | WARN | WARN/ERROR/CRITICAL |
| order_no | VARCHAR(64) DEFAULT | YES | NULL | 关联工单号 |
| detail | TEXT DEFAULT | YES | NULL | 详细描述 |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| resolved_at | DATETIME DEFAULT | YES | NULL | 处理时间 |

---

### violations_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| scenario | VARCHAR(64) | NO |  |  |
| violation_type | VARCHAR(64) | YES |  |  |
| severity | VARCHAR(16) | YES | warning |  |
| order_no | VARCHAR(50) | YES |  |  |
| detail | TEXT,  -- [D7 修复] 改 message → detail | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### wal

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| CREATE | TABLE IF | YES | CURRENT_TIMESTAMP |  |

---

### wechat_msg_log

**来源**: `004_create_wechat_msg_log.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | BIGINT | YES |  |  |
| scenario | VARCHAR(64) | NO |  | 场景:schedule_notify/workorder_created等 |
| tmpl_id | VARCHAR(64) | NO |  |  |
| content | TEXT | NO |  | 实际发送内容(含变量替换后) |
| operators | JSON DEFAULT | YES | NULL | 接收人列表[ |
| content_hash | VARCHAR(64) DEFAULT | YES | NULL | SHA256(content)，用于幂等去重 |
| msg_hash | VARCHAR(64) DEFAULT | YES | NULL | SHA256(scenario+ |
| send_status | VARCHAR(16) | YES | pending | pending/success/fail |
| sent_at | DATETIME DEFAULT | YES | NULL | 实际发送时间(成功后才填) |
| frontend_confirmed_at | DATETIME DEFAULT | YES | NULL | 前端确认收到时间(可为空=未确认) |
| retry_count | INT | YES | 0 |  |
| err_msg | TEXT | YES |  |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### work_orders_local

**来源**: `002_local_mirror_tables.sql`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT | YES |  |  |
| order_no | VARCHAR(50) | NO |  |  |
| customer_name | VARCHAR(128) | YES |  |  |
| product_name | VARCHAR(255) | YES |  |  |
| quantity | DECIMAL(12, 2) | YES | 0 |  |
| status | VARCHAR(32) | YES |  |  |
| is_deleted | TINYINT | YES | 0 |  |
| plan_start | DATETIME | YES |  |  |
| plan_end | DATETIME | YES |  |  |
| updated_at | DATETIME | YES | CURRENT_TIMESTAMP |  |
| created_at | DATETIME | YES | CURRENT_TIMESTAMP |  |

---

### workers

**来源**: `mysql_storage.py`


| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|------|------|--------|--------|------|
| id | INT UNSIGNED | YES |  |  |
| enterprise_id | VARCHAR(64) | NO |  |  |
| name | VARCHAR(128) | NO |  |  |
| phone | VARCHAR(32) | YES |  |  |
| role | VARCHAR(64) | YES |  |  |
| department | VARCHAR(128) | YES |  |  |
| status | VARCHAR(32) | YES | active |  |
| sync_at | DATETIME | YES |  |  |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP |  |
| wechat_userid | VARCHAR(64) | YES |  | 企业微信用户ID |
| can_receive_wechat | TINYINT(1) | YES | 1 | 是否接收微信消息 |
| can_send_wechat | TINYINT(1) | YES | 1 | 是否发送微信消息 |
| max_tasks | INT | YES | 10 | 最大任务数 |

---
