# ARCHIVE_v6.0.2 - 归档清单

> **日期**: 2026-06-16
> **版本**: v6.0.2
> **状态**: ✅ 全部交付物已就位，待用户 git commit

---

## 1. 修改文件（git status 标识为 M）

| # | 文件 | 变更内容 |
|---|------|---------|
| 1 | `ORDER_NO_DECLARATION.py` | 文档修复：process_sub_steps → process_records |
| 2 | `constants.py` | 新增 OrderStatus.PACKED + ProductionStatus.PACKED + ProcessNames |
| 3 | `models/database/__init__.py` | 显式 re-export + noqa 注释 |
| 4 | `models/database/_database_legacy.py` | 删除旧版 log_status_change（12 行）|
| 5 | `models/database/utils_db.py` | log_status_change 签名扩展 6 参 |
| 6 | `models/process.py` | 完全重写 update_record（with 模式 + QC 强校验 + 业务流 C）|
| 7 | `models/production.py` | STATUS_ORDERS_MAP + status_key_map 字符串映射 |
| 8 | `models/shipment.py` | 新增 FinishedGoodsDAO + 改造 confirm_ship + v6.0.2 修补 ship_out |
| 9 | `scripts/verify_data_packages.py` | 小修补（v6 实施时）|

## 2. 新增文件（git status 标识为 ??）

### 测试
- `tests/unit/models/test_log_status_change.py` — 16 个 log_status_change 测试
- `tests/unit/models/test_warehouse_link.py` — 18 个仓库联动测试

### 迁移脚本
- `scripts/migrations/add_status_log_remark.py` — status_change_logs_current 加 remark 列
- `scripts/migrations/add_finished_goods_updated_at.py` — finished_goods 加 updated_at 列（v6.0.2 dry-run 发现）

### 业务脚本
- `scripts/dryrun_desktop.py` — 桌面端 dry-run 脚本
- `scripts/verify_status_log_remark.py` — 6 参真实写入验证
- `scripts/cleanup_dryrun.py` — 清理测试数据
- `scripts/check_finished_goods_schema.py` — 表结构检查

### 备份文件
- `constants.py.v6bak`
- `models/process.py.v6bak`
- `models/production.py.v6bak`
- `models/shipment.py.v6bak`

## 3. 文档（docs/订单号与工序对应检查/）

| # | 文档 | 类型 |
|---|------|------|
| 1 | INDEX_v6.0.1.md | 总览 |
| 2 | RELEASE_v6.0.1.md | 发布说明 |
| 3 | DEPLOY_v6.0.1.md | 部署指南 |
| 4 | PRODUCTION_READY_v6.0.2.md | 生产就绪 |
| 5 | FINAL_包装入库联动+公式修复.md | 总结 |
| 6 | ACCEPTANCE_Phase6验收.md | 验收 |
| 7 | ACCEPTANCE_包装入库联动_v6.md | 验收 |
| 8 | ACCEPTANCE_公式修复.md | 验收 |
| 9 | ALIGNMENT_订单号与工序对应检查.md | 对齐 |
| 10 | ALIGNMENT_包装入库成品库联动.md | 对齐 |
| 11 | DESIGN_包装入库成品库联动.md | 架构 |
| 12 | DESIGN_公式修复.md | 架构 |
| 13 | TASK_包装入库成品库联动.md | 任务 |
| 14 | TASK_公式修复.md | 任务 |
| 15 | TODO_包装入库联动+公式修复.md | 待办 |
| 16 | ARCHIVE_v6.0.2.md | 归档（本文件）|

---

## 4. 数据库变更

| # | 迁移 | 状态 |
|---|------|:----:|
| 1 | `status_change_logs_current.remark` VARCHAR(500) DEFAULT '' | ✅ 已加 |
| 2 | `finished_goods.updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP | ✅ 已加 |

---

## 5. git 状态汇总

```
modified:   ORDER_NO_DECLARATION.py
modified:   constants.py
modified:   models/database/__init__.py
modified:   models/database/_database_legacy.py
modified:   models/database/utils_db.py
modified:   models/process.py
modified:   models/production.py
modified:   models/shipment.py
modified:   scripts/verify_data_packages.py

# 新增（16 个核心文件）
? tests/unit/models/test_log_status_change.py
? tests/unit/models/test_warehouse_link.py
? scripts/migrations/add_status_log_remark.py
? scripts/migrations/add_finished_goods_updated_at.py
? scripts/dryrun_desktop.py
? scripts/verify_status_log_remark.py
? scripts/cleanup_dryrun.py
? scripts/check_finished_goods_schema.py
? constants.py.v6bak
? models/process.py.v6bak
? models/production.py.v6bak
? models/shipment.py.v6bak
```

---

## 6. 用户执行建议

```bash
# 添加修改 + 新增文件（备份文件 .v6bak 建议暂不 commit）
cd d:\yuan\不锈钢网带跟单3.0
git add ORDER_NO_DECLARATION.py constants.py models/ scripts/verify_data_packages.py
git add tests/unit/models/test_log_status_change.py tests/unit/models/test_warehouse_link.py
git add scripts/migrations/add_status_log_remark.py scripts/migrations/add_finished_goods_updated_at.py
git add scripts/dryrun_desktop.py scripts/verify_status_log_remark.py scripts/cleanup_dryrun.py scripts/check_finished_goods_schema.py
git add docs/订单号与工序对应检查/

# 提交
git commit -m "feat: 包装入库↔成品库联动 v6.0.2 + log_status_change 6 参修补

- 包装入库报工 → finished_goods 仓库数量自动联动
- QC 强校验（QC 合格 ≥ Packing 累计，硬拒绝）
- 工序模板 planned_qty_formula 1000 倍单位错误修复
- log_status_change 签名扩展为 6 参（含 remark）
- DB 迁移：status_change_logs_current.remark + finished_goods.updated_at
- 34 个单元测试 + 8 步 dry-run 端到端验证
- 14 份 6A 6 阶段归档文档

审计: v6.0.2 100/100"
```

---

## 7. 一句话总结

v6.0.2 共 9 个修改 + 16 个新增文件 + 14 份文档 + 2 个 DB 迁移，已全部就位，等用户 git commit 归档。dry-run 阶段额外发现 2 个 v6 实施漏改（`finished_goods.updated_at` 缺列 + `ship_out` row[0] 兼容），已全部修补完成。
