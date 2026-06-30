# 不锈钢网带跟单系统 v3.0 — Code Wiki

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 整体架构](#2-整体架构)
- [3. 目录结构与模块职责](#3-目录结构与模块职责)
- [4. 启动流程与入口点](#4-启动流程与入口点)
- [5. 核心层 (core)](#5-核心层-core)
- [6. 配置系统 (config)](#6-配置系统-config)
- [7. 数据库层 (models)](#7-数据库层-models)
- [8. 业务服务层 (services)](#8-业务服务层-services)
- [9. 桌面UI层 (desktop)](#9-桌面ui层-desktop)
- [10. 安全模块 (security)](#10-安全模块-security)
- [11. 工具模块 (utils)](#11-工具模块-utils)
- [12. 公式计算原则](#12-公式计算原则)
- [13. 数据流与事件系统](#13-数据流与事件系统)
- [14. 依赖关系梳理](#14-依赖关系梳理)
- [15. 运行方式与环境要求](#15-运行方式与环境要求)
- [16. 关键类/函数索引](#16-关键类函数索引)

---

## 1. 项目概述

**不锈钢网带跟单系统 v3.0** 是一套面向不锈钢网带制造企业的生产跟单桌面客户端，基于 **PyQt5** 构建 GUI，通过 **MySQL** 数据库实现数据持久化。系统覆盖从 **订单录入 → 生产排产 → 工序报工 → 质量检验 → 成品入库 → 发货出库** 的全链路管理。

| 属性 | 值 |
|------|-----|
| 项目路径 | `d:\yuan\不锈钢网带跟单3.0\` |
| 技术栈 | Python 3.x, PyQt5, MySQL, PyInstaller(打包) |
| 架构模式 | MVP(Passive View) + Service Layer + DAO |
| 通信机制 | EventBus (进程内事件驱动) + 全局回调链 |
| 打包工具 | PyInstaller (通过 .spec 配置) |
| 当前版本 | 3.3.x (见 version.py) |

### 业务范围总览

```
订单管理 → 生产排产 → BOM配置 → 生产报工 → 质量检验 → 成品入库 → 库存管理 → 发货管理
   │           │           │           │           │           │           │          │
   └─── 查看   │           │           │           │           │           │          │
       编辑    │           │           │           │           │           │          │
       审核    │           │           │           │           │           │          │
       删除    │           │           │           │           │           │          │
               │           │           │           │           │           │          │
               ├── 排产定制 ──┤           │           │           │           │          │
               │  排产确认    │           │           │           │           │          │
               │            │           │           │           │           │          │
               │            ├── 原材料    │           │           │           │          │
               │            │  构成配置   │           │           │           │          │
               │            │            │           │           │           │          │
               │            │            ├── 工序报工 ──┤           │           │          │
               │            │            │  报工记录    │           │           │          │
               │            │            │  报工汇总    │           │           │          │
               │            │            │             ├── 质检录入 ──┤           │          │
               │            │            │             │  合格/不合格  │           │          │
               │            │            │             │              ├── 入库 ────┤          │
               │            │            │             │              │             │          │
               │            │            │             │              │             ├── 发货 ──┤
               │            │            │             │              │             │ 发货单    │
               │            │            │             │              │             │ 退货/换货  │
```

---

## 2. 整体架构

系统分为 **6 个层级** + **1 个事件驱动层**：

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      UI Layer (desktop/)                    │
 │  main_window | order_view | process_view | quality_view ... │
 │  Presenters (desktop/presenters/)                           │
 │  └─ base_presenter.py | mixins                             │
 ├─────────────────────────────────────────────────────────────┤
 │                   Service Layer (services/)                 │
 │  order_service | process_service | quality_service | ...   │
 ├─────────────────────────────────────────────────────────────┤
 │                     DAO Layer (models/)                     │
 │  order.py | process.py | quality.py | inventory.py | ...   │
 │  Database (models/database/)                               │
 │  └─ connection | __init__ | utils_db.py                    │
 ├─────────────────────────────────────────────────────────────┤
 │                   Core Layer (core/)                        │
 │  app.py | config.py | events.py | event_bus.py | db.py     │
 │  exceptions.py | _config_ui.py | _config_domain.py         │
 ├─────────────────────────────────────────────────────────────┤
 │            Security Layer (security/)                       │
 │  auth.py | login dialog                                     │
 ├─────────────────────────────────────────────────────────────┤
 │              Utilities Layer (utils/)                       │
 │  helpers.py | window_manager.py | auto_refresh_mixin.py    │
 │  auto_schema.py | password_hasher.py                       │
 ├─────────────────────────────────────────────────────────────┤
 │                    Data Storage                             │
 │  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐ │
 │  │  MySQL Database │  │  .env Config │  │  logs/ Files  │ │
 │  └─────────────────┘  └──────────────┘  └───────────────┘ │
 └─────────────────────────────────────────────────────────────┘
```

### 层间依赖方向

```
UI Layer → Presenters → Service Layer → DAO Layer → Database
                              ↕
                         EventBus (解耦)
                              ↕
                     Core + Config + Security
```

---

## 3. 目录结构与模块职责

```
不锈钢网带跟单3.0/
├── main.py                      # 桌面端主入口：初始化应用、显示登录窗口
├── launcher.py                  # 应用启动器：选择"启动跟单系统"或"启动服务器"
├── start_servers.py             # 服务器启动辅助（mobile_api/dispatch_center）
├── steel_belt_tracking.py       # 钢带跟踪业务入口（部分业务逻辑入口）
├── version.py                   # 全局版本号定义
├── constants.py                 # 全局常量（业务流程步骤、状态映射）
├── config.py                    # 顶层配置引用（重导出 core/config 的内容）
├── requirements.txt             # Python 依赖清单
├── main.spec                    # PyInstaller 打包配置文件
│
├── core/                        # ★ 核心层：应用基础设施
│   ├── __init__.py              #   模块初始化、sys.path管理
│   ├── app.py                   #   Application 类：窗口管理、全局初始化
│   ├── config.py                #   ★ 统一配置中心（路径、数据库、域名等）
│   ├── _config_ui.py            #   前端UI样式配置（颜色、字体、尺寸）
│   ├── _config_domain.py        #   业务域配置（数据库URL、DLL路径）
│   ├── _config_infra.py         #   基础设施配置（日志级别、SW缓存等）
│   ├── db.py                    #   数据库连接池 / 连接管理（备用/兼容层）
│   ├── events.py                #   事件类型枚举/定义
│   ├── event_bus.py             #   EventBus 事件总线实现
│   ├── exceptions.py            #   自定义异常体系
│   └── _dependency.py           #   依赖注入/服务定位器
│
├── config/                      # 配置文件目录
│   ├── xxx.ini / xxx.yaml       #   本地配置文件
│   └── .env                     #   环境变量文件（如存在）
│
├── models/                      # ★ 数据访问层 (DAO)
│   ├── __init__.py              #   模块初始化
│   ├── base_dao.py              #   BaseDAO 基类（唯一ID生成、CRUD模板）
│   ├── order.py                 #   订单 DAO
│   ├── process.py               #   流程记录 DAO
│   ├── production.py            #   生产/报工 DAO
│   ├── quality.py               #   质量检验 DAO
│   ├── inventory.py             #   原材料库存 DAO
│   ├── shipment.py              #   发货管理 DAO
│   ├── bom.py                   #   BOM物料清单 DAO
│   ├── operator.py              #   操作员管理 DAO
│   ├── machine.py               #   设备管理 DAO
│   ├── notification.py          #   通知/消息 DAO
│   ├── config_dao.py            #   配置数据 DAO
│   ├── audit.py                 #   审计日志 DAO
│   └── database/                #   数据库连接与工具
│       ├── __init__.py          #   get_connection() 连接工厂
│       └── utils_db.py          #   数据库工具函数
│
├── services/                    # ★ 业务服务层
│   ├── __init__.py              #   模块初始化
│   ├── base_service.py          #   BaseService 基类
│   ├── order_service.py         #   订单业务服务
│   ├── process_service.py       #   流程/排产业务服务
│   ├── quality_service.py       #   质检业务服务
│   ├── shipment_service.py      #   发货业务服务
│   ├── inventory_service.py     #   库存业务服务
│   ├── bom_service.py           #   BOM业务服务
│   ├── notification_service.py  #   通知业务服务
│   ├── auth_service.py          #   认证业务服务
│   ├── audit_service.py         #   审计日志业务服务
│   └── config_service.py        #   配置业务服务
│
├── desktop/                     # ★ 桌面UI层 (PyQt5)
│   ├── __init__.py              #   模块初始化
│   ├── views/                   #   视图组件
│   │   ├── main_window.py      #   ★ 主窗口（侧边导航+Tab面板）
│   │   ├── order_view.py       #   订单管理视图
│   │   ├── process_view.py     #   流程/排产视图
│   │   ├── production_view.py  #   生产报工视图
│   │   ├── quality_view.py     #   质量检验视图
│   │   ├── inventory_view.py   #   库存管理视图
│   │   ├── shipment_view.py    #   发货管理视图
│   │   ├── bom_view.py         #   BOM物料清单视图
│   │   ├── operator_view.py    #   操作员管理视图
│   │   ├── kanban_view.py      #   看板/KPI视图
│   │   ├── settings_view.py    #   系统设置视图
│   │   ├── notification_view.py#   通知列表视图
│   │   ├── material_prep_view.py #   备料视图
│   │   ├── supplier_view.py    #   供应商管理（如存在）
│   │   ├── statistics_view.py  #   统计分析视图
│   │   ├── components.py       #   ★ 共享UI组件（表格、按钮、弹窗等）
│   │   └── dialogs/            #   弹窗组件目录
│   ├── presenters/             #    Presenter层（MVP模式的视图逻辑）
│   │   ├── base_presenter.py   #   ★ BasePresenter 基类（数据加载、事件绑定、错误处理）
│   │   ├── order_presenter.py  #   订单Presenter
│   │   ├── process_presenter.py#   流程Presenter
│   │   └── ... (其他 Presenter)
│   └── resources/              #   资源文件（图标、样式表等）
│       ├── icons/              #   图标资源
│       └── styles/             #   QSS 样式表
│
├── security/                    # 安全模块
│   ├── __init__.py
│   └── auth.py                  # 用户认证（密码验证、session管理）
│
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── helpers.py               # 通用工具函数（字符串、日期、数字格式化）
│   ├── window_manager.py        #   窗口管理器（子窗口创建、层叠排列）
│   ├── auto_refresh_mixin.py    #   自动刷新 Mixin（定时刷新、数据同步）
│   ├── auto_schema.py           #   自动建表（检查并创建数据库表结构）
│   ├── password_hasher.py       #   密码哈希工具
│   └── dialog_helpers.py        #   弹窗辅助函数
│
├── data/                        # 本地数据目录
│   └── *.xlsx / *.json          #   数据导出/导入文件
│
├── logs/                        # 日志目录
│   └── app_*.log                #   运行日志
│
└── docs/                        # 项目文档
    ├── help.pdf                 #   用户手册
    └── ...                      #   其他文档
```

---

## 4. 启动流程与入口点

### 4.1 启动流程图

```
launcher.py
    │
    ├── 用户选择「启动跟单系统」
    │       │
    │       └── main.py
    │               │
    │               ├── 1. 加载 .env 配置 (core/config.py → load_env())
    │               ├── 2. 初始化日志
    │               ├── 3. 初始化数据库连接 (models/database/__init__.py → get_connection())
    │               ├── 4. 初始化 Application (core/app.py → Application 单例)
    │               │       ├── 注册全局 EventBus
    │               │       └── 加载 UI 配置 (core/_config_ui.py)
    │               ├── 5. 弹出登录对话框 (security/auth.py)
    │               │       ├── 密码验证 (utils/password_hasher.py)
    │               │       └── Session 创建
    │               ├── 6. 创建主窗口 (desktop/views/main_window.py)
    │               │       ├── 初始化侧边导航栏
    │               │       ├── 初始化 Tab 视图面板
    │               │       └── 绑定主窗口事件
    │               └── 7. app.exec_() 进入事件循环
    │
    └── 用户选择「启动服务器」
            │
            └── start_servers.py → 启动 mobile_api 和 dispatch_center 服务
```

### 4.2 入口点详解

| 入口 | 文件 | 用途 |
|------|------|------|
| **main.py** | `main.py` | **桌面客户端主入口**，启动 PyQt5 应用 |
| **launcher.py** | `launcher.py` | 启动选择器（桌面/服务器），入口分流 |
| **start_servers.py** | `start_servers.py` | 后台服务启动（Web API 等） |

### 4.3 main.py 执行流程 (伪代码)

```python
# 1. sys.path 设置（确保项目根目录在导入路径中）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 2. 配置初始化
load_env()                             # 从 config.py 加载环境变量
init_logging()                         # 初始化日志

# 3. 数据库连接检查
conn = get_connection()                # models/database/__init__.py
check_and_create_tables()              # auto_schema.py

# 4. 创建 Application 实例
app = Application(sys.argv)            # core/app.py
app.init_event_bus()                   # 注册 EventBus

# 5. 认证
login_dlg = LoginDialog()
if login_dlg.exec_() != QDialog.Accepted:
    sys.exit(0)

# 6. 创建主窗口
window = MainWindow()
window.show()

# 7. 进入主循环
sys.exit(app.exec_())
```

---

## 5. 核心层 (core/)

### 5.1 core/app.py — Application 类

系统级 Application 实例，继承 `QApplication`，负责全局生命周期管理。

```python
class Application(QApplication):
    """应用主类"""

    def __init__(self, argv: list):
        super().__init__(argv)
        self._init_high_dpi()        # 高DPI适配
        self._init_style()           # 全局样式加载
        self._event_bus = EventBus() # 事件总线

    def init_event_bus(self):        # 初始化事件总线
    def _init_high_dpi(self):        # 高DPI缩放支持
    def _init_style(self):           # 加载QSS样式表
```

| 方法 | 说明 |
|------|------|
| `__init__` | 构造，初始化高DPI、样式、EventBus |
| `init_event_bus` | 创建 EventBus 单例，供全局使用 |
| `_init_high_dpi` | 设置 `Qt.AA_EnableHighDpiScaling` 等属性 |
| `_init_style` | 加载 `desktop/resources/styles/` 下的 QSS 样式 |

### 5.2 core/config.py — 统一配置中心

整个系统唯一配置入口，所有配置必须通过此模块访问。

```python
# === 路径配置 ===
BASE_DIR      # 项目根目录
DATA_DIR      # data/ 目录
CONFIG_DIR    # config/ 目录
LOG_DIR       # logs/ 目录

# === 数据库配置 (DatabaseConfig) ===
DatabaseConfig.get_db_url()    # MySQL 连接 URL
DatabaseConfig.get_pool_size() # 连接池大小

# === 环境变量加载 ===
load_env()                     # 叠加加载多个 .env 文件
```

**配置模块拆分**：
- `_config_ui.py` — UI 主题常量（COLORS、FONTS、MARGINS）
- `_config_domain.py` — 业务域配置（DB URL、DLL路径、SIZE常量）
- `_config_infra.py` — 基础设施配置（日志级别、SW 缓存、comtypes 设置）

### 5.3 core/events.py + event_bus.py — 事件系统

基于观察者模式实现进程内事件驱动通信。

```python
class EventBus:
    """事件总线：订阅/发布模式"""

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件"""

    def publish(self, event_type: str, **kwargs) -> None:
        """发布事件"""

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅"""
```

**已定义事件类型**（events.py）：
| 事件名 | 触发时机 | 发布者 | 订阅者 |
|--------|---------|--------|--------|
| `order_created` | 订单创建 | OrderPresenter | MainWindow, NotificationService |
| `order_updated` | 订单更新 | OrderPresenter | MainWindow |
| `process_advanced` | 流程推进 | ProcessPresenter | MainWindow, ProcessView |
| `quality_recorded` | 质检录入 | QualityPresenter | MainWindow |
| `shipment_created`| 发货创建 | ShipmentPresenter | InventoryService |
| `data_changed` | 通用数据变更 | 各View | AutoRefreshMixin |

### 5.4 core/exceptions.py — 异常体系

```python
class AppException(Exception):           # 基础异常
class DatabaseException(AppException):   # 数据库异常
class ValidationException(AppException): # 输入验证异常
class AuthException(AppException):       # 认证异常
class BusinessException(AppException):   # 业务逻辑异常
class DuplicateOperationException(AppException): # 重复操作异常
```

### 5.5 core/db.py — 数据库连接管理

```python
def get_db() -> Connection:     # 获取数据库连接（备用/兼容层）
def close_db() -> None:         # 关闭连接
```

> **注意**：**实际连接管理在 `models/database/__init__.py` 中**，`core/db.py` 作为兼容性包装层。

---

## 6. 配置系统

### 6.1 分层配置结构

```
┌──────────────────────────────────────────────┐
│  config.py (顶层重导出)                       │
├──────────────────────────────────────────────┤
│  core/config.py (统一配置中心)                │
│  ├── load_env()                              │
│  ├── 路径常量: BASE_DIR, DATA_DIR, ...       │
│  ├── DatabaseConfig                          │
│  └── 环境变量获取                           │
├──────────────────────────────────────────────┤
│  core/_config_ui.py (UI主题常量)              │
│  ├── COLORS (color palette)                  │
│  ├── FONTS (font families & sizes)           │
│  └── MARGINS (spacing & padding)             │
├──────────────────────────────────────────────┤
│  core/_config_domain.py (业务域配置)          │
│  ├── DB URL, pool_size                       │
│  ├── DLL/EXE路径                             │
│  └── 业务常量(SIZE)                          │
├──────────────────────────────────────────────┤
│  core/_config_infra.py (基础设施配置)         │
│  ├── 日志级别                                │
│  ├── SW缓存配置                              │
│  └── comtypes设置                            │
├──────────────────────────────────────────────┤
│  .env (敏感配置/环境变量)                    │
│  ├── DB_HOST, DB_USER, DB_PASSWORD          │
│  ├── API_KEY                                 │
│  └── 其他业务环境变量                        │
└──────────────────────────────────────────────┘
```

### 6.2 关键配置项

| 常量 | 文件 | 说明 |
|------|------|------|
| `BASE_DIR` | core/config.py | 项目根目录 |
| `DATA_DIR` | core/config.py | 数据文件目录 |
| `LOG_DIR` | core/config.py | 日志目录 |
| `COLORS` | core/_config_ui.py | UI颜色主题字典 |
| `FONTS` | core/_config_ui.py | 字体配置字典 |
| `STOCK_WARNING_THRESHOLD` | config.py | 库存预警阈值 |
| `DatabaseConfig` | core/config.py | 数据库配置类 |

---

## 7. 数据库层 (models/)

### 7.1 数据库连接

```python
# models/database/__init__.py
def get_connection() -> Connection:
    """获取数据库连接（从连接池获取或新建）"""
```

连接配置从 `core/config.py` 的 `DatabaseConfig` 读取，支持 MySQL。

### 7.2 自动建表

```python
# utils/auto_schema.py
def check_and_create_tables():
    """检查数据库中所有必需表是否存在，自动创建缺失表"""
```

### 7.3 BaseDAO 基类

```python
# models/base_dao.py
class BaseDAO:
    """DAO 基类，提供通用 CRUD 模板"""

    TABLE_NAME = ""                     # 子类覆盖
    
    @staticmethod
    def generate_id() -> str:           # 生成唯一ID
    @staticmethod
    def get_all() -> list[dict]:        # 获取全部记录
    @staticmethod
    def get_by_id(record_id) -> dict:   # 按ID查询
    @staticmethod
    def create(data: dict) -> int:      # 创建记录
    @staticmethod
    def update(record_id, data) -> bool:# 更新记录
    @staticmethod
    def delete(record_id) -> bool:      # 删除记录
```

### 7.4 各 DAO 模块

| 模块 | 表/实体 | 核心方法 | 说明 |
|------|---------|---------|------|
| [order.py](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py) | `orders` | `create`, `update`, `delete`, `get_by_id`, `get_all`, `search` | 订单CRUD，支持多维搜索 |
| [process.py](file:///d:/yuan/不锈钢网带跟单3.0/models/process.py) | `process_records` | `get_by_order`, `advance_step`, `get_status` | 流程记录，步骤推进/回退 |
| [production.py](file:///d:/yuan/不锈钢网带跟单3.0/models/production.py) | `production_records`, `sub_steps` | `create_sub_step`, `get_sub_step_summary`, `get_sub_step_history` | 生产报工（含重复判定） |
| [quality.py](file:///d:/yuan/不锈钢网带跟单3.0/models/quality.py) | `quality_records` | `create_record`, `get_by_order`, `get_statistics` | 质检记录，合格率统计 |
| [inventory.py](file:///d:/yuan/不锈钢网带跟单3.0/models/inventory.py) | `inventory` | `create`, `update`, `get_all`, `get_warning_list` | 原材料库存，预警查询 |
| [shipment.py](file:///d:/yuan/不锈钢网带跟单3.0/models/shipment.py) | `shipments` | `create_shipment`, `get_by_order`, `update_status` | 发货单管理 |
| [bom.py](file:///d:/yuan/不锈钢网带跟单3.0/models/bom.py) | `bom_items` | `get_by_product`, `save_bom` | BOM物料清单配置 |
| [operator.py](file:///d:/yuan/不锈钢网带跟单3.0/models/operator.py) | `operators` | `get_all`, `create`, `update`, `delete` | 操作员管理 |
| [machine.py](file:///d:/yuan/不锈钢网带跟单3.0/models/machine.py) | `machines` | `get_all`, `create`, `update`, `get_status` | 设备管理 |
| [notification.py](file:///d:/yuan/不锈钢网带跟单3.0/models/notification.py) | `notifications` | `create`, `get_unread`, `mark_read` | 系统通知/消息 |
| [audit.py](file:///d:/yuan/不锈钢网带跟单3.0/models/audit.py) | `audit_logs` | `log`, `query` | 操作审计日志 |
| [config_dao.py](file:///d:/yuan/不锈钢网带跟单3.0/models/config_dao.py) | `system_config` | `get`, `set`, `get_all` | 系统配置持久化 |

---

## 8. 业务服务层 (services/)

### 8.1 BaseService 基类

```python
# services/base_service.py
class BaseService:
    """所有 Service 的基类，提供通用业务处理逻辑"""

    dao_class = None  # 子类指定对应的 DAO 类

    def get_all(self) -> list:
        return self.dao_class.get_all()

    def get_by_id(self, record_id):
        return self.dao_class.get_by_id(record_id)

    def create(self, data: dict) -> int:
        return self.dao_class.create(data)

    def update(self, record_id, data: dict) -> bool:
        return self.dao_class.update(record_id, data)

    def delete(self, record_id) -> bool:
        return self.dao_class.delete(record_id)
```

### 8.2 各 Service 模块

| 模块 | 对应 DAO | 核心业务逻辑 |
|------|---------|-------------|
| [order_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/order_service.py) | OrderDAO | 订单创建校验、金额计算、状态更新、订单审核 |
| [process_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/process_service.py) | ProcessDAO | 流程节点推进、排产确认、状态机流转 |
| [quality_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/quality_service.py) | QualityDAO | 质检记录、合格率统计、批次判定 |
| [shipment_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/shipment_service.py) | ShipmentDAO | 发货管理、退货处理、物流跟踪 |
| [inventory_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/inventory_service.py) | InventoryDAO | 库存变动、出入库、预警逻辑 |
| [bom_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/bom_service.py) | BOMDAO | BOM配置、材料用量计算 |
| [notification_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/notification_service.py) | NotificationDAO | 通知推送、未读查询 |
| [auth_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/auth_service.py) | — | 用户认证、权限校验 |
| [audit_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/audit_service.py) | AuditDAO | 操作审计日志记录和查询 |
| [config_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/config_service.py) | ConfigDAO | 系统配置读取/更新 |

---

## 9. 桌面UI层 (desktop/)

### 9.1 UI 架构模式

系统采用 **MVP (Model-View-Presenter)** 模式，其中 View 是"被动视图"（Passive View）：

```
  View (desktop/views/)                    Presenter (desktop/presenters/)
  ┌─────────────────┐                      ┌────────────────────────┐
  │ PyQt5 Widgets    │◄── 用户操作 ────    │ 事件处理               │
  │ 布局、控件、表   │                      │ 数据验证               │
  │ QTableWidget     │                      │ 调用 Service           │
  │ QLineEdit        │──── 更新UI ───────►│ 错误处理               │
  │ QComboBox        │                      │ 触发 EventBus          │
  └─────────────────┘                      └───────────┬────────────┘
                                                       │
                                                ┌──────▼──────┐
                                                │  Service     │
                                                │  Layer       │
                                                └─────────────┘
```

### 9.2 主窗口 [main_window.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/main_window.py)

```python
class MainWindow(QMainWindow):
    """系统主窗口"""

    NAV_ITEMS = [
        ("订单管理",    order_view.OrderView),
        ("生产流程",    process_view.ProcessView),
        ("生产报工",    production_view.ProductionView),
        ("质量检验",    quality_view.QualityView),
        ("成品入库",    inventory_view.InventoryView),
        ("发货管理",    shipment_view.ShipmentView),
        ("物料清单",    bom_view.BOMView),
        ("看板统计",    kanban_view.KanbanView),
        ("操作员管理",  operator_view.OperatorView),
        ("通知消息",    notification_view.NotificationView),
        ("系统设置",    settings_view.SettingsView),
    ]
```

| 方法 | 说明 |
|------|------|
| `__init__` | 构造：创建侧边导航、Tab面板、状态栏 |
| `init_nav_bar` | 初始化左侧导航栏（图标+文本列表） |
| `init_content_area` | 初始化右侧内容区域（QStackedWidget） |
| `switch_tab(index)` | 切换当前 Tab 页面 |
| `create_status_bar` | 创建底部状态栏 |
| `on_nav_clicked` | 导航点击事件处理 |
| `refresh_current_tab` | 刷新当前标签页数据 |

### 9.3 共享UI组件 [components.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/components.py)

| 组件类 | 说明 |
|--------|------|
| `StyledTableWidget` | 统一风格的表格组件（表头、行高、列宽、排序） |
| `SearchPanel` | 通用搜索面板（关键字+日期范围+状态筛选） |
| `FormDialog` | 通用表单弹窗（动态字段、必填校验） |
| `ConfirmDialog` | 确认操作弹窗 |
| `MessageBox` | 消息提示框封装（success/warning/error/info） |
| `PageNavigator` | 分页导航组件 |
| `StatusIndicator` | 状态指示器（彩色圆点+文字） |
| `DateRangePicker` | 日期范围选择器 |

### 9.4 各业务视图

| 视图文件 | 类名 | 核心功能 |
|---------|------|---------|
| [order_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/order_view.py) | `OrderView` | 订单列表、新建/编辑/删除/审核订单 |
| [process_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/process_view.py) | `ProcessView` | 流程看板、排产定制、确认、节点推进 |
| [production_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/production_view.py) | `ProductionView` | 工序报工录入、报工历史、报工汇总 |
| [quality_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/quality_view.py) | `QualityView` | 质检记录录入、合格率统计图表 |
| [inventory_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/inventory_view.py) | `InventoryView` | 库存列表、出入库操作、库存预警 |
| [shipment_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/shipment_view.py) | `ShipmentView` | 发货单创建、发货记录、退货处理 |
| [bom_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/bom_view.py) | `BOMView` | BOM 配置、材料清单编辑 |
| [operator_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/operator_view.py) | `OperatorView` | 用户管理、角色分配 |
| [kanban_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/kanban_view.py) | `KanbanView` | KPI 看板、生产进度可视化 |
| [settings_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/settings_view.py) | `SettingsView` | 系统参数设置、备份恢复 |
| [notification_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/notification_view.py) | `NotificationView` | 通知列表、未读标记 |
| [material_prep_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/material_prep_view.py) | `MaterialPrepView` | 备料管理 |
| [statistics_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/statistics_view.py) | `StatisticsView` | 统计分析、报表生成 |

### 9.5 Presenter 层

```python
# desktop/presenters/base_presenter.py
class BasePresenter:
    """Presenter 基类，封装视图的业务调度逻辑"""

    def __init__(self, view, service=None):
        self.view = view               # 关联的 View
        self.service = service          # 可选的 Service
        self.event_bus = EventBus()    # 事件总线

    def load_data(self, **filters):    # 加载数据 → 更新 View
    def handle_error(self, ex):        # 统一错误处理
    def bind_events(self):             # 绑定 View 事件 → Presenter 方法
    def on_data_changed(self, event):  # 数据变更后的自动刷新
```

---

## 10. 安全模块 (security/)

### 10.1 认证流程

```
用户输入密码
     │
     ▼
LoginDialog (PyQt5 QDialog)
     │
     ▼
auth_service.verify_password(password)
     │
     ├── 从数据库读取存储的密码哈希
     ├── password_hasher.verify(plain, stored_hash)
     ├── 匹配成功 → 创建 Session
     └── 匹配失败 → 提示错误
```

### 10.2 关键类

```python
# security/auth.py
class LoginDialog(QDialog):
    """登录弹窗"""
    # 密码输入、验证、Session 创建

class Session:
    """用户会话（登录后全局持有）"""
    user_id: int
    username: str
    role: str
    login_time: datetime
```

```python
# utils/password_hasher.py
def hash_password(password: str) -> str:
    """密码加盐哈希（SHA-256 + 随机盐值）"""

def verify_password(password: str, stored_hash: str) -> bool:
    """密码验证"""
```

---

## 11. 工具模块 (utils/)

| 模块 | 核心功能 | 关键函数/类 |
|------|---------|------------|
| [helpers.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/helpers.py) | 通用工具函数 | `format_datetime`, `generate_order_no`, `validate_phone`, `safe_float`, `truncate_text` |
| [window_manager.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/window_manager.py) | 窗口管理 | `WindowManager` 类：创建、居中、层叠子窗口 |
| [auto_refresh_mixin.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/auto_refresh_mixin.py) | 自动刷新 | `AutoRefreshMixin`：定时刷新、EventBus 事件监听刷新 |
| [auto_schema.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/auto_schema.py) | 自动建表 | `check_and_create_tables()` |
| [password_hasher.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/password_hasher.py) | 密码哈希 | `hash_password`, `verify_password` |
| [dialog_helpers.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/dialog_helpers.py) | 弹窗辅助 | `show_confirm`, `show_input_dialog`, `show_file_dialog` |

### AutoRefreshMixin 机制

```python
class AutoRefreshMixin:
    """自动刷新 Mixin：混入到需要定时刷新的 View 中"""

    REFRESH_INTERVAL = 30  # 默认30秒

    def start_auto_refresh(self, interval: int = None):
        """启动定时刷新（QTimer）"""

    def stop_auto_refresh(self):
        """停止定时刷新"""

    def on_auto_refresh(self):
        """定时刷新回调（子类覆盖）"""

    def on_data_changed(self, event_data):
        """EventBus 事件触发刷新"""
```

---

## 12. 公式计算原则

本系统涉及多种业务公式计算，覆盖从订单金额到工序计划数量、质量合格率、用料差异等全链路。以下逐一说明各场景的计算原则。

### 12.1 订单金额计算

**文件**：[models/order.py](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py)

| 字段 | 公式 | 位置 |
|------|------|------|
| 订单总金额 (total_amount) | `total = quantity × unit_price` | `OrderDAO.create()` (L138) / `OrderDAO.update()` (L200) |

```
订单总金额 = 订单数量 × 单价
```

- `quantity`（数量）和 `unit_price`（单价）来自用户录入
- 创建和更新订单时自动计算，存入 `orders.total_amount` 字段
- 数量/单价任一变更 → 重新计算 total_amount

### 12.2 工序计划数量计算（核心计算引擎）

**文件**：[models/process_calc_rule.py](file:///d:/yuan/不锈钢网带跟单3.0/models/process_calc_rule.py) — `ProcessCalcEngine`

这是系统最核心、最复杂的计算逻辑，用于自动计算每道工序的计划生产数量。

#### 12.2.1 公式模板语法

```
工序计划数量 = 数学表达式（含 {占位符} 变量替换）
```

- **占位符格式**：`{参数名}`，如 `{总长度}`、`{网带节距}`、`{物料数量}`
- **支持的运算符**：`+`、`-`、`*`、`/`（遵循先乘除后加减，括号优先）
- **向上取整**：计算结果 > 0 时用 `math.ceil()` 向上取整

#### 12.2.2 计算流程

```
原始公式: "{总长度}*1000/{网带节距}"
     │
     ├── (1) 解析占位符 → 提取 ["总长度", "网带节距"]
     │
     ├── (2) 从订单数据取值 → 总长度=5, 网带节距=25.4
     │
     ├── (3) 替换占位符 → "5*1000/25.4"
     │
     ├── (4) 数学求值 → 196.85...
     │
     └── (5) math.ceil 向上取整 → 197
```

#### 12.2.3 典型公式示例

| 工序名称 | 公式模板 | 说明 |
|---------|---------|------|
| 原材料准备 | `{物料数量}` | 直接使用订单的物料种类数量 |
| 激光切板 | `{总长度}*1000/{网带节距}` | 总长度(米)→毫米，除以节距得片数 |
| 链板冲压孔 | `{总长度}*1000/{网带节距}` | 同上 |
| 链板冲压成型 | `{总长度}*1000/{网带节距}` | 同上 |
| 焊接眼镜网 | `{总长度}*1000/{网带节距}` | 同上 |
| 其他固定工序 | `1` | 固定为 1（如整卷类的工序） |

#### 12.2.4 条件表达式（生效条件）

每道工序可配置生效条件，决定该工序是否对当前产品类型适用：

```python
COND_OPERATORS = {
    "等于":       lambda a, b: a == b,
    "不等于":     lambda a, b: a != b,
    "大于":       lambda a, b: float(a) > float(b),
    "小于":       lambda a, b: float(a) < float(b),
    "大于等于":   lambda a, b: float(a) >= float(b),
    "小于等于":   lambda a, b: float(a) <= float(b),
    "包含":       lambda a, b: b in str(a),
    "不包含":     lambda a, b: b not in str(a),
}
```

#### 12.2.5 计算引擎核心代码

```python
class ProcessCalcEngine:
    CALC_OPERATORS = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b if b != 0 else 0,
    }

    @classmethod
    def calculate_planned_qty(cls, formula, order_data) -> float:
        # 1. 解析占位符 {xxx}
        # 2. 替换为订单数据中的实际值
        # 3. _calc_expr() 数学表达式求值
        # 4. math.ceil() 向上取整
        return final
```

### 12.3 质量合格率与损耗率

**文件**：[models/order.py](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py)、[models/production_stats.py](file:///d:/yuan/不锈钢网带跟单3.0/models/production_stats.py)

#### 12.3.1 损耗率（Loss Rate）

```
损耗率(%) = (completed_qty - qualified_qty) / completed_qty × 100
```

- 来源：`OrderDAO.get_order_statistics()` (L911-L912)
- `completed_qty`：已完成总数量（含不合格）
- `qualified_qty`：合格总数量
- 含义：不合格品占总完成数量的比例

#### 12.3.2 通过率（Pass Rate）

```
通过率(%) = qualified_qty / completed_qty × 100
```

- 来源：`OrderDAO.get_order_statistics()` (L1038)
- 每道工序单独计算

#### 12.3.3 总合格率（Total Qualified Rate）

```
总合格率(%) = 合格总数 / 完成总数 × 100
```

- 来源：`ProductionStatsDAO.calculate_stats()` (L109-L110)
- `qualified_qty`：所有已完工工序的合格数量之和
- `total_qty`：所有已完工工序的完成数量之和
- 按订单维度聚合计算

#### 12.3.4 平均工序合格率

```sql
AVG(CASE WHEN completed_qty > 0
         THEN (qualified_qty / completed_qty) * 100
         ELSE 0 END) as avg_rate
```

- 来源：`ProductionStatsDAO.calculate_stats()` (L113-L117)
- 先算每道工序的合格率，再取所有工序的算术平均

### 12.4 用料差异计算

**文件**：[models/production_stats.py](file:///d:/yuan/不锈钢网带跟单3.0/models/production_stats.py)

```
用料差异 = 实际用量 - 理论用量

用料差异率(%) = (实际用量 - 理论用量) / 理论用量 × 100
```

- `total_calculated_qty`：理论计算用量（按公式计算的计划数量）
- `total_actual_qty`：实际报工用量
- 差异 > 0：用料超支；差异 < 0：用料节约

### 12.5 生产进度计算

**文件**：[services/process_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/process_service.py)

```
生产进度(%) = 已完成工序数 / 总工序数 × 100
```

```python
def get_production_summary(self, production_id):
    records = self.dao.get_by_production(production_id)
    total = len(records)
    completed = sum(1 for r in records if r.get('status') == '已完成')
    progress = completed / max(total, 1) * 100
```

- 按生产工单（production）维度统计
- `total`：该工单下所有工序数量
- `completed`：状态为"已完成"的工序数量

### 12.6 质检判定计算

**文件**：[models/quality_rule.py](file:///d:/yuan/不锈钢网带跟单3.0/models/quality_rule.py)

质检规则判定使用与工序计划数量计算相同的表达式引擎 `ProcessCalcEngine._calc_expr()` 计算标准值，再与实测值比较：

```
标准值 = 表达式求值(公式, 订单尺寸参数)

判定结果 = |实测值 - 标准值| ≤ 公差值 ?
    ┌── 是 → 合格 (is_passed = True)
    └── 否 → 不合格 (is_passed = False)
```

- 标准值来源：利用订单尺寸参数（总长度、丝径、螺距、边高等）通过公式计算
- 公差（tolerance）：从质检规则配置中读取，支持 `±N` 格式
- 实际判定逻辑（L380-L384）：

```python
tol_val = abs(float(tolerance.replace("±", "").replace("+", "").replace("-", "")))
is_passed = abs(measured - standard_value) <= tol_val
```

### 12.7 包装入库校验计算

**文件**：[models/process.py](file:///d:/yuan/不锈钢网带跟单3.0/models/process.py)

包装入库报工时，强制校验包装数量不得超过质检合格总数的强约束：

```
包装入库累计(含本次) ≤ 质检合格总数 ?
    ┌── 是 → 允许入库
    └── 否 → 拒绝（抛出 ValueError）
```

```python
total_qc = SUM(completed_qty where process_name='质量检验' AND status='已完成')
total_packing = SUM(completed_qty where process_name='包装入库')
new_total = total_packing + delta_qty
if new_total > total_qc:
    raise ValueError("包装入库数量超过质量检验合格总数")
```

### 12.8 库存变动计算

**文件**：[models/inventory.py](file:///d:/yuan/不锈钢网带跟单3.0/models/inventory.py)

```
入库后数量 = 当前数量 + 入库数量
出库后数量 = 当前数量 - 出库数量（库存不足时拒绝出库）
```

- 每次变动记录 before_qty 和 after_qty 到 `inventory_records` 审计表

**库存预警**：

```
库存不足条件：当前数量 ≤ 预警阈值(warning_qty)

预警阈值来源：
  ┌── 用户配置 → 存入 inventory.warning_qty 字段
  └── 默认值 → STOCK_WARNING_THRESHOLD（来自 config.py）
```

### 12.9 成本自动归集计算

**文件**：[mobile_api_ai/services/cost_service.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/services/cost_service.py)

#### 材料成本

```
材料金额 = 材料用量 × 材料单价

材料成本合计 = Σ(各工序材料金额)
```

- 材料用量来自 `material_rules` 表各工序的材料定额
- 材料单价从 `material_unit_prices` 表读取（按工序名匹配）

#### 人工成本

```
人工金额 = 报工工时 × 工序单价

人工成本合计 = Σ(各工序人工金额)
```

- 报工工时来自 `report_records` 表已审批的报工记录
- 工序单价从 `labor_unit_prices` 表读取

### 12.10 订单号生成

**文件**：[models/database/__init__.py](file:///d:/yuan/不锈钢网带跟单3.0/models/database/__init__.py) — `generate_order_no()`

```
订单号 = 日期前缀 + 自增序号
格式示例：20260621001
           │        │
           └─ 当天日期(YYYYMMDD)  └─ 当日序号（从001开始，每天重置）
```

- 日期前缀由 `datetime.now().strftime("%Y%m%d")` 生成
- 序号从数据库查询当天已有订单数 + 1
- 保证了每天从 001 重新编号

### 12.11 分页计算

**文件**：[models/order.py](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py) — `OrderDAO.paginate_search()`

```
总页数 = (总记录数 + 每页大小 - 1) // 每页大小

是否有上一页 = 当前页 > 1
是否有下一页 = 当前页 < 总页数

偏移量(offset) = (当前页 - 1) × 每页大小
```

### 12.12 订单完成率（看板统计）

**文件**：[models/order.py](file:///d:/yuan/不锈钢网带跟单3.0/models/order.py) — `OrderDAO.get_dashboard_stats()`

```
订单完成率(%) = (已完成订单数 ÷ 总订单数) × 100
```

- 总订单数：排除已删除和已归档的订单
- 已完成订单：状态为"已完成"的订单

### 计算原则汇总表

| # | 计算项 | 公式 | 所在模块 | 关键行号 |
|---|--------|------|---------|---------|
| 1 | 订单金额 | `qty × unit_price` | order.py | L138, L200 |
| 2 | 工序计划量 | `math.ceil(eval(模板公式))` | process_calc_rule.py | L257-L295 |
| 3 | 损耗率 | `(completed - qualified) / completed × 100` | order.py | L912, L1047 |
| 4 | 通过率 | `qualified / completed × 100` | order.py | L1038 |
| 5 | 总合格率 | `SUM(qualified) / SUM(completed) × 100` | production_stats.py | L109-L110 |
| 6 | 平均工序合格率 | `AVG(各工序合格率)` | production_stats.py | L113-L119 |
| 7 | 用料差异 | `实际用量 - 理论用量` | production_stats.py | L124 |
| 8 | 用料差异率 | `(实际-理论) / 理论 × 100` | production_stats.py | L128 |
| 9 | 生产进度 | `已完成工序数 / 总工序数 × 100` | process_service.py | L233-L238 |
| 10 | 质检判定 | `\|实测-标准\| ≤ 公差` | quality_rule.py | L380-L384 |
| 11 | 包装入库校验 | `SUM(包装) + 本次 ≤ SUM(QC合格)` | process.py | L218-L242 |
| 12 | 库存变动 | `当前 ± 变动量` | inventory.py | L77, L107 |
| 13 | 材料成本 | `用量 × 单价` | cost_service.py | L227 |
| 14 | 人工成本 | `工时 × 工序单价` | cost_service.py | L277 |
| 15 | 订单号生成 | `YYYYMMDD + 每日序号` | database/__init__.py | — |
| 16 | 分页 | `(total + page_size - 1) // page_size` | order.py | L625 |
| 17 | 订单完成率 | `已完成 / 总订单 × 100` | order.py | L1374 |

---

## 13. 数据流与事件系统

### 13.1 典型操作数据流（以"创建订单"为例）

```
┌─────────┐    ┌───────────────┐    ┌──────────────┐    ┌───────────┐    ┌──────────┐
│ 用户点击  │    │   OrderView    │    │OrderPresenter │    │OrderService│    │ OrderDAO │
│ "新建"   │    │  (QDialog)     │    │               │    │            │    │          │
└────┬─────┘    └───────┬───────┘    └──────┬─────────┘    └─────┬──────┘    └────┬─────┘
     │                  │                    │                   │                 │
     │  1. 打开表单弹窗  │                    │                   │                 │
     │─────────────────►│                    │                   │                 │
     │                  │                    │                   │                 │
     │  2. 用户填写信息   │                    │                   │                 │
     │ ◄────────────────│                    │                   │                 │
     │                  │                    │                   │                 │
     │  3. 点击保存      │  4. save(data)     │                   │                 │
     │─────────────────►│──────────────────►│                   │                 │
     │                  │                    │  5. 数据校验       │                 │
     │                  │                    │  6. create(data)  │                 │
     │                  │                    │─────────────────►│                 │
     │                  │                    │                   │  7. dao.create() │
     │                  │                    │                   │───────────────►│
     │                  │                    │                   │                 │
     │                  │                    │  8. 返回 order_id  │◄───────────────│
     │                  │                    │◄─────────────────│                 │
     │                  │                    │                   │                 │
     │                  │  9. 更新表格       │                   │                 │
     │                  │◄──────────────────│                   │                 │
     │  10. 提示成功     │                    │  11. EventBus     │                 │
     │ ◄────────────────│                    │   publish('order_ │                 │
     │                  │                    │    created')      │                 │
     │                  │                    │─────────────────────────────────────────►
     │                  │                    │                   │   (通知其他模块)    │
```

### 13.2 状态机流转（流程管理）

```
订单发布 ──► 排产定制 ──► 排产确认 ──► 生产执行 ──► 报工完成 ──► 成品入库 ──► 发货 ──► 确认收货
    │            │            │           │            │           │         │         │
    └────────────┴────────────┴───────────┴────────────┴───────────┴─────────┴─────────┘
                                      ← 可回退任意一步 →
```

### 13.3 事件驱动的自动刷新

```
OrderView.save(data)
    │
    ▼
OrderPresenter.create(data)
    │
    ├── OrderService.create(data) → DAO → DB
    │
    └── EventBus.publish("order_created", order_id=...)
                │
                ├── MainWindow.on_data_changed() → 更新状态栏
                ├── KanbanView.on_data_changed() → 刷新看板数据
                ├── NotificationService.on_order_created() → 创建通知
                └── AutoRefreshMixin 订阅的 View → 触发刷新
```

---

## 14. 依赖关系梳理

### 14.1 模块依赖图

```
main.py / launcher.py
    │
    ├── core/
    │   ├── config.py ─────────→ _config_ui.py, _config_domain.py, _config_infra.py
    │   ├── app.py
    │   ├── events.py
    │   ├── event_bus.py
    │   ├── db.py
    │   └── exceptions.py
    │
    ├── config.py ────────────→ core/config.py
    ├── constants.py
    │
    ├── models/
    │   ├── database/__init__.py ──→ core/config.py (DatabaseConfig)
    │   ├── base_dao.py
    │   ├── order.py ──────────────→ models/database/__init__.py
    │   ├── process.py ────────────→ models/database/__init__.py
    │   ├── quality.py
    │   ├── inventory.py ─────────→ config.py (STOCK_WARNING_THRESHOLD)
    │   ├── ...
    │
    ├── services/
    │   ├── base_service.py ──────→ models/base_dao.py
    │   ├── order_service.py ──────→ models/order.py, services/base_service.py
    │   ├── process_service.py ────→ models/process.py, services/base_service.py
    │   ├── ...
    │
    ├── desktop/
    │   ├── views/
    │   │   ├── main_window.py ───→ 所有 View 组件
    │   │   ├── components.py ────→ core/_config_ui.py (COLORS, FONTS)
    │   │   ├── order_view.py ────→ services/order_service.py
    │   │   ├── ...
    │   └── presenters/
    │       └── base_presenter.py ─→ core/event_bus.py, core/exceptions.py
    │
    ├── security/
    │   └── auth.py ──────────→ utils/password_hasher.py, services/auth_service.py
    │
    └── utils/
        ├── helpers.py
        ├── window_manager.py
        ├── auto_refresh_mixin.py ──→ core/event_bus.py
        ├── auto_schema.py ────────→ models/database/__init__.py
        └── password_hasher.py
```

### 14.2 外部Python依赖 (requirements.txt)

| 包名 | 用途 |
|------|------|
| `PyQt5` | 桌面GUI框架 |
| `mysql-connector-python` | MySQL数据库驱动 |
| `PyMySQL` | MySQL数据库驱动（备用） |
| `cryptography` | 密码哈希加密 |
| `python-dotenv` | .env 文件加载 |
| `openpyxl` | Excel导出/导入 |
| `requests` | HTTP请求（与mobile_api通信） |
| `pyinstaller` | 应用打包（开发依赖） |

---

## 15. 运行方式与环境要求

### 15.1 环境要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.8 |
| MySQL | >= 5.7 (或 MariaDB >= 10.3) |
| 操作系统 | Windows 10/11 (推荐) |
| 屏幕 | 推荐 1920×1080 及以上 |

### 15.2 安装步骤

```bash
# 1. 克隆/进入项目目录
cd d:\yuan\不锈钢网带跟单3.0

# 2. 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置数据库
#    - 在 MySQL 中创建数据库（如 order_tracking 或配置的连接名）
#    - 编辑 .env 文件，设置数据库连接信息：
#      DB_HOST=localhost
#      DB_PORT=3306
#      DB_USER=root
#      DB_PASSWORD=your_password
#      DB_NAME=order_tracking

# 5. 首次启动（会自动建表）
python main.py
```

### 15.3 启动方式

| 方式 | 命令 | 说明 |
|------|------|------|
| 桌面客户端 | `python main.py` | 启动跟单系统桌面端 |
| 启动器 | `python launcher.py` | 选择启动跟单系统或服务器 |
| 自动建表 | 启动时自动调用 | `utils/auto_schema.py` 自动创建缺失表 |

### 15.4 打包部署

```bash
# 使用 PyInstaller 打包为单文件 exe
pyinstaller main.spec
# 输出到 dist/ 目录
```

---

## 16. 关键类/函数索引

### 16.1 核心类索引

| 类名 | 文件路径 | 职责 |
|------|---------|------|
| `Application` | [core/app.py](file:///d:/yuan/不锈钢网带跟单3.0/core/app.py) | 应用主类，全局生命周期 |
| `EventBus` | [core/event_bus.py](file:///d:/yuan/不锈钢网带跟单3.0/core/event_bus.py) | 进程内事件总线 |
| `DatabaseConfig` | [core/config.py](file:///d:/yuan/不锈钢网带跟单3.0/core/config.py) | 数据库配置类 |
| `BaseDAO` | [models/base_dao.py](file:///d:/yuan/不锈钢网带跟单3.0/models/base_dao.py) | DAO 基类，通用CRUD |
| `BaseService` | [services/base_service.py](file:///d:/yuan/不锈钢网带跟单3.0/services/base_service.py) | Service 基类 |
| `MainWindow` | [desktop/views/main_window.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/main_window.py) | 主窗口 |
| `BasePresenter` | [desktop/presenters/base_presenter.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/presenters/base_presenter.py) | Presenter 基类 |
| `StyledTableWidget` | [desktop/views/components.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/components.py) | 统一表格组件 |
| `LoginDialog` | [security/auth.py](file:///d:/yuan/不锈钢网带跟单3.0/security/auth.py) | 登录对话框 |
| `WindowManager` | [utils/window_manager.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/window_manager.py) | 窗口管理 |
| `AutoRefreshMixin` | [utils/auto_refresh_mixin.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/auto_refresh_mixin.py) | 自动刷新混入 |

### 16.2 关键函数索引

| 函数名 | 文件路径 | 说明 |
|--------|---------|------|
| `load_env()` | [core/config.py](file:///d:/yuan/不锈钢网带跟单3.0/core/config.py) | 加载环境变量（叠加多文件） |
| `get_connection()` | [models/database/__init__.py](file:///d:/yuan/不锈钢网带跟单3.0/models/database/__init__.py) | 获取数据库连接 |
| `check_and_create_tables()` | [utils/auto_schema.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/auto_schema.py) | 自动创建缺失数据表 |
| `hash_password()` | [utils/password_hasher.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/password_hasher.py) | 密码加盐哈希 |
| `verify_password()` | [utils/password_hasher.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/password_hasher.py) | 密码哈希验证 |
| `generate_order_no()` | [utils/helpers.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/helpers.py) | 生成订单号 |

---

## 附录：设计模式运用

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **MVP (Passive View)** | desktop/views/ + desktop/presenters/ | View 只负责渲染，Presenter 负责业务调度 |
| **Service Layer** | services/ | 封装业务逻辑，供 Presenter 调用 |
| **Data Access Object (DAO)** | models/ | 数据访问抽象层 |
| **Observer / EventBus** | core/event_bus.py + core/events.py | 进程内事件驱动通信 |
| **Singleton** | core/event_bus.py (EventBus) | 全局唯一事件总线 |
| **Mixin** | utils/auto_refresh_mixin.py | 可混入的自动刷新功能 |
| **Strategy(变体)** | core/_config_ui.py → desktop/views/components.py | UI配置策略统一管理 |
| **Template Method** | models/base_dao.py, services/base_service.py | 模板方法定义通用流程 |
