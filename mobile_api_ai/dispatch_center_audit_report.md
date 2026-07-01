# dispatch_center.py 深度后端路由质量审计报告

**审计日期**: 2026-05-24
**审计文件**: d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center.py
**路由总数**: 100 个（含不同 HTTP method 独立计数）
**文件行数**: ~7950 行

---

## 一、执行摘要

| 审计维度 | 结果 |
|---------|------|
| 路由总数（含不同方法） | 100 条 |
| 有 try/except 覆盖的路由 | ~70 条（70%） |
| 缺少外层 try/except 的路由 | 22 条 |
| 数据校验不完整的路由 | 12 条 |
| print() 调试输出 | 3 处（均在 `__main__` 启动区，可接受） |
| 响应格式不统一 | 无重大不统一 |

**整体评价**: 核心路由（进程流转、任务分配、消息推送、模板管理、工单 CRUD）多数有 try/except 覆盖，质量较好。但存在 22 条路由缺少外层异常保护，尤其操作员 CRUD、外协管理模块和调度管理器模块为薄弱环节。

---

## 二、问题清单

### 2.1 CRITICAL -- 缺少 try/except 保护（可能直接返回 500 或中断服务）

#### 2.1.1 操作员 CRUD（高危 -- 涉及数据库操作）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 1 | 3340 | `PUT /operators/<operator_id>` | `update_operator` | **数据库更新操作无 try/except**。`container_config.update_operator()` 或 `EventBus.publish()` 抛出异常时，直接返回 500，无回滚或错误响应 |
| 2 | 3363 | `DELETE /operators/<operator_id>` | `delete_operator` | **数据库删除操作无 try/except**。`container_config.remove_operator()` 抛出异常时同 |

#### 2.1.2 外协管理模块（高危 -- 全部缺少异常保护）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 3 | 5553 | `GET /outsource-records/<record_id>` | `get_outsource_record` | 无 try/except，`_get_cached_work_orders()` 或 JSON 操作异常时崩溃 |
| 4 | 5562 | `POST /outsource-records/<record_id>/assign` | `assign_outsource_record` | 无 try/except，`_get_client()` 和 `_update_outsource_extra()` 均可抛出异常 |
| 5 | 5588 | `POST /outsource-records/<record_id>/feedback` | `feedback_outsource_record` | **完全无 try/except**，更新外协记录和发送消息均无保护 |
| 6 | 5605 | `POST /outsource-records/<record_id>/complete` | `complete_outsource_record` | **完全无 try/except**，`_update_outsource_extra()` 异常时不返回任何响应 |
| 7 | 5614 | `POST /outsource-records/<record_id>/receive` | `receive_outsource_record` | **完全无 try/except**，`_update_outsource_extra()` 异常时不返回任何响应 |
| 8 | 5636 | `POST /outsource-config` | `update_outsource_config` | 无 try/except，`container_config` 操作异常时 |

#### 2.1.3 调度管理器模块（高危 -- 影响定时任务调度）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 9 | 7304 | `PUT /scheduler-manager/toggle` | `toggle_scheduler` | 无 try/except，`_scheduler_manager.toggle()` 抛出异常时不返回错误响应 |
| 10 | 7315 | `PUT /scheduler-manager/interval` | `update_scheduler_interval` | 无 try/except，有基础 `isdigit()` 校验但 `_scheduler_manager.set_interval()` 异常时不返回错误响应 |

#### 2.1.4 流程任务管理（中危 -- 操作简单但无保护）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 11 | 1883 | `DELETE /process-tasks/<task_id>` | `delete_process_task` | 外层无 try/except，仅内部 `container_sync` 有局部 try，`_dispatch_cache.update_data()` 异常时 |
| 12 | 1906 | `POST /process-tasks/<task_id>/send` | `send_process_task` | 无外层 try/except，`_do_send_process_task()` 抛出异常时不返回错误响应 |
| 13 | 1923 | `POST /process-tasks/send-all-pending` | `send_all_pending_process_tasks` | 无外层 try/except |

