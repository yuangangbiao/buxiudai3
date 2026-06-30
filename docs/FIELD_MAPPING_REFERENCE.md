# 字段映射参考文档

**生成时间**: 2026-06-21
**用途**: ETL 同步、跨库查询、字段差异参考

---

## 一、核心表字段映射

### 1. process_records - 工序记录表

| 字段 | steel_belt | container_center | 用途 | 同步策略 |
|------|------------|-----------------|------|----------|
| id | ✅ | ✅ | 主键 | 不同步 |
| order_no | ✅ | ✅ | 工单号 | 同步 |
| process_code | ✅ | ✅ | 工序编码 | 同步 |
| step_name | ✅ | ❌ | 步骤名称 | 任务发布特有 |
| process_name | ✅ | ❌ | 工序名称 | 任务发布特有 |
| **quantity** | ❌ | ✅ | 订单数量 | 容器中心特有 |
| **planned_qty** | ✅ | ❌ | 计划数量 | steel_belt 特有 |
| **completed_qty** | ✅ | ❌ | 已完成数量 | steel_belt 特有 |
| status | ✅ | ✅ | 状态 | 增量更新 |
| flow_type | ✅ | ✅ | 流程类型 | 同步 |
| batch_no | ✅ | ✅ | 批次号 | 同步 |
| customer_name | ✅ | ✅ | 客户名称 | 同步 |
| customer_group | ✅ | ✅ | 客户群 | 同步 |
| product_name | ✅ | ✅ | 产品名称 | 同步 |
| **record_id** | ❌ | ✅ | 任务发布记录ID | 任务发布特有 |
| **steps** | ❌ | ✅ | 工序列表JSON | 任务发布特有 |
| **process_code_prefix** | ❌ | ✅ | 工序编码前缀 | 任务发布特有 |
| **plan_start** | ❌ | ✅ | 计划开始日期 | 任务发布特有 |
| **plan_end** | ❌ | ✅ | 计划结束日期 | 任务发布特有 |
| delivery_date | ✅ | ✅ | 交付日期 | 同步 |
| priority | ✅ | ✅ | 优先级 | 同步 |
| worker | ✅ | ❌ | 工人 | steel_belt 特有 |
| operator | ✅ | ❌ | 操作员 | steel_belt 特有 |
| **is_archived** | ❌ | ✅ | 是否归档 | 容器中心特有 |
| **is_deleted** | ✅ | ✅ | 是否删除 | 同步 |
| created_at | ✅ | ✅ | 创建时间 | 不同步 |
| updated_at | ✅ | ✅ | 更新时间 | 增量更新 |

### 2. process_sub_steps - 报工记录表

| 字段 | steel_belt | container_center | 用途 | 同步策略 |
|------|------------|-----------------|------|----------|
| id | ✅ | ✅ | 主键 | 同步 |
| uuid | ✅ | ❌ | 唯一标识 | steel_belt 特有 |
| process_id | ✅ | ❌ | 工序ID | steel_belt 特有 |
| order_no | ✅ | ✅ | 工单号 | 同步 |
| process_code | ✅ | ✅ | 工序编码 | 同步 |
| step_name | ✅ | ✅ | 步骤名称 | 同步 |
| **quantity** | ✅ | ❌ | 报工数量 | steel_belt 特有 |
| **completed_qty** | ❌ | ✅ | 已完成数量 | 容器中心特有 |
| **qualified_qty** | ✅ | ❌ | 合格数量 | steel_belt 特有 |
| operator | ✅ | ✅ | 操作员 | 同步 |
| operator_id | ✅ | ❌ | 操作员ID | steel_belt 特有 |
| batch_no | ✅ | ✅ | 批次号 | 同步 |
| **status** | ❌ | ✅ | 状态 | 容器中心特有 |
| record_date | ✅ | ❌ | 记录日期 | steel_belt 特有 |
| **unit** | ❌ | ✅ | 单位 | 容器中心特有 |
| **spec** | ❌ | ✅ | 规格 | 容器中心特有 |
| **is_outsource** | ❌ | ✅ | 是否外协 | 容器中心特有 |
| synced | ✅ | ❌ | 已同步标记 | steel_belt 特有 |
| synced_at | ✅ | ❌ | 同步时间 | steel_belt 特有 |
| created_at | ✅ | ✅ | 创建时间 | 不同步 |
| updated_at | ✅ | ✅ | 更新时间 | 增量更新 |

---

## 二、ETL 同步策略

### 2.1 INSERT ... ON DUPLICATE KEY UPDATE

```sql
-- 示例：process_records 增量同步
INSERT INTO container_center.process_records
  (id, order_no, status, updated_at)
VALUES
  (%s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  updated_at = VALUES(updated_at);
```

### 2.2 任务发布特有字段保护

以下字段 ETL 不会覆盖：

```python
_TASK_PUBLISH_ONLY_FIELDS = {
    'process_records': [
        'record_id', 'steps', 'process_code_prefix',
        'plan_start', 'plan_end', 'customer_group',
        'product_name', 'quantity', 'unit',
        'customer_name', 'delivery_date', 'priority',
    ],
}
```

### 2.3 白名单配置

```python
_ETL_TABLE_WHITELIST = {
    'process_records': {
        'id', 'order_no', 'process_code', 'status',
        'flow_type', 'batch_no', 'customer_name', 'customer_group',
        'product_name', 'is_deleted', 'updated_at',
    },
    'process_sub_steps': {
        'id', 'order_no', 'process_code', 'step_name',
        'quantity', 'operator', 'batch_no', 'updated_at',
    },
}
```

---

## 三、字段差异影响分析

### 3.1 高风险字段（代码引用 > 100 处）

| 字段 | 引用次数 | 风险 | 建议 |
|------|----------|------|------|
| status | 192 | 🔴 高 | 确保两边同步 |
| operator | 128 | 🔴 高 | 添加映射层 |
| quantity | 96 | 🔴 高 | 确认容器中心用途 |
| completed_qty | 41 | 🟠 中 | 确认 steel_belt 用途 |

### 3.2 低风险字段（代码引用 < 10 处）

| 字段 | 引用次数 | 风险 | 建议 |
|------|----------|------|------|
| record_id | 5 | 🟢 低 | 仅任务发布使用 |
| steps | 3 | 🟢 低 | 仅任务发布使用 |
| unit | 2 | 🟢 低 | 仅容器中心使用 |

---

## 四、故障排查指南

### 4.1 字段不存在错误

```python
# 错误示例
SELECT quantity FROM container_center.process_records  # ❌ 可能失败

# 正确示例
SELECT COALESCE(quantity, 0) FROM container_center.process_records  # ✅ 有默认值
```

### 4.2 ETL 同步失败

1. 检查白名单配置
2. 检查字段类型是否兼容
3. 检查主键是否唯一

---

## 五、维护记录

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-06-21 | 添加 operators_local, quality_records_local 白名单 | 修复审计问题 |
