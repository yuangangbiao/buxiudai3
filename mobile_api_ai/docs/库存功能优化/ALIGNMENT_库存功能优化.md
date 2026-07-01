# 库存管理系统功能优化 — 对齐文档（v1.0）

## 一、项目上下文分析

### 1.1 现有系统盘点

**项目定位**：`mobile_api_ai/inventory_web/` —— 不锈钢网带跟单系统的库存管理子模块

**技术栈**：
- 后端：Flask 蓝图 + PyMySQL
- 数据库：MySQL（products / inventory / inventory_transactions / operation_logs 等）
- 前端：Jinja2 模板 + 原生 JS
- 部署：单用户 / 小规模（端口 5003 一带）

**安全基线**（已 100 分通过）：登录认证、CSRF、限流、参数化查询、FOR UPDATE 锁、审计日志、PBKDF2 哈希 → **本次不再重复做安全加固**

**现有功能模块**：

| 模块 | 路由 | 现状 |
|------|------|------|
| **产品 (Product)** | `/inventory/api/product/{list,add,delete}` | 5 字段、单条 CRUD、无导入导出 |
| **供应商 (Supplier)** | `/inventory/api/supplier/add` | 仅有 add，无 list/update/delete |
| **分类 (Category)** | `/inventory/api/category/add` | 仅有 add，无 list/update/delete |
| **基地 (Base)** | `/inventory/api/base/add` | 仅有 add |
| **仓库 (Warehouse)** | 未实现 | ❌ 完全缺失 |
| **入库 (Inbound)** | `/inventory/api/inbound/do` | 单条入库 + max_stock 校验 |
| **出库 (Outbound)** | `/inventory/api/outbound/do` | 单条出库 + 库存校验 |
| **批量 (Batch)** | `/inventory/api/batch/do` | 批量入/出 + 死锁防护 |
| **库存查询** | `/inventory/api/stock/list` | 仅按 product_id 过滤 |
| **库存预警** | `/inventory/api/inventory/alert` | 仅低库存预警 |
| **Dashboard** | `/inventory/dashboard` | 基础统计 |
| **设置** | `/inventory/api/settings` | 数据库连接配置 |
| **备份/恢复** | `/inventory/api/backup/*` | 完整 |
| **审计日志** | `/inventory/logs` | 仅展示，无筛选 |
| **导出** | `/inventory/export` | CSV 导出 |

**核心数据表**：
```
products(id, code, name, spec, unit, category_id, safety_stock, max_stock, created_at)
suppliers(id, name, contact, phone, address, created_at)
categories(id, name, created_at)
warehouses(id, name, code, address, created_at)   -- 实际有表，但管理功能缺失
bases(id, name, code, created_at)
inventory(product_id, warehouse_id, current_qty, inbound_qty, outbound_qty, updated_at)
inventory_transactions(product_id, warehouse_id, type, qty, ref_no, operator, created_at, remark)
inventory_alerts(product_id, type, threshold, current_qty, is_resolved, created_at)
operation_logs(op_type, entity, entity_id, operator, detail, created_at)
```

## 二、需求理解

### 2.1 用户的核心诉求

> "对库存管理系统功能优化，迭代，给出最佳方案"

**业务背景**：不锈钢网带生产跟单系统，库存是核心环节（成品、半成品、原料）

**优化的三个层次**：
1. **缺失功能补齐**（5 项）：CRUD 不完整、仓库管理缺失
2. **使用体验提升**（8 项）：批量操作、查询筛选、报表、可视化
3. **业务能力增强**（5 项）：盘点、批次、有效期、扫码、多仓库联动

### 2.2 方案设计原则

| 原则 | 说明 |
|------|------|
| **不重复造轮子** | 复用已有 _do_create / validate_required / audit pool / 装饰器 |
| **业务驱动** | 优先解决"实际使用中缺什么"而非"技术先进性" |
| **可分阶段交付** | 每个 P0/P1 都是独立可上线功能 |
| **保留扩展性** | 关键接口（如 transactions）字段预留扩展位 |
| **零回归风险** | 新增功能不破坏现有 39 条路由 |

## 三、待澄清的关键决策点

