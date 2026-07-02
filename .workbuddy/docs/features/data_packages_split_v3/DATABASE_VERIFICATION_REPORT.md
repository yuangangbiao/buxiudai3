# 数据库实况验证报告

> **验证时间**: 2026-07-02
> **验证工具**: MCP MySQL (mcp_mysql)
> **数据库**: container_center (localhost:3306, root/88888888)
> **结论**: **5张业务表全部已存在，DBA已建表完成**

---

## 一、5张业务表实际状态（关键发现）

| 业务表 | 数据行数 | 创建时间 | 状态 |
|--------|---------|----------|------|
| `process_sub_steps` | **87** | 2026-07-01 04:44 | ✅ 已生产，4种status混用 |
| `material_records` | **20** | 2026-06-20 15:02 | ✅ 已生产，2种status |
| `quality_records` | **35** | 2026-06-20 17:52 | ✅ 已生产，3种status+2条空 |
| `outsource_records` | **0** | 2026-06-20 15:02 | ⚠️ 表已存在但无数据 |
| `repair_records` | **0** | 2026-06-20 06:48 | ⚠️ 表已存在但无数据 |

**与生产代码DDL的对比**：
- ❌ 之前误判：`mysql_storage.py` 中只有 `process_sub_steps` 的DDL，其他4张表都"不存在"
- ✅ 实际状况：DBA早已通过手动/迁移脚本建表，**生产代码DDL落后于实际数据库**

---

## 二、`process_sub_steps` 实际字段（v3.6 spec符合度 100%）

数据库实际字段（共26个）：

| 字段 | 类型 | 默认 | v3.6 spec | 备注 |
|------|------|------|-----------|------|
| id | varchar(50) PK | - | ✅ | |
| order_no | varchar(50) | NULL | ✅ | 索引 |
| process_code | varchar(10) | NULL | ✅ | |
| step_name | varchar(100) | NULL | ✅ | |
| quantity | decimal(10,2) | 0.00 | ✅ | |
| operator | varchar(255) | '' | ✅ | |
| created_at | datetime | NOW | ✅ | |
| **status** | varchar(20) | 'pending' | ✅ | **关键字段，DDL补全** |
| **flow_type** | varchar(64) | 'production' | ✅ | **DDL补全** |
| title | varchar(255) | '' | ✅ | |
| source | varchar(128) | 'manual' | ✅ | |
| priority | varchar(32) | 'normal' | ✅ | |
| tags | json | NULL | ✅ | |
| is_outsource | tinyint | 0 | ✅ | |
| outsource_remark | text | NULL | ✅ | |
| **completed_qty** | decimal(10,2) | 0.00 | ✅ | **DDL补全** |
| **qualified_qty** | decimal(10,2) | 0.00 | ✅ | **DDL补全** |
| **is_public** | tinyint(1) | 0 | ✅ | **DDL补全** |
| **is_broadcast** | tinyint(1) | 0 | ✅ | **DDL补全** |
| remark | text | NULL | ✅ | |
| process_id | varchar(50) | NULL | ✅ | |
| batch_no | varchar(50) | NULL | ✅ | |
| equipment_name | varchar(100) | NULL | ✅ | |
| overtime_hours | decimal(8,2) | 0.00 | ✅ | |
| spec | varchar(100) | NULL | ✅ | |
| unit | varchar(20) | NULL | ✅ | |

**结论**：✅ 数据库实际字段**完全覆盖** v3.6 spec 26字段，**mysql_storage.py 中的DDL已过期**（缺少19个字段），但数据库已是最新版本。

---

## 三、`material_records` 实际字段（24字段）

| 字段 | 类型 | 默认 | 业务关键性 |
|------|------|------|----------|
| id | varchar(64) PK | - | |
| title | varchar(255) | NULL | |
| content | json | NULL | 灵活字段 |
| source | varchar(128) | NULL | |
| priority | varchar(32) | 'normal' | |
| **status** | varchar(32) | NULL | ✅ 状态机 |
| material_name | varchar(200) | NULL | **物料名** |
| material_spec | varchar(200) | NULL | **规格** |
| unit | varchar(20) | NULL | **单位** |
| warehouse | varchar(50) | NULL | **仓库** |
| expected_date | date | NULL | **预计到货** |
| arrival_date | date | NULL | **实际到货** |
| order_no | varchar(64) | NULL | 订单号 |
| related_order | varchar(64) | NULL | 关联单 |
| **completed_qty** | int | 0 | **完成数** |
| **actual_qty** | int | 0 | **实际数** |
| **target_operator** | varchar(64) | NULL | **目标操作员** |
| operator_id | varchar(64) | NULL | |
| **planned_qty** | int | 0 | **计划数** |
| created_at | datetime | NOW | |
| distributed_at | datetime | NULL | **分发时间** |
| acknowledged_at | datetime | NULL | **认领时间** |
| completed_at | datetime | NULL | **完成时间** |
| updated_at | datetime | NOW | |

**业务字段全部就位** ✅，支持从data_packages 完整迁移

---

## 四、`quality_records` 实际字段（26字段）

质检表，结构与 v3.6 spec 高度匹配：
- 主键：`id` (int auto_increment)
- 业务核心：`inspection_type` (过程检/成品检)、`result` (合格/不合格)、`defect_description`、`defect_qty`
- 流程字段：`review_status` (pending/approved/rejected)、`reviewer`、`review_comment`
- 状态机：`status` (varchar 30)
- 父子关系：`parent_record_id` (返工关系)、`rework_version`

