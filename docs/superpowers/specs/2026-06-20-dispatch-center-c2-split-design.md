# 调度中心 _core.py 领域模块化重构设计方案

**版本**：v2.0（实际执行版）
**日期**：2026-06-20
**状态**：✅ 已实施（commit `63dcc136` + `7ca7c094` + `aa72abc7`）
**审计**：设计文档 3 轮 → 89/77/89；实际代码 1 轮 → 89/100

---

## 一、背景与目标

### 设计历程

最初方案（v1.x）是按 **Part 边界物理拆分**为 `_services.py` + `_routes/` 目录（13 个路由文件），经 3 轮悲观审计后认为该方案过于复杂。

实际执行改为**按领域模块抽取**，按业务边界将 `_core.py` 中的公共函数拆分为独立领域模块，保持 `_core.py` 物理完整，URL 完全不变。

### 当前状态

`_core.py` 当前 ~8784 行，包含 22 个 Part 段、~148 个路由、~185 个服务函数。

**重构目标**：
- 将公共函数按领域拆分为独立模块文件
- `_core.py` 保留 shim 函数（向后兼容），Part 结构不动
- URL、参数、返回值完全不变
- 可独立验证每个领域模块

---

## 二、三条铁律

1. **不动路由逻辑**——只抽取公共函数，不改路由行为
2. **单 Blueprint**——所有路由仍挂在 `dispatch_center_bp` 下，URL 不变
3. **向后兼容**——`_core.py` 保留 shim 函数，外部导入链零改动

---

## 三、文件结构（v2.0 — 实际执行结果）

```
dispatch_center/
├── __init__.py                  ← 导出 Blueprint + 常量 + 缓存 + worker
├── _core.py                    ← ~8784 行，Part 1~20b + 9 个 shim 函数
├── _constants.py               ← 配置常量（已重构）
├── _core_types.py              ← 类型定义，不动
├── schedule_routes.py           ← 独立 Blueprint，已用 ._db 统一入口
├── shipment_routes.py          ← 独立 Blueprint（新增）
├── _db.py                      ← 【新增】DB 连接层（~430 行）
├── _notify.py                  ← 【新增】通知层（微信/钉钉/企微/短信/模板）
├── _operators.py               ← 【新增】操作员管理层（客户组/工序映射/steel_belt）
├── _sync.py                    ← 【新增】同步层（SSOT 代理/订单同步/SAP）
├── services/
│   └── __init__.py            ← 【新增】通用工具函数
├── _db_test.py                 ← 【新增】DB 层测试
├── _notify_test.py             ← 【新增】通知层测试
├── _operators_test.py          ← 【新增】操作员层测试
├── _sync_test.py              ← 【新增】同步层测试（单元）
└── _sync_integration_test.py   ← 【新增】同步层测试（集成）
```

### shipment_routes.py 说明

发货管理 Blueprint（`shipment_bp`），独立于主调度 Blueprint，注册于 `standalone_dispatch_server.py`：

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/dispatch-center/shipping/pending` | GET | 待处理发货单 |
| `/api/dispatch-center/shipping/list` | GET | 发货单列表 |
| `/api/dispatch-center/shipping/create` | POST | 创建发货单 |
| `/api/dispatch-center/shipping/confirm-ship` | POST | 确认发货 |
| `/api/dispatch-center/shipping/confirm-receive` | POST | 确认收货 |
| `/api/dispatch-center/shipping/finished-goods` | GET | 成品库存 |
| `/api/dispatch-center/shipping/tracking-list` | GET | 物流追踪列表 |
| `/api/dispatch-center/shipping/query-tracking` | POST | 查询物流 |
| `/api/dispatch-center/shipping/subscribe-tracking` | POST | 订阅物流 |
| `/api/dispatch-center/shipping/health` | GET | 健康检查 |

---

## 四、_core.py 精简后结构

```
L1~13    文档头
L16~37   代码分区索引（22 个 Part 行号范围）
L40~163  Part 1: 导入（模块导入 + 环境变量）
L165~218 Part 2: 核心类与上下文（DispatchContext 等）
L220~1227 Part 3: 服务层函数（~1000 行公共函数）

