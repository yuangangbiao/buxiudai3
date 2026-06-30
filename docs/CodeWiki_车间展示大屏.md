# 车间展示大屏 Code Wiki

## 一、项目概览

### 1.1 项目简介

**宁津晨圣输送机械有限公司 — 生产监控大屏（Dashboard）** 是一个实时生产数据可视化系统。运行于局域网内的大屏显示器上，用于车间管理人员实时掌握生产进度、订单状态、库存预警、发货记录等关键指标。

| 属性 | 值 |
|------|-----|
| 项目名称 | 生产监控大屏（Dashboard） |
| 技术栈 | Python Flask + Chart.js + MySQL |
| 当前版本 | V3（紧凑卡片版） |
| 默认端口 | 5007 |
| 历史版本 | V1（深蓝经典版）、V2（进度卡片版） |
| 数据库 | MySQL（steel_belt） |

### 1.2 核心功能

- **生产进度追踪** — 实时查看各工单生产进度百分比与工序详情
- **全局统计指标** — 总订单数、本月新增、生产中、待发货、逾期预警、完成率
- **订单状态分布** — 饼图展示各状态订单占比
- **预警中心** — 交期预警（逾期/即将到期）+ 库存不足告警
- **近期发货** — 最近发货记录列表
- **缺料预警** — 按物料合并的库存短缺显示
- **滚动信息条** — 关键指标滚动播报
- **自动刷新** — 每 20 秒自动从服务端拉取最新数据

---

## 二、项目目录结构

```
gbd3.0/
├── start_dashboard.py                          # [入口] 大屏启动脚本（桌面GUI启动器）
│
├── desktop/views/
│   └── dashboard/                              # 大屏模块（核心）
│       ├── __init__.py                         # 模块导出（空）
│       ├── dashboard_server.py                 # [核心] Flask API 服务器
│       ├── db_config.json                      # 数据库连接配置（用户可写）
│       └── templates/
│           ├── dashboard_v3.html               # [当前默认] V3 紧凑卡片版
│           ├── dashboard_v1.html               # V1 深蓝经典版
│           ├── dashboard_v2.html               # V2 进度卡片版
│           └── dashboard_config.html           # 大屏配置页（数据库配置/状态查看）
│
├── desktop/views/
│   └── dashboard_view.py                       # Tkinter 桌面视图（启动/停止/打开浏览器）
│
├── models/                                     # DAO 层（数据访问对象）
│   ├── order.py                                # OrderDAO - 订单维度查询
│   ├── production.py                           # ProductionDAO - 生产工单维度查询
│   ├── process.py                              # ProcessDAO - 工序维度查询
│   ├── inventory.py                            # InventoryDAO - 库存维度查询
│   ├── shipment.py                             # ShipmentDAO - 发货维度查询
│   └── alert.py                                # AlertDAO - 预警维度查询
│
├── constants.py                                # 枚举常量（状态定义）
├── config.py                                   # 全局配置
│
├── mobile_api_ai/
│   ├── container_dashboard.py                  # 容器中心可视化大屏（备用）
│   ├── templates/
│   │   ├── container_dashboard.html            # 容器大屏前端
│   │   └── reports_dashboard.html              # 报表大屏前端
│   └── inventory_web/templates/inventory/
│       └── dashboard.html                      # 库存管理仪表板
│
└── controllers/
    └── dashboard_controller.py                 # 独立看板控制器（备用 API）
```

---

## 三、系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          浏览器（大屏页面）                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  dashboard_v3.html (Chart.js 饼图 + DOM 操作)                  │  │
│  │  每隔 20s 轮询 /api/dashboard_data                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP GET
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Flask API Server (dashboard_server.py)                 │
│                                                                     │
│  GET /api/dashboard_data  ←── 聚合 8 个子查询                         │
│  GET /api/province_distribution                                     │
│  GET /api/health                                                    │
│  GET /api/status                                                    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ DAO 调用
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DAO 层 (models/)                              │
│                                                                     │
│  OrderDAO        ─── orders 表（统计/分布/预警）                      │
│  ProductionDAO   ─── production_orders 表（生产列表）                │
│  ProcessDAO      ─── process_records 表（工序进度）                  │
│  InventoryDAO    ─── inventory 表（库存/低库存预警）                  │
│  ShipmentDAO     ─── shipments 表（最近发货）                        │
│  AlertDAO        ─── 多表联合（综合预警）                             │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ MySQL
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MySQL Database (steel_belt)                   │
│   orders, production_orders, process_records,                        │
│   inventory, shipments, order_materials 等 50+ 表                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 分层说明

