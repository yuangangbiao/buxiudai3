# 不锈钢网带跟单系统 v3.0 — Code Wiki

> **生成时间**: 2026-06-09
> **仓库路径**: `d:\yuan\不锈钢网带跟单3.0\`
> **技术栈**: Python 3.11 · Tkinter · Flask · MySQL · Redis · 企业微信
> **代码规模**: ~247 个核心源文件 / ~56 万 tokens（Repomix 度量）

本 Wiki 是对整个仓库的结构化梳理，覆盖 **项目架构、模块职责、关键类与函数、依赖关系、运行方式**，供新成员快速建立全局视图，也作为日常开发的导航索引。

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 整体架构](#2-整体架构)
- [3. 仓库目录结构](#3-仓库目录结构)
- [4. 入口与启动流程](#4-入口与启动流程)
- [5. 核心框架层 `core/`](#5-核心框架层-core)
- [6. 数据访问层 `models/`](#6-数据访问层-models)
- [7. 业务服务层 `services/`](#7-业务服务层-services)
- [8. 公共工具层 `utils/`](#8-公共工具层-utils)
- [9. 桌面端 `desktop/`](#9-桌面端-desktop)
- [10. 微服务集群 `mobile_api_ai/`](#10-微服务集群-mobile_api_ai)
- [11. 插件系统 `plugins/`](#11-插件系统-plugins)
- [12. 配置体系](#12-配置体系)
- [13. 数据模型与状态机](#13-数据模型与状态机)
- [14. 事件总线与发布订阅](#14-事件总线与发布订阅)
- [15. 关键类与函数索引](#15-关键类与函数索引)
- [16. 依赖关系](#16-依赖关系)
- [17. 测试体系](#17-测试体系)
- [18. 部署与运行方式](#18-部署与运行方式)
- [19. 死代码清理记录（Dead Code Cleanup Log）](#19-死代码清理记录dead-code-cleanup-log)
- [20. 附录：脚本与辅助工具](#20-附录脚本与辅助工具)

---

## 1. 项目概述

### 1.1 业务背景

不锈钢输送网带跟单系统（"钢带订单追踪系统"）是一套面向**生产制造企业**的综合性 MES（制造执行系统），主要解决以下问题：

- 不锈钢网带产品的**订单全生命周期管理**（9 状态流转）；
- **生产排产、工序追踪、报工**（含微信扫码移动报工）；
- **质检规则与质检流程**；
- **备料计算**（基于工艺规则与产品类型自动计算物料需求）；
- **库存管理**（原材料 + 成品）；
- **发货与物流**对接；
- 与**企业微信**深度集成（机器人、应用消息、扫码登录、人脸考勤）；
- **数据可视化看板**（生产状态、订单分布、统计图表）。

### 1.2 系统定位

- **形态**：C/S（桌面端 Tkinter）+ B/S（Flask 微服务）混合架构；
- **数据底座**：MySQL 为主，SQLite 用于本地缓存/容器存储；
- **核心特点**：模块化分层、事件驱动、服务层封装、统一配置、UI 懒加载。

### 1.3 版本信息

| 维度 | 取值 |
|------|------|
| 当前版本 | 3.0.0（CHANGELOG 标记 2026-05-26） |
| 桌面端入口 | `main.py` |
| 服务端入口 | `mobile_api_ai/app.py` |
| Python 版本 | 3.11（参见 `pyproject.toml` / `.python-version`） |
| 数据库 | MySQL 5.7+ / MariaDB 10.2+（仅 MySQL，SQLite 仅作开发兼容） |

---

## 2. 整体架构

### 2.1 分层视图

```
┌────────────────────────────────────────────────────────────────────┐
│                          桌面端 Tkinter                            │
│  main.py → MainWindow (懒加载侧边栏模块)                            │
├────────────────────────────────────────────────────────────────────┤
│ 视图层 desktop/views  │ OrderView / ProcessView / QualityView …   │
├────────────────────────────────────────────────────────────────────┤
│ 校验层 desktop/views/validators │ 表单/工序校验                      │
├────────────────────────────────────────────────────────────────────┤
│ 对话框层 desktop/views/dialogs  │ BaseDialog + popup_form           │
├────────────────────────────────────────────────────────────────────┤
│ Presenter desktop/presenters  │ MVVM 中介（new_order/process）       │
├────────────────────────────────────────────────────────────────────┤
│ 服务层 services/        │ OrderService / ProcessService / …       │
├────────────────────────────────────────────────────────────────────┤
│ 数据访问层 models/      │ OrderDAO / ProcessDAO / …               │
├────────────────────────────────────────────────────────────────────┤
│ 核心框架 core/          │ EventBus / Config / DB / 异常体系        │
├────────────────────────────────────────────────────────────────────┤
│ 工具层 utils/           │ validators / templates / 缓存 / 窗口     │
├────────────────────────────────────────────────────────────────────┤
│ 插件层 plugins/         │ 材质 / 工艺 / 业务扩展点                 │
└────────────────────────────────────────────────────────────────────┘
          ▲                     │                            ▲
          │ UI 操作             │ DAO 直连 MySQL             │ HTTP
          │                     ▼                            │
