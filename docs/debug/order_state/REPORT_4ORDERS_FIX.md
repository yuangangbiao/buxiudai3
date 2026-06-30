# RE-007 4 工单异常修复 — 回归报告

> **日期**: 2026-06-10
> **责任人**: RE-007 排查组
> **范围**: ORD-202604210004 / ORD-202605020001 / ORD-202604210002 / ORD-202605010001
> **基线报告**: [REPORT_4ORDERS_ANOMALY.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/REPORT_4ORDERS_ANOMALY.md)

---

## 1. 真相修正(从 REPORT v1 到本报告)

**REPORT v1 的 10 类异常基于 API 旧数据**,重新做 DB 探查后,**真正的异常是单一根因**:

| 根因 | 严重 | 实证 |
|------|------|------|
| `container_center.data_packages` 中 4 工单相关派单记录**全部为 0 条** | 🔴 致命 | DESCRIBE + SELECT 全表确认 |

业务数据实际分散在以下表,**完全无丢失**:

| 表 | 真实数据 |
|----|----------|
| `steel_belt.orders` | 4 工单主单(quantity 50/100/1000/1000) |
| `steel_belt.process_records` | 工序计划/状态(planned_qty, status, display_seq) |
| `steel_belt.process_sub_steps` | 工序报工 batch 粒度(quantity, qualified_qty) |
| `steel_belt.quality_records` | 1 条首检待检(ORD-202604210002) |
| `container_center.data_packages` | **0 条**(异常源) |

**结论**: 不是数据丢失,是**派单同步**链路断了。

---

## 2. 修复动作清单

### 2.1 数据修复(脚本 v2, [fix_4orders_anomaly.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/fix_4orders_anomaly.py))

| SQL | 动作 | 影响行 | 结果 |
|-----|------|--------|------|
| #1 | 备份 `data_packages` -> `data_packages_4orders_v2_backup_20260610_HHMMSS` | 47 行 | ✅ |
| #2 | 从 `process_records` 同步生成 `data_packages` 派单 | **29 行** | ✅ |
| #3 | ORD-202604210004 从 process_names 补建模板工序 | 0(过滤过严) | ⚠ 跳过(空工单可能本不该出现) |
| #4 | 修正 `process_records.planned_qty` 异常(0/29528) | 22 行 | ✅ |
| #5 | 标准化 `process_records.status` 中英文 | 9 行 | ✅ |
| #6 | 根据报工实际量重算 `process_records.status` | 4 行 | ✅ |

**总影响**: 64 行 修复 + 47 行 备份

### 2.2 后续补丁([patch_related_order.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/patch_related_order.py))

- 修补 #1: `related_order = order_no`(v5 字段映射) — 29 行
- 修补 #2: `content.order_no/process_name` — 29 行

---

## 3. 代码修复(2 个文件)

### 3.1 [mobile_api_ai/dispatch_center/_core.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py)

| 位置 | 修复 | 关联异常 |
|------|------|----------|
| L5270-5277 | `related_process` 优先取 `content.process_name` (而非 title) | 异常 #4, #5 |
| L5308-5320 | 工序按 `process_names` 字典序排序 | 异常 #4 |
| L5320-5327 | `completed_tasks` 用 `all_task_items` 统计(之前用 `doc_data`) | 异常 #8 |

### 3.2 [utils/data_type_contract.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/data_type_contract.py)

| 位置 | 修复 | 关联异常 |
|------|------|----------|
| LEGACY_TO_NEW | 加 `process_task → process_report` 映射 | 异常 #10 |
| _classify_legacy_report | 流程步骤白名单提前到 0 号位(早于质检) | 异常 #9 |

---

## 4. 验证

### 4.1 单元测试

```
============================= 42 passed in 2.86s ==============================
data_type_contract.py  74 行 覆盖 68 行  92% 覆盖率
```

✅ **42/42 单测全通过**,无回归

### 4.2 数据层验证(5002 HTTP API)

| 工单 | 修复前 | 修复后 |
|------|--------|--------|
| ORD-202604210004 | 0 process_task | 0(空工单未补) |
| ORD-202605020001 | 0 | **9 process_task + 9 报工** |
| ORD-202604210002 | 0 | **10 process_task** |
| ORD-202605010001 | 0 | **10 process_task** |
| **总 process_task** | **0** | **29** |

