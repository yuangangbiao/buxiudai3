# 不锈钢网带跟单 3.0 — 前端页面清单

> **版本**: v1.0
> **生成日期**: 2026-06-28
> **扫描范围**: `d:\yuan\不锈钢网带跟单3.0\`
> **扫描方式**: HTML 模板 + Jinja2 路由 + Tkinter 视图枚举

---

## 一、系统服务架构总览

项目采用"桌面端 GUI + 多端 Web"双形态,各前端分布在不同端口的服务中。

| 端口 | 服务名 | 入口文件 | 形态 | 前端页面数 |
|:----:|:------:|:---------|:----:|:----------:|
| 5000 | 大屏展示 | `desktop/views/dashboard/dashboard_server.py` | 浏览器 (HTML+ECharts) | 4 |
| 5001 | 桌面端 Web 替代 | `desktop_web/server.py` | 浏览器 (HTML+Bootstrap) | 18 |
| 5002 | 容器中心 | `mobile_api_ai/container_center_api.py` + `container_dashboard.py` | 浏览器 | 2 |
| 5003 | 调度中心 | `mobile_api_ai/standalone_dispatch_server.py` | 浏览器 + API | 2 |
| 5008 | 移动端报工 H5 | `mobile_api_ai/app.py` | 浏览器 (移动端 SPA) | 3 |
| 5010 | 库存管理 (legacy) | `mobile_api_ai/inventory_api_server.py` | 浏览器 | 1 |
| —    | 库存管理 Web | `mobile_api_ai/inventory_web/routes_*.py` | 浏览器 | 24 |
| —    | 人脸签到 | `mobile_api_ai/face_checkin*` | 浏览器 (TensorFlow.js) | 2 |
| —    | 桌面端 GUI | `main.py` → `desktop/views/main_window.py` | Tkinter | 17 |
| —    | Swagger 文档 | `mobile_api_ai/api/swagger.py` | 浏览器 | 1 |
| —    | 报表中心 | `mobile_api_ai/api/reports.py` | 浏览器 | 1 |

---

## 二、桌面端 GUI (Tkinter) — `desktop/views/`

> **入口**: `desktop/views/main_window.py`
> **形态**: 单窗口多 Tab,Tkinter + ttk
> **数据源**: 直接读写 MySQL (`models/*.py` DAO)

### 2.1 主窗口与侧边栏

| 模块ID | 中文名称 | 视图文件 | 继承类 | 功能简介 |
|:------:|:---------|:---------|:------:|:---------|
| — | 主窗口 | `desktop/views/main_window.py` | `MainWindow(tk.Tk)` | 应用入口,顶栏+左侧导航+右侧内容区 |
| — | 通用组件 | `desktop/views/components.py` | — | 公共控件(按钮、表格、对话框工具) |
| — | 基础对话框 | `desktop/views/dialogs/base.py` | `BaseDialog` | 对话框基类,统一按钮/布局/回调 |
| — | 验证器 | `desktop/views/validators/*.py` | — | 表单字段校验(订单/工序) |

### 2.2 业务功能视图(17 个)

| # | 模块ID | 中文名称 | 视图文件 | 功能简介 |
|:-:|:------:|:---------|:---------|:---------|
| 1 | `orders` | 订单管理 | `desktop/views/orders/list_view.py` (`OrderListView`) | 订单卡片列表、新建/编辑/确认/导入/详情 |
| 1a | — | 新建订单对话框 | `desktop/views/orders/new_order_dialog.py` | 表单录入(规格/材质/数量等) |
| 1b | — | 订单编辑对话框 | `desktop/views/orders/order_form_dialog.py` | 编辑已有订单字段 |
| 1c | — | 订单导入预览 | `desktop/views/orders/import_preview_dialog.py` | Excel 导入前预览对比 |
| 1d | — | 订单确认对话框 | `desktop/views/orders/confirm.py` (`show_order_confirm`) | 确认信息 + 状态流转 |
| 1e | — | 订单表单字段定义 | `desktop/views/orders/form.py` | 新建/编辑字段动态构造 |
| 2 | `order_query` | 订单查询 | `desktop/views/order_query_view.py` (`OrderQueryView`) | 多条件查询、详情查看 |
| 3 | `production` | 生产排单 | `desktop/views/production_view.py` (`ProductionView`) | 工单列表、优先级/计划/分配 |
| 4 | `material_prep` | 材料备料 | `desktop/views/material_prep_view.py` (`MaterialPrepView`) | 物料需求、备料状态 |
| 5 | `process` | 工序追踪 | `desktop/views/process_view.py` (`ProcessView`) | 工序任务列表、进度 |
| 6 | `quality` | 质检管理 | `desktop/views/quality_view.py` (`QualityView`) | 质检任务、合格/不合格 |
| 7 | `shipment` | 发货管理 | `desktop/views/shipment_view.py` (`ShipmentView`) | 发货单、物流跟踪 |
| 8 | `finished_stats` | 成品统计 | `desktop/views/finished_product_stats_view.py` | 成品数量/工时/良率 |
| 9 | `logs` | 后台日志 | `desktop/views/log_view.py` (`LogView`) | 操作日志检索、导出 |
| 10 | `bom` | BOM 清单 | `desktop/views/bom_view.py` (`BOMView`) | 物料清单编辑/导入 |
| 11 | `alerts` | 逾期预警 | `desktop/views/alert_view.py` (`AlertView`) | 逾期订单预警 + 弹窗 `show_alert_popup` |
| 12 | `excel` | 数据导入导出 | `desktop/views/excel_view.py` (`ExcelView`) | Excel 导出/模板下载 |
| 13 | `dashboard` | 看板 | `desktop/views/kanban_view.py` (`KanbanView`) | 7 列状态看板 |
| 14 | `operators` | 操作员管理 | `desktop/views/operator_view.py` (`OperatorManagerView`) | 操作员 CRUD、批量导入 |
| 15 | `inventory` | 库存管理(弹窗) | `_archive/desktop/views/inventory_view.py` *(已归档)* | 跳转到 5010 Web |
| 16 | `settings` | 系统设置 | `desktop/views/settings_dialog.py` (`show_settings_dialog`) | 弹窗式系统配置 |
| — | 数据库设置 | — | `desktop/views/db_settings_window.py` | DB 连接配置窗口 |

### 2.3 业务对话框

| 文件 | 功能 |
|:-----|:-----|
| `desktop/views/dialogs/material_dialogs.py` | 物料相关弹窗(新增/编辑) |
| `desktop/views/dialogs/quality_dialogs.py` | 质检相关弹窗 |
| `desktop/views/dialogs/rule_dialogs.py` | 规则配置弹窗 |
| `desktop/views/dialogs/widgets.py` | 通用对话框控件 |
| `desktop/views/material_rules_view.py` | 物料规则独立窗口 |
| `desktop/views/quality_rule_view.py` | 质检规则独立窗口 |
| `desktop/views/process_calc_rule_view.py` | 工序计算规则窗口 |
| `desktop/views/finished_product_stats_view.py` | 成品统计窗口 |
| `desktop/views/error_lookup_view.py` | 错误码查询窗口 |
| `desktop/views/backup_view.py` | 数据备份窗口 |
| `desktop/views/components.py` | 通用控件库 |

---

## 三、桌面端 Web 替代(5001 端口) — `desktop_web/`

> **入口**: `desktop_web/server.py`
> **形态**: Flask + Jinja2 + 原生 JS/Bootstrap
> **设计目标**: 1:1 复刻桌面端 Tkinter 视图,可在浏览器访问
> **鉴权**: `require_auth` + `verify_csrf_token` + Session

### 3.1 页面路由清单(18 个)

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/` | `orders.html`(重定向) | 首页 | 重定向到 `/orders` |
| 2 | `/orders` | `orders.html` | 订单列表 | 卡片列表 + 筛选 + 新建/编辑/确认 |
| 3 | `/orders/new` | `order_new.html` | 新建订单 | 完整订单表单 |
| 4 | `/order-query` | `order_query.html` | 订单查询 | 多条件检索 + 详情面板 |
| 5 | `/operators` | `operators.html` | 操作员管理 | CRUD + 批量导入/导出 |
| 6 | `/kanban` | `kanban.html` | 看板视图 | 7 列状态看板(对标桌面 KanbanView) |
| 7 | `/production` | `production.html` | 生产排单 | 工单列表、优先级、分配 |
| 8 | `/scheduling` | `production.html`(同模板) | 排产调度 | 同上,语义别名 |
| 9 | `/production-admin` | `production_admin.html` | 生产管理(管理员) | 高级设置/批量操作 |
| 10 | `/material` | `material.html` | 材料备料 | 物料需求与状态 |
| 11 | `/material-admin` | `material_admin.html` | 物料管理(管理员) | 物料 CRUD、模板、规则 |
| 12 | `/process-track` | `process_track.html` | 工序追踪 | 甘特图+状态时间线 |
| 13 | `/process-admin` | `process_admin.html` | 工序管理(管理员) | 工序模板/规则配置 |
| 14 | `/quality` | `quality.html` | 质检管理 | 质检任务、上报结果 |
| 15 | `/quality-admin` | `quality_admin.html` | 质检管理(管理员) | 质检规则、阈值配置 |
| 16 | `/dashboard` | `dashboard.html` | 仪表板 | 关键指标卡片 |
| 17 | `/work-reports` | `work_reports.html` | 报工记录 | 报工历史/失败重试 |
| 18 | `/shipment` | `shipment.html` | 发货管理 | 发货单 + 物流跟踪 |
| 19 | `/shipment-admin` | `shipment_admin.html` | 发货管理(管理员) | 物流公司/规则 |
| 20 | `/order-import` | `order_import.html` | 订单导入 | Excel 上传/字段映射 |
| 21 | `/login` | `login.html` | 登录页 | 账号密码登录 + CSRF |
| 22 | `/health` | — | 健康检查 | JSON 状态 |

---

## 四、移动端报工 H5(5008 端口) — `mobile_api_ai/app.py`

> **入口**: `mobile_api_ai/app.py` (`create_app` 内定义)
> **形态**: 移动端响应式 SPA
> **鉴权**: `X-User-Id` header(在 `before_request` 强制)

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/` | `mobile_unified.html` | 统一报工主页 | 扫码 + 任务列表 + 报工提交 |
| 2 | `/scanner` | `scanner.html` | 扫码页面 | html5-qrcode 摄像头扫码 |
| 3 | `/mobile_login.html` | `mobile_login.html` (send_from_directory) | 移动端登录 | 操作员扫码登录 |

### 4.1 移动端 API 资源(由蓝图注册)

- `api/auth.py` — 登录/校验
- `api/scan.py` — 扫码报工
- `api/process.py` — 工序报工
- `api/quality.py` — 质检上报
- `api/message.py` — 消息接收
- `api/approval.py` — 审批
- `api/health.py` — 健康检查
- `api/quality_inspection.py` — 质检详情
- `api/stats.py` — 统计(可选)

---

## 五、调度中心(5003 端口) — `mobile_api_ai/standalone_dispatch_server.py`

> **入口**: `mobile_api_ai/standalone_dispatch_server.py`
> **形态**: 浏览器 + JSON API
> **鉴权**: JWT (`JWT_SECRET_KEY` 环境变量强制)

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/` | — | 根重定向 | 302 → `/api/dispatch-center/` |
| 2 | `/api/dispatch-center/` | `dispatch_center.html` | 调度中心主面板 | 单页应用,侧边栏 21 个 Tab |
| 2a | 同上 → `overview` | `dispatch_center.html` (内嵌) | 概览 | 待处理/进行中/已完成/逾期卡片 |
| 2b | 同上 → `operators` | 同上 | 操作员管理 | 操作员 CRUD、部门绑定 |
| 2c | 同上 → `tasks` | 同上 | 任务调度 | 任务列表、分配/转派/取消 |
| 2d | 同上 → `messages` | 同上 | 消息调度 | 微信消息模板、发送历史 |
| 2e | 同上 → `processes` | 同上 | 流程编排 | 工序推进/拒绝/回退 |
| 2f | 同上 → `rules` | 同上 | 规则配置 | 流程匹配规则 |
| 2g | 同上 → `process-config` | 同上 | 工序配置 | 工序名称/部门 |
| 2h | 同上 → `monitor` | 同上 | 监控告警 | 实时监控 + 告警 |
| 2i | 同上 → `cloud` | 同上 | 云端配置 | 云端 API Key、企业微信 |
| 2j | 同上 → `repairs` | 同上 | 报修管理 | 报修记录、完成 |
| 2k | 同上 → `outsource` | 同上 | 外协管理 | 外协发出/接收/完成 |
| 2l | 同上 → `warehousing` | 同上 | 成品入库 | 入库确认 |
| 2m | 同上 → `feedback` | 同上 | 反馈管理 | 用户反馈列表 |
| 2n | 同上 → `quality-inspect` | 同上 | 质检管理 | 质检记录 |
| 2o | 同上 → `report-records` | 同上 | 报工记录 | 报工历史 |
| 2p | 同上 → `quality-regression` | 同上 | 质检回归 | 质检回退数据 |
| 2q | 同上 → `material-regression` | 同上 | 物料回归 | 物料回退数据 |
| 2r | 同上 → `outsource-regression` | 同上 | 外协回归 | 外协回退数据 |
| 2s | 同上 → `schedule-regression` | 同上 | 排产回归 | 排产回退数据 |
| 2t | 同上 → `schedule` | 同上 | 排产列表 | 排产任务列表 |
| 2u | 同上 → `material-dc` | 同上 | 物料任务 | 物料任务管理 |
| 2v | 同上 → `system-config` | 同上 | 系统配置 | 系统级参数 |
| 2w | 同上 → `sync-queue` | 同上 | 同步队列 | 失败队列、重试 |

### 5.1 调度中心 API(蓝图)

| 蓝图 | 前缀 | 文件 | 端点数(约) |
|:-----|:-----|:-----|:----------:|
| `dispatch_center_bp` | `/api/dispatch-center` | `dispatch_center/_core.py` | ~120 |
| `schedule_bp` | `/api/schedule` | `dispatch_center/schedule_routes.py` | 13 |
| `workorder_bp` | `/api/workorder` | 同上 | 2 |
| `shipment_bp` | `/api/dispatch-center/shipping` | `dispatch_center/shipment_routes.py` | 10 |
| `sync_bp` | `/api/sync` | `sync_bp.py` | 16 |
| `config_center_bp` | `/api/config-center` | `config_center/` | — |

> **说明**: `dispatch_center.html` 内 `switchTab()` 通过 JS 切换右侧内容面板,所有数据通过 fetch 调上述 API。

---

## 六、容器中心 / 看板(5002 端口) — `mobile_api_ai/container_dashboard.py`

> **入口**: `mobile_api_ai/container_dashboard.py` + `mobile_api_ai/container_center_api.py`
> **形态**: 浏览器 + JSON API

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/` | `unified_container.html` | 容器中心主面板 | 容器状态、统计、操作员配置 |
| 2 | `/config` | (待确认) | 容器配置 | 操作员/命令/日志 |
| 3 | `/alert-rules` | `alert_rules.html` (legacy) | 告警规则 | 阈值规则配置 |

> **备注**: `unified_container.html` 同时被 `container_dashboard_bp.route('/')` 和 `/api/dispatch-center/container-stats` 反向代理共用。

---

## 七、库存管理(5010 端口)— `mobile_api_ai/inventory_web/`

> **入口**: `mobile_api_ai/inventory_api_server.py` (legacy) + `inventory_web/routes_*.py`
> **形态**: Flask + Jinja2 + Bootstrap 5 + html5-qrcode
> **鉴权**: Session + CSRF + Rate Limit (`rate_limiter.py`)

### 7.1 入口页(legacy 登录)

| # | 路由 | 模板文件 | 页面名称 |
|:-:|:----:|:---------|:---------|
| 1 | `/login` | `mobile_api_ai/templates/login.html` | 库存管理登录页(账号密码) |
| 2 | `/` | 重定向至 `/inventory/dashboard` | 首页 |
| 3 | `/logout` | — | 退出登录 |

### 7.2 库存业务页面(24 个)— `inventory_web/routes_*.py`

| # | 路由 | 模板文件 | 页面名称 | 所属文件 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/inventory/dashboard` | `inventory/dashboard.html` | 库存仪表板 | `routes_core.py` |
| 2 | `/inventory/stock` | `inventory/stock_list.html` | 库存清单 | `routes_core.py` |
| 3 | `/inventory/inbound` | `inventory/inbound.html` | 入库 | `routes_core.py` |
| 4 | `/inventory/outbound` | `inventory/inbound.html`(复用) | 出库 | `routes_core.py` |
| 5 | `/inventory/alerts` | `inventory/alerts.html` | 库存预警 | `routes_core.py` |
| 6 | `/inventory/warehouses` | `inventory/warehouses.html` | 仓库管理 | `routes_core.py` |
| 7 | `/inventory/categories` | `inventory/categories.html` | 分类管理 | `routes_core.py` |
| 8 | `/inventory/export` | `inventory/export.html` | 数据导出 | `routes_core.py` |
| 9 | `/inventory/print/preview` | `inventory/print_preview.html` | 打印预览 | `routes_core.py` |
| 10 | `/inventory/base` | `inventory/base_data.html` | 基础数据 | `routes_core.py` |
| 11 | `/inventory/settings` | `inventory/settings.html` | 系统设置 | `routes_core.py` |
| 12 | `/inventory/batch` | `inventory/batch.html` | 批量操作 | `routes_core.py` |
| 13 | `/inventory/stocktake` | `inventory/stocktake.html` | 库存盘点 | `routes_core.py` |
| 14 | `/inventory/transfer` | `inventory/transfer.html` | 调拨 | `routes_core.py` |
| 15 | `/inventory/products` | `inventory/products.html` | 产品管理 | `routes_data.py` |
| 16 | `/inventory/suppliers` | `inventory/suppliers.html` | 供应商管理 | `routes_data.py` |
| 17 | `/inventory/recycle-bin` | `inventory/recycle_bin.html` | 回收站 | `routes_data.py` |
| 18 | `/inventory/backup` | `inventory/backup.html` | 备份管理 | `routes_system.py` |
| 19 | `/inventory/reports` | `inventory/reports.html` | 报表中心 | `routes_api.py` |
| 20 | `/inventory/notifications` | `inventory/notifications.html` | 通知中心 | `routes_api.py` |
| 21 | `/inventory/scanner` | `inventory/scanner.html` | 扫码出入库 | `routes_api.py` |
| 22 | `/inventory/bom` | `inventory/bom.html` | BOM 清单 | (待确认) |
| 23 | `/inventory/logs` | `inventory/logs.html` | 操作日志 | (待确认) |
| 24 | `/inventory/dashboard` (新版) | `inventory/dashboard.html` | 数据看板 | `routes_external.py` |

### 7.3 库存 API 端点(节选)

| 蓝图 | 前缀 | 端点数(约) |
|:-----|:-----|:----------:|
| `web_bp` (routes_core) | `/inventory` | 35+ |
| `routes_data` | `/inventory/api` | 18+ |
| `routes_system` | `/inventory` + `/inventory/api` | 11 |
| `routes_api` | `/inventory` + `/inventory/api` | 14 |
| `routes_external` | `/api/external/inventory` | 3 (防腐层) |

---

## 八、大屏展示(5000 端口) — `desktop/views/dashboard/`

> **入口**: `desktop/views/dashboard/dashboard_server.py`
> **形态**: Flask + HTML + ECharts
> **特点**: 三个版本切换 + 配置页

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/` | `dashboard_v3.html` | 大屏主页面(默认 v3) | 生产监控大屏 |
| 2 | `/v1` | `dashboard_v1.html` | 方案1 - 深蓝经典版 | 历史版本,对比保留 |
| 3 | `/v2` | `dashboard_v2.html` | 方案2 - 进度卡片版 | 历史版本,对比保留 |
| 4 | `/v3` | `dashboard_v3.html` | 方案3 - 紧凑卡片版 | 最新推荐版 |
| 5 | `/config` | `dashboard_config.html` | 大屏配置页 | 数据源/刷新频率配置 |
| 6 | `/api/health` | — | 健康检查 | JSON |
| 7 | `/api/dashboard_data` | — | 大屏数据 API | 订单/工时/良率汇总 |
| 8 | `/api/status` | — | 系统状态 API | 服务状态 |
| 9 | `/api/province_distribution` | — | 省份分布 API | ECharts 数据源 |

---

## 九、人脸签到 — `mobile_api_ai/face_checkin*`

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/face/` | `face_checkin/index.html` | 人脸签到主页 | TensorFlow.js 摄像头人脸识别 |
| 2 | `/face/admin/` | `face_checkin/admin/index.html` | 签到管理后台 | 签到记录查询、统计、导出 |

> **静态资源**:
> - `face_checkin/admin/admin.js` — 后台逻辑
> - `face_checkin/admin/style.css` — 后台样式
> - `face_checkin_static/assets/index-*.js` — TensorFlow.js 打包
> - `face_checkin_static/wasm/*.wasm` — WASM 后端
> - `face_checkin_static/models/*.json` — 模型权重

---

## 十、Swagger API 文档 — `mobile_api_ai/api/swagger.py`

| # | 路由 | 页面名称 |
|:-:|:----:|:---------|
| 1 | `/api/swagger/` | Swagger UI 文档 |
| 2 | `/api/swagger/openapi.json` | OpenAPI 规范 |
| 3 | `/api/swagger/summary` | 文档摘要 |

> **模板**: `mobile_api_ai/templates/swagger.html`

---

## 十一、报表中心 — `mobile_api_ai/api/reports.py`

| # | 路由 | 模板文件 | 页面名称 | 功能简介 |
|:-:|:----:|:---------|:---------|:---------|
| 1 | `/api/reports/page` | `reports_dashboard.html` | 报表管理主页 | 报表定义/Profile/Schedule/Outputs |

> **API 端点**: `/api/reports/definitions`、`/api/reports/profiles`、`/api/reports/schedules`、`/api/reports/outputs`、`/api/reports/scheduler/*`

---

## 十二、其他模板/页面资产

| 文件 | 路径 | 用途 |
|:-----|:-----|:-----|
| `mobile_unified.html` | `mobile_api_ai/templates/` | 移动端报工主页面 |
| `mobile_login.html` | `mobile_api_ai/templates/` | 移动端登录页(企业微信OAuth) |
| `config_center.html` | `mobile_api_ai/templates/` | 配置中心(预留,需确认路由) |
| `template_manage.html` | `mobile_api_ai/templates/` | 模板管理(预留) |
| `admin_audit.html` | `mobile_api_ai/static/` | 审计后台(纯静态) |
| `cs_report.html` | `mobile_api_ai/archive/templates/` | 客服报表(已归档) |
| `xref-库存管理系统.html` | `temp_inventory_build/`, `final_inventory_build/` | 历史构建产物,需清理 |

### 订单模板(Excel,非 HTML)

| 文件 | 用途 |
|:-----|:-----|
| `orders_template.xlsx` | 通用订单导入模板 |
| `orders_乙型网带_template.xlsx` | 乙型网带专用 |
| `orders_螺旋网带_template.xlsx` | 螺旋网带专用 |
| `orders_人字形网带_template.xlsx` | 人字形网带专用 |
| `orders_链条网带_template.xlsx` | 链条网带专用 |
| `orders_链板网带_template.xlsx` | 链板网带专用 |
| `orders_编织网带_template.xlsx` | 编织网带专用 |
| `orders_full_template.xlsx` | 完整字段模板 |

> 路径: `d:\yuan\不锈钢网带跟单3.0\templates\`

---

## 十三、汇总统计

| 形态 | 页面数 |
|:-----|:------:|
| Tkinter 桌面 GUI 视图 | **17** |
| Flask Jinja2 HTML 页面 | **57** |
| 纯静态 HTML(face_checkin / admin_audit) | **3** |
| **合计** | **77** |

### 端口分布

| 端口 | 页面数 |
|:----:|:------:|
| 5000 (大屏) | 4 |
| 5001 (桌面 Web) | 18 |
| 5002 (容器中心) | 2 |
| 5003 (调度中心) | 1(单页 SPA,含 21 Tab) |
| 5008 (移动端) | 2 |
| 5010 (库存 legacy) | 1 |
| inventory_web(蓝图) | 24 |
| face_checkin | 2 |
| 桌面端 GUI(Tkinter) | 17 |
| Swagger/报表 | 2 |

---

## 十四、待确认/潜在死页面

> 以下页面在源码中未发现显式路由绑定,可能为历史残留或预留页面:

| 文件 | 状态 |
|:-----|:----:|
| `mobile_api_ai/templates/config_center.html` | 未见路由绑定 |
| `mobile_api_ai/templates/template_manage.html` | 未见路由绑定 |
| `mobile_api_ai/templates/container_dashboard.html` | 未见路由绑定(可能由 container_dashboard_bp 直接返回 unified_container) |
| `mobile_api_ai/templates/container_config.html` | 未见路由绑定 |
| `mobile_api_ai/templates/alert_rules.html` | legacy 路径,可能由 inventory_web 接管 |
| `mobile_api_ai/static/admin_audit.html` | 静态文件,需手动访问 |
| `mobile_api_ai/archive/templates/cs_report.html` | 已归档,建议清理 |
| `temp_inventory_build/库存管理系统/xref-库存管理系统.html` | 历史构建产物,建议清理 |
| `final_inventory_build/库存管理系统/xref-库存管理系统.html` | 历史构建产物,建议清理 |
| `desktop/views/dashboard/templates/dashboard_v1.html` | 仅保留用于版本对比,可通过 `/v1` 访问 |
| `desktop/views/dashboard/templates/dashboard_v2.html` | 同上 |
| `desktop/views/dashboard/templates/dashboard_v3.html` | 默认版本 |

---

## 十五、访问入口速查

```
桌面端 GUI      : python main.py                 → Tkinter 窗口
桌面端 Web(5001) : python desktop_web/server.py  → http://localhost:5001
调度中心(5003)   : python -m mobile_api_ai.standalone_dispatch_server → http://localhost:5003/api/dispatch-center/
容器中心(5002)   : python -m mobile_api_ai.container_dashboard       → http://localhost:5002/
大屏(5000)      : python desktop/views/dashboard/dashboard_server.py → http://localhost:5000/
移动端(5008)    : python -m mobile_api_ai.app                        → http://localhost:5008/
库存(5010)      : python -m mobile_api_ai.inventory_api_server       → http://localhost:5010/
```

---

**文档结束**