┌─────────────────────────────────────┐  ┌────────────────────────────────┐
│      Flask 微服务集群                │  │       企业微信 (外部)           │
│      mobile_api_ai/                 │  │  · 群机器人 (群消息回调)        │
│  ┌──────────────────────────────┐  │  │  · 应用机器人 (私聊)            │
│  │  app.py → 注册 14+ 蓝图     │  │◀─┤  · 通讯录/部门结构              │
│  │  · auth/scan/process/quality │  │  │  · 人脸考勤                     │
│  │  · message/approval/health   │  │  └────────────────────────────────┘
│  │  · dispatch_center/         │  │
│  │  · container_center_v5/     │  │
│  │  · inventory_web/           │  │
│  └──────────────────────────────┘  │
│  · sync_bridge (HTTP 反向同步)     │
│  · integration/ (微信通知+桌面回调)│
└─────────────────────────────────────┘
```

### 2.2 模块清单（高层级）

| 模块 | 路径 | 职责 |
|------|------|------|
| 桌面端 | `main.py` + `desktop/` | 订单/工序/质检/库存/发货/看板/操作员/规则等 UI |
| 核心框架 | `core/` | 配置、事件总线、数据库连接、异常、错误码、指标、规则引擎、Saga、熔断器 |
| DAO | `models/` | 25+ 个业务实体的数据访问对象 |
| 服务层 | `services/` | 业务编排（订单/工序/排产/微信报工/审计） |
| 工具 | `utils/` | 验证、模板、窗口、缓存、日志、Excel、备份等 |
| 插件 | `plugins/` | 业务扩展点（材质/工艺） |
| 微服务 | `mobile_api_ai/` | 14+ 蓝图、容器中心、调度中心、库存 Web、人脸考勤 |
| 脚本 | `scripts/` | 一次性工具、数据迁移、DB 检查 |
| 文档 | `docs/` | 设计/任务/复盘/规范/Wiki |

---

## 3. 仓库目录结构

```
d:\yuan\不锈钢网带跟单3.0\
├── main.py                       # 桌面端主入口
├── config.py                     # 兼容旧导入的 re-export 壳
├── constants.py                  # 业务常量与状态枚举
├── version.py                    # 版本号
├── requirements.txt              # 统一依赖（v3.0）
├── pyproject.toml                # pytest / black / isort 配置
│
├── core/                         # 核心框架（无业务依赖）
│   ├── app.py                    # initialize_app() / create_secure_flask_app()
│   ├── config.py + _config_*.py  # 统一配置（路径/数据库/业务/UI/工具）
│   ├── db.py                     # 统一连接池（v3.0 唯一入口）
│   ├── event_bus.py + events.py  # 进程内事件总线 + 事件类型常量
│   ├── redis_event_bus.py        # 跨进程事件总线（可选）
│   ├── event_store.py / event_bus_factory.py
│   ├── error_codes.py / error_codes_structured.py
│   ├── error_handler.py          # 全局异常 → 用户提示
│   ├── exceptions.py             # 业务异常体系
│   ├── logger.py                 # 统一日志
│   ├── metrics.py / feature_flags.py
│   ├── rule_engine.py / circuit_breaker.py / saga.py
│   ├── common_queries.py / json_safe.py / cors_config.py
│
├── models/                       # 数据访问层（DAO）
│   ├── database/
│   │   ├── __init__.py           # 过渡包 → 转发到 core.db
│   │   ├── config.py             # 数据库配置
│   │   ├── _database_legacy.py   # init_db / ensure_*_indexes
│   │   └── utils_db.py           # generate_order_no / log_status_change
│   ├── base_dao.py               # DAO 基类
│   ├── order.py / order_log.py
│   ├── process.py / process_calc_rule.py
│   ├── production.py / production_stats.py
│   ├── quality.py / quality_rule.py
│   ├── shipment.py
│   ├── inventory.py
│   ├── material_rules.py / material_rules_template.py
│   ├── product_type.py / product_flow_map.py
│   ├── operator.py               # 含 OperatorLogDAO
│   ├── operation_log.py
│   ├── photo_storage.py
│   ├── alert.py / bom.py / unit.py / enums.py
│
├── services/                     # 业务服务层
│   ├── base_service.py           # 单例 + 委托基类
│   ├── order_service.py          # 订单 9 状态机
│   ├── process_service.py        # 工序推进
│   ├── schedule_dispatch_service.py  # 本地队列 → 容器中心 → 调度中心 → 企微
│   ├── wechat_report_service.py  # 微信报工回写（幂等）
│   ├── audit_service.py          # 审计日志
│   ├── inventory_sync.py / inventory_notifier.py
│
├── utils/                        # 公共工具
│   ├── validators.py / custom_types.py / pagination.py
│   ├── excel_utils.py / order_templates.py / process_templates.py / material_templates.py
│   ├── query_cache.py / settings_manager.py / backup_manager.py
│   ├── window_manager.py / log_cleanup.py / log_scheduler.py
│   ├── auto_schema.py / dao_patches.py / db_utils.py
│   ├── helpers.py / copyable_widgets.py / password_hasher.py
│   ├── logistics_companies.py / logistics_tracker.py
│   ├── material_calculator.py / auto_refresh_mixin.py
│   ├── op_logger.py / app_init.py
│   ├── storage/  (json_store)
│   └── validation/
│
├── desktop/                      # 桌面端（Tkinter）
│   ├── presenters/               # MVVM 中介
│   │   ├── base_presenter.py
│   │   ├── new_order_presenter.py
│   │   └── process_presenter.py
│   ├── views/
│   │   ├── main_window.py        # 主窗口（侧边栏导航）
│   │   ├── db_settings_window.py
│   │   ├── dashboard/            # 看板服务器（Flask 子模块）
│   │   ├── dialogs/              # 对话框（BaseDialog + popup_form）
│   │   │   ├── base.py
│   │   │   ├── widgets.py
│   │   │   ├── material_dialogs.py
│   │   │   ├── quality_dialogs.py
│   │   │   └── rule_dialogs.py
│   │   ├── orders/               # 订单表单/列表/确认
│   │   ├── validators/           # 校验
│   │   ├── order_view.py / order_query_view.py
│   │   ├── production_view.py / process_view.py / process_calc_rule_view.py
│   │   ├── quality_view.py / quality_rule_view.py
│   │   ├── shipment_view.py
│   │   ├── material_prep_view.py / material_rules_view.py
│   │   ├── kanban_view.py / dashboard_view.py / finished_product_stats_view.py
│   │   ├── excel_view.py / alert_view.py / log_view.py / bom_view.py
│   │   ├── operator_view.py / settings_dialog.py / error_lookup_view.py
│   │   ├── components.py
│   └── window_config.json        # 窗口尺寸记忆
│
├── plugins/                      # 插件系统
│   ├── __init__.py               # PluginRegistry
│   └── materials/
│       ├── __init__.py
│       └── stainless_steel.py    # 不锈钢材质参数
│
├── mobile_api_ai/                # Flask 微服务集群（独立子项目）
│   ├── app.py                    # create_app() 注册 14+ 蓝图
│   ├── api/                      # 14+ 蓝图（auth/scan/process/quality/…）
│   ├── services/                 # 业务服务（notifier/scheduler/…）
│   ├── storage/                  # 存储抽象层（MySQL）
│   ├── dispatch_center/          # 调度中心（_core / schedule_routes）
│   ├── container_center/         # 容器中心（storage/api/services/client）
│   │   ├── api/  (configs / alerts / documents / messages / health)
│   │   ├── storage/ (DocumentStore / IndexStore / ConfigStore / AlertStore)
│   │   └── services/ (AlertEngine)
│   ├── container_center_v5.py    # 容器中心 v5 入口（DataPackage/DataType）
│   ├── inventory_web/            # 库存 Web（8 个 routes_* 拆分）
│   ├── face_checkin/             # 人脸考勤（FastAPI + TF.js 资源）
│   ├── bots/                     # 群机器人/应用机器人基类与工厂
│   ├── commands/                 # 企微指令注册中心
│   ├── integration/              # wechat_notifier / desktop_callback
│   ├── bridge/ sync_bridge_client
│   ├── modules/                  # 增强模块（api_signature/circuit_breaker/…）
│   ├── sync/                     # 事件总线 + 同步处理（attendance/order/…）
│   ├── tests/                    # 单元/集成/E2E 测试
│   ├── utils/  storage/  static/  templates/  specs/
│   └── …（配置/启动脚本/部署文件）
│
├── tests/                        # 桌面端单元 + 集成测试
│   ├── unit/
│   │   ├── core/   (event_bus / config / db / exceptions …)
│   │   ├── models/ (各 DAO 覆盖)
│   │   ├── services/
│   │   └── utils/
│   ├── integration/
│   ├── modular/                  # 模块化集成（auto_publish / 容器监听…）
│   ├── e2e/
│   └── conftest.py
│
├── docs/                         # 项目文档（含本 Wiki）
│   ├── CODE_WIKI.md              # ★ 本文件
│   ├── system_architecture_document.md
│   ├── system_design.md
│   ├── 业务流程分析与优化方案.md / 系统业务流程图.md / 全流程架构图.md
│   ├── …（按模块/任务分类的设计与验收文档）
│
├── scripts/                      # 维护/数据脚本
│   ├── tools/   scripts/archive/  scripts/*.py
│
├── data/                         # 运行时数据
│   ├── rules/                    # 工艺/工序规则 JSON 模板
│   ├── backup_config.json / window_config.json / modular_config.json
│
├── logs/                         # 日志目录
├── db_upgrades/                  # 数据库升级元数据
├── _archive/                     # 旧版归档
│   ├── legacy_db/                # 2026-06-09 归档：旧版 MySQL 连接池
│   └── models/                   # 历史版本模型
├── _deploy/                      # 部署包
└── api/                          # 外部回调（企微）单文件
```

---

## 4. 入口与启动流程

### 4.1 桌面端入口

主入口为 `main.py`。它按以下阶段顺序执行（每段均有计时日志）：

| 阶段 | 动作 | 关键模块 |
|------|------|----------|
| 1 | **并行**：异步升级检查 + 同步许可证校验 | `updater` / `security.license_tool` |
| 2 | 数据库连通性探测；不通过则弹出 `DatabaseSettingsWindow` | `models.database.get_connection` / `db_settings_window` |
| 3 | `initialize_app()`：建表 + 注册事件处理器 + 发布 `APP_STARTED` | `core.app` / `core.event_bus` / `core.events` |
| 4 | 后台线程启动：备份调度、排产队列恢复、容器事件监听 | `backup_system` / `services.schedule_dispatch_service` / `container_event_listener` |
| 5 | 创建 `MainWindow` → `app.run()` 进入主循环 | `desktop.views.main_window` |

关键代码（[main.py:166-285](file:///d:/yuan/不锈钢网带跟单3.0/main.py#L166-L285)）：

- `_check_license()` → 单例指纹 + 机器绑定校验；
- `_check_updates_async()` → 后台线程 `check_for_updates()`；
- `_check_db_and_show_settings()` → 不通过时弹窗引导配置；
- `initialize_app()` → 初始化 DB / 审计表 / 默认事件订阅；
- `MainWindow()` → 侧边栏 16 个模块按需懒加载。

### 4.2 微服务入口

`mobile_api_ai/app.py` 定义 `create_app()`：

- 启动时**清理 `__pycache__`**（避免旧代码残留）；
- 加载项目根 `.env`；
- 注册蓝图：必选（auth/scan/process/quality/message/approval/health/quality_inspection），可选（stats/ai/cost/reports/legacy_routes/inventory_external）；
- 注册容器中心自定义路由：`/api/all-process-tasks`、`/api/process_sub_step`；
- `app.run()` 启动（默认端口由 `FLASK_HOST/FLASK_PORT` 决定）。

### 4.3 关键启动开关

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_HOST` | `0.0.0.0` | 微服务监听地址 |
| `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` | `localhost/3306/root//steel_belt` | MySQL 连接 |
| `DB_POOL_SIZE` | `10` | 连接池大小 |
| `MYSQL_POOL_SIZE` | `20`（legacy） | 回退值 |
| `JWT_SECRET_KEY` | 必填 | 移动端 JWT 签名 |
| `CONTAINER_STORAGE_TYPE` | `mysql` | 容器中心存储后端 |
| `MYSQL_CHARSET` | `utf8mb4` | 字符集 |

---

## 5. 核心框架层 `core/`

> 核心层**不依赖**具体业务，是整个系统的横切关注点。

### 5.1 配置中心 `core/config.py` + `_config_*.py`

- `core/config.py` 是 **facade**，从四个子模块 `import *` 后 re-export，保持外部 import 路径不变：
  - `_config_infra.py` — 路径、环境变量、数据库、超时、调度；
  - `_config_domain.py` — 材质/产品/工序/订单状态/业务阈值；
  - `_config_ui.py` — API 密钥、字体、布局、窗口、颜色、遗留 Config；
  - `_config_funcs.py` — 工具函数、Redis 事件总线。
- 顶层 `config.py` 再次 re-export，使得 `from config import APP_NAME, MYSQL_CONFIG, COLORS` 兼容旧代码。

主要导出（见 [config.py](file:///d:/yuan/不锈钢网带跟单3.0/config.py)）：

- 路径：`BASE_DIR / DATA_DIR / CONFIG_DIR / LOG_DIR`；
- 应用：`APP_NAME / APP_VERSION / RESOURCE_DIR`；
- DB：`DB_PATH / MYSQL_CONFIG / DatabaseConfig / get_db_config / is_sqlite / get_sqlite_path`；
- 业务：`MATERIALS / MATERIAL_DENSITIES / PRESET_MAT_PARAMS / PRESET_DIM_PARAMS / PRODUCT_TYPES / SURFACE_TREATMENTS / ORDER_STATUS / PROCESSES / UNITS`；
- 质检：`INSPECTION_TYPES / INSPECTION_RESULTS / INSPECTION_ITEMS_BY_CATEGORY`；
- 阈值：`STOCK_WARNING_THRESHOLD / BusinessConfig`；
- API：`ApiKeyConfig`；
- 样式：`FONTS / COLORS / StyleConfig / LAYOUT / WINDOW_SIZES / WINDOW / CONTAINER_CENTER_URL`。

### 5.2 数据库连接 `core/db.py`

v3.0 唯一连接入口（[core/db.py:1-167](file:///d:/yuan/不锈钢网带跟单3.0/core/db.py)）：

- `ConnectionPool`（单例）：懒加载 MySQL 连接，池大小取自 `DB_POOL_SIZE`（默认 10）；
- `PooledConnection`（上下文管理器）：`__enter__` 取连接 / `__exit__` 归还；
- `DB` 静态门面：暴露 `get_connection()` / `get_connection_context()`；
- 配置优先 `DB_*` 环境变量，回退 `MYSQL_*`；
- 兼容 `models.database.get_connection()` 旧调用。

### 5.3 事件总线 `core/event_bus.py` + `core/events.py`

- [core/events.py:18-100](file:///d:/yuan/不锈钢网带跟单3.0/core/events.py#L18-L100) 定义 `EventType` 事件常量：
  - 订单 `order:*`、工序 `process:*`、生产 `production:*`、备料 `material:*`、质检 `qc:*`、库存 `inventory:*`、任务 `task:*`、系统 `system:*`；
  - `get_all_events()` / `is_valid_event()` 用于反射/校验。
- [core/event_bus.py:14-100](file:///d:/yuan/不锈钢网带跟单3.0/core/event_bus.py#L14-L100) `EventBus`（**单例**）：
  - `subscribe(event, handler)` / `unsubscribe` / `publish(event, data)`；
  - 处理函数签名 `handler(event, data)`；
  - `reset()` 仅供测试使用。
- `core/redis_event_bus.py` 提供**跨进程**事件总线（基于 Redis Pub/Sub）；
- `core/event_bus_factory.py` 选择本地或 Redis 实现；
- `core/event_store.py` 持久化事件（事件溯源基础）。

### 5.4 异常与错误码

- [core/exceptions.py:9-89](file:///d:/yuan/不锈钢网带跟单3.0/core/exceptions.py#L9-L89) 定义业务异常体系：
  - `BusinessException` 基类
  - `ValidationException` / `NotFoundException` / `DuplicateException` / `PermissionException` / `StateException` / `DatabaseException` / `ConfigException`
- [core/error_codes.py](file:///d:/yuan/不锈钢网带跟单3.0/core/error_codes.py) 提供结构化错误码：
  - `ErrorCode` / `ErrorDomain` / `ErrorSeverity`；
  - `StructuredErrorCode`（含 code/severity/recoverable/suggestion）；
  - 同时提供 `error_codes_structured.py` 兼容层。
- `core/error_handler.py` 集成全局 `sys.excepthook`：
  - 调用 `recognize_error_code()` → 友好提示 → `messagebox.showerror`；
  - 见 [main.py:49-80](file:///d:/yuan/不锈钢网带跟单3.0/main.py#L49-L80) 的 `log_error`。

### 5.5 其他核心模块

| 模块 | 关键类/函数 | 用途 |
|------|-------------|------|
| `core/logger.py` | `LogManager`, `StructuredLogger` | 统一日志 |
| `core/metrics.py` | `MetricsCollector` | 指标采集 |
| `core/feature_flags.py` | `FeatureFlags` | 特性开关 |
| `core/rule_engine.py` | `RuleEngine` | 业务规则求值（白名单公式） |
| `core/circuit_breaker.py` | `CircuitBreaker` + `CircuitBreakerOpenError` | 熔断保护 |
| `core/saga.py` | `SagaStep`, `SagaOrchestrator` | 分布式事务编排 |
| `core/cors_config.py` | `init_cors(app, default_origins)` | CORS 注入 |
| `core/common_queries.py` | — | 公共 SQL 片段 |
| `core/json_safe.py` | — | JSON 安全序列化（datetime/Decimal） |
| `core/app.py` | `initialize_app()`, `get_build_info()`, `create_secure_flask_app()` | 启动聚合 |

---

## 6. 数据访问层 `models/`

> DAO 层全部采用**静态方法**风格（无状态），通过 `get_connection()` 取连接，`try/finally` 确保关闭。

### 6.1 数据库包 `models/database/`

- `__init__.py` 薄壳：从 `core.db` 与 `_database_legacy` 转发，保持旧 API 不变；
- ~~`connection_pool.py` 旧版 `MySQLConnectionPool` + `PooledConnection`~~ —— **2026-06-09 起已归档至 `_archive/legacy_db/connection_pool.py`**。同名类现由 `core.db.ConnectionPool` + `core.db.PooledConnection` 提供；
- `_database_legacy.py` 提供 `init_db()` / `ensure_unique_indexes()` / `ensure_performance_indexes()`，包含完整的**建表 DDL**（`orders / production / process_records / process_sub_steps / quality / material / inventory / operators / audit_logs / data_packages …`）；
- `utils_db.py`：`generate_order_no` / `generate_shipment_no` / `log_status_change` / `_validate_sql_identifier` / `_safe_table_name`；
- `config.py`：`_get_db_config` / `MYSQL_CONFIG`。

### 6.2 业务 DAO 列表

| 模块 | 关键类 | 主要方法 |
|------|--------|----------|
| `order.py` | `OrderDAO` | `create/update/get/list/delete/update_status` + 审计写入 |
| `order_log.py` | `OrderLogDAO` | 订单操作流水 |
| `process.py` | `ProcessDAO` | 工序记录 + 推进 |
| `process_calc_rule.py` | `ProcessCalcRuleDAO` | 工序计算规则（白名单公式） |
| `production.py` | `ProductionDAO` | 生产工单 |
| `production_stats.py` | `ProductionStatsDAO` | 产量统计 |
| `quality.py` | `QualityDAO` | 质检记录 |
| `quality_rule.py` | `QualityRuleDAO` | 质检规则 |
| `shipment.py` | `ShipmentDAO` | 发货 |
| `inventory.py` | `InventoryDAO` | 库存（`stock_in/stock_out/transfer`） |
| `material_rules.py` / `material_rules_template.py` | `MaterialRulesDAO` / `MaterialRulesTemplateDAO` | 备料规则 |
| `product_type.py` | `ProductTypeDAO` | 产品类型字典 |
| `product_flow_map.py` | `ProductFlowMapDAO` | 工艺路径 |
| `operator.py` | `OperatorDAO` / `OperatorLogDAO` | 操作员 + 操作日志 |
| `operation_log.py` | `OperationLogDAO` | 全局操作日志 |
| `photo_storage.py` | — | 照片（质检/产品） |
| `alert.py` | `AlertDAO` | 预警 |
| `bom.py` | `BOMDAO` | 物料清单 |
| `unit.py` | `UnitDAO` | 单位字典 |
| `enums.py` | — | 业务枚举 |
| `base_dao.py` | `BaseDAO` | 通用 CRUD 基类 |

### 6.3 订单 DAO 详例

[models/order.py:32-200](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py#L32-L200) `OrderDAO.create(data)` 的关键设计：

- `FIXED_ORDER_KEYS` 白名单字段直接入库列；其余进入 `extra_params` JSON 字符串；
- 数量 × 单价 = 总额自动计算；
- 自动生成 `order_no`；
- `delivery_date` 空串转 NULL；
- 同步写 `order_logs`（状态变更）。

---

## 7. 业务服务层 `services/`

> 服务层 = **业务编排** + **事务边界** + **事件触发** + **跨模块协作**。
> 大多采用 **单例 + 委托模式**（`base_service.py`）。

### 7.1 `BaseService` 基础设施

[services/base_service.py:18-…](file:///d:/yuan/不锈钢网带跟单3.0/services/base_service.py)：

- 通用单例（`_instance` + `_lock`）；
- 提供 `AuditService` 装饰：自动记录 `before/after` 快照；
- 提供 DB 事务上下文管理。

### 7.2 关键服务

#### 7.2.1 `OrderService`（[services/order_service.py:28-…](file:///d:/yuan/不锈钢网带跟单3.0/services/order_service.py#L28)）

- 9 状态流转机 `STATUS_FLOW`；
- 状态变更 → `AuditService` 记录 → `EventBus.publish(ORDER_STATUS_CHANGED, …)`；
- 委托 `OrderDAO` 完成 CRUD；
- 校验：`OrderValidator`（[utils/validators.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/validators.py)）。

#### 7.2.2 `ProcessService`

- 工序推进、全部完成检查、报工数据回写；
- 委托 `ProcessDAO` + `ProductionDAO`；
- 与 `schedule_dispatch_service` 协作发布报工事件。

#### 7.2.3 `ScheduleDispatchService`（[services/schedule_dispatch_service.py:33-…](file:///d:/yuan/不锈钢网带跟单3.0/services/schedule_dispatch_service.py#L33)）

- **排产调度核心**：本地队列 → 容器中心 → 调度中心 → 企微；
- `start_queue_recovery()` 启动时**自动重发**失败的工单；
- 与 `container_event_listener` 协同（订阅 EventBus 事件）。

#### 7.2.4 `WeChatReportService`

- 微信报工回调的**幂等回写**到 MySQL；
- 防重复、防错位；
- 与 `mobile_api_ai/api/legacy_routes.py::api_dashboard` 对接。

#### 7.2.5 `AuditService` / `inventory_sync` / `inventory_notifier`

- `AuditService`：审计日志统一入口；
- `inventory_sync`：库存系统同步（与库存 Web 通信）；
- `inventory_notifier`：库存低水位通知（企业微信 + EventBus）。

---

## 8. 公共工具层 `utils/`

> 工具层不依赖业务，按职责分组。

| 子目录/文件 | 关键导出 | 用途 |
|-------------|---------|------|
| `validators.py` | `OrderValidator` 等 | 表单/业务校验 |
| `custom_types.py` | `get_unit_options()` 等 | 单位/类型选项 |
| `pagination.py` | `Pagination` | 分页 |
| `excel_utils.py` | — | Excel 导入/导出 |
| `order_templates.py` / `process_templates.py` / `material_templates.py` | — | 模板加载/保存 |
| `query_cache.py` | `QueryCache` | 内存缓存（带 TTL） |
| `settings_manager.py` | — | 配置文件读写（`data/*.json`） |
| `backup_manager.py` | — | 备份目录管理 |
| `window_manager.py` | `setup_resizable_window(win, key, default)` | 窗口尺寸记忆 |
| `log_cleanup.py` / `log_scheduler.py` | — | 日志轮转与清理 |
| `auto_schema.py` | `SafeCursor` | 自动建表/索引 |
| `dao_patches.py` | — | DAO 猴子补丁（兼容） |
| `db_utils.py` | — | DB 工具 |
| `helpers.py` | — | 通用工具函数 |
| `copyable_widgets.py` | — | Tkinter 可复制控件 |
| `password_hasher.py` | — | 密码哈希 |
| `logistics_companies.py` / `logistics_tracker.py` | — | 物流公司字典 + 物流跟踪 |
| `material_calculator.py` | — | 物料需求计算 |
| `auto_refresh_mixin.py` | `AutoRefreshMixin` | Tkinter 自动刷新基类 |
| `op_logger.py` | — | 操作日志装饰器 |
| `app_init.py` | — | 应用初始化辅助 |
| `storage/json_store.py` | — | JSON 持久化 |
| `validation/` | — | 校验子包 |

---

## 9. 桌面端 `desktop/`

### 9.1 启动与导航

[desktop/views/main_window.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/main_window.py) 顶层骨架：

- `MainWindow.__init__`：
  - `init_db()` / `ensure_*_indexes`；
  - `setup_resizable_window(self.root, "main_window", f"{WINDOW['width']}x{WINDOW['height']}")` → **窗口尺寸记忆**；
  - `setup_styles()`（来自 `steel_belt_tracking`）；
  - `_check_alerts()` 启动后 500ms 弹预警。
- `create_sidebar()`：16 个业务模块按钮（**侧边栏导航**）：
  - 订单管理、订单查询、生产排单、材料备料、工序追踪、质检管理、发货管理、成品统计、后台日志、BOM 清单、逾期预警、数据导入导出、看板、操作员管理、库存管理、系统设置。
- `show_module(module_id)`：按 ID 懒加载对应 View 组件；切换时 `widget.destroy()` 清理旧视图。

### 9.2 视图模块清单

| 模块 ID | 视图类（位置） | 职责 |
|---------|----------------|------|
| `orders` | `OrderListView` ([desktop/views/orders/list_view.py:23](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/orders/list_view.py#L23)) | 订单列表/新增/编辑 |
| `order_query` | `OrderQueryView` ([desktop/views/order_query_view.py:48](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/order_query_view.py#L48)) | 多条件查询 |
| `production` | `ProductionView` ([desktop/views/production_view.py:21](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/production_view.py#L21)) | 生产排单 |
| `material_prep` | `MaterialPrepView` ([desktop/views/material_prep_view.py:31](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/material_prep_view.py#L31)) | 备料 |
| `process` | `ProcessView` ([desktop/views/process_view.py:37](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/process_view.py#L37)) | 工序追踪 |
| `quality` | `QualityView` ([desktop/views/quality_view.py:26](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/quality_view.py#L26)) | 质检 |
| `shipment` | `ShipmentView` ([desktop/views/shipment_view.py:26](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/shipment_view.py#L26)) | 发货 |
| `finished_stats` | `FinishedProductStatsView` ([desktop/views/finished_product_stats_view.py:19](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/finished_product_stats_view.py#L19)) | 成品统计 |
| `logs` | `LogView` ([desktop/views/log_view.py:19](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/log_view.py#L19)) | 后台日志 |
| `bom` | `BOMView` ([desktop/views/bom_view.py:13](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/bom_view.py#L13)) | BOM 清单 |
| `alerts` | `AlertView` ([desktop/views/alert_view.py:22](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/alert_view.py#L22)) | 逾期预警 |
| `excel` | `ExcelView` ([desktop/views/excel_view.py:13](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/excel_view.py#L13)) | 导入/导出 |
| `dashboard` / `kanban` | `DashboardView` / `KanbanView` | 看板（与 `dashboard/dashboard_server.py` 子 Flask 集成） |
| `operators` | `OperatorManagerView` / `LogViewer` / `LoginDialog` | 操作员管理 + 登录 |
| `inventory` | — | 库存管理（跳转到 `inventory_web`） |
| `settings` | `show_settings_dialog()` | 系统设置（数据库/主题/字体/容器） |

### 9.3 对话框体系 `desktop/views/dialogs/`

遵循 [views/dialogs/使用规范](file:///d:/yuan/不锈钢网带跟单3.0/.trae/rules/对话框使用规范.md)：

- `base.py`：
  - 顶层工具：`alert()` / `confirm()` / `center_window()` / `manage_custom_types_dialog()` / `validate_field_config()` 装饰器 / `popup_form()` / `show_detail()`；
  - `BaseDialog` 类（[desktop/views/dialogs/base.py:755-…](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/dialogs/base.py#L755)）：**复杂对话框基类**。
- `widgets.py`：`PlaceholderEntry` 等自定义控件；
- `material_dialogs.py`：`MaterialPrepHistoryDialog` / `MaterialQueryLogDialog` / `MaterialRulesContainerDialog` / `BatchCalcMaterialDialog` / `MaterialTemplateManagerDialog` / `MaterialTemplatePreviewDialog`；
- `quality_dialogs.py`：`QualityTaskCompileDialog` / `QualityPublishDialog` / `QualityRecordFormDialog` / `CompletionConfirmDialog` / `QualityRulesDialog` / `QualitySaveResultDialog`；
- `rule_dialogs.py`：`AddProductTypeDialog` / `QualityRuleDialog` / `MaterialRuleDialog` / `SaveRuleTemplateDialog` / `LoadRuleTemplateDialog` / `ManageRuleTemplatesDialog` / `SaveProcessRuleTemplateDialog` / `ProcessRuleEditDialog` / `FlowTypeConfigDialog` / `_get_process_dim_options` / `get_all_param_options_for_quality`。

> **2026-06-09 清理**：原 `desktop/views/dialogs.py`（单文件 13 行的兼容 shim）已**删除**。该文件因与同名包 `desktop/views/dialogs/` 重名，从未被加载；包 `__init__.py`（如存在/未来建立）已承担兼容导出职责。

### 9.4 校验层 `desktop/views/validators/`

- `order_form_validator.py::validate_order_form(data, dim_fields)` → `(bool, List[str])`；
- `process_validator.py::validate_report_submission` / `validate_process_input` / `parse_numeric_inputs`。

### 9.5 Presenter 层 `desktop/presenters/`

- `base_presenter.py`：通用 View ↔ Service 中介；
- `new_order_presenter.py`：新订单表单的 MVVM 中介；
- `process_presenter.py`：工序表单的中介。

### 9.6 看板子模块 `desktop/views/dashboard/`

- `dashboard_server.py`：嵌入式 Flask 子服务（`/api/dashboard-data`、`/api/status`、`/api/province-distribution`）；
- 模板：`dashboard_v1/v2/v3.html`、`dashboard_config.html`。

---

## 10. 微服务集群 `mobile_api_ai/`

> 独立子项目，部署在 `mobile_api_ai/` 下，但通过共享 `core/` 与 `models/` 复用桌面端代码。

### 10.1 入口与蓝图

[mobile_api_ai/app.py:46-300](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/app.py#L46-L300) `create_app()` 启动时：

- 清理 `__pycache__`；
- 加载项目根 `.env`；
- 注入 CORS / Limiter；
- 注册 14+ 蓝图（部分可选/容错）。

### 10.2 蓝图清单 `mobile_api_ai/api/`

| 蓝图文件 | URL 前缀 | 关键路由 | 用途 |
|----------|----------|----------|------|
| `auth.py` | `/api/auth` | `POST /login` | 操作员扫码登录（JWT） |
| `scan.py` | `/api/scan` | `GET /workorder/<order_no>` / `POST /task` / `GET /worker/<id>` | 扫码报工（解析二维码 + 查任务） |
| `process.py` / `process_v2.py` | `/api/process` | `GET /my-tasks` / `POST /<id>/report` / `GET /history` | 工序任务查询/报工 |
| `quality.py` / `quality_inspection.py` | `/api/quality` | — | 质检提交/查询 |
| `message.py` | `/api/message` | — | 消息中心 |
| `approval.py` | `/api/approval` | — | 审批流 |
| `health.py` | `/health` | — | 健康检查 |
| `stats.py` | `/api/stats` | — | 统计（可选） |
| `reports.py` | `/api/reports` | — | 报表（可选） |
| `cost.py` | `/api/cost` | — | 成本（可选） |
| `ai.py` | `/api/ai` | — | AI 辅助（可选） |
| `auto_advance.py` | — | `decide_auto_advance()` | 工序自动推进决策 |
| `decorators.py` | — | — | 限流/鉴权/日志装饰器 |
| `limiter.py` | — | `limiter = Limiter(...)` | Flask-Limiter 实例 |
| `legacy_routes.py` | `/api/*` | `dashboard / scan-info / quality / sub_step_records / production-orders / workers / attendance` | 兼容旧版移动端 |
| `swagger.py` | `/swagger` | — | API 文档 |
| `step_status_helper.py` | — | `compute_step_statuses` | 工序状态计算 |
| `api_validators.py` | — | — | 入参校验 |
| `metrics_api.py` | `/metrics` | — | Prometheus 指标 |

### 10.3 调度中心 `mobile_api_ai/dispatch_center/`

[dispatch_center/_core.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py)（**~65k tokens，最重的单文件**）：

- `_core.py` 集中实现：
  - **数据访问**：`get_steelbelt_cursor` / `get_steelbelt_connection`（直连桌面端 MySQL）；
  - **路由 100+ 个**（按 URL 排序的函数路由），见 [grep 结果](#15-关键类与函数索引)；
  - **核心类**：`DispatchContext` / `DispatchDataCache` / `DispatchStatus` / `AlertLevel` / `_UnavailableClient`；
  - **关键流程函数**：
    - `api_publish_order`（工单发布）
    - `api_submit_schedule` / `api_confirm_schedule` / `api_get_schedule_status`（排产）
    - `api_notify_production`（生产通知）
    - `_do_send_process_task`（实际下发企微）
    - `task_notify`（统一通知入口）
    - `match_flow_type`（匹配工艺路径）
    - `trigger_process_confirmation` / `check_and_trigger_auto_confirmation`（工序确认）
  - **组织结构管理**：`get_wechat_departments` / `list_wechat_users` / `handle_enterprise_structure_push` / `_save_enterprise_to_cache` / `_build_dept_tree_from_raw`；
  - **模板管理**：`get_templates / save_template / update_template / delete_template / reset_template / manage_templates`；
  - **任务管理**：`list_tasks / assign_task / reassign_task / cancel_task / batch_assign`；
  - **缓存**：`DispatchDataCache`（订单/操作员/部门）。
- `schedule_routes.py`：排产相关路由（`api_publish_order` / `api_submit_schedule` / `api_get_pending_schedules` 等）；
- `_constants.py` / `_core_types.py`：常量与类型。

### 10.4 容器中心 `mobile_api_ai/container_center/`

[container_center/__init__.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center/__init__.py) 导出：

- `DocumentStore` / `IndexStore` / `ConfigStore` / `AlertStore`（存储层）；
- `create_container_api_bp` / `init_api_bp`（API 注册）；
- `ContainerCenterClient`（客户端 SDK）；
- `AlertEngine`（告警引擎服务）。

子结构：

| 路径 | 关键类/函数 | 用途 |
|------|------------|------|
| `storage/document_store.py` | `DocumentStore` | 文档桶存储 |
| `storage/index_store.py` | `IndexStore` | 索引 |
| `storage/config_store.py` | `ConfigStore` | 配置 |
| `storage/alert_store.py` | `AlertStore` | 告警 |
| `storage/mysql_router.py` | `MySQLRouter` | MySQL 路由 |
| `storage/redis_cache.py` | `RedisCache` | Redis 缓存 |
| `api/app.py` | `create_app(data_dir)` / `run_server(host, port)` | 独立 Flask 服务 |
| `api/__init__.py` | `create_container_api_bp(name, url_prefix='/api/v4')` | 蓝图工厂 |
| `api/configs.py` | `register_config_routes(bp)` | 配置管理路由 |
| `api/alerts.py` | `register_alert_routes(bp)` | 告警路由 |
| `api/messages.py` | `register_message_routes(bp)` | 消息路由（含企微推送） |
| `api/documents.py` | `register_document_routes(bp)` | 文档路由 |
| `api/health.py` | `register_health_routes(bp)` | 健康检查 |
| `services/alert_engine.py` | `AlertEngine` | 告警规则引擎 |
| `client/container_client.py` | `ContainerCenterClient` | Python 客户端 |
| `v5_compatible_client.py` | — | v5 兼容客户端 |

入口文件 [`container_center_v5.py`](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_v5.py) 定义：

- 枚举 `DataType`（`REPORT/QUALITY/MATERIAL/APPROVAL/ORDER/PROCESS/COST`）+ `DataStatus`（`PENDING/DISTRIBUTED/ACKNOWLEDGED/COMPLETED/EXPIRED/CANCELLED`）；
- 数据类 `DataPackage`（含 `to_dict/from_dict`）；
- `ContainerCenter` 主类（约 4000+ 行）；
- 状态映射 `STATUS_KEY_TO_MYSQL`（同步到 MySQL 时使用）。

### 10.5 库存 Web `mobile_api_ai/inventory_web/`

[mobile_api_ai/inventory_web/](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/)：

- `routes.py` + `routes_api.py` + `routes_core.py` + `routes_data.py` + `routes_external.py` + `routes_system.py`（按职责拆分）；
- `services/`：`inventory_service / notification_service / product_service / report_service / stocktake_service / transfer_service`（v2.0 库存功能优化产物）；
- `templates/inventory/`：20+ HTML（base / dashboard / stock_list / inbound / alerts / bom / backup / reports / stocktake / transfer / warehouses …）；
- `migrations/001_function_optimization.sql`：v2.0 优化迁移；
- `db_utils.py` / `admin_auth.py` / `rate_limiter.py` / `feature_flags.py`：横切关注点。

### 10.6 人脸考勤 `mobile_api_ai/face_checkin/`

- `admin/admin.html + admin.js + style.css`（管理后台前端）；
- `admin_html.py`：服务端 HTML 生成；
- `mobile_api_ai/face_checkin_static/`：TF.js BlazeFace + FaceMesh 资源（`models/*.json`、`wasm/*.wasm`）。

### 10.7 机器人与指令 `mobile_api_ai/bots/`

- `base.py`：机器人基类；
- `factory.py`：工厂方法；
- `app_bot.py`：应用机器人（私聊）；
- `group_bot.py`：群机器人（群消息回调）；
- `message_hub.py`：消息中心。

`mobile_api_ai/commands/`：

- `base.py`：指令基类；
- `manager.py`：注册中心；
- `help_cmd.py` / `outsource_cmd.py` / `query_cmd.py` / `repair_cmd.py` / `repair_complete_cmd.py` / `report_cmd.py` / `task_cmd.py`：业务指令（**32 种命令类型**）。

### 10.8 集成层 `mobile_api_ai/integration/`

- `wechat_notifier.py`：企微消息发送统一入口；
- `desktop_callback.py`：回调桌面端；
- `instruction_handler.py`：指令处理器。

### 10.9 桥接与同步

- `mobile_api_ai/bridge/sync_client.py`：HTTP 反向同步客户端；
- `mobile_api_ai/sync/`：
  - `event_bus.py`：同步事件总线；
  - `init.py`：初始化；
  - `sync_log.py`：同步日志；
  - `handlers/`：`attendance_handler` / `order_handler` / `quality_handler` / `sub_step_handler` / `worker_handler`；
  - `mappers/field_mapper.py`：字段映射。

### 10.10 增强模块 `mobile_api_ai/modules/`

- `api_signature.py`：API 签名校验；
- `circuit_breaker.py`：熔断器；
- `deployment_manager.py`：部署管理；
- `enhanced_audit_logger.py`：增强审计；
- `enhanced_backup.py`：增强备份；
- `fault_tolerance.py`：容错；
- `health_checker.py`：健康检查；
- `queue_manager.py`：队列管理。

### 10.11 存储抽象层

- `mobile_api_ai/storage/mysql_storage.py`：MySQL 存储实现；
- `storage_layer.py`：`create_storage(...)` / `BaseStorage` / `StorageType` 抽象接口。

---

## 11. 插件系统 `plugins/`

- `plugins/__init__.py::PluginRegistry`：插件注册器（按"材质"维度扩展）；
- `plugins/materials/__init__.py`：材质插件注册入口；
- `plugins/materials/stainless_steel.py`：**不锈钢**材质参数（密度、规格、默认值）。

设计原则：

- 业务方调用 `PluginRegistry.get("materials.stainless_steel")` 即可获取对应材质参数；
- 未来新增材质（如 镀锌铁/碳钢）只需添加 `plugins/materials/galvanized_steel.py` 即可，无需改业务代码。

---

## 12. 配置体系

### 12.1 配置文件层级

| 文件 | 用途 |
|------|------|
| `.env`（项目根） | 环境变量（DB 连接 / JWT / 容器配置） |
| `desktop/window_config.json` | 桌面端窗口尺寸记忆 |
| `data/window_config.json` | 全局窗口配置 |
| `data/backup_config.json` | 备份配置 |
| `data/modular_config.json` | 模块化开关 |
| `data/rules/process_rules.json` | 工序规则 |
| `data/工序规则模板*.json` | 模板库 |
| `inventory_server_config.json` / `inventory_client_config.json` | 库存系统（v2 兼容） |
| `mobile_api_ai/data/config.json` | 微服务配置 |
| `mobile_api_ai/data/enterprise_structure.json` | 企业微信组织结构缓存 |

### 12.2 业务常量（[constants.py](file:///d:/yuan/不锈钢网带跟单3.0/constants.py)）

| 枚举 | 取值 |
|------|------|
| `OrderStatus` | 待确认 / 待排产 / 待发布 / 已发布 / 已排产 / 生产中 / 质检中 / 已完成 / 待发货 / 已发货 / 已取消 |
| `ProductionStatus` | 待开始 / 生产中 / 已完成 / 待发布 / 已排产 / 已暂停 |
| `ProcessStatus` | 待开始 / 进行中 / 已完成 / 外协 |
| `QualityStatus` | 待质检 / 质检中 / 已通过 / 未通过 |
| `ShipmentStatus` | 待发货 / 已发货 / 已收货 |
| `FinishedGoodsStatus` | 在库 / 已出库 |
| `InventoryStatus` | 在库 / 已出库 |
| `PriorityLevel` | 高 / 中 / 低 |

并提供 `STATUS_MAPPING / PRIORITY_MAPPING / PRIORITY_VALUE_MAPPING / UNITS / TEMPLATE_TYPES / MODULES / COLOR_TAGS / MEASUREMENT_UNITS / PRODUCTION_PROCESSES`。

### 12.3 业务配置（[core/_config_domain.py](file:///d:/yuan/不锈钢网带跟单3.0/core/_config_domain.py)）

`BusinessConfig` 类集中：

- 9 种材质密度；
- 34 个尺寸参数（PRESET_DIM_PARAMS）；
- 13 种产品类型；
- 17 个工序；
- 表面处理选项；
- 库存预警阈值 `STOCK_WARNING_THRESHOLD`；
- 质检类型与项目分类。

---

## 13. 数据模型与状态机

### 13.1 订单 9 状态流转

```
PENDING → CONFIRMED → PENDING_PUBLISH → PUBLISHED → SCHEDULED
   ↓
CANCELLED ←──────────────────────────────────┘
   ↓
PRODUCTION → QC → PENDING_SHIP → SHIPPED → FINISHED
```

> 见 [services/order_service.py:48-59](file:///d:/yuan/不锈钢网带跟单3.0/services/order_service.py#L48-L59) `STATUS_FLOW`。

### 13.2 数据包状态机（容器中心 v5）

```
PENDING → DISTRIBUTED → ACKNOWLEDGED → COMPLETED
   ↓           ↓             ↓
CANCELLED   EXPIRED       EXPIRED
```

### 13.3 关键表（来自 `_database_legacy.py`）

| 表 | 用途 |
|----|------|
| `orders` | 订单主表（含 `extra_params` JSON 扩展字段） |
| `order_logs` | 订单操作流水 |
| `production_orders` | 生产工单 |
| `process_records` | 工序记录 |
| `process_sub_steps` | 工序子步骤（手机报工回写） |
| `process_calc_rules` | 工序计算规则（白名单公式） |
| `quality_records` | 质检记录 |
| `quality_rules` | 质检规则 |
| `material_rules` / `material_rules_templates` | 备料规则 |
| `product_types` / `product_flow_map` | 产品类型 + 工艺路径 |
| `operators` / `operator_logs` | 操作员 |
| `operation_logs` | 全局操作日志 |
| `inventory` | 库存 |
| `bom` | 物料清单 |
| `data_packages` | 容器中心数据包 |
| `audit_logs` | 审计日志 |
| `alerts` | 预警 |
| `shipments` | 发货 |
| `units` | 单位字典 |
| `schedule_queue` | 排产队列（持久化） |
| `wechat_callback_log` | 企微回调日志（幂等） |
| `window_config` | 窗口尺寸（持久化） |

---

## 14. 事件总线与发布订阅

### 14.1 事件类型（[core/events.py](file:///d:/yuan/不锈钢网带跟单3.0/core/events.py)）

```python
ORDER_CREATED         = 'order:created'
ORDER_UPDATED         = 'order:updated'
ORDER_STATUS_CHANGED  = 'order:status_changed'
ORDER_CONFIRMED       = 'order:confirmed'
ORDER_SHIPPED         = 'order:shipped'
ORDER_DELETED         = 'order:deleted'

PROCESS_CREATED       = 'process:created'
PROCESS_STARTED       = 'process:started'
PROCESS_REPORTED      = 'process:reported'
PROCESS_COMPLETED     = 'process:completed'
PROCESS_STATUS_CHANGED= 'process:status_changed'

PRODUCTION_CONFIRMED  = 'production:confirmed'
PRODUCTION_UPDATED    = 'production:updated'
PRODUCTION_CANCELLED  = 'production:cancelled'

MATERIAL_PREPARED     = 'material:prepared'
MATERIAL_SELECTED     = 'material:selected'
MATERIAL_PUBLISHED    = 'material:published'
MATERIAL_LOW_STOCK    = 'material:low_stock'

QC_PASSED             = 'qc:passed'
QC_REJECTED           = 'qc:rejected'
QC_REQUESTED          = 'qc:requested'

INVENTORY_LOW         = 'inventory:low'
INVENTORY_ALERT       = 'inventory:alert'
INVENTORY_UPDATED     = 'inventory:updated'

TASK_PUBLISHED        = 'task:published'
TASK_ASSIGNED         = 'task:assigned'
TASK_COMPLETED        = 'task:completed'
TASK_TIMEOUT          = 'task:timeout'

SYSTEM_READY          = 'system:ready'
SYSTEM_ERROR          = 'system:error'
SYNC_COMPLETED        = 'sync:completed'
```

### 14.2 使用模式

```python
from core.event_bus import EventBus
from core.events import EventType

# 订阅
def on_order_published(event, data):
    print(f"订单 {data['order_no']} 已发布")
EventBus.subscribe(EventType.ORDER_PUBLISHED, on_order_published)

# 发布
EventBus.publish(EventType.ORDER_PUBLISHED, {'order_no': 'D20260609-001'})

# 取消订阅
EventBus.unsubscribe(EventType.ORDER_PUBLISHED, on_order_published)
```

### 14.3 跨进程扩展

- `core/redis_event_bus.py::RedisEventBus`：基于 Redis Pub/Sub；
- `core/event_bus_factory.py`：`create_event_bus()` 按环境选择本地 / Redis；
- 微服务集群中通过 `mobile_api_ai/sync/event_bus.py` + `bridge/sync_client.py` 实现服务间同步。

---

## 15. 关键类与函数索引

### 15.1 核心框架（[core/](file:///d:/yuan/不锈钢网带跟单3.0/core/)）

| 名称 | 类型 | 位置 | 作用 |
|------|------|------|------|
| `DatabaseConfig` | class | `core/_config_infra.py:58` | 数据库配置读取 |
| `ConnectionPool` | class | `core/db.py:61` | MySQL 连接池（单例） |
| `PooledConnection` | class | `core/db.py:143` | 池化连接上下文 |
| `DB` | class | `core/db.py:168` | 数据库门面（`get_connection` 等） |
| `EventBus` | class | `core/event_bus.py:14` | 事件总线（单例） |
| `Events` | class | `core/event_bus.py:104` | 事件名常量（**旧名，新代码请用 `EventType`**） |
| `EventType` | class | `core/events.py:18` | 事件名常量（新） |
| `EventData` | class | `core/events.py:123` | 事件数据封装 |
| `RedisEventBus` | class | `core/redis_event_bus.py:16` | Redis 事件总线 |
| `EventStore` | class | `core/event_store.py:26` | 事件持久化 |
| `BusinessException` | class | `core/exceptions.py:9` | 业务异常基类 |
| `ErrorCode / ErrorDomain / ErrorSeverity` | enum | `core/error_codes.py` | 错误码体系 |
| `LogManager / StructuredLogger` | class | `core/logger.py` | 日志 |
| `MetricsCollector` | class | `core/metrics.py:7` | 指标 |
| `FeatureFlags` | class | `core/feature_flags.py:5` | 特性开关 |
| `RuleEngine` | class | `core/rule_engine.py:9` | 规则引擎 |
| `CircuitBreaker` | class | `core/circuit_breaker.py:8` | 熔断器 |
| `SagaOrchestrator / SagaStep` | class | `core/saga.py:13/19` | Saga 事务 |
| `initialize_app()` | fn | `core/app.py:40` | 应用启动初始化 |
| `create_secure_flask_app()` | fn | `core/app.py:109` | 构造安全 Flask |
| `init_cors(app, ...)` | fn | `core/cors_config.py` | CORS 注入 |

### 15.2 DAO（[models/](file:///d:/yuan/不锈钢网带跟单3.0/models/)）

> 全部采用**静态方法**风格；下表仅列类名（`create/update/get/list/delete` 通用方法均存在，部分 DAO 暴露业务专用方法）。

| 类 | 文件 | 关键方法 |
|----|------|----------|
| `BaseDAO` | `models/base_dao.py:24` | CRUD 基类 |
| `OrderDAO` | `models/order.py:32` | `create/update/get/list/update_status` |
| `OrderLogDAO` | `models/order_log.py:11` | 订单日志 |
| `ProcessDAO` | `models/process.py:10` | 工序 CRUD + 推进 |
| `ProcessCalcRuleDAO` | `models/process_calc_rule.py:14` | 公式规则 |
| `ProductionDAO` | `models/production.py:13` | 生产工单 |
| `ProductionStatsDAO` | `models/production_stats.py:11` | 统计 |
| `QualityDAO` | `models/quality.py:11` | 质检记录 |
| `QualityRuleDAO` | `models/quality_rule.py:16` | 质检规则 |
| `ShipmentDAO` | `models/shipment.py:11` | 发货 |
| `InventoryDAO` | `models/inventory.py:10` | `stock_in/stock_out/transfer` |
| `MaterialRulesDAO` | `models/material_rules.py` | 备料规则 |
| `MaterialRulesTemplateDAO` | `models/material_rules_template.py` | 模板 |
| `ProductTypeDAO` | `models/product_type.py:9` | 产品类型 |
| `ProductFlowMapDAO` | `models/product_flow_map.py:4` | 工艺路径 |
| `OperatorDAO / OperatorLogDAO` | `models/operator.py:11/255` | 操作员 |
| `OperationLogDAO` | `models/operation_log.py:12` | 操作日志 |
| `AlertDAO` | `models/alert.py:9` | 预警 |
| `BOMDAO` | `models/bom.py:9` | BOM |
| `UnitDAO` | `models/unit.py` | 单位 |
| `PhotoStorage` | `models/photo_storage.py` | 照片 |
| `generate_order_no()` | `models/database/utils_db.py` | 订单号生成 |
| `generate_shipment_no()` | 同上 | 发货单号生成 |
| `log_status_change()` | 同上 | 状态变更日志 |
| `init_db()` / `ensure_*_indexes` | `models/database/_database_legacy.py` | 建表 + 索引 |

### 15.3 服务（[services/](file:///d:/yuan/不锈钢网带跟单3.0/services/)）

| 类 | 文件 | 职责 |
|----|------|------|
| `BaseService` | `services/base_service.py:18` | 单例 + 委托基类 |
| `OrderService` | `services/order_service.py:28` | 9 状态机 + 业务编排 |
| `ProcessService` | `services/process_service.py:20` | 工序推进 |
| `ScheduleDispatchService` | `services/schedule_dispatch_service.py:33` | 排产队列 + 容器中心投递 |
| `WeChatReportService` | `services/wechat_report_service.py:29` | 微信报工幂等回写 |
| `AuditService` | `services/audit_service.py:15` | 审计 |
| `InventorySync` / `InventoryNotifier` | `services/inventory_sync.py` / `services/inventory_notifier.py` | 库存同步/通知 |

### 15.4 桌面端 View / Dialog（[desktop/views/](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/)）

| 名称 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `MainWindow` | class | `desktop/views/main_window.py:23` | 主窗口 |
| `OrderListView` | class | `desktop/views/orders/list_view.py:23` | 订单列表 |
| `NewOrderDialog` | class | `desktop/views/orders/new_order_dialog.py:35` | 新订单对话框 |
| `OrderQueryView` | class | `desktop/views/order_query_view.py:48` | 订单查询 |
| `ProductionView` | class | `desktop/views/production_view.py:21` | 生产排单 |
| `ProcessView` | class | `desktop/views/process_view.py:37` | 工序追踪 |
| `ProcessCalcRuleView` | class | `desktop/views/process_calc_rule_view.py:21` | 工序计算规则 |
| `QualityView` | class | `desktop/views/quality_view.py:26` | 质检 |
| `QualityRuleView` | class | `desktop/views/quality_rule_view.py:88` | 质检规则 |
| `ShipmentView` | class | `desktop/views/shipment_view.py:26` | 发货 |
| `MaterialPrepView` | class | `desktop/views/material_prep_view.py:31` | 备料 |
| `MaterialRulesView` | class | `desktop/views/material_rules_view.py:85` | 备料规则 |
| `FinishedProductStatsView` | class | `desktop/views/finished_product_stats_view.py:19` | 成品统计 |
| `KanbanView` | class | `desktop/views/kanban_view.py:14` | 看板 |
| `DashboardView` | class | `desktop/views/dashboard_view.py:11` | 仪表板 |
| `AlertView` | class | `desktop/views/alert_view.py:22` | 预警 |
| `BOMView` | class | `desktop/views/bom_view.py:13` | BOM |
| `ExcelView` | class | `desktop/views/excel_view.py:13` | 导入导出 |
| `LogView` | class | `desktop/views/log_view.py:19` | 日志 |
| `OperatorManagerView` | class | `desktop/views/operator_view.py:22` | 操作员管理 |
| `LoginDialog` | class | `desktop/views/operator_view.py:458` | 登录 |
| `LogViewer` | class | `desktop/views/operator_view.py:404` | 日志查看 |
| `ErrorLookupView` | class | `desktop/views/error_lookup_view.py:11` | 错误码查询 |
| `DatabaseSettingsWindow` | class | `desktop/views/db_settings_window.py:13` | 数据库设置 |
| `BaseDialog` | class | `desktop/views/dialogs/base.py:755` | 对话框基类 |
| `popup_form()` | fn | `desktop/views/dialogs/base.py:328` | 简单表单工厂 |
| `alert() / confirm()` | fn | 同上 16/43 | 提示/确认 |
| `QualityTaskCompileDialog` | class | `desktop/views/dialogs/quality_dialogs.py:17` | 质检任务汇总 |
| `QualityRecordFormDialog` | class | 同上 :319 | 质检记录表单 |
| `QualityRuleDialog` | class | `desktop/views/rule_dialogs.py:87` | 质检规则对话框 |
| `MaterialRuleDialog` | class | `desktop/views/rule_dialogs.py:506` | 备料规则对话框 |
| `FlowTypeConfigDialog` | class | `desktop/views/rule_dialogs.py:1356` | 工艺路径配置 |
| `BasePresenter` | class | `desktop/presenters/base_presenter.py` | 通用中介 |
| `NewOrderPresenter` | class | `desktop/presenters/new_order_presenter.py` | 新订单中介 |
| `ProcessPresenter` | class | `desktop/presenters/process_presenter.py` | 工序中介 |

### 15.5 微服务（[mobile_api_ai/](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/)）

| 名称 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `create_app()` | fn | `mobile_api_ai/app.py:46` | Flask 应用工厂 |
| `dispatch_center_bp` | bp | `mobile_api_ai/dispatch_center/__init__.py` | 调度中心蓝图 |
| `DispatchContext / DispatchDataCache` | class | `dispatch_center/_core.py:213/571` | 调度上下文 + 缓存 |
| `DispatchStatus / AlertLevel` | enum | `dispatch_center/_core.py:553/563` | 状态/告警级别 |
| `ContainerCenter` | class | `mobile_api_ai/container_center_v5.py` | 容器中心主类 |
| `DataPackage / DataType / DataStatus` | class/enum | 同上 | 数据包模型 |
| `create_container_api_bp()` | fn | `container_center/api/__init__.py:11` | 容器中心蓝图工厂 |
| `DocumentStore / IndexStore / ConfigStore / AlertStore` | class | `container_center/storage/` | 存储实现 |
| `AlertEngine` | class | `container_center/services/alert_engine.py` | 告警引擎 |
| `ContainerCenterClient` | class | `container_center/client/container_client.py` | Python 客户端 |
| `create_storage() / BaseStorage / StorageType` | class | `mobile_api_ai/storage_layer.py` | 存储抽象 |
| `mysql_storage.py::MySQLStorage` | class | `mobile_api_ai/storage/mysql_storage.py` | MySQL 实现 |
| `auth.bp / scan.bp / process.bp / quality.bp / message.bp / approval.bp / health.bp` | bp | `mobile_api_ai/api/*` | 移动 API 蓝图 |
| `legacy_routes.bp` | bp | `mobile_api_ai/api/legacy_routes.py` | 兼容路由 |
| `app_bot / group_bot / message_hub` | class | `mobile_api_ai/bots/*` | 机器人 |
| `BaseCommand + 7 个指令类` | class | `mobile_api_ai/commands/*` | 企微指令 |
| `wechat_notifier / desktop_callback` | module | `mobile_api_ai/integration/*` | 集成层 |
| `bridge/sync_client` | module | `mobile_api_ai/bridge/sync_client.py` | HTTP 同步 |

---

## 16. 依赖关系

### 16.1 第三方依赖（[requirements.txt](file:///d:/yuan/不锈钢网带跟单3.0/requirements.txt)）

| 分类 | 库 | 版本区间 | 用途 |
|------|----|----------|------|
| Web 框架 | `flask` | 3.1.x | 微服务 Web 框架 |
| | `flask-cors` | 6.0.x | CORS 支持 |
| | `flask-limiter` | 4.1.x | API 限流 |
| | `werkzeug` | 3.1.x | WSGI 工具集 |
| | `limits` | 5.8.x | 限流后端 |
| 认证加密 | `PyJWT` | 2.13.x | JWT 令牌 |
| | `cryptography` | 48.x | 加密原语 |
| 数据库 | `pymysql` | 1.2.x | MySQL 驱动（**唯一**） |
| HTTP | `requests` | 2.34.x | 同步 HTTP |
| 配置 | `python-dotenv` | 1.2.x | .env 加载 |
| 图像 | `Pillow` | 12.2.x | 扫码/人脸图像 |
| 调度 | `APScheduler` | 3.11.x | 定时任务 |
| 日期 | `python-dateutil` | 2.9.x | 日期工具 |
| 类型 | `typing-extensions` | 4.12.x | 类型扩展 |
| 缓存 | `redis` | 5.0.x | Redis 客户端 |
| 测试 | `pytest` / `pytest-cov` / `pytest-mock` | 9.0 / 7.1 / 3.14 | 测试与覆盖率 |
| | `coverage` | 7.6.x | 覆盖率引擎 |
| 开发工具 | `flake8` / `black` / `isort` / `bandit` | 7.1 / 24.8 / 5.13 / 1.8 | 静态检查与格式化 |

> **国内镜像**安装时建议使用 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`。

### 16.2 项目内部模块依赖图

```
                   ┌──────────────┐
                   │   main.py    │  (桌面端)
                   └──────┬───────┘
                          ▼
   ┌────────────────────────────────────────────────┐
   │  core/  ──────────────────────────────────────►│
   │   ├ config / db / event_bus / exceptions        │
   │   ├ error_handler / logger / metrics           │
   │   └ app.py (initialize_app)                    │
   └──────┬──────────────────────────┬──────────────┘
          │                          │
          ▼                          ▼
   ┌─────────────┐            ┌──────────────┐
   │  models/    │            │  services/   │
   │  (DAO)      │◀───────────│  (业务编排)  │
   └──────┬──────┘            └──────┬───────┘
          │                          │
          ▼                          ▼
   ┌──────────────────────────────────────────┐
   │             core.db (MySQL 池)            │
   └──────────────────────────────────────────┘
          ▲                          ▲
          │                          │
   ┌──────┴──────────────────────────┴──────┐
   │              desktop/  (Tkinter)        │
   │   views ← presenters ← services         │
   └─────────────────────────────────────────┘
          ▲
          │ HTTP / 配置共享
          │
   ┌──────┴──────────────────────────────────┐
   │            mobile_api_ai/                │
   │   app.py ← api/* ← dispatch_center      │
   │             ← container_center_v5       │
   │             ← inventory_web              │
   │             ← integration/wechat         │
   └─────────────────────────────────────────┘
```

### 16.3 关键依赖边界

- **`core/` 不允许依赖 `models/` `services/` `desktop/` `mobile_api_ai/`**（单向）。
- **`models/` 只能依赖 `core/` `utils/`**。
- **`services/` 依赖 `models/` `core/` `utils/`**。
- **`desktop/` 依赖 `services/` `models/` `core/` `utils/`**。
- **`mobile_api_ai/` 共享 `core/` `models/`**（通过 `sys.path` 注入根目录）。

---

## 17. 测试体系

### 17.1 桌面端测试 `tests/`

`pyproject.toml` 中 pytest 配置：

- 测试目录：`tests/`（排除 `e2e/` 和 `integration/`）；
- 覆盖率目标：`core/ models/ services/ utils/`，**门禁 `--cov-fail-under=48`**；
- 排除 `tests/` `scripts/` `views/` `build/` `dist/` `temp_*/` `_backup/` `visualization_app/` `mobile_api_ai/`；
- 输出 `term-missing / html:coverage_html / xml:coverage.xml`。

```
tests/
├── conftest.py
├── unit/
│   ├── core/        (event_bus / config / db / saga / circuit_breaker / process_code …)
│   ├── models/      (各 DAO + base_dao + bulk_models + push_40/45 …)
│   ├── services/    (order_service / process_service / audit / wechat_report / schedule_dispatch …)
│   └── utils/       (helpers / log / cache / pagination / validators / window_manager …)
├── integration/     (test_schedule_publish / test_template_api)
├── modular/         (auto_publish / container_listener / publish_mode_manager …)
├── e2e/             (test_flows)
└── test_auto_advance / test_re002 / test_step_status_unify / test_v354_*
```

### 17.2 微服务测试 `mobile_api_ai/tests/`

```
mobile_api_ai/tests/
├── conftest.py
├── unit/                 (test_storage / test_session / test_dao / test_dispatcher …)
├── integration/          (test_api_core / test_api_aux / test_sync_bridge_routing …)
├── fixtures/             (mock_api_data / mock_storage_data / test_body.json …)
└── run_all_tests.py
```

覆盖范围：DAO 单元、API 集成、并发、回归、Mock 验证、Swagger、限流、统计引擎、成本模块等。

### 17.3 常用测试命令

```bash
# 桌面端全部测试 + 覆盖率
pytest

