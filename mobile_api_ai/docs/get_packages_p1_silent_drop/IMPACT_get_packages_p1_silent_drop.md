# 业务影响报告 - get_packages P1 静默丢数据修复

## 1. 用户场景对比

> 改善前（痛点） → 改善后（价值）表格

| # | 用户角色 | 改善前（痛点） | 改善后（价值） |
|---|---------|---------------|---------------|
| 1 | 质检员 (质检模块 UI) | 打开质检任务列表 → 看到空白 → 误以为今日无质检任务, 实际是 API 静默返 `[]` | 列表正常显示 35 条质检记录（含 inspection_type=normal/异常), 可点击处理 |
| 2 | 仓库管理员 (备料模块 UI) | 物料申请 (material_request) 显示正常, 但**领料 (material_pickup) 任务列表始终空白**, 实际有 0 条 (表为空) → 数据真实性无法验证 | material_pickup 走正确查询路径, 即使 0 条也能确认 "查了, 没有", 而非 "系统坏了" |
| 3 | 外协管理员 | 外协任务列表一直空白, 不知道是没外协任务还是系统 bug | outsource 表正确查询, 业务真实状态可见 |
| 4 | 报修人员 | 报修任务列表空白, 报修工单无人响应 | repair 表正确查询, 报修流程可追踪 |
| 5 | 调度中心 (后台 API) | `legacy_routes.py:599` `cc.storage.get_packages(data_type='quality_task', limit=200)` 永远返 `[]` → 上层 UI 看到的质检任务数永远是 0 | 真实返回 35 条数据 (limit 20 截断), 业务监控准确 |

## 2. 业务能力新增

> 按业务流分类

| 业务流 | 新增/优化功能 | 影响范围 |
|--------|--------------|---------|
| 质检 | 6 个 P1 data_type 中 2 个 (quality_inspection / quality_task) 现在能正常查表, 真实表 35 行可查 | 优化: 质检任务列表从空白变为可显示 |
| 物料 | material_request / material_purchase (已修) + material / material_pickup (本次修) 共 4 个 data_type 全覆盖 | 优化: 物料申请 + 领料两条业务线查询一致 |
| 外协 | outsource 之前静默丢数据 → 现可正确查 outsource_records | 优化: 外协任务可见性 |
| 报修 | repair 之前静默丢数据 → 现可正确查 repair_records | 优化: 报修流程可追踪 |
| 监控 | `get_packages_count_group` 仍用内联 list (留 P2), 但 `get_packages` 派发逻辑统一了 | 部分优化: 监控口径与查询口径开始对齐 |

## 3. 不变更部分

> 防回归保护清单（哪些保持原样，行为零变更）

| # | 模块/功能 | 保护措施 | 验证方式 |
|---|----------|---------|---------|
| 1 | `save_package` (L1009) | 未触碰, 仍用 `_TASK_TYPE_TABLE_MAP.get(data_type)` | 22 个测试中未调用 save, 但导入 storage 无错 |
| 2 | `get_packages` 8 个已修分支 (quality / material_request / material_purchase / process系) | 不破坏 | test_get_packages_process_report.py 17/17 通过 (0.58s) |
| 3 | `get_packages` 未知 data_type 返 `[]` 行为 | 保留 | test_unknown_data_type_returns_empty / test_no_data_type_returns_empty 通过 |
| 4 | `get_packages` 无 data_type 返 `[]` 行为 | 保留 | 同上 |
| 5 | `fetch_all` 返 None 降级为 `[]` 行为 | 保留 | test_fetch_all_returns_none_fallback_to_empty_list 通过 |
| 6 | `status` / `related_order` / `limit` / `offset` 过滤参数 | 完全兼容 8 个旧分支 + 6 个新分支 | test_regression (8) + test_p1_filters (4) 通过 |
| 7 | `_TASK_TYPE_TABLE_MAP` 14 个 key 完整内容 | 内容锁定 | test_static_assert_table_map_contents 通过, 防意外增删 |
| 8 | `get_package` (L1241) / `delete_package` (L1253) | 未触碰 | (无变更需要测试) |
| 9 | `package_exists` (L1190) | 未触碰 (虽然也有同类问题, 但任务范围外) | 留 P2 |
| 10 | `get_packages_count_group` (L1163) | 未触碰 (虽然也有同类问题, 但任务范围外) | 留 P2 |

## 4. 一句话总结

> 本次改动让 `MySQLStorage.get_packages` 从 **"硬编码 if/elif 漏 6 个 data_type 静默返 []"** 变为 **"查 _TASK_TYPE_TABLE_MAP 自动派发, 14 个 key 全覆盖"**, 真实业务场景 (质检/物料领料/外协/报修) 从 **"列表空白, 业务方误以为无数据"** 变为 **"准确查询 5 张业务表, 0 静默丢数据"**。

---

## 数字三要素 (业务影响维度)

| 维度 | 数字 | 测量命令 | 测量时间 | 文件来源 |
|------|------|---------|---------|---------|
| 修复点数量 | 6 个 data_type | grep "_TASK_TYPE_TABLE_MAP" | 2026-06-23 14:20 | mysql_storage.py:992-1007 |
| 测试通过率 | 22/22 (新) + 17/17 (旧) = 39/39 (100%) | `python -m pytest -v` | 2026-06-23 14:25-27 | tests/unit/test_get_packages_*.py |
| 代码行数变化 | -20 行 (50 行 if/elif → 30 行查表) | `git diff HEAD -- storage/mysql_storage.py` | 2026-06-23 14:30 | mysql_storage.py:1127-1161 |
| E2E 真实数据 | quality_records 35 行 → get_packages 返 20 行 | `python tests/unit/e2e_get_packages_p1_silent_drop.py` | 2026-06-23 14:29 | e2e 输出: `data_type="quality_task" → quality_records | get_packages: 20 行 (2.6ms) \| 真实表行数: 35` |
| 真实业务调用点 | 1 处 (legacy_routes.py:599) | grep "get_packages.*quality_task" | 2026-06-23 14:21 | api/legacy_routes.py:599 |
| 查询响应时间 | 0.9-14.0ms (各 data_type) | E2E 实时打印 | 2026-06-23 14:29 | e2e 输出 |

---

## 已知未闭环 (主动暴露)

| # | 模块 | 风险描述 | 建议 |
|---|------|---------|------|
| 1 | `package_exists` (L1190-1206) | 内联 dict 只覆盖 7 个 key, 漏 7 个 (quality_inspection / quality_task / material / material_pickup / report / process_report / process_task) | P2: 改用 `_TASK_TYPE_TABLE_MAP.get()` 自动派发 |
| 2 | `get_packages_count_group` (L1163-1188) | 内联 list 5 个表, 不走 `_TASK_TYPE_TABLE_MAP`, 统计口径可能漏表 | P2: 改用遍历 `_TASK_TYPE_TABLE_MAP.values()` |

**本次修复仅覆盖 `get_packages`, 这两个模块未触碰, 是诚实暴露的已知风险。**
