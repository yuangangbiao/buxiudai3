# ACCEPTANCE 库存功能优化（实施验收记录）

> 项目：库存管理系统 v2.3 优化（19 项修复 + 数据库迁移 + 服务恢复）
> 实施日期：2026-06-03
> 实施人：AI 结对编程 + 用户决策

---

## 1. 19 项代码层修复（前期方案）

| # | 修复项 | 涉及文件 | 状态 |
|---|--------|---------|------|
| C-1 | MySQL 5.6+ 兼容的动态 DDL（替换 `ADD COLUMN IF NOT EXISTS`）| `migrations/001_function_optimization.sql` | ✅ |
| C-2 | 安全装饰器 `safe_require_feature`（灰度检查失败降级放行）| `inventory_web/feature_flags.py` | ✅ |
| H-1 | Windows 批处理 UTF-8 支持（`chcp 65001` + `PYTHONIOENCODING=utf-8`）| `scripts/install_transfer_reaper_windows.bat` | ✅ |
| H-2 | SQL `%Y-%m` 转义（替换 `DATE_FORMAT` 为 `CONCAT(YEAR(), '-', LPAD(MONTH(), 2, '0'))`）| `report_service.py` | ✅ |
| H-3 | Service 层 feature flag bypass 修复（加 `_feature_enabled` 检查）| `transfer_service.py` | ✅ |
| O-1 | 模板变量缺失导致 500（`dashboard.html` 9 个变量补齐 + try/except）| `routes_core.py` | ✅ |
| O-2 | 模板变量缺失（`stock_list.html`）| `routes_core.py` | ✅ |
| O-3 | 模板变量缺失（`inbound_page.html`）| `routes_core.py` | ✅ |
| O-4 | Jinja2 `UndefinedError`（`items` 数组补传）| `routes_core.py` | ✅ |
| O-5 | TypeError: Undefined JSON serializable 修复 | `routes_core.py` | ✅ |
| S-1 | CSRF token 生成 | `inventory_web/admin_auth.py` | ✅ |
| S-2 | Admin 登录限流（5 次失败锁 5 分钟）| `inventory_web/rate_limiter.py` | ✅ |
| S-3 | 输入校验 + 转义 | `routes_core.py` | ✅ |
| B-1 | BarcodeDetector API 浏览器原生降级（`textContent` 防 XSS）| `static/vendor/html5-qrcode.min.js` | ✅ |
| P-1 | XLSX 性能测试 + OOM 保护 + 内存检查 | `scripts/perf_test_xlsx.py` | ✅ |
| T-1 | 传输清理 cron（Linux `.sh` + Windows `.bat`）| `scripts/install_transfer_reaper_cron.sh` / `.bat` | ✅ |
| T-2 | Cron 任务日志路径/超时可配置（环境变量）| 同上 | ✅ |
| F-1 | 灰度发布白名单默认 False + reload 函数 | `inventory_web/feature_flags.py` | ✅ |
| F-2 | 环境变量预检（`FLASK_SECRET_KEY` ≥32 字符）| `inventory_api_server.py` | ✅ |

---

## 2. 服务启动错误修复（5 阶段）

| 阶段 | 错误 | 根因 | 修复 |
|------|------|------|------|
| ① 启动失败 | `[CRITICAL] FLASK_SECRET_KEY 必须设置（≥32字符随机）` | 父进程未注入 | IDE 启动器注入 FLASK_SECRET_KEY |
| ② 500 错误 | `dashboard.html` Jinja2 渲染失败 | 模板变量未传 | 补 9 个变量 + try/except |
| ③ 500 错误 | 5 路由模板变量缺失 | 同上 | 逐个补齐 |
| ④ 500 错误 | `POST /login` → 500 AttributeError | `rate_limiter` 是函数不是实例 | 重写 `rate_limiter.py`，把模块级 `rate_limiter` 立即绑定为实例 |
| ⑤ 401 错误 | 密码不匹配 | IDE 启动器注入的 `INVENTORY_ADMIN_PASSWORD_HASH` 是 .env 修改前的旧值（`load_dotenv` 默认不覆盖）| `start_inventory_clean.py` 用 `load_dotenv(override=True)` 强制覆盖 |

---

## 3. 密码临时降级（开发用途）

- **临时密码**：`Admin@2026`
- **生成方式**：`scripts/generate_password_hash.py` + 写入 `.env` 第 5 行
- **位置**：`d:\yuan\不锈钢网带跟单3.0\.env` 第 5 行
- **备份**：`d:\yuan\不锈钢网带跟单3.0\.env.bak.<timestamp>`
- ⚠️ **生产部署前必须重置**

---

## 4. ⚠️ 数据库落地审计（重要发现）

### 4.1 真相

前期所有"功能优化"在数据库层面**完全没落地**。证据：

| 检查项 | `container_center` | `steel_belt` | `inventory_db` |
|---|---|---|---|
| `products` 表存在？ | ❌ 不存在 | ❌ 不存在 | ✅ 存在 |
| `last_purchase_price` 字段？ | — | — | ✅（本次新加）|
| `last_purchase_price_at` 字段？ | — | — | ✅（本次新加）|
| 索引 `uk_products_code_active`？ | — | — | ✅（本次新加）|
| `users` / `notifications` / `import_sessions` / `stocktakes` / `transfers` / `transfer_items` / `stocktake_items` | ❌ | ❌ | ✅（本次新建）|

