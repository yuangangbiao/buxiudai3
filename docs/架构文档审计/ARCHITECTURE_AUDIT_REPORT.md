# 架构文档审计报告

> 审计日期: 2026-06-20
> 审计范围: `docs/` 下所有架构相关文档
> 真值来源:
> - 入口文件: `mobile_api_ai/{app.py, standalone_dispatch_server.py, container_center_api.py, inventory_api_server.py, sync_bridge_server.py}` + `start_*.py`
> - 配置: `core/_config_infra.py`
> - 默认存储: `mobile_api_ai/container_center_v5.py` (`DEFAULT_STORAGE_TYPE`)
> - 规则: `d:\yuan\.trae\rules\wechat_server_cloud_only.md`

---

## 一、当前架构真值

### 1.1 服务端口（5 个活跃 + 1 个外部）

| 端口 | 入口 | 状态 | 启动脚本 |
|:----:|------|:----:|----------|
| **5002** | `container_center_api.py` | ✅ 活跃 | `start_5002.py` |
| **5003** | `standalone_dispatch_server.py` | ✅ 活跃 | `start_5003.py` |
| **5008** | `app.py` | ✅ 活跃 | `start_5008.py` |
| **5010** | `inventory_api_server.py` | ✅ 活跃 | `start_5010.py` |
| **8008** | `sync_bridge_server.py` | ✅ 活跃 | `start_8008.py` |
| 5000 | `dashboard_server.py` | ❌ **文件不存在** | 旧版本 |
| 5006 | 云端 `124.223.57.82` | ☁️ 外部 | 不可本地启动 |

### 1.2 数据库（3 个 MySQL + 1 个 SQLite 桌面端副本）

| 库名 | 类型 | 用途 | 配置项 |
|------|------|------|--------|
| `steel_belt` | MySQL | 桌面端主权威 | `DB_HOST/PORT/USER/PASS` |
| `container_center` | MySQL | 容器池/流程运行时 | `CONTAINER_STORAGE_TYPE=mysql`（默认） |
| `inventory_db` | MySQL | 库存独立 | `INVENTORY_*` |
| `steel_belt.db` | SQLite | 桌面端本地副本 | `SQLITE_DB_PATH` |

### 1.3 关键事实

- **容器池默认存储 = MySQL**（`container_center_v5.py:61`）
- **DEPRECATED SQLite**: `wechat_container.db` / `container_center.db` / `chengsheng.db` / `operation_logs.db`（保留仅为兼容）
- **wechat_server.py 是云端专用**（`.trae/rules/wechat_server_cloud_only.md`），本地禁止修改
- **本地 5003 入口 = `standalone_dispatch_server.py`**（不是 `dispatch_center.py`）
- **5001 端口未作为服务端口使用**（仅错误码 `5001` 出现 28 次）

---

## 二、不符项分类

| 类别 | 不符项 | 涉及文档数 | 严重度 |
|------|--------|:----------:|:------:|
| A. 旧服务名（`wechat_work_bot_v2.py` / `wechat_server.py` / `inventory_*.py` 等已删除/被替换） | 5 类 | 25+ | 🔴 HIGH |
| B. 容器池 = SQLite（已迁移到 MySQL） | 3 处 | 8 | 🔴 HIGH |
| C. 端口错配（5001 / 5006 直连 / 80 等） | 4 类 | 12 | 🟠 MEDIUM |
| D. 已删除文件（`dashboard_server.py` / `dispatch_center.py` / `quick_test.py` 等） | 6 个 | 15+ | 🟠 MEDIUM |
| E. 早期 API Key 或旧 IP 配置 | 2 类 | 6 | 🟡 LOW |

---

## 三、详细不符清单

### 🔴 A 类：旧服务名 / 已替换模块