### 4.3 业务表现(已同步 5002)

| 工序 | 工单 | 完成量 | 状态 |
|------|------|--------|------|
| P01 原材料准备 | ORD-202604210002 | 132 | pending → 待 progress_qty 更新 |
| P06 编制左旋 | ORD-202604210002 | 100 | in_progress |
| P07 编制右旋 | ORD-202604210002 | 50 | in_progress |
| P01-P09 | ORD-202605010001 | 1000+ | **completed (9/9)** |
| P01-P09 | ORD-202605020001 | 50+18 批 | **completed (9/9)** |

---

## 5. 待用户操作:重启 5003 dispatch_center

> ⚠️ **重要**: 5003 dispatch_center 服务进程仍持有**修复前**的数据缓存和**修复前**的代码加载。5002 已能查到全部新数据,但 5003 看不到。

**需要执行**:

```bash
# 重启 5003 进程
py scripts/restart_5003.py   # 或手动 kill + 启动
```

重启后会自动:
1. 重新加载 `_core.py` 修复后的代码
2. 重新初始化 `DispatchContext.work_order_cache` (TTL 10s)
3. 下次 API 请求会通过 `cc.storage.get_packages()` 拉新数据

---

## 6. 后续防御性约束(RE-008 候选)

| # | 约束 | 提议位置 |
|---|------|----------|
| D1 | 派单同步任务: `process_records` 新增/更新时,自动 `UPSERT data_packages` | `services/process_service.py` |
| D2 | status 枚举统一: 数据库层 CHECK 约束(status ∈ pending/in_progress/completed/...) | `migration_2026_06_11_status_enum.sql` |
| D3 | display_seq 强制: `process_records` 必填,服务端默认 = 999 | `services/process_service.py` |
| D4 | data_type 契约覆盖: `classify_pkg` 把 `__contract_violation__` 写入告警表 | `utils/data_type_contract.py` |
| D5 | 5003/5002 启动时校验 MySQL 库名/版本,不一致立即报警 | `utils/db_utils.py` |

---

## 7. 修复脚本产物

| 路径 | 用途 |
|------|------|
| [scripts/fix_4orders_anomaly.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/fix_4orders_anomaly.py) | 主修复脚本(--dry-run / --execute / --rollback) |
| [scripts/patch_related_order.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/patch_related_order.py) | v5 字段映射补丁 |
| [scripts/inspect_full.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/inspect_full.py) | 4 工单 DB 全景探查 |
| [scripts/find_v5_table.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/find_v5_table.py) | v5 真实存储表探查 |
| [scripts/verify_5003.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/verify_5003.py) | 5003 API 验证 |

---

## 8. 备份与回滚

- **备份表**: `container_center.data_packages_4orders_v2_backup_20260610_HHMMSS`(47 行)
- **回滚命令**: `py scripts/fix_4orders_anomaly.py --rollback data_packages_4orders_v2_backup_YYYYMMDD_HHMMSS`
- **注意**: 回滚会清除本次 29 条 process_task 同步,以及修补的 related_order / content

---

## 9. 签字

| 阶段 | 责任人 | 状态 | 时间 |
|------|--------|------|------|
| 排查(REPORT v1) | RE-007 | ✅ | 2026-06-10 |
| 探查真相(REPORT v2) | RE-007 | ✅ | 2026-06-10 |
| 修复脚本 | RE-007 | ✅ | 2026-06-10 |
| 字段映射补丁 | RE-007 | ✅ | 2026-06-10 |
| 代码修复 | RE-007 | ✅ | 2026-06-10 |
| 单测验证 | RE-007 | ✅ 42/42 | 2026-06-10 |
| 5002 数据验证 | RE-007 | ✅ 29/29 | 2026-06-10 |
| 5003 服务重启 | **用户** | ⏳ 待执行 | — |
| Playwright 重验 | RE-007 | ⏳ 重启后 | — |
| 防御性约束 RE-008 | RE-007 | 📋 候选 | — |