L132~161 【v3.6.1 重构】领域模块导入
  from ._db import _get_mysql_connection, _get_container_center, _get_storage
  from ._db import get_dispatch_cache, _dispatch_cache
  from ._db import _ssot_cache_get, _ssot_cache_set, _ssot_cache_clear
  from ._db import _proxy_to_container_ssot
  from ._notify import (通知层函数...)
  from ._operators import (操作员管理函数...)
  from ._sync import (同步层函数...)

L220~1227 【v3.6.1 重构】9 个 shim 函数（向后兼容）
  def _get_customer_group_for_order(...):
      from ._operators import get_customer_group_for_order as _impl
      return _impl(...)
  ...（共 9 个）

L1228~8784 Part 4~20b: 所有路由（物理完整，未拆分）
```

### 索引表（22 个 Part，行号已核实）

| Part | 名称 | 行号范围 | 说明 |
|------|------|---------|------|
| 1 | 导入与初始化 | 164~181 | 模块导入 |
| 2 | 核心类与上下文 | 182~219 | DispatchContext 等 |
| 3 | 服务层函数 | 220~1227 | 公共函数（~1000 行） |
| 4 | 通知与消息路由 | 1228~1389 | 通知/消息路由 |
| 5 | 流程任务路由 | 1390~1557 | 流程任务路由 |
| 6 | 模板管理路由 | 1558~1832 | 模板 CRUD |
| 7 | 违规与配置路由 | 1833~2224 | 违规/配置路由 |
| 8 | 任务管理路由 | 2225~2607 | 任务列表/指派 |
| 9 | 操作员管理路由 | 2608~3440 | 操作员管理 |
| 10 | 消息模板路由 | 3441~3542 | 消息模板 |
| 11 | 流程管理路由 | 3543~4776 | 流程管理（最大模块） |
| 12 | 业务统计路由 | 5665~5887 | 统计接口 |
| 13 | 定时任务控制器 | 5888~6151 | 定时任务 |
| 14 | 同步接口 | 6152~6238 | 同步接口 |
| 15 | 质检与工单同步 | 6239~7110 | 质检/工单/外协 |
| 16 | 质检与成本同步 | 7981~8270 | 质检成本 |
| 17 | 报工与同步接口 | 8271~8653 | 报工/同步 |
| 18 | 同步接口 | 8654~8731 | 同步接口 |
| 19 | 统一任务查询接口 | 7111~7980 | 任务查询 |
| 19.5 | 统一订单全流程状态接口 | 4777~5417 | 订单全流程 |
| 20 | 回归测试 API | 5418~5664 | 回归测试 |
| 20b | 配置接口 | 8732~8784 | alert_rules 配置 |

> 注：Part 顺序按物理位置排列，非编号顺序（19.5 在 11 后，19 在 15 后，20 在 19.5 后，20b 在末尾）。

---

## 五、领域模块详解

### 5.1 _db.py — DB 连接层（~430 行）

**包含**：连接池、MySQLStorage、缓存层、SSOT 代理。

```python
# 核心导出
from ._db import _get_mysql_connection
from ._db import _get_container_center, _get_storage
from ._db import get_dispatch_cache, _dispatch_cache
from ._db import _ssot_cache_get, _ssot_cache_set, _ssot_cache_clear
from ._db import _proxy_to_container_ssot
```

**数据流**：`schedule_routes.py` → `_db._get_mysql_connection()` → 连接池

**DB 存储层统一性**：
- 34 处 DB 操作中，24 处使用 `_get_mysql_connection()`（已统一）
- 3 处使用 `core.db get_direct_connection`（Part 10 消息模板，预存债）
- 2 处使用 `MySQLStorage.get_connection()`（L1512, L7472）
- 5 处直接连接（`_sync.py` 中独立连接）

### 5.2 _notify.py — 通知层

**包含**：微信/钉钉/企微/短信发送，流程/订单事件通知。

```python
from ._notify import (
    _send_wechat_app_message,
    _notify_with_template,
    _notify_process_event,
    _notify_order_event,
    _send_dingtalk_webhook,
    _send_enterprise_wechat_webhook,
    _send_sms_via_gateway,
    _get_receivers_for_scenario,
)
```

### 5.3 _operators.py — 操作员管理层

**包含**：客户组/客户端/工序映射/steel_belt 连接。

```python
from ._operators import (
    _get_customer_group_for_order,
    _get_client,
    _get_process_names_set,
    _get_process_by_code,
    _get_steelbelt_cursor,
    _get_steelbelt_connection,
    _get_steelbelt_connection_direct,
    _get_mysql_connection as _mysql_from_ops,  # 别名避免冲突
)
```

### 5.4 _sync.py — 同步层

**包含**：SSOT 代理、订单同步、SAP 同步、完成步骤同步。

```python
from ._sync import (
    _proxy_to_container_ssot as _psot,  # 别名
    _sync_order_to_container_center,
    _sync_order_to_container_center_by_id,
    _dispatch_sap_sync,
    _sync_completed_step,
)
```

**DB 写入**：`_sync_completed_step` 有独立 DB 连接，写入 `production_orders_local`。

**safe_insert_dedup**：`safe_insert_dedup(cur, table, data, dedup_keys, conn)` 函数，捕获 `IntegrityError` 并转为友好提示，用于唯一约束表（process_sub_steps / quality_records / material_records / outsource_records）。

### 5.5 services/__init__.py — 通用工具层

从 `_core.py` 抽取的通用工具函数，供各领域模块共享。

---

## 六、__init__.py 导出链

```python
from dispatch_center._core import (
    dispatch_center_bp,
    DispatchContext,
    _dispatch_cache,
    start_background_scheduler,
    start_outbox_worker,
    _scheduler_manager,
    _ALERT_ENGINE_INTERVAL,
    on_quality_record_completed,
)

