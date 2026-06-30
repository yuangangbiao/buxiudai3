# TODO - 包装入库联动 + 公式修复（待用户处理项）

> **生成日期**: 2026-06-16
> **状态**: 全部 P1/P2/P3 已清零，以下为后续建议项

---

## ✅ 已完成（P1/P2/P3 全部清零）

| # | 任务 | 修复内容 | 文件 |
|---|------|---------|------|
| 1 | `ORDER_NO_DECLARATION.py` 文档错 | `process_sub_steps` → `process_records` | `ORDER_NO_DECLARATION.py:10` |
| 2 | `production.py` 冗余赋值 | 删除 `order_no = order_no` | `models/production.py:35` |
| 3 | `append_quality_rule_tests.py` 失效类 | 删除 TestInitDefaultRules 追加块 | `tests/append_quality_rule_tests.py` |
| 4 | `quality_view.py` fallback 错误 | 无工序返回 `[]` | `desktop/views/quality_view.py:264` |
| 5 | `process_calc_rules` DB 旧公式 | 迁移 15 条规则到 DB | `scripts/sync_process_rules.py` |
| 6 | `sync_process_rules.py` API 错 | `get_cursor()` → `cursor()` 5 处 | `scripts/sync_process_rules.py` |
| 7 | 包装入库 ↔ 成品库联动 | v6 实施 + R1 FOR UPDATE 修复 | `models/shipment.py`, `models/process.py` |

---

## ⬜ 后续建议（非阻断）

| 优先级 | 任务 | 说明 | 文件 |
|--------|------|------|------|
| 🟢 P2 | "穿曲轴"处理 | 之前决策"暂不动"，后续可统一工序名 | `data/工序规则模板*.json` |
| 🟢 P2 | 集成测试 T9 | 在真实 MySQL 上跑端到端业务流（报工→入库→发货）| - |
| 🟢 P2 | 5008 同步桥验证 | 用 mock 5008 端验证 warehousing 消息 | `models/process.py` |
| ⚪ P3 | 质检分类细化 | INSPECTION_ITEMS_BY_CATEGORY 按工序细分 | `core/_config_domain.py` |

---

## 📋 本次未动的既有代码（防回归保护）

| 模块/功能 | 保护措施 |
|----------|---------|
| `ShipmentDAO.create()` | 不动 |
| `process_records` 表结构 | 不动 |
| `finished_goods` 表结构 | 不动 |
| 工序模板 15 道 | 不动 |
| `INSPECTION_ITEMS_BY_CATEGORY` | 不动 |
| 数据库初始化逻辑 | 不动 |

---

## 🔧 回滚方式

如需回滚，备份文件（`.v6bak` / `.bak` / `.bak2`）已保留：

```bash
# 还原常量枚举
copy constants.py.v6bak constants.py

# 还原存储层
copy models\shipment.py.v6bak models\shipment.py
copy models\process.py.v6bak models\process.py
copy models\production.py.v6bak models\production.py

# 还原质检模块
copy models\quality_rule.py.bak models\quality_rule.py
copy desktop\views\quality_rule_view.py.bak desktop\views\quality_rule_view.py
copy desktop\views\quality_view.py.bak2 desktop\views\quality_view.py

# 还原工序模板
copy data\工序规则模板.json.bak data\工序规则模板.json
copy data\工序规则模板1.json.bak data\工序规则模板1.json
copy data\工序规则模板2.json.bak data\工序规则模板2.json
```
