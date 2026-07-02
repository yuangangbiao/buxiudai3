# CHANGELOG

> 记录所有版本变更。遵循语义化版本（SemVer）规范。

---

## [v3.6.0] - 2026-07-02 - data_packages 业务分表收敛

### 🎯 重大变更
- **全面去除 data_packages 表**：11 业务表独立运营（process_sub_steps/material_records/quality_records/outsource_records/repair_records/approval_records/production_orders/schedule_flow_logs/process_records/tbl_configs）
- 9 业务表 + tbl_configs 全部加 6 字段（is_deleted/created_by/updated_by/updated_at）
- **status 字典统一**：pending / in_progress / completed（含特殊值 shortage/approved/rejected/cancelled/failed）
- 数据迁移 142 行（中文 status → 英文 status）

### ✨ 新增功能
- **approval_records 表**（18 字段 + 4 索引 + 1 CHECK 约束）— 之前无
- **4 重鉴权装饰器**（`@require_auth` + `@require_role` + `@require_owner_or_admin` + `@audit_log`）— 11 业务表 44 端点
- **11 路由白名单**（`data_type_router.py`）+ 批量接口（`get_packages_batch()`，UNION ALL 1 次查询）
- **quantity 业务化校验函数**（`utils/quantity_validator.py`）— 5 业务类型 × 4 边界
- **派工并发原子 INSERT**（`utils/dispatch_task.py`）— INSERT + IntegrityError（不累加）
- **全局异常处理器**（`utils/exception_handler.py`）— trace_id + 中文提示
- **全局日志脱敏**（`utils/log_sanitizer.py`）— 手机号 138****5678 / 身份证号 110101********1234
- **完整迁移脚本**（`migrations/v3_6_data_packages_split.sql`）— 7 段 + ROLLBACK 段

### 🐛 修复
- P1 silent_drop bug（6 测试用例）
- 派工并发累加 bug（100 线程 1 成功 + 99 冲突）
- 22 项安全漏洞（22 安全检查清单全过）
- 8 项越权漏洞（4 重鉴权防护）
- 20+ 处 global 变量改字典包装
- 20+ 文件 str(e) 异常泄露
- 3 处硬编码密码（88888888）
- 1 处云端直连（wechat_server 走 5003）

### 🗑️ 删除
- `data_packages` 表（已 RENAME + 触发器）
- `process_packages` / `quality_packages`（历史 ETL 中间表）
- `enterprise_structure` 表（F6 P9 已 DROP）
- `stats_smart_sheet/` 整个模块（云端 5005 端口废弃）
- 358 个 scripts/tools/archive 调试脚本移到 `archive/`

### 🔧 重构
- `get_packages()` 改为 11 路由 + 软删除过滤
- `get_packages_batch()` 批量接口（1 次 UNION ALL）
- `mysql_storage.py` 12 处 DDL 全部梳理
- `stats_engine.py` 3 处 data_packages 替换为 process_sub_steps
- `flow_type_alert.py` 注释中 data_packages 替换

### 📊 测试
- CP-1 检查点 8/8 通过
- CP-2 检查点 8/8 通过
- T1 11 路由 5/5 通过
- T2b 鉴权 8/8 通过
- T3 quantity 8/8 通过
- T4 派工并发 5/5 通过
- T6.5 日志脱敏 4/4 通过

### 🛡️ 8 项关键规范合规
- R-002 云端通信走 5003：✅ 0 处违规
- R-031 Flask global 禁止：✅ 0 处违规
- R-092 异常脱敏：✅ 0 处违规
- R-171 数据库密码加密：✅ 0 处违规
- R-220 设计文档：✅ 完整
- R-222 CHANGELOG：✅ 完整
- R-241 for remove 反模式：✅ 0 处违规
- 云端通信规范 v1.1：✅ 5005 已删除

### ⚠️ 破坏性变更
- `data_packages` 表物理废弃（已 RENAME + 触发器）
- status 字段字典统一（中文 → 英文）
- 业务接口需使用 `data_type` 参数（12 种白名单）
- 5 业务表加 is_deleted=0 过滤条件

### 📁 新增文件
- `storage/data_type_router.py` — 11 路由白名单
- `api/decorators.py` — 4 重鉴权
- `utils/exception_handler.py` — 全局异常
- `utils/log_sanitizer.py` — 日志脱敏
- `utils/quantity_validator.py` — quantity 业务化校验
- `utils/dispatch_task.py` — 派工并发
- `migrations/v3_6_data_packages_split.sql` — 完整迁移脚本
- `ci/check_stage_1.py` / `ci/check_stage_2.py` — CI 检查点
- `archive/` 目录（358 个备份文件）

---

## [v3.5.0] - 2026-07-01 - 之前版本

(略，见 `.workbuddy/docs/features/data_packages_split_v3/` 历史文档)
