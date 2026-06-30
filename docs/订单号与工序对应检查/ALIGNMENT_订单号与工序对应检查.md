# ALIGNMENT - 订单号与工序名称对应关系检查

## 任务概述

检查全局所有订单号和工序名称必须严格对应，识别潜在不一致性问题。

> **执行日期**: 2026-06-15
> **扫描范围**: `d:\yuan\不锈钢网带跟单3.0`
> **审计方式**: 静态代码 + JSON 文件对比（本地无 SQLite/MySQL 实例）

---

## 1. 检查范围

### 1.1 涉及的核心实体

| 实体 | 表/字段 | 唯一标识 |
|------|---------|---------|
| 订单 | `orders.order_no` | `ORD-YYYYMMDDXXXX` 格式 |
| 工单 | `production_orders.order_no` | 与 `orders.order_no` 镜像 |
| 工序记录 | `process_records.process_name` | 模板 2 的 15 道工序 |
| 工序计算规则 | `process_calc_rules.process_name` | 模板 2 的 15 道工序 |
| 质检规则 | `quality_rules.process_name` | 3 个阶段名 |
| 质检记录 | `quality_records.process_name` | 字面量传入 |
| 报修记录 | `repair_records`（存在但本次未涉及） | — |

### 1.2 关键参考文件