| 层 | 职责 | 技术 |
|----|------|------|
| **前端展示层** | 数据可视化、定时刷新、用户交互 | HTML5 + CSS3 + Chart.js + Vanilla JS |
| **API 服务层** | 聚合数据、路由分发、JSON 响应 | Flask |
| **DAO 数据层** | 数据库查询、数据封装 | MySQL + pymysql (DictCursor) |
| **存储层** | 数据持久化 | MySQL 8.0+ (InnoDB) |

### 数据流向

```
浏览器定时轮询 (20s)
    ↓
Flask /api/dashboard_data
    ↓
并行调用多个 DAO 方法（OrderDAO / ProductionDAO / ProcessDAO / ...）
    ↓
各 DAO 独立建立数据库连接、执行 SQL、返回 dict 列表
    ↓
dashboard_server.py 聚合所有数据为单一 JSON 响应
    ↓
前端 JavaScript 更新 DOM（数值动画、饼图、列表渲染）
```

---

## 四、核心模块详解

### 4.1 启动入口

#### `start_dashboard.py`

| 属性 | 说明 |
|------|------|
| 文件路径 | `d:\yuan\gbd3.0\start_dashboard.py` |
| 作用 | 大屏启动脚本，调用 `dashboard_view.py` 中的 `DashboardLauncherUI` 显示图形界面 |
| 启动方式 | `python start_dashboard.py` |

启动后弹出桌面窗口，提供：数据库配置、启动/停止服务器、打开大屏网页三个主要功能。

#### `dashboard_view.py`

| 属性 | 说明 |
|------|------|
| 文件路径 | `d:\yuan\gbd3.0\desktop\views\dashboard_view.py` |
| 关键类 | `DashboardLauncherUI` (Tkinter 窗口) |
| 功能 | 提供 GUI 界面：启动/停止 Flask 服务器、数据库设置、打开浏览器访问大屏 |

---

### 4.2 API 服务端（核心）

#### `dashboard_server.py`

| 属性 | 说明 |
|------|------|
| 路径 | `d:\yuan\gbd3.0\desktop\views\dashboard\dashboard_server.py` |
| 框架 | Flask |
| 默认端口 | 5007 |
| 模板目录 | `../templates/`（与 server.py 同级的 templates 目录） |

##### 生命周期

1. **启动时** → `_load_db_config_to_env()` 从 `db_config.json` 读取 MySQL 配置到环境变量
2. **初始化** → 导入 DAO 层（OrderDAO / ProductionDAO / ProcessDAO / InventoryDAO / ShipmentDAO）
3. **运行时** → Flask 路由分发请求，每个请求独立建立数据库连接
4. **停止时** → Flask 关闭，连接池释放

##### 配置加载机制

```python
def _load_db_config_to_env():
    # 1. 优先读取与 exe/server.py 同目录的 db_config.json
    # 2. 将 host/port/database/user/password 写入 os.environ
    # 3. 供 models.database.get_connection() 中的环境变量读取使用
```

配置来源优先级：db_config.json > 环境变量 > 默认值（localhost/root/空密码/steel_belt）

---

### 4.3 前端模板

#### dashboard_v3.html（当前默认版本）

| 属性 | 说明 |
|------|------|
| 样式 | 深色科技风主题、渐变背景、发光边框 |
| 布局 | 标题栏 → 滚动信息条 → 统计卡片(6宫格) → 主内容区（左:订单卡片 + 右:饼图/预警/发货/缺料） |
| 图表 | Chart.js doughnut 饼图（订单状态分布） |
| 刷新 | `setInterval(fetchData, 20000)` 每20秒轮询 |
| 动画 | requestAnimationFrame 实现数字滚动动画 |

**UI 布局结构：**

```
┌──────────────────────────────────────────────────────────────┐
│  宁津晨圣输送机械有限公司 · 生产监控大屏 V3        [时钟][日期] │  ← 标题栏
├──────────────────────────────────────────────────────────────┤
│  📋 总订单 N 单  🆕 本月新增 N 单  ⚙️ 生产中 N 单  ...         │  ← 滚动信息条
├──────────────────────────────────────────────────────────────┤
│ [📋总订单] [🆕本月新增] [⚙️生产中] [📦待发货] [🚨逾期] [✅完成率] │  ← 统计卡片
├───────────────────────────────────┬──────────────────────────┤
│                                   │  订单状态分布 (饼图)       │
│   生产进度追踪 (订单卡片网格)       ├──────────────────────────┤
│   ┌───────┐ ┌───────┐            │  🚨 预警中心              │
│   │订单A   │ │订单B   │            ├──────────────────────────┤
│   │进度80% │ │进度50% │            │  🚚 近期发货              │
│   │交期倒计│ │工序详情│            ├──────────────────────────┤
│   └───────┘ └───────┘            │  📦 缺料显示              │
└───────────────────────────────────┴──────────────────────────┘
│ 数据自动刷新中 (20秒)  最后更新: --:--  方案1 | 方案2 | 方案3  │  ← 底部
└──────────────────────────────────────────────────────────────┘
```

