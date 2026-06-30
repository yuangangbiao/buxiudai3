# ALIGNMENT v2 - 包装入库 ↔ 成品库联动修复

> **版本**: v2（同步 DESIGN v2 修补）
> **修补日期**: 2026-06-16
> **第 1 轮审计**: 4 CRITICAL + 3 HIGH + 5 MEDIUM → v2 全部修补

## 1. 任务背景

### 1.1 业务语义（用户已澄清）

| 概念 | 语义 | 维度 |
|------|------|------|
| **包装入库** | 工序名 — "完成多少产品具备包装入库条件" | 动作（process）|
| **成品入库** | 仓库名 — "仓库里已存储多少已完成的订单产品" | 位置（location）|

### 1.2 业务规则

- 每次"包装入库"工序**报工** → 仓库自动入库对应数量（增量）
- 实际生产存在**分批发货**，仓库剩余数量随之减少
- 不需要等所有工序完成才能入库

### 1.3 现状问题

| # | 问题 | 严重度 |
|---|------|:------:|
| 1 | `status_key_map` 把仓库名"成品入库"当 status 用，语义错位 | 🔴 P0 |
| 2 | 工序"包装入库"报工后**不联动** `finished_goods` 仓库表 | 🔴 P0 |
| 3 | 仓库"成品入库"数量**不会**随报工自动更新 | 🔴 P0 |
| 4 | 发货时**不分批**，一次性扣减 | 🟡 P1 |
| 5 | 订单状态用"成品入库"（仓库名），应该是工序名 | 🟡 P1 |

---

## 2. 检查范围

| 实体 | 表/字段 | 涉及文件 |
|------|---------|---------|
| 工序记录 | `process_records.completed_qty` | `models/process.py` |
| 工序记录 | `process_records.unit` | `models/process.py` |
| 仓库 | `finished_goods`（id, order_id, warehouse, quantity, unit, in_date, status, remark）| `models/shipment.py` 新建 `FinishedGoodsDAO` |
| 发货 | `shipments`（已存在）| `models/shipment.py` |
| 订单 | `production_orders.status` | `models/production.py` |
| 订单 | `orders.status` | `models/production.py` |
| 翻译表 | `status_key_map` | `models/production.py:213-221` |
| 翻译表 | `STATUS_ORDERS_MAP` | `models/production.py:170-179` |

---

## 3. 用户决策（已确认）

| # | 决策点 | 选择 |
|---|--------|------|
| 1 | 修复范围 | ✅ 方案 1：完整联动 |
| 2 | 报工数量联动 | ✅ 增量入库（delta_qty） |
| 3 | finished_goods.unit | ✅ 从 process_records.unit 取 |
| 4 | 订单状态联动 | ✅ 是（production_orders.status = "包装入库"）|
| 5 | 分批发货联动 | ✅ 发货时减 finished_goods.quantity |

---

## 4. 业务流（修复后）

