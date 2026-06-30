# API 方案细则 (完整版)
> 版本: 2.0 | 日期: 2026-05-30 | 端点: 206

---

## 报工程序 (port 5008) — 32 routes

### 核心报工

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/v1/report` | 提交报工 |
| POST | `/api/wechat/pool/report` | 微信池批量报工 |
| GET | `/my-tasks` | 我的任务列表 |
| POST | `/<record_id>/report` | 单任务报工 |
| POST | `/api/process_sub_step` | 子步骤报工 |

### 扫码 / 工单

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/scan-info` | 扫码配置 |
| POST | `/task` | 扫码接任务 |
| GET | `/workorder/<order_no>` | 工单详情 |
| GET | `/worker/<worker_id>` | 工人统计 |
| GET | `/api/workers` | 全部工人 |
| GET | `/api/production-orders` | 生产单列表 |

### 考勤

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/attendance` | 今日考勤 |
| POST | `/api/attendance` | 打卡 |
| GET | `/api/attendance/<username>` | 个人考勤 |

### 质检

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/list` | 质检任务列表 |
| POST | `/<int:order_id>/create` | 创建质检单 |
| GET | `/types` | 质检类型 |
| GET | `/api/quality` | 质检记录 |
| POST | `/api/quality` | 提交质检结果 |

### 看板 / 入库 / 子步骤

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/dashboard` | 看板数据 |
| GET | `/api/warehousing/pending` | 待入库列表 |
| POST | `/api/warehousing/confirm` | 确认入库 |
| GET | `/api/sub_step_records` | 子步骤记录 |
| GET | `/api/debug_info` | 调试信息 |

### 页面 / 认证

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| GET | `/scanner` | 扫码页 |
| GET | `/mobile` | 手机页 |
| GET | `/mobile_login.html` | 登录页 |
| POST | `/api/login` | 登录 |

---

## 容器中心 (port 5002) — 59 routes

### 排产发布 [桌面端 →]

| 方法 | 路由 | 请求体 |
|------|------|--------|
| POST | `/api/schedule/publish` | `{order_no, product_type, quantity, flow_type?, customer_name?, ...}` |
| POST | `/api/flow-map/sync` | `{mappings: [{product_type_id, flow_type}]}` |
| GET | `/api/flow-type/<id>` | — |
| POST | `/api/internal/publish` | 内部发布 |
| POST | `/api/internal/outsource/publish` | 外协发布 |

### 流程记录 CRUD

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/processes` | 列表 `?status=&type=` |
| POST | `/api/processes` | 创建 |
| GET | `/api/processes/<id>` | 详情 |
| PUT | `/api/processes/<id>` | 更新 |
| DELETE | `/api/processes/<id>` | 删除 |
| PUT | `/api/processes/<id>/status` | 更新状态 |
| PUT | `/api/processes/<id>/step` | 推进步骤 |
| PUT | `/api/processes/<id>/tasks` | 更新任务 |
| PUT | `/api/processes/<id>/template` | 更新模板 |
| GET | `/api/processes/by-order/<no>` | 按订单查 |

### 外协

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/outsource/config` | 外协配置 |
| POST | `/api/outsource/config` | 保存配置 |
| GET | `/api/outsource/records` | 外协记录列表 |
| GET | `/api/outsource/records/<id>` | 外协详情 |
| POST | `/api/outsource/records/<id>/receive` | 接收 |
| POST | `/api/outsource/records/<id>/feedback` | 反馈 |
| POST | `/api/outsource/records/<id>/complete` | 完成 |

### 子步骤

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/process_sub_step` | 上报子步骤 |
| POST | `/api/sub-step/report` | 子步骤报工 |
| GET | `/api/process_sub_steps/<no>` | 子步骤列表 |
| GET | `/api/process_sub_step_summary/<no>` | 汇总 |
| GET | `/api/sub-step/audit/<no>` | 审计 |
| POST | `/api/sub-step/rollback` | 回滚 |
| POST | `/api/sub-step/repair-mysql` | 修复 |

### 任务

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/<id>` | 任务详情 |
| POST | `/api/tasks/<id>/acknowledge` | 确认接收 |
| POST | `/api/tasks/<id>/complete` | 完成 |
| GET | `/api/tasks/unacknowledged` | 未确认列表 |
| GET | `/api/pool/status` | 任务池状态 |

### 企业架构

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/enterprise/structure` | 读架构 |
| POST | `/api/enterprise/structure` | 保存 |