#### dashboard_v1.html（V1 深蓝经典版）

与 V3 结构类似，区别在于订单列表使用表格而非卡片网格、统计卡片为 4 宫格（不含完成率和逾期），更早期版本。

#### dashboard_v2.html（V2 进度卡片版）

与 V3 类似，同为 6 宫格统计卡片 + 生产进度追踪 + 右侧面板布局，中间版本过渡设计。

#### 三个版本对比

| 特性 | V1 | V2 | V3（当前默认） |
|------|:--:|:--:|:-------------:|
| 统计卡片 | 4 格 | 6 格 | 6 格 |
| 订单展示 | 表格列表 | 卡片网格 | 卡片网格 |
| 工序详情 | 无 | 有 | 有 |
| 饼图 | 有 | 有 | 有 |
| 预警中心 | 有 | 有 | 有 |
| 缺料合并 | 无 | 有 | 有 |
| 前端路由 | `/v1` | `/v2` | `/` 或 `/v3` |

---

### 4.4 配置页面

#### `dashboard_config.html`

| 属性 | 说明 |
|------|------|
| 路由 | `/config` |
| 功能 | 提供数据库连接测试、端口配置、服务状态查看的 Web 配置界面 |
| 样式 | 深色主题、紫色强调色 |

---

### 4.5 备用大屏

#### `container_dashboard.py`（容器中心大屏）

| 属性 | 说明 |
|------|------|
| 路径 | `d:\yuan\gbd3.0\mobile_api_ai\container_dashboard.py` |
| 蓝图 | `container_dashboard_bp` |
| 数据源 | 容器中心（ContainerCenter）的数据包 |
| 功能 | 实时监控数据流转、操作员工作量统计、告警规则管理 |
| API | `/api/stats`、`/api/trend`、`/api/distribution`、`/api/activities`、`/api/flow` 等 |

此大屏与主大屏数据源不同（容器中心 vs MySQL 订单系统），用于监控数据流转而非生产进度。

---

## 五、API 接口文档

### 5.1 主大屏 API（`dashboard_server.py`）

| 端点 | 方法 | 说明 | 返回格式 |
|------|------|------|---------|
| `/` | GET | 默认 V3 大屏页面 | HTML |
| `/v1` | GET | V1 深蓝经典版 | HTML |
| `/v2` | GET | V2 进度卡片版 | HTML |
| `/v3` | GET | V3 紧凑卡片版 | HTML |
| `/config` | GET | 配置管理页面 | HTML |
| `/api/dashboard_data` | GET | **核心** — 获取所有聚合数据 | JSON |
| `/api/province_distribution` | GET | 各省份订单分布 | JSON |
| `/api/health` | GET | 健康检查 | JSON |
| `/api/status` | GET | 服务运行状态 | JSON |

#### `/api/dashboard_data` 响应结构