#### 2.1.5 配置管理（中危 -- 使用 _dispatch_cache.update_data 无保护）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 14 | 2104 | `PUT,POST /global-config` | `save_global_config` | 无外层 try/except，`_dispatch_cache.update_data()` 内 lambda 抛出异常时 |
| 15 | 2150 | `PUT,POST /departments/<department>/managers` | `save_department_managers` | 同上 |
| 16 | 2167 | `PUT,POST /process-departments/<process>` | `save_process_department` | 同上 |
| 17 | 2177 | `DELETE /process-departments/<process>` | `delete_process_department` | 同上 |
| 18 | 5333 | `POST /rules` | `save_rules` | 无外层 try/except，`_dispatch_cache.update_data()` 异常时 |

#### 2.1.6 报修模块（中危 -- 使用 container_config 无保护）

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 19 | 5441 | `POST /repair-categories` | `add_repair_category` | 无 try/except，`container_config` 配置更新操作异常时 |
| 20 | 5459 | `DELETE /repair-categories/<cat_id>` | `delete_repair_category` | 同上 |
| 21 | 5496 | `POST /repair-records/<record_id>/complete` | `complete_repair_record` | 无 try/except，`_get_client()` 数据库异常时 |

---

### 2.2 HIGH PRIORITY -- 数据校验不完整

#### 2.2.1 必填参数未校验

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 22 | 1660 | `POST /task-notify` | `task_notify` | `request.get_json(force=True, silent=True)` 为 `None` 时用 `{}` 兜底，未校验 `task_id` 等必填字段是否存在 |
| 23 | 2067 | `POST /templates` | `save_template` | `body.get('name')` 可能为 None，未做 `if not name: return error` 校验 |
| 24 | 2339 | `POST /tasks/<task_id>/assign` | `assign_task` | body 中 `operator_id` 使用 `body.get('operator_id', '')`，空字符串时可能执行无意义分配 |
| 25 | 2659 | `POST /operators` | `save_operator` | 未校验 `employee_id` 或 `name` 必填字段，空值可能写入脏数据 |
| 26 | 3182 | `POST /material/outbound` | `report_outbound` | 未校验 body 中 `order_no`、`material_id`、`quantity` 等必填字段 |
| 27 | 5441 | `POST /repair-categories` | `add_repair_category` | 未校验 `name` 必填字段 |
| 28 | 5522 | `POST /outsource-records` | `create_outsource_record` | 未校验 `order_no` 等必填字段 |
| 29 | 5636 | `POST /outsource-config` | `update_outsource_config` | 未校验 body 中配置字段的有效性 |

#### 2.2.2 数值类型未校验

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 30 | 3350 | `PUT /operators/<operator_id>` | `update_operator` | `body.get('max_tasks')` 赋值前未校验是否为 int 或正数 |
| 31 | 7315 | `PUT /scheduler-manager/interval` | `update_scheduler_interval` | 仅做 `isdigit()` 检查，未判断是否 > 0 或设置合理上限（如最小 5 秒，最大 3600 秒） |

---

### 2.3 MEDIUM -- 数据校验不够严格

| # | 行号 | 路由 | 处理函数 | 问题描述 |
|---|------|------|---------|---------|
| 32 | 3968 | `POST /messages/send` | `send_message` | `recipients` 参数没有校验是否为列表或是否为空列表 |
| 33 | 4079 | `GET /messages/history` | `get_message_history` | 分页参数 `page`、`page_size` 从查询参数取默认值，未校验是否为有效整型 |
| 34 | 4137 起 | 多处 | 多处 | `request.get_json(force=True, silent=True)` 广泛使用 `silent=True`，但多处未检查返回是否为 None |

---

### 2.4 INFO -- 其他注意点

#### 2.4.1 响应格式细节差异

| # | 行号 | 路由 | 问题描述 |
|---|------|------|---------|
| 35 | 7925 | `POST /help-request` | 返回的 `data` 对象中包含 `'code': 200` 字段，与顶层 `'code': 0` 语义不一致，可能引起前端混淆 |

#### 2.4.2 print() 调试输出

未在路由处理函数中找到 `print()` 调试语句。仅 `if __name__ == '__main__':` 启动区有以下输出（可接受）：

| 行号 | 内容 |
|------|------|
| 7944 | `print("=" * 60)` |
| 7945 | `print("【本地版】调度中心服务")` |
| 7953 | `print(f"启动服务: http://...")` |