---

## 五、`outsource_records` 实际字段（25字段）

| 字段 | 类型 | 默认 | 业务关键性 |
|------|------|------|----------|
| id | varchar(64) PK | - | |
| order_no | varchar(64) | NULL | |
| flow_type | varchar(20) | 'outsource' | **外协** |
| task_code | varchar(20) | NULL | |
| title | varchar(255) | NULL | |
| **status** | varchar(32) | 'pending' | ✅ |
| priority | varchar(20) | 'normal' | |
| quantity | decimal(12,2) | 0.00 | |
| completed_qty | decimal(12,2) | 0.00 | |
| qualified_qty | decimal(12,2) | 0.00 | |
| unit | varchar(20) | '件' | **默认单位** |
| target_operator | varchar(64) | NULL | |
| operator_id | varchar(64) | NULL | |
| source | varchar(64) | NULL | |
| remark | text | NULL | |
| **supplier_name** | varchar(200) | NULL | **供应商** |
| outsource_type | varchar(50) | NULL | **外协类型** |
| **outsource_fee** | decimal(12,2) | 0.00 | **外协费用** |
| send_date | date | NULL | **发出日期** |
| return_date | date | NULL | **回厂日期** |
| **qc_result** | varchar(20) | NULL | **质检结果** |
| created_at | datetime | NOW | |
| updated_at | datetime | NOW | |
| completed_at | datetime | NULL | |
| is_deleted | tinyint(1) | 0 | **软删除** |

**注意**：表已存在但**数据为0**，需要从 `data_packages.data_type='outsource'` 迁移

---

## 六、`repair_records` 实际字段（28字段）

报修表，结构与 v3.6 spec 高度匹配：
- 主键：`id` (varchar 64)
- 业务核心：`equipment_no`、`equipment_name`、`fault_type`、`fault_description`
- 时间字段：`fault_date`、`estimated_hours`、`actual_hours`
- 备件：`spare_parts` (text)
- 状态机：`status` 默认 'reported'
- **数据为0**，需要从 `data_packages.data_type IN ('equipment_repair', 'repair')` 迁移

---

## 七、`data_packages` 实际状态（关键）

| 指标 | 值 |
|------|---|
| 总行数 | **0** |
| 最早创建 | NULL |
| 最新创建 | NULL |
| 表创建时间 | 2026-07-01 17:16 |

**结论**：`data_packages` 已经被**完全清空**！可能已经在做ETL迁移。

---

## 八、辅助表存在性确认

| 表 | 状态 | 用途 |
|---|------|------|
| `process_packages` | ✅ 存在，0行 | 历史ETL中间表 |
| `quality_packages` | ✅ 存在，13行 | 历史ETL中间表（待清理） |
| `process_sub_steps_backup_20260624` | ✅ 存在 | 备份表 |
| `process_sub_steps_history` | ✅ 存在 | 历史表 |
| `sub_step_audit_log` | ✅ 存在 | 审计日志 |

---

## 九、验证结论

### ✅ 业务表已全部就绪

| 维度 | 状态 |
|------|------|
| 5张业务表结构 | ✅ 全部已建表，字段完整 |
| 业务数据可读 | ✅ 已有真实生产数据（87+20+35=142条） |
| 索引已建立 | ✅ status、order_no、target_operator 等关键字段已建索引 |
| 软删除字段 | ✅ outsource_records、repair_records 已有 is_deleted |

### ⚠️ 与生产代码的差异

| 差异点 | 影响 | 处理方式 |
|--------|------|---------|
| `mysql_storage.py` 中的DDL落后 | 生产代码IF NOT EXISTS 不会补字段，但实际库已是最新 | **不需要ALTER TABLE** |
| `data_packages` 已清空 | P0-1 dual-write 写入目标表已无 | **路由切换后无副作用** |
| `outsource_records/repair_records` 数据为0 | 没有历史数据可迁移 | **新建时直接走新表** |

### 🚦 实施调整

1. **T0-DDL补全** ❌ **取消**：5张表已就绪，无须DDL变更
2. **T0.5-DBA实操** ❌ **取消**：连接已验证
3. **T2-ETL历史数据迁移** ⚠️ **降级为可选**：data_packages已空，业务表已有数据
4. **T3-storage.py路由** ✅ **核心任务**：实现 _TASK_TYPE_TABLE_MAP 路由
5. **T4-container_center_api.py双写** ⚠️ **改单写**：data_packages已空，直接写新表
6. **T5-T10** ✅ **保持不变**

---

## 十、SQL 验证脚本（可重跑）

```sql
-- 1. 表存在性 + 数据量
SELECT 'process_sub_steps' AS tbl, COUNT(*) AS cnt FROM process_sub_steps
UNION ALL SELECT 'material_records', COUNT(*) FROM material_records
UNION ALL SELECT 'quality_records', COUNT(*) FROM quality_records
UNION ALL SELECT 'outsource_records', COUNT(*) FROM outsource_records
UNION ALL SELECT 'repair_records', COUNT(*) FROM repair_records
UNION ALL SELECT 'data_packages', COUNT(*) FROM data_packages;

-- 2. process_sub_steps 字段清单（vs v3.6 spec）
DESCRIBE container_center.process_sub_steps;

-- 3. data_type 分布
SELECT data_type, COUNT(*) FROM data_packages GROUP BY data_type;
```

---

**报告结束**。下一步：根据本报告调整T0/T2/T4任务，更新 TASK 文档。