```json
{
  "totalOrders": 152,           // 总订单数（排除已删除+归档）
  "monthlyNew": 12,             // 本月新增
  "statusDistribution": {       // 订单状态分布
    "待确认": 15,
    "生产中": 28,
    "待发货": 10,
    "已完成": 85,
    "已取消": 14
  },
  "completionRate": 55.9,       // 完成率 %
  "producingOrders": 28,        // 生产中订单数
  "readyToShip": 10,            // 待发货订单数
  "overdueOrders": 3,           // 逾期订单数
  "productionList": [           // 生产工单列表（最多20条）
    {
      "prod_id": 1,
      "order_no": "ORD20260601",
      "priority": 1,
      "priority_text": "🔴高",
      "customer_name": "客户A",
      "product_type": "不锈钢网带",
      "quantity": 100,
      "unit": "件",
      "status": "生产中",
      "specs": "网孔10mm / 丝径2mm / 宽1000mm",
      "progress": 80.0,
      "progress_text": "4/5 工序",
      "process_details": [
        {"name": "原材料准备", "progress": 100.0, "status": "已完成", ...},
        {"name": "焊接", "progress": 100.0, "status": "已完成", ...},
        {"name": "整形校直", "progress": 60.0, "status": "进行中", ...}
      ],
      "delivery_date": "2026年6月25日",
      "countdown": -2,
      "countdown_text": "逾期2天",
      "countdown_level": "overdue"
    }
  ],
  "orderList": [],               // 订单列表（v1兼容）
  "shortageList": [],            // 物料缺料列表
  "alerts": [                    // 预警列表
    {"level": "critical", "title": "🚨 订单逾期", "description": "订单ORD20260601已逾期2天", ...},
    {"level": "warning", "title": "⚠️ 即将到期", "description": "订单ORD20260605距到期仅剩3天", ...},
    {"level": "info", "title": "📦 库存不足", "description": "不锈钢丝当前库存50kg", ...}
  ],
  "recentShipments": [],         // 最近发货记录
  "inventory": [],               // 库存概览
  "inventoryWarnings": []        // 库存预警（按物料合并）
}
```

### 5.2 容器中心大屏 API（`container_dashboard.py`）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 容器中心仪表盘页面 |
| `/config` | GET | 配置管理标签页 |
| `/alert-rules` | GET | 告警规则标签页 |
| `/api/stats` | GET | 容器统计数据 |
| `/api/trend` | GET | 小时级趋势数据 |
| `/api/distribution` | GET | 数据类型分布 |
| `/api/activities` | GET | 最近活动记录 |
| `/api/flow` | GET | 任务流程数据（流程图） |
| `/api/container/operators` | GET | 操作员工作量统计 |
| `/api/container/flow/logs` | GET | 数据流转记录 |
| `/api/alert-rules` | GET/PUT | 告警规则配置 CRUD |

---

## 六、DAO 层详解

所有 DAO 类均为 **静态方法模式**（`@staticmethod`），每次调用独立创建连接、执行查询、关闭连接。

### 6.1 OrderDAO（`models/order.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_dashboard_order_stats()` | 获取全量统计（总订单/本月新增/状态分布/生产中/待发货/逾期/完成率） | 7 次查询 | orders |
| `get_delivery_alert_orders(days_ahead)` | 获取即将到期/逾期的订单 | 1 次查询 | orders |
| `get_dashboard_order_list(limit)` | 获取大屏订单列表（排除已完成/已取消） | 1 次查询 | orders |
| `get_province_data()` | 获取客户名称+地址原始数据 | 1 次查询 | orders |

### 6.2 ProductionDAO（`models/production.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_dashboard_production_list(limit)` | 获取生产工单列表（生产工单 LEFT JOIN 订单，筛选已排产/生产中/质检中/待发货） | 1 次查询 | production_orders + orders |

### 6.3 ProcessDAO（`models/process.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_by_production(production_id)` | 按生产ID获取所有工序记录（按顺序排列） | 1 次查询 | process_records |
| `get_progress(production_id)` | 计算某生产工单的完成百分比 | 1 次查询 | process_records |

### 6.4 InventoryDAO（`models/inventory.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_dashboard_overview()` | 获取所有物料库存概览 | 1 次查询 | inventory |
| `get_low_inventory_alerts(limit)` | 获取低库存告警（按缺料严重程度排序） | 1 次查询 | inventory |

### 6.5 ShipmentDAO（`models/shipment.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_recent_for_dashboard(limit)` | 获取最近发货记录（shipments LEFT JOIN orders） | 1 次查询 | shipments + orders |

### 6.6 AlertDAO（`models/alert.py`）

| 方法 | 说明 | SQL 复杂度 | 涉及表 |
|------|------|:---------:|--------|
| `get_low_inventory_alerts()` | 获取低于安全库存的物料预警 | 1 次查询 | inventory |
| `get_all_alerts(days)` | 聚合所有预警（逾期订单+低库存） | 2+ 次查询 | orders + inventory |

---

## 七、数据模型依赖关系