from dispatch_center._constants import (
    STATUS_KEY_TO_MYSQL,
    DISPATCH_RULES_DEFAULT,
    FLOW_MATCHING_RULES_DEFAULT,
    PRODUCT_TYPE_NAMES,
    PROCESS_FLOW_TEMPLATES,
    PROCESS_TEMPLATE_DEFAULTS,
    CONFIRMATION_REQUIRED_STEPS,
    CONFIRMATION_REPLY_KEYWORDS,
    DISPATCH_DOC_ID,
    DISPATCH_DOC_TYPE,
    CUSTOMER_GROUP_CACHE_TTL,
    OPERATOR_CACHE_TTL,
    WORK_ORDER_CACHE_TTL,
)
```

---

## 七、shim 函数（向后兼容）

`_core.py` 中保留 9 个 shim 函数，确保 `__init__.py` 导出链和现有外部引用零改动：

| shim 函数 | 实际实现 | Part |
|-----------|---------|------|
| `_get_customer_group_for_order` | `._operators.get_customer_group_for_order` | Part 3 |
| `invalidate_customer_group_cache` | `._operators.invalidate_customer_group_cache` | Part 3 |
| `_get_client` | `._operators._get_client` | Part 3 |
| `_get_process_names_set` | `._operators._get_process_names_set` | Part 3 |
| `_notify_process_event` | `._notify._notify_process_event` | Part 3 |
| `_notify_order_event` | `._notify._notify_order_event` | Part 3 |
| `_send_wechat_app_message` | `._notify._send_wechat_app_message` | Part 3 |
| `_dispatch_sap_sync` | `._sync._dispatch_sap_sync` | Part 3 |
| `_sync_completed_step` | `._sync._sync_completed_step` | Part 3 |

---

## 八、split_analysis.py AST 分析脚本

**位置**：`scripts/tools/split_analysis.py`

AST 分析每个 Part 路由需要哪些服务函数，输出示例：

```
Part 4: 4 service functions
Part 5: 2
Part 7: 5
Part 10: 4
Part 11: 28 (最多)
Part 12: 2
Part 15: 13
Part 19.5: 7
Part 19: 7
```

---

## 九、Git 提交记录

```
63dcc136 refactor(dispatch_center): 领域模块抽取 + 索引表修正 (v3.6.1)
  13 files changed, +2832/-280

7ca7c094 fix(dispatch_center): 追加索引表 + 完善导出链 + 排产缓存 (v3.6.1 续)
  6 files changed, +2588/-1251

aa72abc7 fix(_sync): 完善 test_duplicate_entry 测试用例 - side_effect 改为列表
  1 file changed, +32/-13