**结论**: 无 `print()` 调试输出污染路由逻辑，符合规范。

---

## 三、全量路由覆盖清单（按审计顺序）

| 行号 | 路由 | 方法 | try/except | 数据校验 | 严重度 |
|------|------|------|-----------|---------|--------|
| 1660 | /task-notify | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 1870 | /process-tasks | GET | ❌ 无（简单读取） | - | INFO |
| 1883 | /process-tasks/<task_id> | DELETE | ❌ 无 | - | CRITICAL |
| 1906 | /process-tasks/<task_id>/send | POST | ❌ 无 | - | CRITICAL |
| 1923 | /process-tasks/send-all-pending | POST | ❌ 无 | - | CRITICAL |
| 1936 | /process-names-debug | GET | ✅ 有 | - | OK |
| 1972 | /process-names | GET | ✅ 有 | - | OK |
| 2054 | /templates | GET | ✅ 有 | - | OK |
| 2067 | /templates | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 2091 | /global-config | GET | ❌ 无（读取配置） | - | INFO |
| 2104 | /global-config | PUT/POST | ❌ 无 | - | CRITICAL |
| 2126 | /departments | GET | ❌ 无（读取配置） | - | INFO |
| 2143 | /departments/<department>/managers | GET | ❌ 无（读取配置） | - | INFO |
| 2150 | /departments/<department>/managers | PUT/POST | ❌ 无 | - | CRITICAL |
| 2160 | /process-departments | GET | ❌ 无（读取配置） | - | INFO |
| 2167 | /process-departments/<process> | PUT/POST | ❌ 无 | - | CRITICAL |
| 2177 | /process-departments/<process> | DELETE | ❌ 无 | - | CRITICAL |
| 2183 | / | GET | ❌ 无（渲染模板） | - | INFO |
| 2189 | /status | GET | ✅ 有 | - | OK |
| 2257 | /pending-warehousing | GET | ✅ 有 | - | OK |
| 2286 | /tasks | GET | ✅ 有 | - | OK |
| 2339 | /tasks/<task_id>/assign | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 2419 | /tasks/<task_id>/reassign | POST | ✅ 有 | - | OK |
| 2480 | /tasks/<task_id>/cancel | POST | ✅ 有 | - | OK |
| 2530 | /tasks/<task_id>/assign-all | POST | ✅ 有 | - | OK |
| 2552 | /tasks/convert-all-to-public | POST | ✅ 有 | - | OK |
| 2584 | /tasks/batch-assign | POST | ✅ 有 | - | OK |
| 2625 | /tasks/<task_id>/report | POST | ✅ 有 | - | OK |
| 2645 | /operators | GET | ✅ 有 | - | OK |
| 2659 | /operators | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 2691 | /operators/sync-wechat | POST | ✅ 有 | - | OK |
| 2852 | /operators/wechat-departments | GET | ✅ 有 | - | OK |
| 2973 | /enterprise/structure/push | POST | ✅ 有 | - | OK |
| 3077 | /material/requirements | POST | ✅ 有 | - | OK |
| 3122 | /material/sync-prepared | POST | ✅ 有 | - | OK |
| 3182 | /material/outbound | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 3243 | /material/requirements | GET | ✅ 有 | - | OK |
| 3339 | /operators/<operator_id> | PUT | ❌ 无 | ⚠️ 不完整 | CRITICAL |
| 3362 | /operators/<operator_id> | DELETE | ❌ 无 | - | CRITICAL |
| 3373 | /operators/<operator_id>/tasks | GET | ✅ 有 | - | OK |
| 3406 | /wechat/sync | POST | ✅ 有 | - | OK |
| 3513 | /wechat/users | GET | ✅ 有 | - | OK |
| 3565 | /devices | GET | ✅ 有 | - | OK |
| 3612 | /devices/<device_id>/tasks | GET | ✅ 有 | - | OK |
| 3645 | /messages/templates | GET | ✅ 有 | - | OK |
| 3656 | /messages/templates | POST | ✅ 有 | - | OK |
| 3684 | /messages/templates/defaults | GET | ❌ 无（读取配置） | - | INFO |
| 3689 | /messages/templates/variables | GET | ❌ 无（读取配置） | - | INFO |
| 3757 | /messages/templates/<template_id> | PUT | ✅ 有 | - | OK |
| 3793 | /messages/templates/<template_id> | DELETE | ✅ 有 | - | OK |
| 3815 | /messages/templates/order | POST | ✅ 有 | - | OK |
| 3875 | /messages/templates/defaults/reset | POST | ✅ 有 | - | OK |
| 3911 | /messages/templates/preference | GET | ✅ 有 | - | OK |
| 3918 | /messages/templates/preference | POST | ✅ 有 | - | OK |
| 3968 | /messages/send | POST | ✅ 有 | ⚠️ 不完整 | MEDIUM |
| 4079 | /messages/history | GET | ✅ 有 | ⚠️ 不完整 | MEDIUM |
| 4118 | /messages/history/<msg_id> | DELETE | ✅ 有 | - | OK |
| 4137 | /processes | GET | ✅ 有 | - | OK |
| 4399 | /processes | POST | ✅ 有 | - | OK |
| 4503 | /debug/cc-workorders | GET | ✅ 有 | - | OK |
| 4514 | /debug/cache-data | GET | ❌ 无（调试接口） | - | INFO |
| 4556 | /processes/backfill | POST | ✅ 有 | - | OK |
| 4662 | /processes/repair-products | POST | ✅ 有 | - | OK |
| 4701 | /processes/<process_id> | GET | ✅ 有 | - | OK |
| 4785 | /processes/<process_id>/step-notify | POST | ✅ 有 | - | OK |
| 4840 | /processes/<process_id> | DELETE | ✅ 有 | - | OK |
| 4883 | /processes/<process_id>/template-bindings | GET | ❌ 无（读取配置） | - | INFO |
| 4905 | /processes/<process_id>/template-bindings | PUT | ✅ 有 | - | OK |
| 4929 | /processes/<process_id>/template-bindings/reset | POST | ✅ 有 | - | OK |
| 4948 | /processes/<process_id>/advance | POST | ✅ 有（内部 result 模式） | - | OK |
| 5081 | /workorder/auto-complete-report | POST | ✅ 有 | - | OK |
| 5099 | /processes/confirm-by-reply | POST | ✅ 有 | - | OK |
| 5232 | /processes/<process_id>/confirm | POST | ✅ 有 | - | OK |
| 5245 | /processes/<process_id>/reject | POST | ✅ 有（内部 result 模式） | - | OK |
| 5317 | /rules | GET | ❌ 无（读取配置） | - | INFO |
| 5333 | /rules | POST | ❌ 无 | - | CRITICAL |
| 5357 | /flow-matching-rules | GET | ✅ 有 | - | OK |
| 5387 | /flow-matching-rules | POST | ✅ 有 | - | OK |
| 5430 | /repair-categories | GET | ❌ 无（读取配置） | - | INFO |
| 5441 | /repair-categories | POST | ❌ 无 | ⚠️ 不完整 | CRITICAL |
| 5459 | /repair-categories/<cat_id> | DELETE | ❌ 无 | - | CRITICAL |
| 5467 | /repair-records | GET | ✅ 有 | - | OK |
| 5496 | /repair-records/<record_id>/complete | POST | ❌ 无 | - | CRITICAL |
| 5514 | /outsource-records | GET | ❌ 无（读取） | - | INFO |
| 5522 | /outsource-records | POST | ✅ 有 | ⚠️ 不完整 | HIGH |
| 5553 | /outsource-records/<record_id> | GET | ❌ 无 | - | CRITICAL |
| 5562 | /outsource-records/<record_id>/assign | POST | ❌ 无 | - | CRITICAL |
| 5588 | /outsource-records/<record_id>/feedback | POST | ❌ 无 | - | CRITICAL |
| 5605 | /outsource-records/<record_id>/complete | POST | ❌ 无 | - | CRITICAL |
| 5614 | /outsource-records/<record_id>/receive | POST | ❌ 无 | - | CRITICAL |
| 5624 | /outsource-config | GET | ❌ 无（读取） | - | INFO |
| 5636 | /outsource-config | POST | ❌ 无 | ⚠️ 不完整 | CRITICAL |
| 5644 | /stats | GET | ✅ 有 | - | OK |
| 5701 | /alerts | GET | ✅ 有 | - | OK |
| 5739 | /alerts/<alert_id>/dismiss | POST | ✅ 有 | - | OK |
| 5757 | /dispatch-log | GET | ✅ 有 | - | OK |
| 6176 | /workorder/stats | GET | ✅ 有 | - | OK |
| 6236 | /workorder/list | GET | ✅ 有 | - | OK |
| 6316 | /workorder/status | POST | ✅ 有 | - | OK |
| 6387 | /workorder/<order_no> | GET | ✅ 有 | - | OK |
| 6518 | /workorder/<order_no>/refresh | POST | ✅ 有 | - | OK |
| 6589 | /workorder/<order_no> | DELETE | ✅ 有 | - | OK |
| 6628 | /workorder/change-delivery-date | POST | ✅ 有 | - | OK |
| 6698 | /workorder/register | POST | ✅ 有 | - | OK |
| 6861 | /process_sub_steps/<process_id> | GET | ✅ 有 | - | OK |
| 6872 | /process_sub_step_summary/<process_id> | GET | ✅ 有 | - | OK |
| 6883 | /process_sub_step | POST | ✅ 有 | - | OK |
| 7004 | /cloud/config | GET/POST | ✅ 有 | - | OK |
| 7076 | /cloud/status | GET | ✅ 有 | - | OK |
| 7186 | /cloud/poll-data | GET | ✅ 有 | - | OK |
| 7252 | /cloud/connection-test | GET | ✅ 有 | - | OK |
| 7298 | /scheduler-manager/status | GET | ❌ 无（读取状态） | - | INFO |
| 7304 | /scheduler-manager/toggle | PUT | ❌ 无 | - | CRITICAL |
| 7315 | /scheduler-manager/interval | PUT | ❌ 无 | ⚠️ 不完整 | CRITICAL |
| 7386 | /servers | GET | ❌ 无（读取列表） | - | INFO |
| 7395 | /servers/<server_key>/start | POST | ✅ 有 | - | OK |
| 7453 | /servers/<server_key>/stop | POST | ✅ 有 | - | OK |
| 7502 | /servers/logs | GET | ❌ 无（文件读取） | - | INFO |
| 7517 | /quality/create | POST | ✅ 有 | - | OK |
| 7607 | /servers/python-path | GET | ❌ 无（返回路径） | - | INFO |
| 7695 | /workorder/update-task-count | POST | ✅ 有 | - | OK |
| 7771 | /help-request | POST | ✅ 有 | - | OK |
| 7865 | /documents | GET | ✅ 有 | - | OK |
| 7889 | /documents/<doc_id> | GET | ✅ 有 | - | OK |