```
┌─────────────────────────────────────────────────────────────┐
│ 工序"包装入库" 报工 (delta_qty = X)                          │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. UPDATE process_records SET completed_qty += X            │
│ 2. process_records.unit = "件"/"米"  ← 新增联动获取           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FinishedGoodsDAO.stock_in(                                 │
│      order_id, qty=X, warehouse="成品仓库",                  │
│      unit=process_records.unit,                               │
│      operator=worker, remark="包装入库工序报工 X 件"           │
│    )  ← 增量入库（同 order_id 累加）                          │
│                                                              │
│    SQL:                                                      │
│    - SELECT existing finished_goods WHERE order_id=X         │
│    - 如果存在 → UPDATE quantity += X                         │
│    - 如果不存在 → INSERT                                     │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. production_orders.status = "包装入库"                     │
│ 5. orders.status = "包装入库"                                  │
│ 6. POST 5008 /api/sync/status-change {                       │
│      status_key: "warehousing"                                │
│    }                                                          │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼ (后续发货)
┌─────────────────────────────────────────────────────────────┐
│ 分批发货 Y 件 (Y <= finished_goods.quantity)                   │
│                                                              │
│ ShipmentDAO.ship_out(                                         │
│   order_id, qty=Y, finished_goods_id, ...                   │
│ )                                                            │
│   1. UPDATE shipments (status="待发货")                       │
│   2. UPDATE finished_goods SET quantity -= Y                  │
│      如果 quantity == 0 → status="已出库"                     │
│   3. production_orders.status = "已发货"                      │
│   4. orders.status = "已发货"                                  │
│   5. POST 5008 /api/sync/status-change {                     │
│        status_key: "shipped"                                   │
│      }                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 验收标准

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 工序"包装入库"报工后，`finished_goods.quantity` 自动 +X（增量）| 端到端测试 |
| 2 | 报工 5→8→10 件，仓库数量：5→8→10（**累加**不是覆盖）| 端到端测试 |
| 3 | `finished_goods.unit` 取 `process_records.unit` | 单测 |
| 4 | 报工后 `production_orders.status = "包装入库"` | 端到端测试 |
| 5 | 5008 收到 `status_key="warehousing"` 同步 | 抓包/单测 |
| 6 | `status_key_map` 不再含 `'成品入库'` key | grep 验证 |
| 7 | 分批发货 Y 件后，`finished_goods.quantity -= Y` | 端到端测试 |
| 8 | 全部发货后 `finished_goods.status = "已出库"` | 端到端测试 |
| 9 | 单测 + 端到端测试全部通过 | pytest |
| 10 | 不破坏现有 `ShipmentDAO.create()` / `confirm_ship()` 行为 | 回归测试 |

---

## 6. 风险与边界

| # | 风险 | 缓解 |
|---|------|------|
| 1 | 单位不一致：报工"件" vs finished_goods 旧记录"米" | 首次入库检查单位一致性，冲突报警 |
| 2 | 同一订单多次入库产生多条 finished_goods 记录 | `stock_in()` 内部按 order_id 合并 |
| 3 | 报工回滚/改小（已报 10 改回 5）| delta 可能是负数，需要**反向出库**逻辑 |
| 4 | 工序重复报工（同一 record_id 多次调用）| 用 delta_qty 而不是累计 completed_qty |
| 5 | 跨订单联动失败 | 严格用 `process_records.order_id` 联动 |
| 6 | 旧数据：`finished_goods` 表已有记录 | 存量数据按 order_id 关联，不动 |
| 7 | 测试覆盖：缺少 process_records 单元测试 | 补单测 |
| 8 | `ProductionDAO.update_status()` 仍含 `'成品入库'` 字符串 | 同步清理（见修复范围 #4）|
| 9 | 数据库 `process_calc_rules` 旧公式 | 之前 P3 任务，本次不动 |
| 10 | 跨平台：单位换算 | 单位来自 process_records，不做隐式换算 |

---

## 7. 不变更部分（防回归）

| # | 模块 | 保护 |
|---|------|------|
| 1 | `ShipmentDAO.create()` 现有逻辑 | 不动 |
| 2 | `ShipmentDAO.confirm_ship()` 现有逻辑 | 不动 |
| 3 | `ProcessDAO.update_record()` 报工主体逻辑 | **保留并扩展**，不重写 |
| 4 | `process_records` 表结构 | 不动 |
| 5 | `finished_goods` 表结构 | 不动 |
| 6 | `shipments` 表结构 | 不动 |
| 7 | 5008 协议字段（warehousing/shipped）| 不动 |
| 8 | `INSPECTION_ITEMS_BY_CATEGORY` 质检规则 | 不动 |
| 9 | 工序模板 15 道 | 不动 |
| 10 | `production.py:39-40` 冗余赋值 | 之前 P2 任务，本次不动 |

---

## 8. 业务影响

### 8.1 用户场景对比

| 场景 | 改善前 | 改善后 |
|------|--------|--------|
| 包装入库报工 5 件 | 工序记录 +5，仓库数量**不变** | 工序记录 +5，**仓库 +5 自动联动** |
| 报工 5→8→10（分 3 批）| 仓库数量**始终 0** | 仓库 5→8→10 **累加** |
| 部分发货 3 件 | 仓库数量**仍不变**，数据不一致 | 仓库 8-3=5，**自动减少** |
| 全部发完 | 仓库显示有库存但实际已发 | 仓库 status="已出库"，**清晰** |
| 订单状态显示 | "成品入库"（仓库名）| "包装入库"（工序名），**语义清晰** |

### 8.2 业务能力新增

| 业务流 | 新增/优化功能 |
|--------|--------------|
| 报工 | 报工数量自动联动到仓库 |
| 库存 | `finished_goods` 数量自动维护（增量入库+减发出库）|
| 发货 | 分批发货逻辑，仓库剩余数量准确 |
| 订单 | 订单状态用工序名（"包装入库"），不再用仓库名 |
| 监控 | 报工数量 = 仓库入库数量 = 已发货 + 剩余，三方一致 |
| 调度 | 5008 端 100% 同步 warehousing / shipped 状态 |

---

## 9. 下一刀

待用户确认后进入 DESIGN + TASK 文档。

| 阶段 | 内容 |
|------|------|
| DESIGN | 模块依赖图、接口契约、数据流图、异常处理策略 |
| TASK | 8-10 个原子任务，含输入/输出契约、依赖关系 |
| Automate | 按依赖顺序执行 |
| Assess | 完成度报告 + 业务影响报告 + 归档 |