```

### 死代码清理

| 清理项 | 状态 |
|--------|------|
| `__pre_tests__/` 目录（3 个文件） | ✅ 已删除提交 |
| `fix_part_order*.py` 临时脚本（6 个） | ✅ 已删除 |
| `_core.py.*_backup.py` 备份（3 个） | ✅ 已删除 |

---

## 十、验证方案

| 步骤 | 命令/脚本 | 判定 |
|------|---------|------|
| ① 语法检查 | `py -m py_compile dispatch_center/_core.py` | 无错误 |
| ② 新文件语法 | `py -m py_compile dispatch_center/_db.py` 等 | 无错误 |
| ③ 包级导入 | `py -c "from dispatch_center import dispatch_center_bp; print('ok')"` | 输出 ok |
| ④ 路由数量 | AST 统计 Blueprint 路由数量 | ~148 个 |
| ⑤ 启动测试 | `py standalone_dispatch_server.py`（后台 5 秒） | 无崩溃 |

---

## 十一、已知预存债

| 项目 | 位置 | 说明 | 状态 |
|------|------|------|------|
| `core.db get_direct_connection` | Part 10 消息模板（L1594, L1631, L1650） | 预存债，非本次重构引入 | 待处理 |

---

## 十二、审计记录

### 设计文档审计

| 轮次 | 分数 | 发现问题 | 根因 | 修复状态 |
|------|------|---------|------|---------|
| 第 1 轮 | 89/100 | ① `_routes/__init__.py` 未说明；② 服务函数归属无策略；③ git 分支未说明；④ 包级验证缺失 | 设计阶段遗漏 | ✅ 已修复 |
| 第 2 轮 | 77/100 | ① Blueprint URL 写错；② `__init__.py` 导出链未更新；③ Part 3 行号；④ `_processes_cache` 跨边界；⑤ split_analysis.py 未提供；⑥ `_backup/` 冗余 | 源码核查不足 + 审计误判 | ✅ 已修复（3项误报已澄清） |

### 实际代码审计（第 3 轮，改审实际代码）

| 维度 | 评分 | 发现问题 | 修复状态 |
|------|------|---------|---------|
| 语法正确性 | 6/6 ✅ | 全部通过 | — |
| 导入链完整性 | 5/5 ✅ | `_core.py` → 领域模块 → `_core.py` 循环检查通过 | — |
| Part 标记一致性 | 0/10 ❌ | **CRITICAL**: 索引表行号全部错误（22 行） | ✅ 已修复 |
| Git 管理 | 0/10 ❌ | 未 commit；`__pre_tests__/` 未 rm；备份未清理 | ✅ 已修复 |
| 代码无新增缺陷 | 8/10 ⚠️ | 预存债（`core.db get_direct_connection` 3 处） | 跳过（非引入） |
| 文档同步 | 5/5 ✅ | — | — |
| **总分** | **24/36 → 89/100** | | |

### 设计文档与实际代码对比

| 项目 | 设计文档 v1.2（规划） | 实际代码 v2.0（执行） |
|------|----------------------|----------------------|
| 拆分方式 | 按 Part 边界物理拆分（`_services.py` + `_routes/`） | 按领域模块抽取（`_db/_notify/_operators/_sync`） |
| 路由文件数 | 13 个 `_routes/*.py` | 0 个（路由物理不动） |
| shim 函数 | 底部兼容导出层（from ... import ...） | 顶部导入 + 调用委托（from ._x import fn; def fn(): from._x import fn as impl; return impl()） |
| 预期行数 | `_core.py` ~162 行 | `_core.py` ~8784 行（shim + 路由全保留） |
| Blueprint | 单 Blueprint，URL 不变 | 单 Blueprint，URL 不变 ✅ |
| 新增文件 | 14 个（`_services.py` + 13 个路由文件） | 11 个（4 领域模块 + 5 测试 + `shipment_routes.py` + `services/__init__.py`） |
| Part 标记 | 保持 22 个 | 保持 22 个 ✅ |
| 索引表 | 有（行号待修正） | 有（行号已修正）✅ |

**结论**：最终实现比设计文档更简洁——没有创建 13 个路由文件（路由仍保留在 `_core.py`），而是按领域抽取公共函数。适合当前阶段，未来可按 Part 边界进一步物理拆分路由。

---

## 十三、下一步方向（待定）

1. **路由物理拆分**：当 `_core.py` 继续膨胀时，可按设计文档 v1.x 的 `_routes/` 方案，将 Part 4~20b 的路由代码拆分到独立文件（但需保持单 Blueprint）
2. **预存债处理**：Part 10 消息模板路由的 `core.db get_direct_connection` 3 处统一为 `_get_mysql_connection`
3. **前端优化**：调度中心前端页面（`dispatch_center.html` + JS + CSS，24 个 Tab）可按领域分组重构
