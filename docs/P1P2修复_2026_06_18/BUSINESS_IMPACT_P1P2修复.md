# 业务影响报告 - P1+P2 修复

## 1. 用户场景对比

> 改善前（痛点） → 改善后（价值）表格，≥3 场景

| # | 用户角色 | 改善前（痛点） | 改善后（价值） |
|---|---------|---------------|---------------|
| 1 | **操作工**（扫码报工） | 报工需要严格按"step_name + operator"格式，前端用错字段名（如 process_code）就 400 报错 | 字段名兼容 step_name/process_code + operator/operator_name，报工成功率提升 |
| 2 | **质检员**（扫袋质检） | 质检记录 id 为空，orderName 不显示，无法定位到具体订单 | id 字段有值，orderName 显示订单号，可精确定位到订单 |
| 3 | **办公室管理**（看老板看板） | 5/6 KPI 字段为 0，看板形同虚设，老板看不到真实运营数据 | pending/processing/completed 反映真实订单状态，processing=5（生产中）准确 |
| 4 | **车间主任**（看生产看板） | dashboard 订单的 orderId + order_no 重复，material/spec/name 三重相同，前端解析混乱 | 字段去重，orderId 唯一，name/material/spec 各自有明确语义 |
| 5 | **移动端前端**（扫码模块） | POST /api/scan-info 405（Method Not Allowed），扫码功能完全不可用 | HTTP 200 支持 POST，扫码流程顺畅 |

## 2. 业务能力新增

> 按业务流分类

| 业务流 | 新增/优化功能 | 影响范围 |
|--------|--------------|---------|
| 生产 | 报工字段名兼容（step_name/process_code, operator/operator_name）| 优化 — 报工成功率 |
| 生产 | dashboard expectedOrders 字段去重（去掉 order_no/orderNo 重复）| 优化 — 数据清晰 |
| 生产 | 老板 KPI 数据源切换为 production_orders | 修复 — KPI 反映真实数据 |
| 质检 | 质检记录补 orderName = order_no | 修复 — 定位订单 |
| 质检 | inspectionItems 归一化为 array | 优化 — 前端渲染稳定 |
| 移动端 | scan-info 端点支持 POST | 修复 — 扫码可用 |
| 物料 | production-orders 端点补 planStart/planEnd/assignedTo | 优化 — 字段完整 |

## 3. 不变更部分

| # | 模块/功能 | 保护措施 | 验证方式 |
|---|----------|---------|---------|
| 1 | 报工主路径 /api/process_sub_step 字段 | 保留 step_name + operator 原字段 | curl 测试通过 |
| 2 | 调度中心架构 5003 | 不变 | 端到端调用 |
| 3 | 移动端架构 5008 | 不变 | 端到端调用 |
| 4 | 报工原子事务边界 | 不变 | 跑存储层测试 |
| 5 | production-orders 端点路径 | 不变 | curl /api/production-orders |
| 6 | dashboard 端点路径 | 不变 | curl /api/dashboard |
| 7 | P0 修复代码（Bug #1-#5, #14 部分） | 不变 | _verify_final.py 跑过 |

## 4. 一句话总结

本次改动让**操作工报工 / 质检员看记录 / 老板看 KPI / 车间主任看生产看板 / 移动端扫码** 5 个核心场景从**字段不兼容 / id 空 / KPI 全 0 / 字段重复 / POST 405** 变为 **字段兼容 / id 有值 / KPI 真实 / 字段去重 / POST 200**。

## 已知数据建模缺陷

| 字段 | 状态 | 数据源表 | 修复方向 |
|------|------|----------|----------|
| material | 100% 空 | production_orders / orders 都没有 | 加 SQL migration 补列 |
| spec | 100% 空 | 同上 | 同上 |
| flowType | 部分空 | process_records.flow_type | 写入时填充 |