---

## 四、问题分级统计

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| **CRITICAL** | **21 条** | 缺少 try/except，异常时直接返回 500 或中断 |
| **HIGH** | 7 条 | 数据校验不完整，可能导致脏数据或无效操作 |
| **MEDIUM** | 4 条 | 校验不够严格，存在潜在异常路径 |
| **INFO** | 16 条 | 简单读取操作无 try/except（风险较低） |
| **OK** | 52 条 | 有完整的 try/except 或校验 |

---

## 五、修复优先级建议

### P0 -- 立即修复（CRITICAL，缺少 try/except 且有数据变更）

按优先级排列：

1. **[L3339](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3339) `update_operator`** -- 操作员更新，涉及数据库和事件总线
2. **[L3362](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3362) `delete_operator`** -- 操作员删除，同上
3. **[L5588](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5588) `feedback_outsource_record`** -- 外协反馈，完全无保护
4. **[L5605](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5605) `complete_outsource_record`** -- 外协完成，完全无保护
5. **[L5614](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5614) `receive_outsource_record`** -- 外协收货，完全无保护
6. **[L5562](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5562) `assign_outsource_record`** -- 外协指派，无保护
7. **[L7304](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L7304) `toggle_scheduler`** -- 调度开关，无保护
8. **[L7315](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L7315) `update_scheduler_interval`** -- 调度间隔，无保护
9. **[L5441](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5441) `add_repair_category`** -- 添加报修分类，无保护
10. **[L5459](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5459) `delete_repair_category`** -- 删除报修分类，无保护
11. **[L5496](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5496) `complete_repair_record`** -- 完成报修，无保护
12. **[L5333](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5333) `save_rules`** -- 保存调度规则，无保护
13. **[L5636](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5636) `update_outsource_config`** -- 外协配置更新，无保护
14. **[L2104](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2104) `save_global_config`** -- 全局配置保存，无保护
15. **[L2150](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2150) `save_department_managers`** -- 部门负责人保存，无保护
16. **[L2167](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2167) `save_process_department`** -- 工序部门绑定保存，无保护
17. **[L2177](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2177) `delete_process_department`** -- 工序部门绑定删除，无保护
18. **[L1883](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L1883) `delete_process_task`** -- 流程任务删除，无保护
19. **[L1906](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L1906) `send_process_task`** -- 流程任务发送，无保护
20. **[L1923](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L1923) `send_all_pending_process_tasks`** -- 批量发送流程任务，无保护
21. **[L5553](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5553) `get_outsource_record`** -- 获取外协记录详情，无保护