# 仅核心
pytest tests/unit/core

# 仅某个 DAO
pytest tests/unit/models/test_order.py

# 详细输出 + 覆盖率报告
pytest --cov=core --cov=models --cov=services --cov=utils --cov-report=term-missing

# 微服务全部
cd mobile_api_ai && python -m pytest tests/

# 集成
cd mobile_api_ai && python -m pytest tests/integration/

# Mock DB 验证
cd mobile_api_ai && python scripts/tmp_verify_mock_db.py
```

### 17.4 静态检查与格式化

```bash
# 语法检查
flake8 .

# 格式化（自动）
black . --line-length 100

# import 排序
isort . --profile black --line-length 100

# 安全扫描
bandit -r .
```

---

## 18. 部署与运行方式

### 18.1 开发环境搭建

```bash
# 1. 克隆/进入项目根
cd "d:\yuan\不锈钢网带跟单3.0"

# 2. 创建虚拟环境（建议 Python 3.11）
python -m venv venv
.\venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 准备 .env
copy .env.example .env
# 编辑 .env，填入 DB_HOST / DB_USER / DB_PASSWORD / JWT_SECRET_KEY

# 5. 初始化数据库
python -c "from models.database import init_db, ensure_unique_indexes, ensure_performance_indexes; \
           init_db(); ensure_unique_indexes(); ensure_performance_indexes()"