```
┌─────────────────────────────────────────────────────────────────────┐
│  核心业务表（orders 为中心）                                          │
│                                                                     │
│  orders ──── 1:N ──── production_orders                             │
│    │                      │                                          │
│    │                      └── 1:N ──── process_records              │
│    │                                                                 │
│    ├── 1:N ──── order_materials (物料需求/缺料)                       │
│    │                                                                 │
│    └── 1:N ──── shipments (发货记录)                                 │
│                                                                     │
│  inventory (独立库存表)                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 大屏涉及的表

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `orders` | 订单主表 | `id, order_no, customer_name, product_type, quantity, unit, status, delivery_date, is_deleted, is_archived, mesh_size, wire_diameter, width, length, surface_treatment` |
| `production_orders` | 生产工单 | `id, order_no, order_id, priority, status` |
| `process_records` | 工序记录 | `id, production_id, process_name, process_seq, status, planned_qty, completed_qty, qualified_qty, worker` |
| `order_materials` | 物料需求 | `id, order_id, material_name, required_qty, prepared_qty, prep_status, unit` |
| `inventory` | 库存 | `id, material_name, quantity, unit, warning_qty` |
| `shipments` | 发货 | `id, shipment_no, order_id, ship_quantity, unit, ship_date, status, logistics_company` |

---

## 八、关键函数与类说明

### 8.1 `dashboard_server.py`

| 函数 | 行号 | 类型 | 说明 |
|------|:----:|:----:|------|
| `_get_user_dir()` | 40 | 辅助 | 获取用户可写目录（PyInstaller 打包后的 exe 目录或源码目录） |
| `_load_db_config_to_env()` | 47 | 辅助 | 从 `db_config.json` 加载 MySQL 配置到环境变量 |
| `row_to_dict(row)` | 87 | 辅助 | 将 cursor 返回的 row 转为 dict |
| `format_cn_date(dt)` | 94 | 辅助 | 将日期格式化为中文显示（"2026年5月5日"） |
| `index()` | 126 | 路由 | 默认路由 → V3 大屏 |
| `index_v1()` | 131 | 路由 | `/v1` → V1 大屏 |
| `index_v2()` | 136 | 路由 | `/v2` → V2 大屏 |
| `index_v3()` | 141 | 路由 | `/v3` → V3 大屏 |
| `show_config()` | 146 | 路由 | `/config` → 配置页 |
| `api_health()` | 152 | 路由 | `/api/health` 健康检查 |
| `get_dashboard_data()` | 163 | **核心** | `/api/dashboard_data` — 聚合 8 个子查询，构建完整响应 |
| `get_province_distribution()` | 434 | 路由 | `/api/province_distribution` — 从客户地址提取省份统计 |

### 8.2 `dashboard_view.py`

| 类/函数 | 说明 |
|---------|------|
| `DashboardLauncherUI` | Tkinter GUI 类，提供启动/停止服务器、数据库配置、打开浏览器功能 |

### 8.3 `container_dashboard.py`

| 函数 | 说明 |
|------|------|
| `get_container_center()` | 延迟获取容器中心实例（支持从不同模块导入） |
| `get_container_stats()` | 按状态统计容器数据包数量 |
| `get_hourly_trend(hours)` | 获取小时级趋势数据（创建/完成量） |
| `get_data_type_distribution()` | 获取数据类型分布统计 |
| `get_recent_activities(limit)` | 获取最近活动记录 |
| `_get_cached_packages(cc, ttl)` | 缓存容器数据包（TTL=5秒） |
| `invalidate_cache()` | 手动清除缓存 |

---

## 九、环境变量与配置

### 9.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_HOST` | 数据库主机 | `localhost` |
| `MYSQL_PORT` | 数据库端口 | `3306` |
| `MYSQL_DATABASE` | 数据库名称 | `steel_belt` |
| `MYSQL_USER` | 数据库用户名 | `root` |
| `MYSQL_PASSWORD` | 数据库密码 | （无默认值） |
| `PORT` | 大屏服务端口 | `5007` |

### 9.2 数据库配置文件（`db_config.json`）

```json
{
    "host": "localhost",
    "port": 3306,
    "database": "steel_belt",
    "user": "root",
    "password": ""
}
```

配置文件保存在 `dashboard_server.py` 同目录下，通过 GUI 的「数据库设置」功能写入。

---

## 十、运行方式

### 10.1 源码运行

**方式一：桌面启动器（推荐）**

```bash
cd d:\yuan\gbd3.0
python start_dashboard.py
```

启动后弹出 Tkinter 窗口，按以下步骤操作：
1. 点击「**数据库设置**」配置 MySQL 连接
2. 点击「**启动服务器**」启动 Flask 服务（默认端口 5007）
3. 点击「**打开大屏网页**」在浏览器中查看

**方式二：直接启动服务器**

```bash
cd d:\yuan\gbd3.0
python desktop/views/dashboard/dashboard_server.py
```