| ❌ 文档中提到 | ✅ 实际 | 影响文档 |
|---------------|--------|---------|
| `wechat_work_bot_v2.py` | ❌ 文件已删除 | `docs/数据分层架构说明.md` / `docs/混合方案使用说明.md` / `docs/企业微信应用机器人部署指南.md` / `docs/任务接收系统使用说明.md` / `docs/企业微信应用机器人/ALIGNMENT_企业微信应用机器人.md` / `docs/企业微信应用机器人/TASK_企业微信应用机器人.md` |
| `wechat_work_bot.py` | ❌ 文件已删除 | 同上 |
| `wechat_server.py`（作为本地入口） | ✅ 实际是云端专用 | `docs/RE-002_消息触发链路修复/ACCEPTANCE_RE-002.md` / `docs/架构重构/` 系列 / `docs/工单绑定/CONSENSUS_工单绑定.md` / `docs/全面测试/FINAL_全面测试.md` / `docs/消除裸except/` 系列 |
| `dispatch_center.py`（作为本地 5003 入口） | ✅ 实际是 `standalone_dispatch_server.py` | `docs/RE-002_*` / `docs/架构重构/` / `docs/内联对话框重构/` / `docs/工单绑定/` / `docs/RE-002_消息触发链路修复/` 等 |
| `inventory_server.py` / `inventory_client.py` / `inventory_configurator.py` / `inventory_db_complete.py` / `inventory_print.py` / `inventory_backup.py` / `inventory_manager_complete.py` | ❌ 全部已删除，已被 `inventory_api_server.py` 替代 | `README.md` / `docs/扫码报工系统接口说明.md` |
| `quick_test.py` | ❌ 文件已删除 | `docs/数据分层架构说明.md` / `docs/混合方案使用说明.md` |

### 🔴 B 类：容器池 = SQLite 错误

| ❌ 文档中描述 | ✅ 实际 | 影响文档 |
|---------------|--------|---------|
| `wechat_container.db`（SQLite 容器池） | ✅ 已迁移到 MySQL `container_center` | `docs/数据分层架构说明.md` (第22, 88, 165行等) / `docs/混合方案使用说明.md` (全文) / `docs/任务接收系统使用说明.md` / `docs/企业微信应用机器人/ALIGNMENT_企业微信应用机器人.md` |
| `task_pool.db` / `tmpjl983k73.db` | ❌ 不存在，容器池是 MySQL | `docs/容器池持久化/ACCEPTANCE_容器池持久化.md` / `docs/容器池持久化/FINAL_容器池持久化.md` / `docs/容器池持久化/TODO_容器池持久化.md` |
| `data/enterprise_structure.json` 作为运行时存储 | ✅ 已迁移到 MySQL | `core/_config_infra.py:168`（DEPRECATED 注释） |

### 🟠 C 类：端口错配

| ❌ 文档提到 | ✅ 实际 | 影响文档 |
|------------|--------|---------|
| 5001 端口 | ✅ 仅作为错误码，非服务端口 | `docs/模块化改造/ERROR_CODES.md` / `docs/模块化改造/API.md` / `docs/企业微信应用机器人部署指南.md`（5003 内部提到 5001） |
| 5000 端口（dashboard_server.py） | ❌ 文件不存在 | `docs/工单绑定/ALIGNMENT_工单绑定.md` / `docs/工单绑定/CONSENSUS_工单绑定.md` / `docs/SSOT架构改造/ARCHITECT_SSOT架构改造.md` / `docs/云端去除调度中心功能/CONSENSUS_云端去除调度中心功能.md` |
| 5006 端口（直连） | ✅ 应通过 5003 转发，不直连 | `docs/小智审查漏洞修复报告_20260615.md` / `docs/订单号与工序对应检查/DEPLOY_v6.0.1.md` / `docs/架构重构/TASK_3.2_统一部署模式.md` / `docs/全面测试/TODO_全面测试.md` |
| 80 / 443 端口 | ✅ 仅用于文档说明，实际服务都是 5xxx/8xxx | `docs/P1P2修复_2026_06_18/` / `docs/order_status_classify_ssot/` / `docs/SSOT架构改造/` 等多处 |

### 🟠 D 类：已删除文件被引用

| ❌ 文件 | ✅ 实际状态 | 引用文档 |
|---------|------------|---------|
| `mobile_api_ai/dashboard_server.py` | ❌ 不存在 | `docs/小智审查漏洞修复报告_20260615.md` / `docs/工单绑定/` / `docs/全面测试/` / `docs/消除裸except/` |
| `mobile_api_ai/dispatch_center.py` | ❌ 不存在 | `docs/RE-002_*` / `docs/架构重构/` / `docs/工单绑定/CONSENSUS_工单绑定.md` / `docs/消除裸except/` 等 |
| `mobile_api_ai/quick_test.py` | ❌ 不存在 | `docs/数据分层架构说明.md` / `docs/混合方案使用说明.md` |
| `mobile_api_ai/inventory_*.py`（7个） | ❌ 全部已删除 | `README.md` / `docs/扫码报工系统接口说明.md` |
| `wechat_work_bot*.py` | ❌ 全部已删除 | 见 A 类 |