```

### 18.2 启动桌面端

```bash
# 直接启动
python main.py

# 或使用便捷脚本
启动库存服务器.bat          # v2 兼容（仅供历史部署）
```

启动后默认进入订单管理模块；侧边栏可切换 16 个业务模块。

### 18.3 启动微服务

```bash
# 进入子项目
cd mobile_api_ai

# 启动 Flask 微服务
python app.py
# 或 gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

可选独立服务：

```bash
# 调度中心（独立部署）
python standalone_dispatch_server.py

# 容器中心 API
python container_api_server.py

# 库存 Web
python inventory_api_server.py

# 容器中心 v5（兼容入口）
python container_center_v5.py

# 人脸考勤
python face_server.py

# 一键启动
start_all.bat / start_all.py
```

### 18.4 部署模式

- **单机模式**：桌面端 + 微服务 + MySQL 同机运行（生产环境最常见）；
- **C/S 模式**：服务端 + 多个桌面端客户端（通过内网 MySQL 共享数据）；
- **云端模式**：使用 `wechat_cloud.py` 接收公网企微回调，内部中转到本机（见 `docs/企业微信应用机器人部署指南.md`）。

### 18.5 端口分配

| 服务 | 默认端口 | 入口 |
|------|----------|------|
| 主 Flask 微服务 | 5000 | `mobile_api_ai/app.py` |
| 微信回调服务 | 5003 | `mobile_api_ai/standalone_dispatch_server.py`（整合原 wechat_server.py） |
| 容器中心 API | 5002 | `mobile_api_ai/container_api_server.py` |
| 库存 API | 5010 | `mobile_api_ai/inventory_api_server.py` |
| 调度中心 | 5001 | `mobile_api_ai/standalone_dispatch_server.py` |
| 人脸考勤 | 8000 | `mobile_api_ai/face_server.py` |
| 看板（嵌入） | 动态 | `desktop/views/dashboard/dashboard_server.py` |