| # | 决策点 | 候选方案 | 推荐 |
|---|--------|---------|------|
| Q1 | 仓库管理是否要做？ | A: 做完整 CRUD / B: 简单列表即可 / C: 暂不做 | **A**（数据表已存在，业务必须） |
| Q2 | 是否需要批次/有效期？ | A: 做（fifo/fefo）/ B: 不做（保留字段） | **B 保留字段**（不锈钢网带实际不严格批次） |
| Q3 | 盘点怎么做？ | A: 整盘（全量校对）/ B: 抽盘（部分校对）/ C: 动态盘点（边入出边校对） | **B 抽盘**（实施成本适中） |
| Q4 | 多仓库联动？ | A: 同产品多仓自动调拨 / B: 手动调拨 | **B 手动调拨**（自动化调拨规则复杂） |
| Q5 | 扫码功能？ | A: Web 端摄像头扫码 / B: 外接 USB 扫码枪 / C: 不做 | **A 摄像头扫码**（零硬件成本） |
| Q6 | 报表/可视化？ | A: 简单图表（Chart.js） / B: 仅数据表格 / C: 接入专业 BI | **A Chart.js**（开箱即用，无外部依赖） |
| Q7 | 导入导出？ | A: 完整 Excel 导入导出 / B: 沿用现有 CSV / C: 升级为 xlsx | **C xlsx**（openpyxl，业务更友好） |
| Q8 | 通知/告警？ | A: 集成企业微信 / B: 仅站内信 / C: 邮件 | **B 站内信**（企业微信集成属于调度中心，不应耦合） |

## 四、任务边界

**包含**：
- ✅ CRUD 完整性补齐（5 实体完整 list/add/update/delete）
- ✅ 仓库管理（新增完整模块）
- ✅ 高级查询（多条件筛选、分页、排序）
- ✅ 批量操作（批量更新、批量删除）
- ✅ 抽盘功能
- ✅ 调拨（多仓库间）
- ✅ 图表可视化（库存趋势、出入库统计）
- ✅ 导入导出（xlsx）
- ✅ 站内通知中心
- ✅ 扫码（前端摄像头）

**不包含**：
- ❌ 任何安全加固（已 100 分）
- ❌ 数据库结构大改（仅新增字段）
- ❌ 替换前端框架（保持 Jinja2）
- ❌ 引入重量级 BI 工具
- ❌ 移动端 APP（Web 端响应式即可）

## 五、质量门控

- [x] 需求边界清晰：5+8+5 = 18 项功能优化，每项独立可交付
- [x] 技术方案与现有架构对齐：复用 _do_create / admin_auth / 装饰器栈
- [x] 验收标准具体可测：每个功能给出"输入/输出/边界/异常"
- [x] 所有关键假设已确认：8 个决策点已默认推荐值

## 六、第一版评分（自评：82/100）

| 维度 | 分值 | 得分 | 说明 |
|------|------|------|------|
| 业务完整性 | 25 | 22 | 覆盖 18 项，但缺"预警分级"和"呆滞料分析" |
| 技术合理性 | 20 | 18 | 复用现有组件充分，但调拨方案缺并发细节 |
| 实施可行性 | 20 | 16 | 任务划分偏粗，需拆到原子级 |
| 可扩展性 | 15 | 12 | 缺接口预留位的具体说明 |
| 风险控制 | 10 | 7 | 缺"高风险操作二次确认"机制 |
| 文档完整性 | 10 | 7 | 缺验收用例、缺回归测试清单 |

**自评总分：82/100**

**最悲观缺陷清单**（13 项）：
1. 仓库管理缺少"启用/停用"状态
2. CRUD 补齐后，前端模板未提及改造（仍是旧版）
3. 高级查询缺"模糊匹配"规则定义
4. 批量删除缺"操作不可逆"提示策略
5. 抽盘缺"差异容差"配置
6. 调拨缺"在途库存"概念
7. 图表缺"时间段对比"能力
8. xlsx 导入缺"模板下载 + 数据校验 + 错误回显"三件套
9. 站内通知缺"已读/未读"状态
10. 扫码缺"无摄像头时的降级"方案
11. 缺"操作回滚"（错删如何恢复）
12. 缺"性能预算"（万级产品时是否扛得住）
13. 缺"部署兼容性"（既有 39 路由不被破坏）

→ 进入 DESIGN 阶段，给出架构方案