### 兼容 / 微信

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/operators` | 操作员(3.01) |
| GET | `/api/v4/operators` | 操作员(v4) |
| GET | `/api/v4/work_order` | 工单(v4) |
| GET | `/api/v4/alerts` | 告警(v4) |
| POST | `/api/dispatch` | 派单 |
| POST | `/api/wechat/dispatch` | 微信派单 |
| GET | `/api/wechat/get_access_token` | 微信token |

### 部署 / 认证

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/verify` | 验token |
| POST | `/api/internal/config/deploy` | 部署配置 |
| POST | `/api/internal/config/rollback` | 回滚 |
| GET | `/api/internal/config/versions/<name>` | 版本历史 |
| POST | `/api/callback` | 回调 |

---

## 调度中心 (port 5003) — 110 routes

### 任务管理

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/tasks` | 任务列表 `?page=&size=&status=` |
| POST | `/tasks/<id>/assign` | 指派 |
| POST | `/tasks/<id>/reassign` | 转派 |
| POST | `/tasks/<id>/cancel` | 取消 |
| POST | `/tasks/batch-assign` | 批量派单 |
| POST | `/task-notify` | 任务通知 |

### 流程任务

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/process-tasks` | 任务列表 |
| DELETE | `/process-tasks/<id>` | 删除 |
| POST | `/process-tasks/<id>/send` | 发送 |
| POST | `/process-tasks/send-all-pending` | 全部发送 |
| GET | `/process-names` | 流程名称 |

### 流程推送 (processes)

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/processes` | 流程列表 |
| POST | `/processes` | 创建 |
| GET | `/processes/<no>` | 详情 |
| DELETE | `/processes/<no>` | 删除 |
| POST | `/processes/<no>/advance` | 推进步骤 |
| POST | `/processes/<no>/confirm` | 确认 |
| POST | `/processes/<no>/reject` | 驳回 |
| POST | `/processes/<no>/step-notify` | 步骤通知 |
| POST | `/processes/backfill` | 回填 |
| POST | `/processes/confirm-by-reply` | 回复确认 |
| POST | `/processes/repair-products` | 修复产品 |
| GET | `/processes/<no>/template-bindings` | 模板绑定 |
| PUT | `/processes/<no>/template-bindings` | 设绑定 |
| POST | `/processes/<no>/template-bindings/reset` | 重置 |

### 消息模板

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/messages/templates` | 模板列表 |
| POST | `/messages/templates` | 创建模板 |
| PUT | `/messages/templates/<id>` | 更新 |
| DELETE | `/messages/templates/<id>` | 删除 |
| GET | `/messages/templates/defaults` | 默认模板 |
| GET | `/messages/templates/variables` | 变量列表 |
| GET | `/messages/templates/preference` | 偏好 |
| POST | `/messages/templates/preference` | 设偏好 |
| POST | `/messages/templates/order` | 排序 |
| POST | `/messages/send` | 发消息 |
| GET | `/messages/history` | 消息历史 |

### 操作员

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/operators` | 列表 |
| POST | `/operators` | 新增 |
| PUT | `/operators/<id>` | 修改 |
| DELETE | `/operators/<id>` | 删除 |
| GET | `/operators/<id>/tasks` | 操作员任务 |
| GET | `/operators/wechat-departments` | 微信部门 |
| GET | `/operators/wechat-form-data` | 微信表单数据 |

### 部门

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/departments` | 列表 `?force_cloud=1` |
| GET | `/departments/<dept>/managers` | 负责人 |
| PUT | `/departments/<dept>/managers` | 设负责人 |
| GET | `/process-departments` | 流程→部门 |
| PUT | `/process-departments/<proc>` | 设映射 |
| DELETE | `/process-departments/<proc>` | 删映射 |

### 工单

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/workorder/register` | 注册 |
| DELETE | `/workorder/<no>` | 删除 |
| POST | `/workorder/<no>/refresh` | 刷新 |
| GET | `/workorder/<no>` | 详情 |
| POST | `/workorder/change-delivery-date` | 改交期 |
| GET | `/workorder/stats` | 统计 |

### 质检 / 外协 / 维修

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/quality/create` | 创建质检任务 |
| GET | `/repair-categories` | 维修分类 |
| POST | `/repair-categories` | 新增分类 |
| DELETE | `/repair-categories/<id>` | 删分类 |
| GET | `/repair-records` | 维修记录 |
| POST | `/repair-records/<id>/complete` | 维修完成 |
| GET | `/outsource-config` | 外协配置 |
| POST | `/outsource-config` | 保存 |
| GET | `/outsource-records` | 外协记录 |
| POST | `/outsource-records` | 创建 |
| GET | `/outsource-records/<id>` | 详情 |
| POST | `/outsource-records/<id>/assign` | 指派 |
| POST | `/outsource-records/<id>/receive` | 接收 |
| POST | `/outsource-records/<id>/feedback` | 反馈 |
| POST | `/outsource-records/<id>/complete` | 完成 |