> 端口与微服务总线 IP 配置在 `.env` 中的 `FLASK_HOST / FLASK_PORT / CONTAINER_CENTER_URL`。

### 18.6 数据库迁移

```bash
# 执行迁移
python db_upgrades/<version>/upgrade.py
# 或
python mobile_api_ai/migrations/run.py

# 同步企业微信组织结构
python mobile_api_ai/re_sync_enterprise.py
```

### 18.7 桌面端打包（PyInstaller）

```bash
# 项目根目录
build.py
# 产物：dist/不锈钢网带跟单系统.exe
```

打包配置参见 `packaging_template/` 和 `一键打包.bat`。

### 18.8 常见启动错误处理

| 现象 | 原因 | 解决 |
|------|------|------|
| `Access denied for user` | MySQL 密码错误 | 编辑 `.env` 中 `MYSQL_PASSWORD` |
| `Can't connect to MySQL server` | MySQL 未启动/网络不通 | 启动 MySQL / 检查端口 |
| `Unknown database 'steel_belt'` | 数据库未创建 | `CREATE DATABASE steel_belt;` |
| 启动时弹出数据库设置窗 | 配置错误 | 填入正确连接信息 |
| 许可证错误 | 机器指纹不匹配 | 联系销售获取许可证 |

---

## 19. 死代码清理记录（Dead Code Cleanup Log）

