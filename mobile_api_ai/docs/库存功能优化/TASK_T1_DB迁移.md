# TASK-T1: DB 迁移脚本

## 输入契约

**前置依赖**：无
**输入数据**：无
**环境依赖**：
- MySQL 5.7+ / 8.0+
- 已存在 products / suppliers / categories / warehouses / bases / inventory / inventory_transactions / inventory_alerts / operation_logs 表

## 输出契约

**输出数据**：
- 文件：`mobile_api_ai/inventory_web/migrations/001_function_optimization.sql`
- 6 张新表：stocktakes / stocktake_items / transfers / transfer_items / notifications / recycle_bin_log
- 5 张表加字段：products/suppliers/categories/warehouses/bases 加 `deleted_at`
- 4 个索引补充：inventory / inventory_transactions

**验收标准**：
- [ ] SQL 脚本可重复执行（IF NOT EXISTS）
- [ ] 不破坏既有 9 张表的数据
- [ ] 字段类型/默认值与 DESIGN v2.0 一致

## 实现约束

- **技术栈**：MySQL 原生 DDL
- **接口规范**：与 DESIGN v2.0 第三章数据表定义完全一致
- **质量要求**：
  - 所有表用 InnoDB
  - 字符集 utf8mb4
  - 注释完整
  - 不使用硬编码（除默认值）

## 依赖关系

**后置任务**：T2/T3/T4/T5/T6/T7/T8
**并行任务**：无