启动后控制台输出访问地址：
- 本机: `http://localhost:5007`
- 局域网: `http://192.168.x.x:5007`
- 在浏览器中打开即可查看大屏（默认 V3 版本）

### 10.2 打包运行

打包后的 EXE 位于 `d:\yuan\gbd3.0\dist_dashboard_new\大屏独立启动器.exe`，双击运行即可。

---

## 十一、依赖清单

| 依赖 | 用途 |
|------|------|
| **Flask** | Web 框架 |
| **PyMySQL** | MySQL 数据库驱动 |
| **Chart.js** (CDN) | 前端图表库（饼图） |
| **Tkinter** | 桌面启动器 GUI（Python 内置） |
| **webbrowser** | 打开浏览器（Python 内置） |
| **socket** | 获取本机 IP（Python 内置） |
| **pystray** (可选) | 系统托盘支持（未安装时可正常运行） |
| **Pillow** (可选) | 托盘图标（未安装时可正常运行） |

---

## 十二、代码规范与约定

### 12.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 函数 | snake_case | `get_dashboard_data()` |
| 类 | PascalCase | `OrderDAO`、`DashboardLauncherUI` |
| 常量 | UPPER_SNAKE_CASE | `OrderStatus.PRODUCTION.value` |
| 路由 | 小写+下划线 | `/api/dashboard_data` |

### 12.2 数据库连接模式

所有 DAO 方法使用统一的连接模式：

```python
@staticmethod
def some_query(param):
    conn = get_connection()      # 创建连接
    try:
        cursor = conn.cursor()   # 获取游标（默认 DictCursor）
        cursor.execute("SQL...", (param,))
        rows = cursor.fetchall() # 获取结果
        cursor.close()           # 关闭游标
        return [dict(r) for r in rows]  # 转为 dict 列表
    finally:
        conn.close()             # 确保连接关闭
```

### 12.3 异常处理模式

API 层统一使用 try-except 包裹，异常时返回默认空数据：

```python
try:
    # 业务逻辑
    return jsonify(data)
except Exception as e:
    import traceback
    traceback.print_exc()
    return jsonify({...默认值...}), 500
```

---

## 十三、容器中心大屏（备用）

### 13.1 定位

`container_dashboard.py` 是一个独立的大屏模块，用于监控容器中心（ContainerCenter）的数据流转状态。与主大屏（`dashboard_server.py`）的数据源不同，它基于容器数据包而非 MySQL 订单表。

### 13.2 缓存机制

```python
_cache_timestamp = 0      # 上次缓存时间
_cache_ttl = 5             # 缓存有效期（秒）
_cache_lock = threading.Lock()  # 线程安全锁
```

- 每个 API 调用通过 `_get_cached_packages()` 获取缓存数据
- 缓存 5 秒自动失效
- 数据变更时调用 `invalidate_cache()` 手动清除缓存

### 13.3 API 端点

| 端点 | 说明 | 数据来源 |
|------|------|---------|
| `/api/stats` | 按状态统计 | `get_container_stats()` |
| `/api/trend` | 小时级趋势 | `get_hourly_trend()` |
| `/api/distribution` | 数据类型分布 | `get_data_type_distribution()` |
| `/api/activities` | 最近活动 | `get_recent_activities()` |
| `/api/flow` | 流程节点数据 | `api_container_flow()` |
| `/api/container/operators` | 操作员工作量 | `api_container_operators()` |
| `/api/container/flow/logs` | 数据流转日志 | `api_data_flow_logs()` |

---

## 十四、常见问题 FAQ

### Q1: 打开大屏看不到数据？

- 检查 `db_config.json` 中的数据库配置是否正确
- 确认 MySQL 服务是否运行，端口是否可达
- 检查浏览器控制台是否有网络错误（F12 → Console）
- 确认 `orders` 表中有未删除、未归档的订单数据

### Q2: 如何切换大屏版本？

访问不同 URL：
- V1：`http://localhost:5007/v1`
- V2：`http://localhost:5007/v2`
- V3（最新）：`http://localhost:5007/` 或 `http://localhost:5007/v3`

底部状态栏也有版本切换链接。

### Q3: 修改刷新频率？

编辑 `dashboard_v3.html` 中的：
```javascript
setInterval(fetchData, 20000);  // 20000ms = 20秒，修改为所需毫秒数
```

### Q4: 数据库表结构变更后大屏不显示？

大屏依赖的字段（如 `mesh_size`, `wire_diameter` 等）必须存在于 `orders` 表中。如需同步字段结构，可使用 `database_field_sync.py` 工具。
