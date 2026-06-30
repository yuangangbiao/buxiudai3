# TODO: v3.8.1 data_packages 架构收敛

> **创建**: 2026-06-26
> **背景**: v3.8.1 完成 CRUD API 从 `data_packages` 到独立表的迁移，以及 `completed_qty` SSOT 修正。但 dispatch 中心层和质检流程仍依赖 `data_packages`，与移动端形成双写。
> **目标**: 彻底收敛 `data_packages` 表的写入路径，实现真正的 SSOT

---

## P0 — 必须修复（影响数据一致性）

### P0-1: container_center_api.py 与移动端 CRUD API 双写不一致

**问题描述**:
dispatch 中心层 (`container_center_api.py`) 仍在向 `data_packages` 写入 `process_code`、`is_public`、`is_broadcast`、`flow_type` 等字段，而移动端 CRUD API 已迁移到 `schedule_records` / `material_records` / `outsource_records`。两者形成双写，状态不一致。

**涉及代码位置**:
- `container_center_api.py:1557` — `UPDATE data_packages SET process_code=...`
- `container_center_api.py:1560` — `UPDATE data_packages SET content=JSON_SET(...)`
- `container_center_api.py:1580` — `UPDATE data_packages SET is_public=..., is_broadcast=...`
- `container_center_api.py:1592` — `UPDATE data_packages SET flow_type=...`

**影响范围**: dispatch 中心派工、广播标记、流程类型管理

**修复方向**:
1. 将 `process_code`、`is_public`、`is_broadcast`、`flow_type` 等字段迁移到 `schedule_records` 表
2. 将 `container_center_api.py` 中的派工逻辑改为写入 `schedule_records`
3. 保留 `data_packages` 作为只读历史（已有数据不删除）

**预估工时**: 4-6 小时

---

### P0-2: quality_inspection.py 仍写 data_packages.status

**问题描述**:
质检流程 (`quality_inspection.py`) 在报工后更新 `data_packages.status = 'quality_reported'`，但质检记录已存储在 `quality_records` 表，前端也从 `quality_records` 读取。`data_packages.status` 无人消费。

**涉及代码位置**:
- `quality_inspection.py:306` — `UPDATE data_packages SET status='quality_reported' WHERE id=...`
- `quality_inspection.py:310` — `UPDATE data_packages SET status='quality_reported' WHERE related_order=...`
- `quality_inspection.py:316` — `UPDATE data_packages SET status='quality_reported' WHERE related_order=... AND data_type='quality_task'`
- `quality_inspection.py:402` — `UPDATE data_packages SET status='pending' WHERE ...`

**影响范围**: 质检提交流程

**修复方向**:
1. 确认 `data_packages.status` 在生产代码中是否有读者
2. 若无人读，直接删除这些 UPDATE 语句
3. 质检状态统一由 `quality_records.status` 提供

**预估工时**: 1-2 小时

---

## P1 — 重要但不紧急（架构优化）

### P1-1: process_v2.py 仍写 data_packages

**问题描述**:
`process_v2.py` 在更新工序状态时写入 `data_packages.content`、`data_packages.title`、`data_packages.status`。

**涉及代码位置**:
- `process_v2.py:125` — `UPDATE data_packages SET content=..., title=..., status=... WHERE id=...`

**修复方向**: 改为更新 `process_sub_steps` 表的对应字段

**预估工时**: 1-2 小时

---

### P1-2: mobile/desktop 双写 completed_qty 路径不一致

**问题描述**:
- **Mobile** 报工：写入 `process_sub_steps.quantity`，由 `_sync_completed_qty_to_package` 维护 `completed_qty`
- **Desktop** 报工：直接写入 `process_sub_steps.completed_qty`

两套路径写入不同字段（quantity vs completed_qty），显示层依赖 `completed_qty`，但 mobile 路径是通过"事后同步"而非直接写入。

**涉及代码位置**:
- `app.py:process_sub_steps` 报工 — 写 quantity
- `standalone_dispatch_server.py` — 写 completed_qty

**修复方向**:
统一为 mobile/desktop 均直接写入 `process_sub_steps.completed_qty`（原子 UPDATE），移除 `quantity` 字段的"报工"语义。

**预估工时**: 2-3 小时

---

### P1-3: legacy_routes.py 读取 completed_qty 的字段来源验证

**问题描述**:
`legacy_routes.py:308` 读取 `ss.get('completed_qty', 0)`，需确认 `process_sub_steps` 表中 `completed_qty` 字段的来源是 mobile 路径还是 desktop 路径。若不一致，订单进度展示可能出现数值不匹配。

**涉及代码位置**:
- `legacy_routes.py:295-322` — 总体进度计算逻辑

**验证步骤**:
1. 检查 `process_sub_steps.completed_qty` 最近 7 天数据的手工 vs 扫码报工比例
2. 若 desktop 写 `completed_qty`、mobile 写 `quantity`，两套数据可能不一致
3. 确认 `get_sub_steps_by_process` 是否返回了 `completed_qty` 字段

**预估工时**: 2 小时

---

## P2 — 后续清理（低优先级）

### P2-1: 废弃方法彻底删除

当 P0-1、P0-2、P1-1 完成后，可安全删除：
- `mysql_storage.py:save_package` / `get_package` / `update_package` / `update_package_status` / `delete_package`
- `mysql_storage.py:cleanup_expired_packages`
- `mysql_storage.py:get_packages` / `get_packages_count_group` / `has_packages`

### P2-2: data_packages 表 DROP

确认零写入后，可执行：
```sql
-- 确认无新写入
SELECT MAX(updated_at) FROM data_packages;

-- 确认无活跃读取
-- （grep 全代码库后确认）

-- 可选：重命名为 data_packages_archive 做历史归档
ALTER TABLE data_packages RENAME TO data_packages_archive;
```

### P2-3: STORAGE_INVENTORY.md 最终评分

当 P0 全部完成后，分数应达到 **100/100**。

---

## 当前状态

| 任务 | 状态 | 备注 |
|------|:----:|------|
| P0-1: container_center_api.py 双写收敛 | 🔴 待处理 | dispatch 中心层架构问题 |
| P0-2: quality_inspection.py 死写入清理 | 🔴 待处理 | 需确认是否有读者 |
| P1-1: process_v2.py 写 data_packages | 🟡 待处理 | 工序状态更新路径 |
| P1-2: mobile/desktop 双写不一致 | 🟡 待处理 | completed_qty 字段来源 |
| P1-3: completed_qty 读取验证 | 🟡 待处理 | 进度计算数据源确认 |
| P2-1: 废弃方法删除 | 🟢 待 P0 后 | 依赖 P0 完成 |
| P2-2: data_packages 表 DROP | 🟢 待 P0 后 | 依赖 P0 完成 |
| P2-3: 文档评分 100/100 | 🟢 待 P0 后 | 依赖 P0 完成 |

**当前完成度**: 65% — v3.8.1 CRUD 迁移 ✅ + completed_qty SSOT 修正 ✅