> 跟踪归档、删除的死文件，每次清理追加一条记录。**严禁直接删除**长结构代码；归档前需先在调试中确认无生产 import。

### 19.1 2026-06-09 第一轮清理

| 操作 | 文件 | 原路径 → 现路径 | 原因 | 备份/兼容 |
|------|------|----------------|------|-----------|
| 归档 | `models/database/connection_pool.py` | `models/database/connection_pool.py` → `_archive/legacy_db/connection_pool.py` | 生产代码 0 引用；被 `core.db.ConnectionPool` + `core.db.PooledConnection` 完全替代 | 头部加 ARCHIVED 注释；`models/database/__init__.py` 注释同步更新 |
| 删除 | `desktop/views/dialogs.py`（13 行 shim） | 直接删除 | 与同名包 `desktop/views/dialogs/` 重名，**从未被加载**；包结构已完全替代 | 无需备份（实质为空壳） |

**触发的测试变更**：

| 测试文件 | 操作 | 原因 |
|----------|------|------|
| `tests/unit/models/database/test_connection_pool.py` | 顶部加 `pytestmark = pytest.mark.skip(...)` | 文件被导入的对象已不存在 |
| `tests/unit/utils/test_push_50_b3.py::TestDatabaseDetails::test_connection_pool_singleton` | 方法加 `@pytest.mark.skip(...)` | 同上 |
| `mobile_api_ai/tests/unit/test_dao.py::TestDatabaseConnectionPool` 两个用例 | 简化为 `pytest.skip(...)` | 原代码已有 `pytest.skip` 兜底，清理后变为显式 skip |

