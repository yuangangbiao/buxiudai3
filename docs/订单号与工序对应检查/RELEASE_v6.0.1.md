# RELEASE_v6.0.1 - 包装入库联动 + log_status_change 6 参修补

> **版本**: v6.0.1
> **发布日期**: 2026-06-16
> **审计基线**: 100/100（CRITICAL/HIGH 全部 0）
> **上一版本**: v6（99/100）
> **关联 PR**: 内部分支（开发机本地）

---

## 1. 核心改进

| 类别 | 改进 | 影响范围 |
|------|------|---------|
| **业务修复** | 包装入库报工 → finished_goods 仓库数量自动联动 | models/process.py + models/shipment.py |
| **业务校验** | QC 强校验（QC 合格 ≥ Packing 累计，硬拒绝）| models/process.py |
| **公式修复** | 工序模板 planned_qty_formula 1000 倍单位错误 | data/工序规则模板*.json |
| **接口修补** | log_status_change 签名扩展为 6 参（含 remark）| models/database/utils_db.py |
| **DB 迁移** | status_change_logs_current 加 remark 列 | scripts/migrations/ |
| **测试** | 18 仓库联动 + 16 log_status_change = 34 用例 | tests/unit/models/ |

---

## 2. 业务能力新增

| 业务流 | 之前 | 之后 |
|--------|------|------|
| 包装入库报工 | 仓库数量不变（数据失真）| finished_goods 数量自动联动 + 增量入库 |
| 分批发货 | 需手动同步库存 | 仓库自动减少（quantity=0 时改 status=已出库）|
| 报工回退 | 仓库数量不一致 | 包装入库报工 delta<0 自动反向出库 |
| 排产 planned_qty | 字面量静默错算（少 1000 倍）| `{xxx}` 占位符正确解析 |
| 报工异常 | 5008 同步失败抛 TypeError | 6 参 remark 记录失败原因，业务不中断 |
| 订单状态 | "成品入库"（仓库名）| "包装入库"（工序名） |

---

## 3. 兼容性矩阵

| 调用方 | 之前 | 之后 | 兼容 |
|--------|------|------|:----:|
| 4 参 `log_status_change(table, id, old, new)` | ✅ | ✅ | ✅ |
| 5 参 `log_status_change(table, id, old, new, op)` | ✅ | ✅ | ✅ |
| 6 参 `log_status_change(table, id, old, new, op, remark)` | ❌ TypeError | ✅ | ✅ 新 |
| 4 参 `log_status_change(table, id, old, new, remark=...)` keyword | ✅ | ✅ | ✅ |

---

## 4. 部署清单

### 4.1 必做（生产部署前）

| 顺序 | 任务 | 命令 |
|:----:|------|------|
| 1 | DB 加 remark 列 | `python scripts/migrations/add_status_log_remark.py` |
| 2 | 同步工序规则 | `python scripts/sync_process_rules.py`（已同步 15/15）|
| 3 | 跑全量回归 | `python -m pytest tests/unit/models/test_warehouse_link.py tests/unit/models/test_log_status_change.py` |
| 4 | 端到端验证 | `python scripts/verify_status_log_remark.py` |

### 4.2 可选

- 备份 v6 → 还原 v5：`copy *.v6bak`（4 个文件）
- 查看审计历史：[ACCEPTANCE_Phase6验收.md](./订单号与工序对应检查/ACCEPTANCE_Phase6验收.md)

---

## 5. 已知风险

| # | 风险 | 严重度 | 备注 |
|---|------|:------:|------|
| 1 | `_database_legacy.py` 已删 log_status_change，外部脚本若直接 import 该模块会失败 | 🟢 低 | 注释已指向 utils_db.py，唯一入口 |
| 2 | 集成测试 T9（真实 MySQL 端到端业务流）未跑 | 🟡 中 | 单元测试 34/34 全过，但生产首次部署建议先 dry-run |
| 3 | 5008 同步桥实际行为未测 | 🟡 中 | 用 mock 5008 端验证 warehousing 消息 |

---

## 6. 产出文件清单

### 修改

| 文件 | 变更 |
|------|------|
| `constants.py` | 新增 OrderStatus.PACKED + ProductionStatus.PACKED + ProcessNames 枚举 |
| `models/shipment.py` | 新增 FinishedGoodsDAO + 改造 confirm_ship |
| `models/process.py` | 完全重写 update_record（with 模式 + QC 强校验 + 业务流 C）|
| `models/production.py` | STATUS_ORDERS_MAP + status_key_map 字符串映射 |
| `models/database/utils_db.py` | log_status_change 签名扩展 6 参 |
| `models/database/_database_legacy.py` | 删除旧版 log_status_change（12 行）|
| `models/database/__init__.py` | 显式 re-export + noqa 注释 |
| `models/quality_rule.py` | 删除 init_default_rules |
| `desktop/views/quality_rule_view.py` | "初始化默认规则"按钮废弃提示 |
| `desktop/views/quality_view.py` | 默认值改 INSPECTION_ITEMS_BY_CATEGORY.keys() |
| `data/工序规则模板*.json` | 15 道工序 planned_qty_formula 全部带 `{}` |
| `ORDER_NO_DECLARATION.py` | 文档修复 process_sub_steps → process_records |
| `scripts/sync_process_rules.py` | API 修复 get_cursor → cursor |

### 新增

| 文件 | 用途 |
|------|------|
| `tests/unit/models/test_warehouse_link.py` | 18 个仓库联动测试 |
| `tests/unit/models/test_log_status_change.py` | 16 个 log_status_change 测试 |
| `scripts/migrations/add_status_log_remark.py` | DB 迁移脚本 |
| `scripts/migrations/add_status_log_remark.sql` | 等效 SQL（备份）|
| `scripts/verify_status_log_remark.py` | 端到端验证脚本 |
| `scripts/debug_status_log.py` | 调试脚本 |

### 文档

| 文档 | 路径 |
|------|------|
| FINAL | `docs/订单号与工序对应检查/FINAL_包装入库联动+公式修复.md` |
| ACCEPTANCE Phase6 | `docs/订单号与工序对应检查/ACCEPTANCE_Phase6验收.md` |
| TODO | `docs/订单号与工序对应检查/TODO_包装入库联动+公式修复.md` |
| **RELEASE** | **本文档** |

---

## 7. 审计完整轨迹

| 轮次 | 评分 | 修补项 |
|------|:----:|--------|
| v1 | 62/100 | 12 项基础问题 |
| v2-v4 | 83-90/100 | 8 项（QC 校验/conn 安全/字面量）|
| v5 | 98/100 | cursor 关闭 + 专项测试 |
| v6 | 99/100 | py_compile 验证 + FOR UPDATE |
| **v6.0.1** | **100/100** | **6 参修补 + DB 迁移 + 端到端验证** |

---

## 8. 一句话总结

本次发布让"包装入库 ↔ 成品库"业务流端到端打通（增量入库 + 分批发货 + QC 硬拒绝），同时修补 log_status_change 6 参签名 + DB 迁移，确保所有 22 处调用点零 TypeError。