### 子步骤 / 审计

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/process_sub_steps/<no>` | 子步骤 |
| GET | `/process_sub_step_summary/<no>` | 汇总 |
| GET | `/api/admin/orders` | 管理-订单 |
| GET | `/api/admin/sub-steps/<no>` | 管理-子步骤 |
| GET | `/api/admin/audit/<no>` | 管理-审计 |
| POST | `/api/admin/rollback` | 管理-回滚 |

### 规则 / 模板

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/templates` | 流程模板 |
| POST | `/templates` | 创建 |
| GET | `/global-config` | 全局配置 |
| PUT | `/global-config` | 更新 |
| GET | `/rules` | 规则列表 |
| POST | `/rules` | 创建规则 |
| GET | `/flow-matching-rules` | 流程匹配规则 |
| POST | `/flow-matching-rules` | 更新规则 |

### 云端 / 调度器 / 服务器

| 方法 | 路由 | 说明 |
|------|------|------|
| GET/POST | `/cloud/config` | 云端配置 |
| GET | `/cloud/status` | 云端状态 |
| GET | `/cloud/poll-data` | 轮询数据 |
| GET | `/cloud/connection-test` | 连接测试 |
| GET | `/scheduler-manager/status` | 调度器 |
| PUT | `/scheduler-manager/toggle` | 启停 |
| PUT | `/scheduler-manager/interval` | 间隔 |
| GET | `/servers` | 服务器列表 |
| POST | `/servers/<key>/start` | 启动 |
| POST | `/servers/<key>/stop` | 停止 |
| GET | `/servers/logs` | 日志 |
| GET | `/servers/python-path` | Python路径 |

### 其他

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| GET | `/status` | 状态 |
| GET | `/stats` | 统计 |
| GET | `/devices` | 设备列表 |
| GET | `/devices/<id>/tasks` | 设备任务 |
| GET | `/dispatch-log` | 调度日志 |
| GET | `/alerts` | 告警列表 |
| POST | `/alerts/<id>/dismiss` | 消除告警 |
| GET | `/documents` | 文档列表 |
| GET | `/documents/<id>` | 文档详情 |
| GET | `/admin` | 管理页 |
| GET | `/wechat/users` | 微信用户 |
| POST | `/api/enterprise/structure/push` | 推送企业架构 |
| GET | `/debug/cc-workorders` | 调试工单 |

---

## 库存管理 (port 5010) — 5 routes

| 方法 | 路由 | 说明 | 参数 |
|------|------|------|------|
| GET | `/api/v1/inventory/query` | 查库存 | `?product_id=&warehouse_id=` |
| POST | `/api/v1/inventory/inbound` | 入库 | `{product_id, warehouse_id, quantity, remark}` |
| POST | `/api/v1/inventory/outbound` | 出库 | `{product_id, warehouse_id, quantity, remark}` |
| GET | `/api/v1/inventory/alert` | 预警 | `?threshold=N` |
| GET | `/api/health` | 健康检查 | — |

---

## 跨服务调用关系

```
桌面端 ──POST──► :5002/api/schedule/publish     (发布排产)
桌面端 ──POST──► :5002/api/flow-map/sync         (产品映射)
桌面端 ──POST──► :5010/api/v1/inventory/inbound  (直接入库)

报工程序 ──GET──► :5003/cloud/poll-data          (轮询任务)
报工程序 ──GET──► :5010/api/v1/inventory/query   (查库存)
报工程序 ──GET──► :5002/api/operators            (操作员)

调度中心 ──GET──► :5002/api/enterprise/structure (部门同步)
调度中心 ──POST─► :5002/api/schedule/publish      (触发发布)
调度中心 ──GET──► :5010/api/v1/inventory/query   (查库存)
```

## 统计

| 服务 | 端点 | 核心域 |
|------|------|--------|
| 报工程序 | 32 | 报工/考勤/质检/扫码/看板 |
| 容器中心 | 59 | 排产/流程CRUD/外协/子步骤/任务/企业架构 |
| 调度中心 | 110 | 任务/流程/消息/操作员/部门/工单/规则/云端 |
| 库存管理 | 5 | 入库/出库/查询/预警 |
| **总计** | **206** | |