**审计原则**：
1. 优先 grep 全仓库 `import` / `from` 引用；
2. 生产代码 0 引用 + 测试仅兜底 → 归档或删除；
3. 与同名包/同名类冲突且自身仅 13 行 → 直接删除；
4. 测试标记 skip（不删）保留回归历史。

### 19.2 2026-06-09 第二轮清理（mobile_api_ai 模块名冲突根除）

**问题诊断**：用户最初反馈 11 个 pytest 收集错误，6 个根因是 `mobile_api_ai/` 与项目根的同文件名模块被 pytest import 解析错乱（核心：`mobile_api_ai/constants.py` 遮蔽项目根 `constants.py`，使 `from constants import OrderStatus` 解析到错误文件）。

**全量审计 8 对同文件**（见用户消息"先看看被哪些引用"）：

| # | 文件对 | 桌面引用 | mobile 引用 | 处置 |
|---|--------|----------|-------------|------|
| 1 | `constants.py` | 22 处 | 1 处（仅 `ServiceURLs`） | **Phase 1.1-1.2**：归档 mobile + 拆 ServiceURLs |
| 2 | `server_launcher.py` | .bat 调用 2 处 | 0 | **Phase 1.3**：归档 mobile |
| 3 | `utils/password_hasher.py` | 2 模块生产 | 0（mobile 自带 3 套独立实现） | **Phase 1.4**：归档 mobile |
| 4 | `utils/op_logger.py` | 13 模块生产 | 0 | **Phase 1.5**：归档 mobile |
| 5 | `utils/auto_schema.py` | 2 模块生产 | 1 模块生产 | **Phase 2.1**：mobile shim re-export |
| 6 | `utils/__init__.py` | 5 validator | 3 http_client | **Phase 2.2**：mobile shim 合并 re-export |
| 7 | `services/__init__.py` | 3 服务 | 6 服务 | **Phase 2.3**：mobile shim 合并 re-export |
| 8 | `tests/conftest.py` | 5 fixture | 3 fixture | **保持双 conftest**（pytest 强制文件名） |

**Phase 1：归档 4 个 mobile_api_ai 死代码文件**

```
_archive/legacy_mobile_api/
├── constants.py              (118 行，含 ARCHIVED 头部)
├── server_launcher.py        (195 行，含 ARCHIVED 头部)
└── utils/
    ├── password_hasher.py    (40 行，含 ARCHIVED 头部)
    └── op_logger.py          (77 行，含 ARCHIVED 头部)
```

**ServiceURLs 唯一活引用迁移**：
- 新建 `mobile_api_ai/_service_urls.py`（含 7 个服务 URL 常量 + `os.getenv` 兜底）
- `mobile_api_ai/confirm_schedule.py:11` 改为 `from ._service_urls import ServiceURLs`

**Phase 2：Re-export shim 改造 3 个两侧都活文件**