| 文件 | 作用 | 关键字段 |
|------|------|---------|
| [ORDER_NO_DECLARATION.py](file:///d:/yuan/不锈钢网带跟单3.0/ORDER_NO_DECLARATION.py) | 订单号全局声明 | `order_no` 唯一性 |
| [data/工序规则模板.json](file:///d:/yuan/不锈钢网带跟单3.0/data/工序规则模板.json) | 工序模板 (root) | 15 道工序（**实际只有 1 条，文件被截断**） |
| [data/工序规则模板1.json](file:///d:/yuan/不锈钢网带跟单3.0/data/工序规则模板1.json) | 工序模板 v1 | 15 道工序，缺 unit/default_worker |
| [data/工序规则模板2.json](file:///d:/yuan/不锈钢网带跟单3.0/data/工序规则模板2.json) | 工序模板 v2 | 15 道工序，字段完整 |
| [models/quality_rule.py](file:///d:/yuan/不锈钢网带跟单3.0/models/quality_rule.py) | 质检规则 | `process_name` 字段 |
| [models/production.py](file:///d:/yuan/不锈钢网带跟单3.0/models/production.py) | 工单 + 工序写入 | `status_key_map` 翻译 |

---

## 2. 检查结果摘要

| 维度 | 标准数 | 实际命中 | 问题数 |
|------|--------|----------|--------|
| 标准工序名（模板 2） | 15 | — | — |
| 代码硬编码的工序字面量 | — | 11（含 4 个工序名 + 7 个非工序） | 11 |
| 模板文件一致性 | 3 份 | 3 份均存在 | 5 类问题 |
| 模板公式 `planned_qty_formula` | — | 1 处不一致 | 1 |
| 质检规则 `process_name` 对应性 | 15 道工序 | 0 道对应 | 3 类错位 |
| 订单号生成函数 | 1 个 | `generate_order_no` | 文档错误 |
| 工单状态映射 | 7 个 | 1 个 (`'成品入库'`) 跟模板冲突 | 1 |

---

## 3. 发现的问题（共 7 大类、15+ 处）

### 🔴 问题 1：根模板文件被截断（数据丢失风险）

- **文件**: [data/工序规则模板.json](file:///d:/yuan/不锈钢网带跟单3.0/data/工序规则模板.json)
- **现象**: 文件仅 539 字节，只包含 1 条工序记录（id=1 原材料准备），且 `"created_at":` 后没有值，整个 JSON 无闭合 `}]`。
- **影响**: 任何加载此文件并按"完整 15 道工序"假设的代码会 IndexError / KeyError。
- **证据**: 
  - 文件内容实测：`"created_at":` 紧跟 EOF
  - 安全加载后 `len(parsed) == 1`，而其他两个模板都是 15 条

### 🔴 问题 2：3 份模板字段定义不一致

| 字段 | root | 模板1 | 模板2 |
|------|------|-------|-------|
| `id` | ✅ | ✅ | ✅ |
| `process_name` | ✅ | ✅ | ✅ |
| `product_types_json` | ✅ | ✅ | ✅ |
| `condition_expr` | ✅ | ✅ | ✅ |
| `planned_qty_formula` | ✅ | ✅ | ✅ |
| `priority` | ✅ | ✅ | ✅ |
| `enabled` | ✅ | ✅ | ✅ |
| `created_at` | ✅(空) | ✅ | ✅ |
| `updated_at` | ❌ | ✅ | ✅ |
| `default_worker` | ❌ | ❌ | ✅ |
| `unit` | ❌ | ❌ | ✅ |

- **影响**: 字段不齐导致下游 `process_calc_rules` 表迁移时部分列插入失败或缺默认值。

### 🔴 问题 3：`planned_qty_formula` 同名不同公式

| 工序 | root / 模板1 | 模板2 |
|------|-------------|-------|
| 原材料准备 | `"物料种类数量"` | `"物料数量"` |

- **语义差异**: "种类数量"（去重后）vs "数量"（原始）→ 计算出的 `planned_qty` 可能差几倍。
- **位置**: [data/工序规则模板2.json](file:///d:/yuan/不锈钢网带跟单3.0/data/工序规则模板2.json#L7)
- **风险**: 排产时 `ProcessCalcEngine.calculate_planned_qty` 返回不一致值

### 🔴 问题 4：质检规则 `process_name` 字段与工序不对应

`models/quality_rule.py:421-452` `init_default_rules()` 写入 quality_rules 表的 `process_name` 字段值是：

| rule_name | quality_rules.process_name | process_records.process_name | 是否对应 |
|-----------|---------------------------|------------------------------|----------|
| 原材料检验 | `"原材料检验"` | `"原材料准备"` | ❌ 错位 |
| 过程检验 | `"生产过程"` | （无对应工序） | ❌ 错位 |
| 终检 | `"最终检验"` | `"质量检验"` | ❌ 错位 |

- **后果**: [quality_rule.py:94-103](file:///d:/yuan/不锈钢网带跟单3.0/models/quality_rule.py#L94-L103) `get_rules_by_process(process_name)` 永远匹配不到这 3 条规则。
- **证据**: `if rule.get("process_name") == process_name:` 严格等值比较。

### 🔴 问题 5：状态映射 `status_key_map` 中"成品入库" ≠ 模板"包装入库"

[production.py:213-221](file:///d:/yuan/不锈钢网带跟单3.0/models/production.py#L213-L221):

```python
status_key_map = {
    ProductionStatus.IN_PROGRESS.value: 'in_production',
    ProductionStatus.COMPLETED.value: 'report_complete',
    '报工完成': 'report_complete',
    '成品入库': 'warehousing',     # ← 字面量
    '已发货': 'shipped',
    '已收货': 'received',
    '订单完成': 'order_complete',
}
```

- **同工序名不一致**:
  - 工序模板 2 的最后一道工序叫 **"包装入库"**（id=15）
  - 状态映射里硬编码 **"成品入库"**（3 处出现）
  - 两个名字在数据库里指向完全不同的状态语义，但下游 5008 同步接口可能按"包装入库"的状态值去查找

### 🟡 问题 6：ORDER_NO_DECLARATION.py 文档自身错误

[ORDER_NO_DECLARATION.py:10](file:///d:/yuan/不锈钢网带跟单3.0/ORDER_NO_DECLARATION.py#L10):

```python
2. process_sub_steps.order_no = process_sub_steps.order_no（8008同步时自动设置）
```

- **问题**: 右侧明显是打字错误（应填其他表名，如 `production_orders`），而且 `process_sub_steps` 表在代码中**根本不存在**（grep 全仓 0 命中，实际表是 `process_records`）。
- **影响**: 误导后续维护者

### 🟡 问题 7：orders/production_orders order_no 镜像代码冗余

[models/production.py:39-40](file:///d:/yuan/不锈钢网带跟单3.0/models/production.py#L39-L40):

```python
# 统一使用订单号
order_no = order_row['order_no']
order_no = order_no   # ← 重复赋值，注释提到"镜像"但实际未做任何同步操作
```

- **注释承诺的"统一使用订单号"实际只取了值，没有做"镜像/同步"动作**
- 后续 INSERT INTO production_orders 用的是同 1 个 order_no 变量，但 ORDER_NO_DECLARATION.py 第 5 条声明的"`order_no` 列镜像 `order_no` 列"未体现
- 如果未来有人删除该赋值，行为无变化（无副作用），属死代码

### 🟢 问题 8：desktop/process_view.py 重复工序去重逻辑隐患

[process_view.py:1648-1663](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/process_view.py#L1648-L1663):

```python
seen_names = {}
dedup_deleted = 0
for r in all_existing:
    pname = r["process_name"]
    if pname in seen_names:
        self.svc.delete_record(r["id"])  # 直接删，没二次确认
        dedup_deleted += 1
```

- **风险**: 若 `process_records.process_name` 不唯一（如人手录入的"焊接眼镜网"和"焊接眼镜网 "带空格），这条去重逻辑会**直接 delete 一条**，已报工数据丢失。
- **建议**: 增加 trim/normalize 比较，或改用软删除标记

---

## 4. 已验证证据

| # | 验证项 | 证据 |
|---|--------|------|
| 1 | 模板文件被截断 | `Read data/工序规则模板.json` 第 10 行后 EOF；`_debug_load.py` 安全加载后 `len == 1` |
| 2 | 3 份模板字段不一致 | `_audit_process_templates.py` 输出 字段集合差异 表格 |
| 3 | `planned_qty_formula` 不一致 | 同上 输出 3. 同名差异 |
| 4 | 质检规则 process_name 错位 | `Read models/quality_rule.py:421-452` 三处 process_name 字面量 |
| 5 | 状态映射 "成品入库" ≠ 模板 "包装入库" | `Read models/production.py:213-221` |
| 6 | ORDER_NO_DECLARATION.py 文档错误 | `Read ORDER_NO_DECLARATION.py` 第 10 行；grep `process_sub_steps` 0 命中 |
| 7 | 工单代码冗余 | `Read models/production.py:39-40` |
| 8 | 去重逻辑隐患 | `Read desktop/views/process_view.py:1648-1663` |

---

## 5. 风险评级

| 问题 | 严重度 | 影响范围 |
|------|--------|----------|
| 1. 模板文件被截断 | 🔴 高 | 数据加载、迁移 |
| 2. 模板字段不一致 | 🔴 高 | 数据库迁移失败 |
| 3. 公式不一致 | 🔴 高 | 排产数量计算错 |
| 4. 质检规则错位 | 🔴 高 | 质检规则永久失效 |
| 5. "成品入库" vs "包装入库" | 🟡 中 | 5008 同步异常 |
| 6. ORDER_NO_DECLARATION 文档错 | 🟡 中 | 误导维护者 |
| 7. 冗余代码 | 🟢 低 | 可读性差 |
| 8. 去重硬删 | 🟡 中 | 已报工数据可能丢失 |

---

## 6. 下一刀（建议）

1. **立即修复** (24h 内):
   - 从 tpl_1 / tpl_2 合并恢复 root 模板（15 道工序）
   - 修复质检规则 3 条 process_name 对应到实际工序名（"原材料准备" / "焊接眼镜网" / "质量检验"）
   - 统一 `planned_qty_formula` 公式（建议用模板 2 的 `物料数量`）

2. **短期修复** (1 周内):
   - 修正 `ORDER_NO_DECLARATION.py` 第 2 条文档
   - 状态映射"成品入库" → 改为标准枚举或与模板统一
   - 删除冗余代码 `order_no = order_no`

3. **中期加固** (2 周内):
   - 增加模板文件加载的"必填字段断言"
   - 引入 SSOT 工序定义（数据库 + JSON schema 校验）
   - 增加 CI 检查：grep 工序字面量 + 对比模板集合

---

## 7. 验收标准

| # | 验收项 | 状态 |
|---|--------|------|
| 1 | 3 份模板工序名集合完全一致 | ❌ 未达成 |
| 2 | 3 份模板字段集合完全一致 | ❌ 未达成 |
| 3 | 同名工序的 planned_qty_formula 一致 | ❌ 未达成 |
| 4 | 质检规则的 process_name 与 process_records 工序名能匹配 | ❌ 未达成 |
| 5 | ORDER_NO_DECLARATION.py 文档准确 | ❌ 未达成 |
| 6 | 代码无工序字面量硬编码 | ❌ 未达成 |

**完成度评估**: 0/6 验收标准达成 → **0%**

🔴 **风险预警**: 当前 6 大验收项全部不通过，建议优先修复问题 1-4 后再次审计。