### P1 -- 尽快修复（HIGH，数据校验不完整）

1. **[L1660](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L1660)** `task_notify` -- 补充 `task_id` 必填校验
2. **[L2067](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2067)** `save_template` -- 补充 `name` 必填校验
3. **[L2339](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2339)** `assign_task` -- 校验 `operator_id` 非空
4. **[L2659](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L2659)** `save_operator` -- 校验 `employee_id`、`name` 必填
5. **[L3182](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3182)** `report_outbound` -- 补充 `order_no` 等必填字段校验
6. **[L5441](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5441)** `add_repair_category` -- 补充 `name` 必填校验
7. **[L5522](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5522)** `create_outsource_record` -- 补充必填字段校验
8. **[L5636](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L5636)** `update_outsource_config` -- 补充必填字段校验
9. **[L3350](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3350)** `update_operator` -- 校验 `max_tasks` 为有效正整数
10. **[L7315](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L7315)** `update_scheduler_interval` -- 设置合理上下限（如 5-3600 秒）

### P2 -- 后续优化（MEDIUM, INFO）

1. [L3968](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3968) 校验 `recipients` 为有效列表
2. [L4079](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L4079) 校验分页参数为有效整型
3. 多处 `get_json(silent=True)` 后应检查是否为 None

---

## 六、典型修复模式