3 个 shim 文件均加防御性 sys.path 注入（确保项目根在 sys.path[0]），通过 `mobile_api_ai/pyproject.toml:31` 的 `pythonpath=[".."]` 默认解析到项目根版本：

| Shim 文件 | 防御机制 | re-export 内容 |
|-----------|----------|----------------|
| `mobile_api_ai/utils/auto_schema.py` | 移除 mobile_api_ai 路径后注入项目根 | `auto_ensure_schema, SafeCursor, clear_schema_cache` |
| `mobile_api_ai/utils/__init__.py` | 同上 | 5 个 validator + 3 个 http_client（合并） |
| `mobile_api_ai/services/__init__.py` | 同上 | 3 个桌面服务 + 6 个 mobile 服务（合并） |

**触发的测试变更**：

| 测试文件 | 操作 | 原因 |
|----------|------|------|
| `mobile_api_ai/tests/unit/test_auto_schema.py::TestAutoSchema::test_empty_data` | 顶部加 `pytest.skip(...)` | 行为差异：旧 mobile 版对空数据 `logger.warning`，桌面版**静默 return**（更合理） |
| 同上 `test_sqlite_connection` | 同上 | 行为差异：旧 mobile 版模块顶层 `import sqlite3`，桌面版**未在顶层 import**（更解耦） |

**验证结果（vs 第一轮清理前）**：

| 指标 | 第一轮清理后 | 本轮清理后 | 变化 |
|------|------------|-----------|------|
| 桌面根 `pytest tests/ --collect-only` 错误数 | 11 | **5** | **-6 ✅** |
| 桌面根可收集测试数 | 2427 | **2558** | **+131 ✅** |
| `test_auto_schema.py` | （未测） | 49 passed / 2 skipped | ✅ |
| `test_http_client.py` | （未测） | requests 缺失（预存） | 待补依赖 |

**消除的 6 个错误**（全部因为 `mobile_api_ai/constants.py` 遮蔽根 `constants.py`）：

- `tests/unit/models/test_operator.py`
- `tests/unit/models/test_operator_depth.py`
- `tests/unit/models/test_photo_storage.py`
- `tests/unit/models/test_process_depth.py`
- `tests/unit/models/test_product_flow_map.py`
- `tests/unit/utils/test_dao_patches.py`

**剩余 5 个错误**（与本次改动无关，**预存依赖问题**）：

- `test_utils_db.py` / `test_schedule_dispatch_service.py` / `test_wechat_report_service.py`（缺 requests / MySQL 实时连接）
- `test_excel_utils.py` / `test_excel_utils_gaps.py`（缺 openpyxl）

---

## 20. 附录：脚本与辅助工具

### 20.1 项目根 `scripts/`

| 脚本 | 用途 |
|------|------|
| `scripts/check_all_orders.py` | 全量订单巡检 |
| `scripts/check_all_prod_status.py` | 生产状态巡检 |
| `scripts/check_all_rules.py` | 规则一致性检查 |
| `scripts/check_data.py` / `check_db_formula.py` / `check_formula.py` | 数据/公式检查 |
| `scripts/check_quality_rules.py` | 质检规则检查 |
| `scripts/diagnose_inventory.py` | 库存问题诊断 |
| `scripts/init_wechat_tables.py` | 企微表初始化 |
| `scripts/migrate_events_init.py` | 事件总线初始化迁移 |
| `scripts/order_archive_manager.py` / `unarchive_order.py` | 订单归档/恢复 |
| `scripts/save_all_rules.py` / `sync_orders.py` / `sync_process_rules.py` | 数据同步 |
| `scripts/qc999_db_migrate.py` | 质检 DB 迁移 |
| `scripts/generate_secrets.py` | 生成密钥 |
| `scripts/test_order_functions.py` / `test_wechat_callback.py` | 单元/集成测试 |

### 20.2 `scripts/tools/`

DB 索引修复、健康检查、SQLite/MySQL 诊断、构建验证等工具集。

### 20.3 `scripts/archive/`

历史构建脚本（PyInstaller 各版本）、MySQL 配置向导、旧版 GUI 启动器等；保留作为历史参考。

### 20.4 微服务脚本 `mobile_api_ai/scripts/`

- `check_*.py`：各种 DB/表/字段诊断；
- `diag_*.py`：问题诊断；
- `download_*.py`：模型下载（face/buffalo_l）；
- `cloud/*.py`：云端流程（备份、广播、监控、demo）；
- `deploy/cloud_deploy.sh`：云端部署脚本；
- `preflight_check.py`：启动前自检。

### 20.5 常用根级脚本

- `npx repomix` — 仓库打包分析（本次 Wiki 即基于其产物撰写）；
- `build.py` — 桌面端 PyInstaller 打包；
- `process_code_*.py` — 工序代码最严审计工具；
- `_audit_*.py` — 各种审计脚本；
- `coverage.json` / `coverage_analysis.xml` — 覆盖率报告。

### 20.6 关键规范文件

- `.trae/rules/对话框使用规范.md` — 对话框三层创建方式；
- `.flake8` / `pyproject.toml` — 风格与覆盖率门禁；
- `CODING_STANDARDS.md` — 编码规范（项目内）；
- `TECH_DEBT.md` — 技术债清单；
- `CHANGELOG.md` — 变更日志；
- `ORDER_NO_DECLARATION.py` — 订单号生成规范。

---

## 附录 A：仓库代码度量（Repomix）

| 指标 | 数值 |
|------|------|
| 核心源文件数 | 247 |
| 总 Token 数 | 559,403 |
| 总字符数 | 2,301,813 |
| Top 1 文件 | `mobile_api_ai/dispatch_center/_core.py`（65,134 tokens / 11.6%） |
| Top 2 文件 | `mobile_api_ai/app.py`（25,114 tokens / 4.5%） |
| Top 3 文件 | `models/database/_database_legacy.py,cover`（16,628 tokens / 3%） |
| Top 4 文件 | `core/error_codes.py,cover`（14,023 tokens / 2.5%） |
| Top 5 文件 | `models/database/_database_legacy.py`（13,919 tokens / 2.5%） |

> 报告路径：`D:\tmp\yuan_codewiki.xml`

---

## 附录 B：关键设计模式

| 模式 | 体现位置 |
|------|----------|
| **单例模式** | `EventBus` `ConnectionPool` `BaseService` `OrderService` |
| **静态工厂/委托** | 所有 DAO 静态方法 + `BaseService` 委托 |
| **发布订阅** | `EventBus`（`EventType` 27 种） |
| **模板方法** | `BaseDialog._build_ui/_validate/_on_confirm` |
| **外观 (Facade)** | `core/config.py`（聚合 4 个子模块） |
| **状态机** | `OrderService.STATUS_FLOW` 9 状态 + `DataStatus` 6 状态 |
| **策略模式** | `EventBus` 本地 vs Redis（`event_bus_factory`） |
| **熔断器** | `CircuitBreaker`（核心层） |
| **Saga** | `SagaOrchestrator` 分布式事务 |
| **插件注册** | `plugins/` 通过 `PluginRegistry` 加载 |
| **MVVM** | 桌面端 `View ↔ Presenter ↔ Service` |
| **抽象存储** | `BaseStorage` + `MySQLStorage` |
| **指数退避** | 微服务 `mobile_api_ai/api/decorators.py` |

---

## 附录 C：常见扩展点

| 场景 | 扩展点 | 操作 |
|------|--------|------|
| 新增业务实体 | `models/<entity>.py` + 在 `_database_legacy.py` 添加建表 DDL | 创建新 DAO，继承 `BaseDAO` 风格 |
| 新增状态事件 | `core/events.py::EventType` | 添加类常量 + 在订阅方 `subscribe` |
| 新增桌面端模块 | `desktop/views/<module>_view.py` + `main_window.show_module` 注册 | 复用 `AutoRefreshMixin` |
| 新增对话框 | `desktop/views/dialogs/<x>_dialogs.py` | 优先 `popup_form`，复杂场景继承 `BaseDialog` |
| 新增业务服务 | `services/<x>_service.py` | 继承 `BaseService` |
| 新增微服务蓝图 | `mobile_api_ai/api/<x>.py` 定义 `bp`，在 `app.py` 注册 | 使用 `limiter` 装饰器 |
| 新增企微指令 | `mobile_api_ai/commands/<x>_cmd.py` 继承 `BaseCommand`，在 `manager.py` 注册 | 命令类格式：`<keyword> <args>` |
| 新增材质 | `plugins/materials/<x>.py` + 在 `__init__.py` 注册 | 提供 `material_type/density/specs` |
| 新增配置项 | `core/_config_*.py` + 在 `config.py` re-export | 避免硬编码 |
| 新增错误码 | `core/error_codes.py` | 添加 `ErrorCode` 常量 + 中文说明 |

---

## 附录 D：故障排查与运维

| 故障 | 排查方向 |
|------|----------|
| 桌面端启动卡死 | 检查 `core/db.py` 连接池是否耗尽；查看 `app.log` |
| 报工后桌面端未更新 | 检查 `sync_bridge` 是否可达；查看 `wechat_callback_log` |
| 排产队列堆积 | 检查 `schedule_queue` 表；`ScheduleDispatchService.start_queue_recovery` 状态 |
| 容器中心无响应 | 端口 5002 是否开放；`ContainerCenter.storage` 初始化日志 |
| 调度中心 500 | 检查 `dispatch_center/_core.py` 的 `_handle_unhandled` 日志 |
| 库存不准 | 触发 `inventory_sync` 全量对账；`scripts/diagnose_inventory.py` |
| 许可证失效 | 重新执行 `security/license_tool.py` 激活 |

---

## 附录 E：术语表

| 术语 | 含义 |
|------|------|
| **MES** | Manufacturing Execution System，制造执行系统 |
| **DAO** | Data Access Object，数据访问对象 |
| **DTO** | Data Transfer Object |
| **JWT** | JSON Web Token，移动端身份令牌 |
| **Saga** | 长事务编排模式 |
| **CB** | Circuit Breaker，熔断器 |
| **DM** | Deployment Manager，部署管理 |
| **QM** | Queue Manager，队列管理 |
| **HC** | Health Checker，健康检查 |
| **AL** | Audit Logger，审计日志 |
| **BM** | Backup Manager，备份管理 |
| **CS** | Configuration Store，配置存储 |
| **企微** | 企业微信 |
| **数据中转** | Container Center 提供工单/报工等数据的转发与持久化 |
| **容器池** | 任务缓冲池，DispatchDataCache 的实现细节 |
| **排产队列** | `schedule_queue` 表 + `ScheduleDispatchService` 内存队列 |
| **外协** | Outsource，工序可派发给外部供应商 |
| **板带/钢带** | 不锈钢网带产品 |
| **白名单公式** | `core/rule_engine.py` 支持的安全公式语法（避免 `eval` 风险） |

---

> **维护说明**：本 Wiki 由 Repomix + 阅读源码自动生成。重大架构变更后请同步刷新：
> 1. 运行 `npx repomix@latest --include "core/**,models/**,services/**,utils/**,desktop/**,mobile_api_ai/api/**,mobile_api_ai/app.py" --output /tmp/yuan_codewiki.xml`
> 2. 阅读新增关键类并补充到对应章节
> 3. 更新本文件"附录 A"中的度量数据