### 🟡 E 类：旧 IP / API Key

| 项 | 说明 | 文档 |
|----|------|------|
| API Key `Wk9Q-8X7Z-3K2M-5P6L` | ✅ 仍正确，但仅出现 1 处 | `docs/服务架构_端口与蓝图.md` / `docs/三元派工架构/ACCEPTANCE_M1_全员派工.md` |
| `124.223.57.82` 直连 | ❌ 应通过 5003 转发 | `docs/P1P2修复_2026_06_18/ACCEPTANCE_P1P2修复.md` / `docs/云端去除调度中心功能/TODO_云端去除调度中心功能.md` |

---

## 四、归档清单

### A. 整文档归档（4 份 - 主体已严重过期）

| 文档 | 原因 |
|------|------|
| `docs/数据分层架构说明.md` | 容器池 = SQLite 错误，引用已删除文件 `wechat_work_bot_v2.py` / `quick_test.py` |
| `docs/混合方案使用说明.md` | 同上 |
| `docs/任务接收系统使用说明.md` | 引用已删除文件 |
| `docs/容器池持久化/` (3 个文件) | 容器池 = SQLite 错误，整个方案已废弃 |

### B. 局部过期（仅标注"部分过期"+保留目录）

| 文档/目录 | 状态 |
|-----------|------|
| `docs/架构重构/` 目录 | 多个 `wechat_server.py` / `dispatch_center.py` 引用过期，但部分设计仍有效 |
| `docs/RE-002_消息触发链路修复/` | 引用 `dispatch_center.py` 过期 |
| `docs/消除裸except/` | 引用旧服务名 |
| `docs/工单绑定/` | 引用 `dashboard_server.py` (不存在) / `wechat_server.py` |
| `docs/企业微信应用机器人/` | 引用 `wechat_work_bot_v2.py` (已删除) |
| `docs/全面测试/` | 引用 `wechat_server.py` 旧服务名 |
| `docs/模块化改造/ERROR_CODES.md` | 5001 端口误用 |
| `docs/扫码报工系统接口说明.md` | 引用已删除的 `inventory_*.py` 套件 |
| `docs/任务接收系统使用说明.md` | 引用已删除的 `wechat_work_bot_v2.py` |
| `docs/README.md` 自身 | 引用已删除的 `inventory_*.py` 套件 |
| `docs/小智审查漏洞修复报告_20260615.md` | 5000 端口/dashboard_server 过期 |
| `docs/订单号与工序对应检查/DEPLOY_v6.0.1.md` | 5006 直连错误 |
| `docs/架构重构/TASK_3.2_统一部署模式.md` | 同上 |
| `docs/SSOT架构改造/ARCHITECT_SSOT架构改造.md` | 引用 `dashboard_server.py` 过期 |

### C. 真实值符合（无需修改）

- `docs/服务架构_端口与蓝图.md` ✅（虽然 5000 描述有误，但主体正确）
- `docs/全局架构细分.md` ✅（数据已迁移，描述基本符合）
- `docs/全流程架构图.md` ✅（流程图正确）
- `docs/system_design.md` ✅（手机端 API 5008 描述正确）
- `docs/云端通信架构规范.md` ✅
- `docs/Python运行环境规范.md` ✅
- `docs/排产流程规范*.md` ✅

---

## 五、行动项

1. **立即归档 A 类 4 份文档** → `docs/架构文档审计/archive/`
2. **B 类 13 份文档标注"部分过期"** → 在文档头部加 `> ⚠️ 本文档部分内容已过期，详见 audit report`
3. **C 类无需修改**
4. **更新 `README.md`** 删除已删除的 `inventory_*.py` 套件引用

---

## 六、审计评分

| 维度 | 得分 | 说明 |
|------|:----:|------|
| 文档与代码一致性 | 50/100 | 50+ 处过期引用，4 份文档完全过期 |
| 文档可读性 | 80/100 | 大部分文档结构清晰，但内容时效性差 |
| 维护及时性 | 40/100 | 多份文档停留在 2026-05 之前 |
| **综合** | **57/100** | 🟡 MEDIUM - 需立即处理 A 类归档 |