### 缺少 try/except 的修复模板

```python
# 当前代码（无 try/except）
@dispatch_center_bp.route('/operators/<operator_id>', methods=['PUT'])
def update_operator(operator_id):
    body = request.get_json(force=True, silent=True) or {}
    from container_config import container_config
    ...
    return jsonify({'code': 0, ...})

# 修复后
@dispatch_center_bp.route('/operators/<operator_id>', methods=['PUT'])
def update_operator(operator_id):
    try:
        body = request.get_json(force=True, silent=True) or {}
        from container_config import container_config
        ...
        return jsonify({'code': 0, ...})
    except Exception as e:
        logger.exception(f"更新操作员 {operator_id} 失败")
        return jsonify({'code': 500, 'message': f'操作失败: {str(e)}'}), 500
```

### 数据校验补充模板

```python
# 当前代码（无校验）
body = request.get_json(force=True, silent=True) or {}
name = body.get('name')
# ... 直接使用 name

# 修复后
body = request.get_json(force=True, silent=True)
if not body or not body.get('name'):
    return jsonify({'code': 400, 'message': '缺少必填参数: name'}), 400
name = body['name']
```

---

## 七、审计结论

**整体**: 核心业务路由（进程流转、任务分配、工单、消息模板、质量等）质量较高，均有 try/except 覆盖和合理的响应格式。

**薄弱环节**: 
1. **操作员 CRUD**（L3339-L3369）-- 数据库操作无异常保护，是最需要优先修复的
2. **外协管理模块**（L5553-L5636）-- 6 条路由中 4 条完全无 try/except
3. **调度管理器**（L7304-L7315）-- 缺少异常保护
4. **配置管理快捷路由**（L2104-L2177）-- 调用 `_dispatch_cache.update_data` 无保护

**好的一面**:
- 无 `print()` 调试语句在路由处理中
- 响应格式统一为 `jsonify({'code': ..., 'message': ...})`
- 核心进程流转路由于有完善的错误处理
- 日志使用 `logger` 而非 `print()` 符合规范