### 4.2 根因

`.env` 中 `INVENTORY_DB_NAME=container_center` 是**错库配置**（这是跟单系统的库，不是库存库）。即使 001 迁移脚本被执行过，它会：
- 在 `container_center` 库找不到 `products` 表 → 全部 `ALTER` 静默失败
- 新表 `users` / `notifications` / `stocktakes` / `transfers` 等创建在 `container_center`（错库）

### 4.3 修正

- ✅ 将 `INVENTORY_DB_NAME` 改为 `inventory_db`（真实库存库）
- ✅ 一次性执行 `migrate_inventory_db_v2.py` 完成所有迁移

### 4.4 实际迁移清单（全部在 `inventory_db` 库）

#### 4.4.1 RENAME
- `products.sku` → `products.code`（代码全用 `code`，原 55 行 SKU 数据保留为 code 值）

#### 4.4.2 ADD COLUMN（8 张表加 `deleted_at`）
- `products`, `suppliers`, `categories`, `warehouses`, `inventory`, `inventory_transactions`, `inventory_alerts`, `operation_logs`

#### 4.4.3 ADD COLUMN（业务字段）
- `products.last_purchase_price`, `products.last_purchase_price_at`, `products.max_stock`
- `warehouses.is_active`, `warehouses.manager`
- `categories.parent_id`
- `inventory_transactions.status`, `cancel_reason`, `cancelled_at`, `cancelled`, `reason`, `receiver`

#### 4.4.4 CREATE TABLE（7 张新表）
- `stocktakes`（盘点单）
- `stocktake_items`（盘点明细）
- `transfers`（调拨单）
- `transfer_items`（调拨明细）
- `notifications`（多用户通知，含 `user_id`）
- `import_sessions`（XLSX 批量导入会话）
- `users`（多用户账号）

#### 4.4.5 CREATE INDEX（8 个）
- `idx_products_deleted`, `idx_suppliers_deleted`, `idx_categories_deleted`, `idx_warehouses_deleted`
- `idx_inv_wh_product`, `idx_inv_qty`
- `idx_trans_created`
- 复合唯一索引 `uk_products_code_active (code, deleted_at)`

### 4.5 备份与回滚

8 张备份表（可 RENAME 还原）：

```
products_backup_20260603_195145
inventory_backup_20260603_195145
inventory_transactions_backup_20260603_195145
warehouses_backup_20260603_195145
suppliers_backup_20260603_195145
categories_backup_20260603_195145
inventory_alerts_backup_20260603_195145
operation_logs_backup_20260603_195145
```

回滚示例：
```sql
RENAME TABLE products TO products_migrated,
             products_backup_20260603_195145 TO products;
```

### 4.6 验证

- ✅ Dashboard 渲染正常（长度 11116 字符，含实际数据）
- ✅ 数据样本：`SKU-0001` M8×50镀锌六角螺栓 / 1号仓 / 500件 / 安全库存50
- ✅ 无其他库污染（`container_center` / `steel_belt` 中无 `_backup_20260603_195145` 残留）

---

## 5. 当前服务状态

| 组件 | 状态 | 信息 |
|------|------|------|
| 库存服务 | ✅ 运行 | PID 24932，监听 5010 |
| 数据库 | ✅ 连接 | `inventory_db` 库 |
| 登录 | ✅ 正常 | 密码 `Admin@2026` |
| Dashboard | ✅ 正常 | 显示 55 商品 / 16382 / 16595 / 26 / 50 / 36 / 65 等真实数据 |
| 调度中心 | ✅ 运行 | PID 未变，5003 端口轮询正常 |

---

## 6. 待办事项（生产前必须处理）

- [ ] **重置管理员密码**：用 `scripts/generate_password_hash.py "新密码"` 替换 `Admin@2026`
- [ ] **生产环境重新部署**：从 .env 加载（不依赖 IDE 注入）
- [ ] **运行 cron 任务**：传输清理 / 备份 / 通知分发
- [ ] **权限收敛**：删除 `scripts/` 下的诊断脚本（或移入 `scripts/diagnostics/`）
- [ ] **代码审计**：`migrate_inventory_db_v2.py` 中所有 DDL 已通过 INFORMATION_SCHEMA 预检（除 RENAME 操作），重复运行是幂等的

---

## 7. 文档归档

- 迁移脚本：`mobile_api_ai/scripts/migrate_inventory_db_v2.py`（可重复运行）
- 审计脚本：`mobile_api_ai/scripts/diag_001_audit.py`、`diag_where_data.py`、`scan_all_dbs.py`
- 服务启动：`mobile_api_ai/scripts/start_inventory_clean.py`（强制 .env override）
- 密码重置：`mobile_api_ai/scripts/reset_admin_pwd_temp.py`
- 端到端测试：`mobile_api_ai/scripts/e2e_final.py`、`e2e_login_test.py`

---

> 文档更新于 2026-06-03 19:55（数据库落地审计 + 服务恢复完成）
