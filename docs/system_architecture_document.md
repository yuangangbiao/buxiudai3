# 不锈钢自动跟单系统整体架构文档

> **文档版本**: v2.0 | **最后更新**: 2026-05-19 | **适用范围**: 全系统架构参考
> **变更责任人**: 系统架构组 | **更新频率**: 架构重大变更时同步更新

---

## 一、文档管理规范

### 1.1 版本管理

| 版本 | 日期 | 变更说明 | 责任人 |
|------|------|---------|--------|
| v1.0 | 2026-05-18 | 初始版本，覆盖7大模块概览 | 系统架构组 |
| v2.0 | 2026-05-19 | 全面扩展：新增配置中心/蓝图/增强模块/告警/业务常量/部署架构/数据库ER等章节 | 系统架构组 |

### 1.2 更新规范

- **重大架构变更**（新增/删除模块、数据库重构、通信方式变更）：必须更新本文档，更新版本号次版本+1
- **接口变更**（API路由增删改、配置字段变更）：更新对应章节，更新文档尾部修订记录
- **业务常量变更**（材质密度、工序、产品类型等）：更新[第十一章](#十一核心业务常量-coreconfigpy)
- 每次更新需填写版本表中的变更说明和日期

### 1.3 文档定位

本文档是不锈钢自动跟单系统的**核心架构参考文档**，覆盖：
- 系统整体架构与模块划分
- 各模块内部详细设计
- 数据流与业务逻辑
- 配置体系与部署架构
- 业务常量与技术栈

---

## 二、系统概述

不锈钢自动跟单系统是一套集生产跟单、调度分发、微信交互、移动报工、人脸考勤、表格自动化于一体的综合性制造执行系统（MES）。系统采用 **主软件桌面应用 + 微服务集群** 混合架构，以 Flask 为 Web 框架，MySQL + SQLite 为双存储引擎，企业微信为主要消息通道。

### 系统架构总览

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   不锈钢自动跟单系统整体架构 (v2.0)                                     │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        主软件 v3.01 (Tkinter Desktop App)                                      │   │
│  │                        d:\yuan\不锈钢网带跟单系统3.01\                                          │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │   │
│  │  │ main.py │→│ core/    │→│ services/│→│ models/  │→│ views/   │                         │   │
│  │  │ 入口     │  │ 核心框架  │  │ 服务层    │  │ DAO层    │  │ UI层     │                         │   │
│  │  └─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘                         │   │
│  │  核心功能:                                                                                     │   │
│  │   ├── 订单管理 | 订单录入/编辑/查询/跟单状态流转(9种状态)                                        │   │
│  │   ├── 生产工单 | 排产/发布/报工/进度追踪/17个工序管理                                            │   │
│  │   ├── 物料计算 | MaterialCalculator引擎(白名单公式解析器)                                        │   │
│  │   ├── 排产调度 | ScheduleDispatchService(本地队列→容器中心→调度中心→云端→企微)                   │   │
│  │   ├── 微信报工 | WeChatReportService(回调幂等回写MySQL)                                         │   │
│  │   ├── 事件驱动 | EventBus(6种事件类型,发布/订阅模式)                                             │   │
│  │   ├── 审计日志 | AuditService                                   │   │
│  │   └── 许可证   | security/机器指纹+许可证绑定                                                   │   │
│  └──────────────────────────────────┬───────────────────────────────────────────────────────────┘   │
│                                     │                                                                │
│                                     ▼                                                                │
│                    ┌────────────────────────────────────────────────────┐                            │
│                    │         MySQL / SQLite 双数据库架构                  │                            │
│                    │  MySQL: orders / production_orders / process_records│                            │
│                    │         process_calc_rules / material_rules         │                            │
│                    │         schedule_queue / wechat_callback_log         │                            │
│                    │  SQLite: app.db (本地容器/缓存)                      │                            │
│                    └───────────────────────┬────────────────────────────┘                            │
│                                            │                                                         │
│                ┌───────────────────────────┼───────────────────────────────┐                         │
│                ▼                           ▼                               ▼                         │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐                 │
│  │   容器中心 v5            │  │   调度中心               │  │   配置中心               │                 │
│  │   container_center_v5   │  │   dispatch_center.py   │  │   config_center.py     │                 │
│  │   (数据中转+存储抽象层)    │  │   (任务看板+流程引擎)    │  │   (8大配置分类可视化)     │                 │
│  │   storage_layer(4127行) │  │   (5783行)             │  │   (461行)              │                 │
│  │   SQLite/Redis双后端     │  │                         │  │   .env文件管理           │                 │
│  └────────────────────────┘  └────────────────────────┘  └────────────────────────┘                 │
│                                                                                                      │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐                 │
│  │   云端微信 Cloud         │  │   企业微信机器人         │  │   增强模块集             │                 │
│  │   wechat_cloud.py      │  │   standalone_dispatch_server │  │   enhanced_modules.py │
│  │   (公网回调接收)         │  │   (内网指令处理)         │  │   (7大组件:CB/QM/HC/    │                 │
│  │   cloud_poller.py      │  │   cloud_matching.py    │  │    DM/AL/BM/CS)        │                 │
│  │   云端-本地双轨架构       │  │   (32种命令类型)         │  │   客户端/服务端双模式    │                 │
│  └────────────────────────┘  └────────────────────────┘  └────────────────────────┘                 │
│                                                                                                      │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐                 │
│  │   人脸识别考勤系统        │  │   移动报工API           │  │   表格机器人             │                 │
│  │   face-liveness-demo   │  │   mobile_api/          │  │   table-bot/app.py    │                 │
│  │   TF.js(BlazeFace+     │  │   scan/process/quality │  │   企微回调服务器         │                 │
│  │   FaceMesh 468点+活体)  │  │   扫码报工+质检         │  │   表格命令解析           │                 │
│  │   FastAPI+SQLite        │  │                         │  │                       │                 │
│  └────────────────────────┘  └────────────────────────┘  └────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 端口与网络架构

```
┌────────────── 公网 ──────────────┬────────────── 内网 ──────────────────┐
│                                   │                                      │
│  企业微信服务器                     │  后端微服务集群 (mobile_api_ai/)       │
│  (回调消息)                        │  ├── standalone_dispatch_server.py :5003   │
│       │                           │  ├── container_center_api :5002      │
│       ▼                           │  ├── inventory_api_server :5010      │
│  ┌─────────────────┐              │  ├── 人脸考勤 server.py :8000        │
│  │ wechat_cloud.py  │──cloud────▶│  └── table-bot app.py :5004          │
│  │ (云端接收层)      │◀──poller──│                                      │
│  └─────────────────┘              │  主软件桌面应用                        │
│                                   │  d:\yuan\不锈钢网带跟单系统3.01\       │
│                                   │  main.py → MySQL/SQLite             │
└───────────────────────────────────┴──────────────────────────────────────┘
```

---

## 三、各模块详细架构

### 3.1 主软件 v3.01 (Main Desktop App)

**路径**：`d:\yuan\不锈钢网带跟单系统3.01\`

#### 架构模式：MVC + Service Layer + EventBus

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       主软件 v3.01 分层架构                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  入口层                                                                   │
│  main.py - 主入口（许可证检查/模块懒加载/异步升级/全局异常处理）               │
├──────────────────────────────────────────────────────────────────────────┤
│  核心框架 core/                                                           │
│  ├── app.py           - 应用初始化（数据库/事件总线/审计日志）                │
│  ├── config.py        - 统一配置管理（路径/数据库/业务参数/样式/布局/颜色）    │
│  │                     含9种材质密度/34个尺寸参数/13种产品类型/17个工序等     │
│  ├── database.py      - DatabaseManager单例（MySQL/SQLite双库切换）        │
│  ├── event_bus.py     - 事件总线（6种事件类型，发布/订阅模式）               │
│  ├── exceptions.py    - 统一异常体系                                       │
│  ├── error_handler.py - 错误处理                                           │
│  └── logger.py        - 日志模块                                           │
├──────────────────────────────────────────────────────────────────────────┤
│  服务层 services/                                                         │
│  ├── order_service.py              - 订单服务（创建/更新/9种状态流转）       │
│  ├── schedule_dispatch_service.py  - 排产调度（本地队列→容器中心→调度中心）  │
│  ├── wechat_report_service.py      - 微信报工（回调数据幂等回写MySQL）       │
│  ├── audit_service.py              - 审计日志服务                          │
│  └── inventory_notifier.py         - 库存通知服务                          │
├──────────────────────────────────────────────────────────────────────────┤
│  数据访问层 models/ (DAO)                                                  │
│  ├── database.py           - 数据库连接函数（get_connection/generate_order_no）│
│  ├── order.py              - 订单DAO（FIXED_ORDER_KEYS + extra_params）    │
│  ├── process.py            - 工序DAO（状态推进/全部完成检查）                 │
│  ├── production.py         - 生产工单DAO                                   │
│  ├── quality.py            - 质检DAO                                       │
│  ├── process_calc_rule.py  - 工序计算规则DAO                               │
│  ├── material_rules.py     - 物料计算规则DAO                               │
│  ├── operator.py           - 操作员DAO                                     │
│  ├── shipment.py           - 发货DAO                                       │
│  ├── bom.py                - BOM物料清单DAO                                │
│  ├── alert.py              - 告警DAO                                       │
│  ├── product_type.py       - 产品类型DAO                                   │
│  ├── quality_rule.py       - 质检规则DAO                                   │
│  ├── inventory.py          - 库存DAO                                       │
│  └── unit.py               - 单位DAO                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  工具层 utils/                                                            │
│  ├── material_calculator.py - 物料计算引擎（安全公式解析器）                  │
│  ├── validators.py          - 订单校验器                                   │
│  ├── helpers.py             - 通用助手函数                                  │
│  ├── op_logger.py           - UI操作日志                                   │
│  ├── window_manager.py      - 窗口管理器                                   │
│  └── material_templates.py  - 物料模板                                     │
├──────────────────────────────────────────────────────────────────────────┤
│  安全层 security/                                                         │
│  ├── license_manager.py    - 许可证管理                                   │
│  ├── machine_fingerprint.py - 机器指纹                                    │
│  └── license_binding.py    - 许可证绑定                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  视图层 views/ (Tkinter界面)                                               │
│  控制器层 controllers/                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 核心数据模型

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `orders` | 订单主表 | order_no, customer_name, product_type, material, 尺寸参数(多字段), quantity, unit_price, total_amount, status(9种), extra_params(JSON) |
| `production_orders` | 生产工单 | order_no, order_id, quantity, status(待发布/已发布/生产中/已完成), plan_start, plan_end, actual_end |
| `process_records` | 工序记录 | production_id, process_name, planned_qty, completed_qty, qualified_qty, status, worker, start_time, end_time |
| `process_calc_rules` | 工序计算规则 | product_types_json, planned_qty_formula(数学表达式), priority, unit |
| `material_rules` | 物料计算规则 | product_type, material_name_template, spec_field, qty_formula |
| `schedule_queue` | 排产队列 | order_no, order_data(JSON), status(pending/sending/success/failed) |
| `wechat_callback_log` | 微信回调日志 | order_no, process_name, status, operator, received_at |

#### 运算逻辑

**订单金额计算**（[order.py](file:///d:/yuan/不锈钢网带跟单系统3.01/models/order.py)）：
```
总金额 = 单价 × 数量
非固定字段 → 序列化为JSON → 存入 extra_params 字段
```

**物料计算引擎**（[material_calculator.py](file:///d:/yuan/不锈钢网带跟单系统3.01/utils/material_calculator.py)）：
```
公式解析流程：
  formula = data['qty_formula'] (如 "width * length / 1000")
  → 替换中文符号(×→* ÷→/)  → 字符白名单校验
  → tokenize() 词法分析（数字+运算符拆分）
  → evaluate() 逆波兰表达式求值
  → 返回计算结果

白名单字符: "0123456789.+-*/() "
安全运算符: +, -, *, /
校验: 所有非法字符 → 抛出 ValueError
```

**工序计划数量计算**（[process_calc_rule.py](file:///d:/yuan/不锈钢网带跟单系统3.01/models/process_calc_rule.py)）：
```
每个工序可配置生效条件（产品类型列表）+ 计划数量公式（尺寸参数表达式）
计算时：匹配产品类型 → 代入尺寸参数 → 执行数学表达式 → 获得计划数量
```

**工序完成推进逻辑**（[process.py](file:///d:/yuan/不锈钢网带跟单系统3.01/models/process.py)）：
```
工序报工完成 → 检查所有工序是否完成 → 全部完成则自动更新工单状态为"已完成"
→ 自动更新订单状态为"质检中" → 记录状态变更日志(log_status_change)

自动时间记录：
  第一次报工时: start_time = NOW()
  工序完成时: end_time = NOW()
  全部完成时: production_orders.actual_end = NOW()
```

**排产调度流程**（[schedule_dispatch_service.py](file:///d:/yuan/不锈钢网带跟单系统3.01/services/schedule_dispatch_service.py)）：
```
主软件"确认发布" → 写入本地 schedule_queue 表(防重复校验)
↓ 后台线程轮询(5秒间隔, 批量5条)
写入容器中心 → 调度中心 → 云端 → 企业微信
↓
操作员确认 → 云端 → 调度中心 → 容器中心
↓
容器中心回调主软件API → 标记已排产

防重复规则：
  - 同工单号 status=success → 拒绝（已成功发送）
  - 同工单号 status=pending/sending → 拒绝（已在队列中）
  - 同工单号 status=failed → 复用记录，重置为pending
```

**微信报工回写**（[wechat_report_service.py](file:///d:/yuan/不锈钢网带跟单系统3.01/services/wechat_report_service.py)）：
```
接收回调数据(order_no, order_no, process_name, status, operator)
→ 校验必填字段
→ 直接写入MySQL(process_records更新)
→ 记录回调日志(wechat_callback_log)
→ 记录状态变更历史(process_status_history)
→ 保证幂等性(重复回调不重复更新)
```

**订单状态流转**（[order_service.py](file:///d:/yuan/不锈钢网带跟单系统3.01/services/order_service.py)）：

```
                        ┌──────────┐
                        │  待确认    │
                        └────┬─────┘
                     ┌───────┼──────────┐
                     ▼       ▼          ▼
                ┌────────┐ ┌──────┐ ┌──────┐
                │ 待排产   │ │已取消 │ │(编辑)│
                └────┬───┘ └──────┘ └──────┘
                     ▼
                ┌────────┐
                │ 待发布   │
                └────┬───┘
                     ▼
                ┌────────┐
                │ 已发布   │
                └────┬───┘
                     ▼
                ┌────────┐
                │ 已排产   │
                └────┬───┘
                     ▼
                ┌────────┐
                │ 生产中   │
                └────┬───┘
                     ▼
                ┌────────┐      ┌────────┐
                │ 质检中   │◀────│生产中   │
                └────┬───┘      (退回)   │
              ┌──────┼──────┐   └────────┘
              ▼      ▼      ▼
          ┌──────┐ ┌──────┐ ┌──────┐
          │待发货 │ │已完成 │ │生产中 │
          └──┬───┘ └──────┘ │(退回) │
             ▼              └──────┘
          ┌──────┐
          │已发货 │
          └──┬───┘
             ▼
          ┌──────┐
          │已完成 │
          └──────┘
```

**EventBus 事件驱动**（[event_bus.py](file:///d:/yuan/不锈钢网带跟单系统3.01/core/event_bus.py)）：
```
事件类型(6种):
  - APP_STARTED           - 应用启动完成
  - ORDER_CREATED         - 订单创建
  - ORDER_UPDATED         - 订单更新
  - ORDER_STATUS_CHANGED  - 订单状态变更
  - PRODUCTION_STARTED    - 生产开始
  - PRODUCTION_COMPLETED  - 生产完成
  - PROCESS_REPORTED      - 工序报工

事件流程: OrderService.create_order() → 发布 Events.ORDER_CREATED
        → 注册的事件处理函数异步执行
        → 审计日志/通知/状态同步
```

---

### 3.2 容器中心 v5 (Container Center)

#### 位置
- 核心：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_v5.py`（1323行）
- API：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_api.py`（2135行）
- 存储层：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\storage_layer.py`（4127行）
- 客户端：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_client.py`（968行）

#### 架构设计

```
┌──────────────────────────────────────────────────────┐
│                   容器中心 v5                          │
├──────────────────────────────────────────────────────┤
│  ContainerCenter (核心类)                              │
│  ├── 数据包管理: collect_report / distribute           │
│  ├── 存储抽象层: BaseStorage (Mixin 组合)                │
│  │   ├── ConnectionMixin        - 连接管理             │
│  │   ├── PackageStorageMixin    - 数据包增删改查        │
│  │   ├── SyncLogMixin           - 同步日志             │
│  │   ├── HealthMixin            - 健康检查             │
│  │   ├── DispatchStorageMixin   - 调度存储             │
│  │   ├── DataFlowStorageMixin   - 数据流记录           │
│  │   ├── ProcessStorageMixin    - 流程存储             │
│  │   └── ScheduleFlowMixin      - 排产流程             │
│  ├── 推送回调机制: push_callbacks                       │
│  ├── 分发策略: direct / round_robin / least_busy       │
│  │   - direct(直连): 直接指定操作员                     │
│  │   - round_robin(轮询): 按操作员列表轮流分配           │
│  │   - least_busy(最少任务): 分配任务数最少的操作员      │
│  └── MySQL同步: 中转模式下自动同步到MySQL               │
├──────────────────────────────────────────────────────┤
│  存储后端 (可切换)                                      │
│  ├── SQLite (默认, container_center.db)               │
│  └── Redis (可选, 需安装 redis 库)                     │
└──────────────────────────────────────────────────────┘
```

#### 数据类型枚举

```python
class DataType(Enum):
    REPORT = 'report'      # 报工数据
    QUALITY = 'quality'    # 质检数据
    MATERIAL = 'material'  # 物料数据
    APPROVAL = 'approval'  # 审批数据
    ORDER = 'order'        # 订单数据
    PROCESS = 'process'    # 工序数据
    COST = 'cost'          # 成本数据

class DataStatus(Enum):
    PENDING = 'pending'           # 待处理
    DISTRIBUTED = 'distributed'   # 已分发
    ACKNOWLEDGED = 'acknowledged' # 已确认
    COMPLETED = 'completed'       # 已完成
    EXPIRED = 'expired'           # 已过期
    CANCELLED = 'cancelled'       # 已取消
```

#### 数据包生命周期

```
创建(collect_report) → 保存(save_package) → 分发(distribute)
→ 下发调度指令(save_dispatch_command) → 状态更新(ack/reject/complete)
→ 同步到MySQL → 归档
```

#### MySQL状态映射

```
STATUS_KEY_TO_MYSQL = {
    'published': '已发布',   'scheduled': '已排产',
    'confirmed': '已排产',   'in_production': '生产中',
    'reported': '质检中',    'qc_passed': '质检通过',
    'completed': '已完成',
}
```

#### 容器中心客户端保护模块 ([container_center_client.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_client.py))

客户端集成7个保护模块，统一管理所有对容器中心API的HTTP调用：

| 模块 | 类/组件 | 配置参数 | 功能 |
|------|---------|---------|------|
| 熔断器 | CircuitBreaker | failure_threshold=10, success_threshold=3, failure_rate=0.5, open_timeout=30s, recovery_timeout=60s | API调用熔断保护，防止雪崩 |
| 签名认证 | EnhancedAPISignature | secret_key(从环境变量读取) | 请求签名认证，防篡改 |
| 队列缓冲 | QueueManager | redis_client(可选), default_max_size=500 | 服务不可用时消息缓冲，异步重试 |
| 时钟同步 | ClockSync | 全局单例 global_clock_sync | 请求时间戳同步，防重放攻击 |
| 数据完整性 | DataIntegrity | SHA256 checksum | 请求载荷校验，确保数据传输完整 |
| 健康检查 | HealthChecker | 向 /health 端点探测 | 容器中心健康探测，自动切换 |
| 部署管理 | DeploymentManager | backup_dir/config_dir/deploy_dir | 配置版本管理，灰度发布 |

**核心方法**：
```
publish_task(data_type, title, content, operator_id, ...) → 发布任务
get_package_status(package_id) → 查询任务状态
get_pending_tasks(operator_id) → 获取待处理任务
acknowledge_task(package_id, operator_id) → 确认任务
complete_task(package_id, operator_id, result_data) → 完成任务
health_check() → 健康探测
login(operator_id) → JWT认证登录
```

---

### 3.3 调度中心 (Dispatch Center)

#### 位置
- 核心：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center.py`（5783行）
- 数据文件：`dispatch_center_data.json`

#### 职责
- 任务调度看板：任务分配/转派/取消、负载均衡
- 消息调度中心：企业微信消息发送、模板管理
- 流程调度引擎：排产-物料-采购-审批流程编排
- 监控看板：全局状态、告警、统计
- 文档服务API：架构文档在线访问

#### API 路由概览

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 调度中心主页面 |
| `/status` | GET | 全局状态统计 |
| `/tasks` | GET | 任务列表（支持分页/状态/操作员过滤） |
| `/tasks/<id>/assign` | POST | 分配任务 |
| `/tasks/<id>/reassign` | POST | 转派任务 |
| `/tasks/<id>/cancel` | POST | 取消任务 |
| `/tasks/batch-assign` | POST | 批量分配 |
| `/operators` | GET/POST | 操作员管理 |
| `/operators/<id>` | PUT/DELETE | 操作员更新/删除 |
| `/process-tasks` | GET | 流程任务列表 |
| `/process-tasks/<id>` | DELETE | 删除流程任务 |
| `/templates` | GET/POST | 消息模板管理 |
| `/messages/templates` | * | 消息模板 CRUD |
| `/messages/templates/variables` | GET | 模板变量提取 |
| `/global-config` | GET/PUT | 全局配置 |
| `/flow-matching-rules` | GET/POST | 流程匹配规则 |
| `/departments` | GET | 部门列表 |
| `/feedback` | GET/POST/DELETE | 反馈管理 |
| `/repairs` | GET/POST/DELETE | 报修管理 |
| `/cloud/config` | GET/POST | 云端配置 |
| `/wechat/sync` | POST | 企业微信通讯录同步 |
| `/server/python-path` | GET | Python路径配置 |
| `/documents` | GET | 文档索引列表 |
| `/documents/<id>` | GET | 文档内容 |

#### 状态映射规则
```
published → 已发布     scheduled → 已排产
confirmed → 已排产     in_production → 生产中
reported → 质检中      qc_passed → 质检通过
completed → 已完成
```

#### 缓存策略
- `_customer_group_cache`: 字典缓存客户群信息，避免重复查询MySQL
- `DispatchContext`: 单例上下文，管理 ContainerCenter 连接和工单缓存
  - work_order_cache: TTL 10s
  - operator_cache: TTL 60s
- `_dispatch_cache`: JSON 文件持久化缓存

#### 流程推进逻辑
```
接收质检完成事件(on_quality_record_completed)
→ 查找流程定义
→ 根据 flow_template 定义的 steps 推进 current_step
→ 记录完成人和完成时间
→ 异步同步到容器中心和 MySQL
→ 发送企业微信通知
```

---

### 3.4 云端微信模板 (Cloud WeChat)

#### 相关文件
- `wechat_cloud.py` - 云端服务（回调接收 + 消息队列 + 主动发送）（1227行）
- `standalone_dispatch_server.py` - 企业微信应用机器人服务器（主服务，整合了原 wechat_server.py 功能）
- `cloud_matching.py` - 指令匹配引擎（32种命令类型）
- `cloud_poller.py` - 云端轮询模块

#### 架构设计

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  企业微信服务器  │────▶│  wechat_cloud.py  │────▶│  cloud_poller.py │
│  (回调)        │◀────│  (云端中转)        │◀────│  (轮询获取消息)   │
└──────────────┘     └───────┬──────────┘     └─────────────────┘
                             │
                             ▼
                ┌──────────────────────────────────┐
                │  standalone_dispatch_server.py      │
                │  (企业微信应用机器人主服务)          │
                │  ├── 消息解密(WXBizMsgCrypt)       │
                │  ├── 消息解析(XML → 命令)          │
                │  ├── 指令匹配(cloud_matching)      │
                │  │   ├── CommandType: 32种命令类型  │
                │  │   ├── MatchMethod: PREFIX/      │
                │  │   │              FORMAT/NONE    │
                │  │   └── PREFIX_COMMANDS:          │
                │  │       "报","工序完成","订单完成"  │
                │  └── 响应发送(JSON → 企业微信)      │
                └──────────────────────────────────┘
```

#### 指令匹配引擎 ([cloud_matching.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/cloud_matching.py))

```python
class CommandType(Enum):
    # 报工类
    REPORT_PRODUCTION = 'report_production'       # 报工
    PROCESS_COMPLETE = 'process_complete'          # 工序完成
    ORDER_COMPLETE = 'order_complete'              # 订单完成
    # 查询类
    QUERY_ORDER = 'query_order'                    # 查询订单
    QUERY_PROCESS = 'query_process'                # 查询工序
    QUERY_QUALITY = 'query_quality'                # 质检查询
    QUERY_INVENTORY = 'query_inventory'            # 库存查询
    QUERY_SCHEDULE = 'query_schedule'              # 排产查询
    QUERY_MATERIAL = 'query_material'              # 物料查询
    QUERY_PROGRESS = 'query_progress'              # 进度查询
    # 排产类
    SCHEDULE_ORDER = 'schedule_order'              # 排产
    DISPATCH_TASK = 'dispatch_task'                # 调度
    # 物料类
    MATERIAL_REQUEST = 'material_request'          # 领料申请
    MATERIAL_RETURN = 'material_return'            # 退料
    # 质检类
    QUALITY_CHECK = 'quality_check'                # 质检
    QUALITY_ISSUE = 'quality_issue'                # 质量问题
    # 管理类
    ADD_OPERATOR = 'add_operator'                  # 添加操作员
    REMOVE_OPERATOR = 'remove_operator'            # 删除操作员
    LIST_OPERATORS = 'list_operators'              # 列出操作员
    SYSTEM_STATUS = 'system_status'                # 系统状态
    HELP = 'help'                                  # 帮助
    # 外协类
    OUTSOURC_REQUEST = 'outsourc_request'          # 外协申请
    OUTSOURC_STATUS = 'outsourc_status'            # 外协状态
    # ... 共32种命令类型

class MatchMethod(Enum):
    PREFIX = 'prefix'  # 前缀匹配: "报" → REPORT_PRODUCTION
    FORMAT = 'format'  # 格式匹配: 严格格式校验
    NONE = 'none'      # 无匹配
```

#### 消息架构
```
企业微信消息 → XML解密(standalone_dispatch_server) → 消息解析 → 指令匹配
→ 命令分发 → 业务处理 → 响应组装 → XML加密 → 返回企业微信
```

---

### 3.5 扫描包工模块 (Scan Work-Contracting)

#### 位置
- `d:\yuan\不锈钢网带跟单3.0\mobile_api\api\scan.py`
- `d:\yuan\不锈钢网带跟单3.0\mobile_api\api\process.py`
- `d:\yuan\不锈钢网带跟单3.0\mobile_api\api\quality.py`

#### 核心接口

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/scan/info` | GET | 扫码获取工单信息及工序进度 |
| `/api/process/report` | POST | 工序报工 |
| `/api/quality/submit` | POST | 质检提交 |

#### 运算逻辑

**工序进度计算**：
```
工序进度 = (已报工数量 / 计划数量) × 100%
工序状态:
  - 未报工: 已报工 = 0
  - 进行中: 已报工 > 0 且 < 计划数量
  - 已完成: 已报工 >= 计划数量
```

---

### 3.6 人脸识别考勤系统 (Face Recognition Attendance)

#### 位置
- 前端：`d:\yuan\face-liveness-demo\dist\`（TensorFlow.js）
- 后端：`d:\yuan\face-liveness-demo\server.py`（FastAPI + SQLite）
- 数据库：`face_checkin.db`（SQLite）
- 集成：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py` 中注册 face_checkin_bp

#### 架构

```
┌───────────────────────────────────────────────────────┐
│                 人脸识别考勤系统                          │
├───────────────────────────────────────────────────────┤
│  前端 (dist/)                                          │
│  ├── TensorFlow.js (BlazeFace 人脸检测)                 │
│  ├── FaceMesh (468个面部关键点)                          │
│  ├── 活体检测 (眨眼/摇头/张嘴动作检测)                     │
│  └── result.ungraded   |  result.html (签到结果展示)      │
├───────────────────────────────────────────────────────┤
│  后端 server.py (FastAPI)                               │
│  ├── 人脸注册: 录入人脸特征向量 → 存入 enrollments 表     │
│  ├── 人脸签到: 拍照 → 特征提取 → 相似度匹配 → 存入签到记录 │
│  ├── 考勤查询: 按人名/日期查询签到记录                      │
│  ├── 配置管理: 存储路径、导出计划                           │
│  └── 导出功能: 按计划自动导出考勤数据                       │
├───────────────────────────────────────────────────────┤
│  数据库 (SQLite)                                        │
│  ├── enrollments: name(主键) / descriptor / created_at   │
│  └── checkins: id / name / similarity / photo /          │
│                photo_path / created_at                   │
└───────────────────────────────────────────────────────┘
```

#### 人脸签到逻辑
```
用户拍照 → BlazeFace 检测人脸区域 → FaceMesh 提取468个关键点
→ 生成128维人脸特征向量 → 与 enrollments 表已注册特征比较
→ 计算余弦相似度 → 最高相似度 > 阈值(0.75) → 签到成功
→ 记录签到时间、相似度、拍照
→ 同时可推送签到通知到企业微信群
```

---

### 3.7 表格机器人 (Table Bot)

#### 位置
- `d:\yuan\table-bot\table_bot\app.py`

#### 架构
```
┌────────────────────────────────────────────────┐
│             表格机器人 (Table Bot)                │
├────────────────────────────────────────────────┤
│  企业微信回调服务器 (Flask)                       │
│  ├── GET /callback - URL验证 (echostr 返回)     │
│  └── POST /callback - 消息处理                  │
│                                                  │
│  消息处理流程:                                    │
│  接收XML消息 → 解密(WXBizMsgCrypt) → 解析XML     │
│  → 提取MsgType/Content/FromUserName             │
│  → 根据Content匹配命令 → 执行表格操作             │
│  → 组装响应XML → 加密返回                        │
└────────────────────────────────────────────────┘
```

---

## 四、数据流详解

### 4.1 主数据流 (订单→生产→完成)

```
┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
│ 创建  │──▶│ 排产  │──▶│ 生产  │──▶│ 质检  │──▶│ 完成  │
│ 订单  │   │ 工单  │   │ 报工  │   │ 检验  │   │ 归档  │
└──────┘   └──────┘   └──────┘   └──────┘   └──────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
  MySQL ─── MySQL ─── MySQL ─── MySQL ─── MySQL
    │                    │
    ▼                    ▼
 订单状态:          工序状态:
 新建 ─→ 已排产     未开始 ─→ 进行中 ─→ 已完成
 ─→ 生产中         全部完成时:
 ─→ 质检中         工单 → 已完成
 ─→ 已完成         订单 → 质检中
```

### 4.2 消息数据流 (企业微信→系统)

```
企业微信用户发送消息
    │
    ▼
┌─────────────────┐
│ 云端接收层        │  wechat_cloud.py (公网)
│ POST /callback   │  XML解密 → 消息解析
└────────┬────────┘
         │ 轮询拉取 (cloud_poller)
         ▼
┌─────────────────┐
│ 本地消息处理层     │  standalone_dispatch_server.py (内网)
│ 指令匹配引擎       │  cloud_matching.py: PREFIX匹配
│ 命令分发          │  CommandType: 32种命令
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 业务处理层        │
│ ├── 查询订单      │
│ ├── 报工处理      │
│ ├── 质检处理      │
│ ├── 排产处理      │
│ └── 物料查询      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 响应组装 & 发送    │
│ 组装Markdown消息  │
│ 调用企业微信API   │
│ 推送到群/个人     │
└─────────────────┘
```

### 4.3 任务调度数据流 (容器中心→调度中心→操作员)

```
Main Software / Mobile API (报工触发)
    │
    ▼
┌──────────────────┐
│ 容器中心 v5       │
│ collect_report()  │  创建数据包(DataPackage)
│ → save_package()  │  保存到SQLite/Redis
│ → distribute()    │  执行分发策略(direct/round_robin/least_busy)
│ → save_dispatch() │  生成调度指令
│ → push_callbacks  │  触发回调通知
└────────┬─────────┘
         │ task_published 事件
         ▼
┌──────────────────┐
│ 调度中心           │
│ /task-notify      │  接收新任务通知
│ get_status()      │  刷新看板
│ assignTask()      │  自动/手动分配任务
│ → 通知操作员      │  企业微信消息推送
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 操作员 (手机端)    │
│ 接收企业微信通知   │
│ 扫码报工          │
│ 查看任务列表      │
│ 完成报工          │
└──────────────────┘
```

### 4.4 云端-本地双轨架构

```
┌─────────────────────────┐     ┌──────────────────────────┐
│      云端 (Cloud)         │     │     本地 (Local)           │
│                          │     │                           │
│  wechat_cloud.py         │     │  standalone_dispatch_server │
│  ├── 微信回调接收         │◀────│  ├── 容器中心集成           │
│  ├── 消息队列             │     │  ├── 指令匹配引擎           │
│  ├── 主动发送             │────▶│  ├── 调度中心              │
│  ├── 云端备份(归档)       │     │  ├── 配置中心              │
│  └── IP白名单             │     │  ├── 人脸签到集成           │
│                          │     │  ├── 增强模块              │
│  cloud_poller.py         │────▶│  │  ├── CircuitBreaker      │
│  ├── 轮询云端消息         │     │  │  ├── QueueManager       │
│  └── 同步到本地          │     │  │  ├── HealthCheck        │
│                          │     │  │  ├── AuditLogger        │
│  cloud_matching.py       │     │  │  └── BackupManager      │
│  ├── 指令匹配引擎         │     │  └── 企业微信API调用        │
│  └── 32种命令类型        │     └──────────────────────────┘
└─────────────────────────┘
```

### 4.5 排产调度全链路数据流

```
主软件"确认发布"
    │
    ▼
┌──────────────────────────────────────┐
│ ScheduleDispatchService              │
│ 1. 写入 schedule_queue 表(防重复校验) │
│ 2. 后台线程轮询(5s间隔, 最多5条/批)   │
└─────────────────┬────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ 容器中心 v5                           │
│ 1. collect_report() → 创建DataPackage │
│ 2. distribute() → 执行分发策略        │
│ 3. 保存调度指令到SQLite               │
└─────────────────┬────────────────────┘
                  │ task_published 事件
                  ▼
┌──────────────────────────────────────┐
│ 调度中心                              │
│ 1. 接收任务通知，刷新看板             │
│ 2. assignTask() 分配操作员           │
│ 3. 调用企业微信API推送消息            │
└─────────────────┬────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ 云端 → 企业微信 → 操作员手机          │
│ 操作员确认 → 回调 → 调度中心 → 容器中心│
│ → 回调主软件API → 标记已排产          │
└──────────────────────────────────────┘
```

---

## 五、推算逻辑与运算逻辑汇总

### 5.1 业务推算逻辑

| 场景 | 输入 | 推算逻辑 | 输出 |
|------|------|---------|------|
| 订单总金额 | 单价, 数量 | `单价 × 数量` | 总金额 |
| 工序计划数量 | 产品类型, 尺寸参数 | 匹配规则 → 代入公式 → 执行数学表达式 | 计划数量 |
| 物料规格 | 产品类型, 尺寸参数 | 匹配物料规则 → 按模板生成规格 | 物料规格描述 |
| 工序进度 | 已报工数量, 计划数量 | `已报工 / 计划数量 × 100%` | 进度百分比 |
| 任务自动分配 | 操作员列表, 任务类型 | direct/round_robin/least_busy 策略 | 目标操作员 |
| 工序完成推进 | 当前工序状态 | 所有工序完成 → 工单完成 → 订单质检中 | 状态更新 |
| 流程步骤推进 | 当前步骤索引, 质检结果 | 合格 → next_step; 不合格 → 保持 | 新步骤索引 |
| 人脸签到 | 拍照图片, 注册特征库 | BlazeFace检测 → FaceMesh提取 → 相似度匹配 > 0.75 | 签到结果 |
| 指令匹配 | 用户输入文本 | PREFIX匹配 → 格式校验 → 参数提取 | 命令类型+参数 |
| 消息模板渲染 | 模板ID, 变量字典 | 查找模板 → 替换占位符 {变量名} → 生成内容 | 渲染后文本 |
| 数据完整性校验 | 数据包 | checksum校验 + 时间漂移检测 + 数量漂移检测 | 校验结果 |
| 缓存失效 | 缓存数据, TTL | `当前时间 - 缓存时间 > TTL` → 重新加载 | 新缓存数据 |

### 5.2 数据库运算逻辑

**订单创建运算**：
```
订单号 = 自动生成（基于时间戳+序列号）
总金额 = SUM(各明细行 单价 × 数量)
生产要求信息 = 将非固定字段合并为JSON存储
状态初始值 = '新建'
日志记录(op_logger.log): 创建订单(订单号, 产品类型, 数量)
```

**工序报工运算**：
```
报工数量累加: 已报工 = 已报工 + 本次报工数量
开始时间: 首次报工时记录
结束时间: 最终完成时记录
完成检查: IF 已报工 >= 计划数量 THEN 工序状态='已完成'
全部完成检查: IF 所有工序状态='已完成' THEN 工单状态='已完成'; 订单状态='质检中'
```

**流程推进运算**：
```
当前步骤 = process.current_step
步骤列表 = PROCESS_FLOW_TEMPLATES[flow_type].steps
推进: IF 当前步骤 < len(步骤列表)-1 THEN 当前步骤 += 1
状态更新: 新状态 = steps[当前步骤].status_key
质检结果处理: IF 质量合格 THEN 推进 ELSE 保持
```

**物料计算引擎安全校验**：
```
formula = data['qty_formula']
→ 替换中文符号(×→*, ÷→/)
→ 白名单校验: 仅允许 "0123456789.+-*/() " 中的字符
→ 非法字符 → 抛出 ValueError
→ tokenize() 词法分析
→ evaluate() 逆波兰表达式求值
→ 返回 float 结果
```

### 5.3 调度运算逻辑

**状态统计算法**：
```
待处理 = COUNT(数据包 WHERE status='pending')
已分发 = COUNT(数据包 WHERE status='distributed')
进行中 = COUNT(数据包 WHERE status='acknowledged')
已完成 = COUNT(数据包 WHERE status='completed')
超时 = COUNT(数据包 WHERE status='pending' AND 创建时间 > 超时阈值)
完成率 = 已完成 / (待处理+已分发+进行中+已完成+超时) × 100%
```

**自动重分配算法**：
```
超时 = 当前时间 - 分配时间 > auto_reassign_timeout
重分配: 通知原操作员 → 重新分配 → 选择新操作员 → 通知新操作员
提醒: 每 reminder_interval 分钟发送一次提醒，最多 max_reminders 次
```

---

## 六、配置中心详解 ([config_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/config_center.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\config_center.py`（461行）

### 6.1 架构概览

可视化配置中心，通过 RESTful API 管理所有外部接口、系统参数、业务配置。配置存储支持 `.env` 文件 + `config_center_data.json` 双持久化。

```
┌─────────────────────────────────────────────────────┐
│                 配置中心 (Config Center)               │
├─────────────────────────────────────────────────────┤
│  API 路由                                            │
│  ├── GET  /api/config-center/        - 首页          │
│  ├── GET  /api/config-center/schema  - 获取schema定义 │
│  ├── GET  /api/config-center/values  - 当前配置值    │
│  ├── POST /api/config-center/save    - 保存配置      │
│  ├── POST /api/config-center/test/mysql - 测试MySQL  │
│  └── POST /api/config-center/test/warehouse - 仓库   │
├─────────────────────────────────────────────────────┤
│  存储层                                              │
│  ├── .env 文件: 环境变量持久化                         │
│  └── config_center_data.json: JSON配置缓存            │
└─────────────────────────────────────────────────────┘
```

### 6.2 配置分类 (CONFIG_SCHEMA)

#### 微信配置 (wechat) - 💬

| 字段 | 类型 | 默认值 | 敏感 | 说明 |
|------|------|--------|------|------|
| WECHAT_WORK_BOT_URL | text | - | 否 | 群机器人Webhook URL |
| WECHAT_CORP_ID | text | - | 否 | 企业微信企业ID |
| WECHAT_AGENT_ID | text | - | 否 | 应用AgentID |
| WECHAT_SECRET | password | - | **是** | 应用Secret |
| WECHAT_TOKEN | password | - | **是** | 回调Token |
| WECHAT_AES_KEY | password | - | **是** | 回调AES密钥 |

#### 通知开关 (notification) - 🔔

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| ENABLE_WECHAT_NOTIFY | boolean | true | 启用微信通知 |
| NOTIFY_ON_TASK_ASSIGNED | boolean | true | 任务分配通知 |
| NOTIFY_ON_TASK_COMPLETED | boolean | true | 任务完成通知 |
| NOTIFY_ON_LOW_STOCK | boolean | false | 库存预警通知 |

#### 服务器配置 (server) - 🖥️

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| FLASK_HOST | text | 0.0.0.0 | 监听地址 |
| FLASK_PORT | number | 5003 | 主服务端口 |
| WECHAT_BOT_PORT | number | 5003 | 机器人端口 |
| CONTAINER_CENTER_PORT | number | 5002 | 容器中心端口 |
| FLASK_DEBUG | boolean | false | 调试模式 |

#### 数据库配置 (database) - 🗄️

| 字段 | 类型 | 默认值 | 敏感 | 说明 |
|------|------|--------|------|------|
| MYSQL_HOST | text | localhost | 否 | 数据库地址 |
| MYSQL_PORT | number | 3306 | 否 | 端口 |
| MYSQL_USER | text | root | 否 | 用户名 |
| MYSQL_PASSWORD | password | - | **是** | 密码 |
| MYSQL_DATABASE | text | production_tracking | 否 | 数据库名 |

支持 **测试连接** 功能。

#### 外部接口配置 (external_api) - 🔌

| 字段 | 类型 | 敏感 | 说明 |
|------|------|------|------|
| ALIYUN_API_KEY | password | **是** | 阿里云API Key |
| ALIYUN_API_SECRET | password | **是** | 阿里云API Secret |
| ALIYUN_SPEECH_APPKEY | password | **是** | 阿里云语音AppKey |
| ALIYUN_VISION_APPKEY | password | **是** | 阿里云视觉AppKey |
| DASHSCOPE_API_KEY | password | **是** | 通义千问API Key |

#### 仓库接口配置 (warehouse) - 📦

| 字段 | 类型 | 默认值 | 敏感 | 说明 |
|------|------|--------|------|------|
| WAREHOUSE_API_URL | text | - | 否 | 仓库API地址 |
| WAREHOUSE_API_KEY | password | - | **是** | API密钥 |
| WAREHOUSE_TIMEOUT | number | 10 | 否 | 请求超时(秒) |

支持 **测试连接** 功能。

#### 业务参数 (business) - ⚙️

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| MAX_TEXT_LENGTH | number | 2048 | 最大文本长度 |
| SESSION_TIMEOUT | number | 300 | 会话超时(秒) |
| JWT_EXPIRE_HOURS | number | 24 | JWT过期时间(小时) |
| PURCHASE_OPERATORS | text | PU001,PU002 | 采购人员ID(逗号分隔) |

#### 容器中心连接 (container) - 🏭

| 字段 | 类型 | 敏感 | 说明 |
|------|------|------|------|
| CONTAINER_CENTER_URL | text | 否 | 服务地址 |
| CONTAINER_CENTER_SECRET | password | **是** | 连接密钥 |

支持 **测试连接** 功能。

---

## 七、核心业务常量 ([core/config.py](file:///d:/yuan/不锈钢网带跟单系统3.01/core/config.py))

**路径**：`d:\yuan\不锈钢网带跟单系统3.01\core\config.py`（466行）

### 7.1 材质密度表 (9种)

| 材质 | 密度(kg/m³) |
|------|-----------|
| 304不锈钢 | 7930 |
| 316不锈钢 | 7980 |
| 316L不锈钢 | 7980 |
| 310S不锈钢 | 7980 |
| 201不锈钢 | 7930 |
| 碳钢镀锌 | 7850 |
| 铝合金 | 2700 |
| 铜合金 | 8500 |
| 钛合金 | 4510 |

### 7.2 尺寸参数预设 (34个)

| 参数 | 单位 | 参数 | 单位 |
|------|------|------|------|
| 总宽 | mm | 净宽 | mm |
| 网带宽度 | mm | 钢丝直径 | mm |
| 加强链片厚度 | mm | 链条厚度 | mm |
| 链板板厚 | mm | 链板网孔直径 | mm |
| 螺距 | mm | 曲轴直径 | mm |
| 穿杆直径 | mm | 主轴直径 | mm |
| 主齿轮直径 | mm | 辅助轮直径 | mm |
| 加强筋直径 | mm | 网带节距 | mm |
| 加强筋间距 | mm | 链条距 | mm |
| 穿杆距 | mm | 中心距 | mm |
| 加强垫片布置 | mm | 扣间隙 | mm |
| 网带排数 | 条 | 加强筋数量 | 条 |
| 主齿轮齿数 | 齿 | 主齿轮数量 | 套 |
| 辅助齿轮齿数 | 齿 | 辅助轮数量 | 个 |
| 单段长度 | m | 网带段数 | 段 |
| 挡板高度 | mm | 挡板厚度 | mm |
| 链板网孔规格 | mm | 材质参数(9种) | - |

### 7.3 材质参数预设 (9种)

曲轴材质、网丝材质、穿杆材质、链条材质、主齿轮材质、挡板材质、辅助轮材质、加强筋材质、链板材质

### 7.4 产品类型 (13种)

1. 乙字形网带
2. 人字形网带
3. 平板型网带
4. 勾子链网带
5. 弹簧网
6. 眼镜网带
7. 螺旋网带
8. 链板式网带
9. 链网
10. 马蹄形网带
11. 冷冻网带
12. 冷冻螺旋网
13. 其他

### 7.5 生产工序 (17个)

| 序号 | 工序名称 | 质检要求 |
|------|---------|---------|
| 1 | 原材料准备 | 材质核对、外观检查 |
| 2 | 焊接眼镜网 | 焊点检查、外观检查 |
| 3 | 激光切板 | 尺寸检查、外观检查 |
| 4 | 链板冲压孔 | 尺寸检查、外观检查 |
| 5 | 链板冲压成型 | 尺寸检查、外观检查 |
| 6 | 编制左旋 | 编织检查、外观检查 |
| 7 | 编制右旋 | 编织检查、外观检查 |
| 8 | 穿曲轴 | 装配检查、外观检查 |
| 9 | 输送带组装穿杆 | 装配检查、外观检查 |
| 10 | 安装链条 | 装配检查、外观检查 |
| 11 | 安装裙边 | 装配检查、外观检查 |
| 12 | 整形校直 | 尺寸检查、外观检查 |
| 13 | 焊接输送带 | 焊点检查、外观检查 |
| 14 | 表面处理 | 处理检查、外观检查 |
| 15 | 质量检验 | 全面检查、报告输出 |
| 16 | 包装入库 | 包装检查、入库核对 |

### 7.6 订单状态 (11种, 带颜色)

| 状态 | 颜色 | 说明 |
|------|------|------|
| 待确认 | `#9E9E9E` 灰色 | 新建订单待确认 |
| 待排产 | `#2196F3` 蓝色 | 已确认待排产 |
| 待发布 | `#00BCD4` 青色 | 已排产待发布 |
| 已发布 | `#0097A7` 深青 | 已发布到车间 |
| 已排产 | `#03A9F4` 亮蓝 | 已排产到设备 |
| 生产中 | `#FF9800` 橙色 | 正在生产 |
| 质检中 | `#FF5722` 深橙 | 质检进行中 |
| 已完成 | `#4CAF50` 绿色 | 全部完成 |
| 待发货 | `#9C27B0` 紫色 | 质检通过待发货 |
| 已发货 | `#9C27B0` 紫色 | 已发货 |
| 已取消 | `#F44336` 红色 | 订单取消 |

### 7.7 质检项目分类 (按工序)

| 工序 | 质检类别 | 质检项目 |
|------|---------|---------|
| 原材料准备 | 材质核对 | 材质报告核查、规格核对、数量核对 |
| 原材料准备 | 外观检查 | 表面质量、锈蚀检查、变形检查 |
| 焊接眼镜网 | 焊点检查 | 焊点质量、焊接强度 |
| 焊接眼镜网 | 外观检查 | 网面平整度、形状核对 |
| 激光切板 | 尺寸检查 | 切割尺寸、切口质量 |
| 激光切板 | 外观检查 | 毛刺检查、平面度 |
| 编制左旋/右旋 | 编织检查 | 编织密度、纬线张力、经线张力 |
| 编制左旋/右旋 | 外观检查 | 网孔尺寸、平整度 |
| 质量检验 | 全面检查 | 尺寸核对、外观检查、性能测试 |
| 质量检验 | 报告输出 | 检验记录、合格判定 |
| ... | ... | (17个工序全覆盖) |

### 7.8 表面处理选项 (5种)

光亮退火、抛光、钝化、喷砂、无处理

### 7.9 单位选项

米、平方米、卷、条、个、套、批

### 7.10 业务阈值配置 (BusinessConfig)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| STOCK_WARNING_THRESHOLD | 50 | 库存预警阈值 |
| STOCK_CRITICAL_THRESHOLD | 10 | 库存严重不足阈值 |
| ORDER_EXPIRY_DAYS | 30 | 订单过期天数 |
| ORDER_ARCHIVE_DAYS | 365 | 订单归档天数 |
| DEFAULT_PAGE_SIZE | 50 | 默认分页大小 |
| MAX_PAGE_SIZE | 200 | 最大分页大小 |
| QUERY_TIMEOUT | 60 | 查询超时(秒) |
| COMMAND_TIMEOUT | 300 | 命令超时(秒) |

### 7.11 UI样式配置 (StyleConfig)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| FONT_FAMILY | Microsoft YaHei | 字体 |
| FONT_SIZE_NORMAL | 10 | 标准字号 |
| FONT_SIZE_TITLE | 14 | 标题字号 |
| PRIMARY_COLOR | `#2196F3` | 主色 |
| SUCCESS_COLOR | `#4CAF50` | 成功色 |
| WARNING_COLOR | `#FF9800` | 警告色 |
| ERROR_COLOR | `#F44336` | 错误色 |

### 7.12 窗口配置

| 参数 | 值 |
|------|-----|
| 默认窗口大小 | 1200×700 |
| 最小窗口 | 800×500 |
| 生产选单 | 1000×450 |
| 订单详情 | 500×400 |
| 自定义类型 | 550×480 |

---

## 八、蓝图路由一览 ([blueprint_registry.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/blueprint_registry.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\blueprint_registry.py`（43行）

### 注册机制

使用声明式配置实现 Flask Blueprint 统一注册，新增模块只需在 `BLUEPRINT_ENTRIES` 列表中添加条目即可。

### 15个蓝图注册列表

| 序号 | 模块路径 | Blueprint变量 | URL前缀 | 功能说明 |
|------|---------|---------------|---------|---------|
| 1 | `face_checkin` | bp | (无) | 人脸签到API |
| 2 | `dispatch_center` | dispatch_center_bp | (无) | 调度中心/文档服务 |
| 3 | `container_dashboard` | container_dashboard_bp | `/container` | 容器中心监控面板 |
| 4 | `schedule_flow` | schedule_bp | (无) | 排产流程引擎 |
| 5 | `config_center` | config_center_bp | (无) | 配置中心(8大分类) |
| 6 | `data_collector_api` | data_collector_bp | (无) | 数据收集API |
| 7 | `api.auth` | bp | (无) | 认证授权 |
| 8 | `api.process` | bp | (无) | 工序管理API |
| 9 | `api.quality` | bp | (无) | 质检管理API |
| 10 | `api.approval` | bp | (无) | 审批流程API |
| 11 | `api.message` | bp | (无) | 消息通知API |
| 12 | `api.stats` | bp | (无) | 统计分析API |
| 13 | `api.scan` | bp | (无) | 扫码查询API |
| 14 | `api.ai` | bp | (无) | AI增强API |

### 自动注册流程

```python
def register_all_blueprints(app):
    """自动注册所有声明的 Blueprint 到 Flask 应用"""
    for module_path, bp_name, url_prefix in BLUEPRINT_ENTRIES:
        module = import_module(module_path)
        bp = getattr(module, bp_name)
        if url_prefix:
            app.register_blueprint(bp, url_prefix=url_prefix)
        else:
            app.register_blueprint(bp)
```

---

## 九、增强模块详解 ([enhanced_modules.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/enhanced_modules.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\enhanced_modules.py`（177行）

### 9.1 架构概览

采用单例模式 (`EnhancedModules集成`)，提供客户端和服务端两种初始化模式。

```
┌──────────────────────────────────────────────────────┐
│              EnhancedModules集成 (单例)                 │
├──────────────────────────────────────────────────────┤
│  initialize_client_side()  - 客户端模式                 │
│  ├── CircuitBreaker   (熔断器)  - 启动                 │
│  └── QueueManager     (队列)    - 启动                 │
│                                                        │
│  initialize_server_side()  - 服务端模式                 │
│  ├── CircuitBreaker          (熔断器)  - 启动           │
│  ├── QueueManager            (队列)    - 启动           │
│  ├── HealthChecker           (健康检查) - 启动          │
│  ├── DeploymentManager       (部署管理) - 启动          │
│  ├── EnhancedAuditLogger     (审计日志) - 启动          │
│  ├── EnhancedBackupManager   (增强备份) - 启动          │
│  └── ClockSync               (时钟同步) - 启动          │
└──────────────────────────────────────────────────────┘
```

### 9.2 组件参数

| 组件 | 类 | 配置参数 |
|------|----|---------|
| **熔断器** | CircuitBreaker | failure_threshold=50, success_threshold=3, failure_rate_threshold=0.5, half_open_max_requests=3, open_timeout=30s |
| **队列管理器** | QueueManager | default_max_size=1000, default_timeout=5s, 支持Redis后端 |
| **健康检查器** | HealthChecker | redis_client, es_hosts(逗号分隔) |
| **部署管理器** | DeploymentManager | backup_dir=_backup, config_dir=_config, deploy_dir=_deploy |
| **审计日志** | EnhancedAuditLogger | es_hosts=localhost:9200, redis_client |
| **增强备份** | EnhancedBackupManager | backup_dir, redis_password |
| **时钟同步** | ClockSync (global_clock_sync) | 全局单例 |

### 9.3 初始化模式

| 模式 | 调用场景 | 启动组件数 |
|------|---------|-----------|
| 客户端 | 仅需要API调用的模块（如容器中心客户端） | 2个(CB+QM) |
| 服务端 | 完整服务（如standalone_dispatch_server主服务） | 7个(CB+QM+HC+DM+EAL+EBM+CS) |

---

## 十、告警模块 ([alert.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/alert.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\alert.py`（281行）

告警模块提供统一的多渠道告警通知能力，支持按级别分级告警、按渠道分发通知、聚合告警防刷。

### 10.1 告警级别 (AlertLevel)

| 级别 | 枚举值 | 日志方法 | 说明 |
|------|--------|---------|------|
| DEBUG | `AlertLevel.DEBUG` | logger.info | 调试信息，仅记录日志 |
| INFO | `AlertLevel.INFO` | logger.info | 普通通知 |
| WARNING | `AlertLevel.WARNING` | logger.warning | 警告，需关注 |
| ERROR | `AlertLevel.ERROR` | logger.error | 错误，需处理 |
| CRITICAL | `AlertLevel.CRITICAL` | logger.critical | 严重错误，立即处理 |

### 10.2 通知渠道 (AlertChannel)

| 渠道 | 枚举值 | 配置环境变量 | 依赖 |
|------|--------|-------------|------|
| 企业微信 | `AlertChannel.WECHAT_WORK` | `WECHAT_WORK_ALERT_WEBHOOK` | requests |
| 钉钉 | `AlertChannel.DINGTALK` | `DINGTALK_ALERT_WEBHOOK` + `DINGTALK_ALERT_SECRET` | requests, hmac |
| 邮件 | `AlertChannel.EMAIL` | `EMAIL_SMTP_HOST/PORT/USER/PASSWORD/FROM/TO` | smtplib |
| 日志 | `AlertChannel.LOG` | 默认启用 | 无 |

### 10.3 核心函数

```python
def send_alert(
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    tags: Optional[List[str]] = None,
    channels: Optional[List[AlertChannel]] = None,
    exception: Optional[Exception] = None
) -> bool
```

**调用流程**：
1. 检查全局开关 `ALERT_ENABLED`
2. 设置默认 channels（仅 LOG）
3. 根据 level 选择日志级别记录
4. 遍历 channels，调用对应渠道发送函数
5. 返回是否有渠道发送成功

### 10.4 装饰器

| 装饰器 | 说明 | 等效于 |
|--------|------|--------|
| `@alert_on_error(level, tags)` | 函数异常时自动告警 | 通用异常告警 |
| `@critical_alert(tags)` | 关键函数异常必告警 | `alert_on_error(CRITICAL)` |

### 10.5 AlertManager 聚合告警

防止高频告警刷屏，支持累计计数 + 时间窗口合并发送。

| 属性/方法 | 说明 |
|-----------|------|
| `_count` | 累计事件计数 |
| `_last_send_time` | 上次发送时间戳 |
| `record(message, tags)` | 记录事件，累计>=10次或距上次>300s时发送 |
| `reset()` | 重置计数器 |

**聚合规则**：计数达到10次 或 距上次发送超过300秒（5分钟）时，触发一次聚合告警。

---

## 十一、统一配置管理 ([settings.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/settings.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\settings.py`（206行）

采用 dataclass + from_env 工厂模式，统一管理应用配置，支持 `.env` 文件和环境变量覆盖。

### 11.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    Settings.load()                        │
├─────────────────────────────────────────────────────────┤
│ 1. _load_dotenv()  → 读取 .env 文件到 os.environ         │
│ 2. DatabaseConfig.from_env()  → MySQL连接参数            │
│ 3. JWTConfig.from_env()       → 鉴权密钥参数             │
│ 4. CORSConfig.from_env()      → 跨域白名单               │
│ 5. FlaskConfig.from_env()     → Web服务参数              │
│ 6. WeChatConfig.from_env()    → 企微应用参数             │
│ 7. LogConfig.from_env()       → 日志参数                 │
└─────────────────────────────────────────────────────────┘
         │
         ▼
    settings = Settings.load()  ← 全局单例
```

### 11.2 配置类详表

| 配置类 | 字段 | 环境变量 | 默认值 | 说明 |
|--------|------|---------|--------|------|
| **DatabaseConfig** | host | `MYSQL_HOST` | localhost | MySQL主机 |
| | port | `MYSQL_PORT` | 3306 | MySQL端口 |
| | user | `MYSQL_USER` | root | MySQL用户 |
| | password | `MYSQL_PASSWORD` | (空) | MySQL密码 |
| | database | `MYSQL_DATABASE` | steel_belt | MySQL数据库名 |
| | pool_size | `MYSQL_POOL_SIZE` | 10 | 连接池大小 |
| | pool_recycle | `MYSQL_POOL_RECYCLE` | 3600 | 连接回收秒数 |
| **JWTConfig** | secret_key | `JWT_SECRET_KEY` | **必填无默认值** | JWT签名密钥 |
| | algorithm | `JWT_ALGORITHM` | HS256 | 签名算法 |
| | expire_hours | `JWT_EXPIRE_HOURS` | 24 | 过期小时数 |
| **CORSConfig** | origins | `CORS_ALLOWED_ORIGINS` | localhost:5000,3000 | 跨域白名单 |
| **FlaskConfig** | debug | `FLASK_DEBUG` | false | 调试模式 |
| | secret_key | `FLASK_SECRET_KEY` | 同JWT_SECRET_KEY | Flask密钥 |
| | host | `FLASK_HOST` | 0.0.0.0 | 监听地址 |
| | port | `FLASK_PORT` | 5000 | 监听端口 |
| **WeChatConfig** | corp_id | `WECHAT_WORK_CORP_ID` | (空) | 企业ID |
| | agent_id | `WECHAT_WORK_AGENT_ID` | (空) | 应用AgentID |
| | token | `WECHAT_WORK_TOKEN` | (空) | 回调Token |
| | aes_key | `WECHAT_WORK_AES_KEY` | (空) | 回调AES密钥 |
| **LogConfig** | level | `LOG_LEVEL` | INFO | 日志级别 |
| | format | `LOG_FORMAT` | 标准格式 | 日志格式 |
| | date_format | `LOG_DATE_FORMAT` | %Y-%m-%d %H:%M:%S | 日期格式 |
| | retention_days | `LOG_RETENTION_DAYS` | 30 | 日志保留天数 |
| | max_bytes | `LOG_MAX_BYTES` | 100MB | 单文件最大字节 |

### 11.3 加载机制

```python
# 1. 模块加载时自动调用 _load_dotenv()
# 2. 每个配置类的 from_env() 方法从 os.environ 读取
# 3. Settings.load() 聚合所有子配置
# 4. 全局单例 settings = Settings.load()

settings = Settings.load()
# 使用: settings.database.host, settings.jwt.secret_key
```

---

## 十二、后端微服务配置 ([config.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/config.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\config.py`（119行）

提供比 settings.py 更低层的基础配置，包括 BASE_DIR 定位、端口分配、业务阈值、颜色定义等。

### 12.1 BASE_DIR 自动定位

```python
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))  # PyInstaller打包后
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))        # 开发模式
```

### 12.2 端口分配表

| 配置项 | 环境变量 | 默认值 | 用途 |
|--------|---------|--------|------|
| `WECHAT_BOT_HOST` | `WECHAT_BOT_HOST` | 0.0.0.0 | 绑定地址 |
| `WECHAT_BOT_PORT` | `WECHAT_BOT_PORT` | 5003 | 微信机器人主服务 |
| `CONTAINER_CENTER_PORT` | `CONTAINER_CENTER_PORT` | 5002 | 容器中心服务 |
| `HTTP_TEST_PORT` | `HTTP_TEST_PORT` | 9999 | HTTP测试端口 |
| `DIAGNOSE_PORT` | `DIAGNOSE_PORT` | 5003 | 诊断端口 |
| `FLASK_HOST` | `FLASK_HOST` | 0.0.0.0 | Flask绑定地址 |

### 12.3 业务阈值

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| `MAX_TEXT_LENGTH` | `MAX_TEXT_LENGTH` | 2048 | 最大文本长度 |
| `SESSION_TIMEOUT` | `SESSION_TIMEOUT` | 300s | 会话超时时间 |
| `DATA_RETENTION_DAYS` | `DATA_RETENTION_DAYS` | 90天 | 数据保留天数 |

### 12.4 颜色配置 (COLORS)

```python
COLORS = {
    'DATA_TYPE_REPORT':   '#4caf50',   # 报工 - 绿色
    'DATA_TYPE_QUALITY':  '#2196f3',   # 质检 - 蓝色
    'DATA_TYPE_MATERIAL': '#ff9800',   # 领料 - 橙色
    'DATA_TYPE_APPROVAL': '#9c27b0',   # 审批 - 紫色
    'DATA_TYPE_ORDER':    '#00bcd4',   # 订单 - 青色
    'DATA_TYPE_PROCESS':  '#607d8b',   # 工序 - 灰蓝
    'DATA_TYPE_REPAIR':   '#FF6B6B',   # 报修 - 红色
}
```

### 12.5 辅助函数

| 函数 | 用途 |
|------|------|
| `get_default_backup_dir()` | 获取默认备份目录（DAT/backup） |
| `get_app_dir()` | 获取应用程序目录 |
| `get_default_redis_dump()` | 获取默认Redis dump文件路径 |

---

## 十三、容器配置类 ([container_config.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_config.py))

**路径**：`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_config.py`（450行）

容器中心的业务参数配置模块，统一管理操作员、工序、数据类型、报修种类、外协配置、通知配置。

### 13.1 配置数据类

| dataclass | 字段 | 说明 |
|-----------|------|------|
| **OperatorConfig** | id, name, role, department, enabled, notify_enabled, max_tasks, wechat_userid | 操作员配置 |
| **ProcessConfig** | id, name, code, sequence, enabled, quality_check_required | 工序配置 |
| **DataTypeConfig** | type, name, icon, color, enabled, auto_distribute | 数据类型配置 |
| **NotificationConfig** | enabled, notify_on_create/distribute/complete/overdue | 通知开关 |
| **RepairCategoryConfig** | id, name, icon, assigned_operator_id, description | 报修种类 |
| **OutsourcConfig** | enabled, default_operator_id, remind_days, overdue_remind_times | 外协配置 |

### 13.2 ContainerConfig 主类

全局单例 `container_config = ContainerConfig()`

**核心能力**：

| 方法类别 | 方法 | 说明 |
|----------|------|------|
| **操作员管理** | get_operator / get_all_operators / get_enabled_operators | 查询操作员 |
| | get_operators_by_department / get_all_departments | 按部门查询 |
| | add_operator / update_operator / remove_operator | 增删改操作员 |
| **工序管理** | get_process / get_all_processes / get_enabled_processes | 查询工序 |
| | get_process_by_name / add_process / update_process | 增改工序 |
| | refresh_processes() | 从容器中心数据库动态刷新 |
| **数据类型** | get_data_type / get_all_data_types / get_enabled_data_types | 数据类型查询 |
| **报修种类** | get_repair_category / get_all_repair_categories | 查询报修种类 |
| | add_repair_category / remove_repair_category | 增删报修种类 |
| **通知配置** | get_notification_config / update_notification_config | 通知开关配置 |
| **外协配置** | get_outsourc_config / update_outsourc_config | 外协参数配置 |
| **序列化** | to_dict / load_from_dict | 字典导入导出 |

### 13.3 持久化机制

| 文件 | 存放路径 | 存储内容 |
|------|---------|---------|
| `operators.json` | `BASE_DIR/operators.json` | 操作员数据（JSON序列化） |
| `repair_categories.json` | `BASE_DIR/repair_categories.json` | 报修种类（JSON序列化） |

**默认工序兜底**（当容器中心不可用时）：

| 工序ID | 名称 | 编码 | 序号 | 需质检 |
|--------|------|------|------|--------|
| P01 | 编织 | WEAVING | 1 | 是 |
| P02 | 质检 | QUALITY | 2 | 是 |
| P03 | 包装 | PACKING | 3 | 否 |

**7种默认数据类型**：

| 类型 | 名称 | 图标 | 颜色 | 自动分发 |
|------|------|------|------|---------|
| report | 报工 | 📝 | #4caf50 | 是 |
| quality | 质检 | 🔍 | #2196f3 | 否 |
| material | 领料 | 📦 | #ff9800 | 否 |
| approval | 审批 | ✅ | #9c27b0 | 否 |
| order | 订单 | 📋 | #00bcd4 | 否 |
| process | 工序 | ⚙️ | #607d8b | 否 |
| repair | 报修 | 🔧 | #FF6B6B | 否 |

### 13.4 外协催单规则

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|---------|--------|------|
| default_operator_id | `OUTSOURC_DEFAULT_OPERATOR` | MG001 | 默认负责人 |
| remind_days | `OUTSOURC_REMIND_DAYS` | 3,2,1 | 到期前N天提醒 |
| overdue_remind_times | `OUTSOURC_REMIND_TIMES` | 08:00,13:30 | 每日提醒时间点 |

---

## 十四、数据库ER关系

系统采用 **MySQL + SQLite 双数据库架构**，MySQL 存储核心业务数据，SQLite 存储容器中心和考勤等辅助数据。

### 14.1 MySQL 核心表（主软件 v3.01）

```
┌─────────────────┐       ┌──────────────────────┐
│     orders      │       │   production_orders   │
├─────────────────┤       ├──────────────────────┤
│ PK order_id     │──1:N──│ PK prod_id            │
│   order_no      │       │ FK order_id           │
│   customer      │       │   product_name        │
│   status        │       │   quantity            │
│   material      │       │   status              │
│   total_weight  │       │   current_process     │
│   total_amount  │       │   start_date          │
│   order_date    │       │   planned_end_date    │
│   delivery_date │       └──────────┬────────────┘
│   remark        │                  │ 1:N
└─────────────────┘                  │
       │1:N                  ┌───────┴──────────────┐
       │                     │    process_records    │
       ▼                     ├──────────────────────┤
┌─────────────────┐         │ PK record_id          │
│  order_items    │         │ FK prod_id            │
├─────────────────┤         │   process_name        │
│ PK item_id      │         │   operator            │
│ FK order_id     │         │   start_time          │
│   product_name  │         │   end_time            │
│   quantity      │         │   quantity            │
│   unit          │         │   quality_status      │
│   unit_price    │         │   remark              │
│   weight        │         └──────────────────────┘
└─────────────────┘
       │
       │ 1:N
       ▼
┌─────────────────┐       ┌──────────────────────┐
│  quality_records│       │    material_records    │
├─────────────────┤       ├──────────────────────┤
│ PK qc_id        │       │ PK material_id         │
│ FK order_id     │       │ FK order_id            │
│ FK prod_id      │       │   material_name        │
│   inspector     │       │   specifications       │
│   check_items   │       │   quantity             │
│   result        │       │   supplier             │
│   check_date    │       │   received_date        │
│   remark        │       └──────────────────────┘
└─────────────────┘
```

### 14.2 SQLite 库分布（容器中心）

| 数据库文件 | 存储内容 | 路径 |
|-----------|---------|------|
| `container.db` | 容器中心核心数据 | `mobile_api_ai/data/container.db` |
| `wechat_container.db` | 微信消息/数据包 | `mobile_api_ai/data/wechat_container.db` |
| `face_attendance.db` | 人脸考勤记录 | `mobile_api_ai/data/face_attendance.db` |
| `face_checkin.db` | 签到记录 | `mobile_api_ai/data/face_checkin.db` |
| `orders.db` | 订单数据(缓存) | `mobile_api_ai/data/orders.db` |
| `production.db` | 生产数据(缓存) | `mobile_api_ai/data/production.db` |
| `quality.db` | 质检数据(缓存) | `mobile_api_ai/data/quality.db` |
| `inventory.db` | 库存数据(缓存) | `mobile_api_ai/data/inventory.db` |
| `equipment.db` | 设备数据 | `mobile_api_ai/data/equipment.db` |
| `maintenance.db` | 设备维保 | `mobile_api_ai/data/maintenance.db` |
| `hr.db` | 人事数据 | `mobile_api_ai/data/hr.db` |
| `customer.db` | 客户数据 | `mobile_api_ai/data/customer.db` |
| `supplier.db` | 供应商数据 | `mobile_api_ai/data/supplier.db` |
| `procurement.db` | 采购数据 | `mobile_api_ai/data/procurement.db` |
| `settlement.db` | 结算数据 | `mobile_api_ai/data/settlement.db` |
| `system.db` | 系统配置 | `mobile_api_ai/data/system.db` |
| `scheduler_configs.db` | 调度配置 | `mobile_api_ai/data/scheduler_configs.db` |

### 14.3 主软件 SQLite 本地库

| 数据库文件 | 存储内容 | 路径 |
|-----------|---------|------|
| `steel_belt.db` | 主软件业务数据(SQLite模式) | `不锈钢网带跟单系统3.01/data/steel_belt.db` |
| `example_db.sqlite` | 示例数据 | `不锈钢网带跟单系统3.01/data/example_db.sqlite` |

---

## 十五、网络部署架构

### 15.1 端口分配总表

| 端口 | 服务 | 所在模块 | 协议 |
|------|------|---------|------|
| 5002 | 容器中心API服务 | [container_center_api.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py) | HTTP |
| 5003 | 微信机器人主服务 | [standalone_dispatch_server.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/standalone_dispatch_server.py) | HTTP |
| 5003 | 云端微信服务 | [wechat_cloud.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_cloud.py) | HTTP |
| 5010 | 库存管理API | [inventory_api_server.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_api_server.py) | HTTP |
| 5000 | 调度中心(默认Flask端口) | [dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py) | HTTP |
| 9999 | HTTP测试 | 测试工具 | HTTP |
| 8000 | 人脸识别服务(FastAPI) | [server.py](file:///d:/yuan/face-liveness-demo/server.py) | HTTP |
| 7860 | 表格机器人服务 | [app.py](file:///d:/yuan/table-bot/table_bot/app.py) | HTTP |

### 15.2 网络拓扑

```
                         ┌─────────────────────┐
                         │    企业微信服务器     │
                         │  (企微开放平台API)    │
                         └──────┬──────┬───────┘
                                │      │
                    ┌───────────┘      └───────────┐
                    ▼                               ▼
          ┌─────────────────┐           ┌─────────────────────┐
          │ wechat_cloud.py │           │  企业微信回调 → 内网   │
          │  (公网/云端)    │           │  standalone_dispatch_server.py  │
          │  端口:5003      │           │  (内网服务)           │
          └───────┬─────────┘           │  端口:5003            │
                  │                     └──────────┬──────────┘
                  │  cloud_poller.poll()            │
                  ▼                                 ▼
          ┌───────────────────────────────────────────────┐
          │             容器中心 container_center_v5.py     │
          │              端口: 5002                         │
          │  ┌─────────────────────────────────────────┐   │
          │  │  Storage Layer (SQLite/Redis 双引擎)     │   │
          │  │  + 7个保护模块(熔断/队列/健康/签名/时钟)  │   │
          │  └─────────────────────────────────────────┘   │
          └──────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────────────┐
         ▼               ▼                       ▼
┌────────────────┐ ┌──────────────┐ ┌────────────────────┐
│ dispatch_center│ │ 主软件 v3.01 │ │  调度中心Web看板    │
│  (调度服务)     │ │ (Tkinter桌面) │ │  (dispatch_center) │
│  端口:5000      │ │ MySQL+SQLite │ │  状态/任务/流程/规则 │
└────────────────┘ └──────────────┘ │  操作员/报修/模板/   │
                                    │  反馈/配置            │
         ▼                          └────────────────────┘
┌────────────────┐
│ wechat_cloud.py│──→ 企业微信模板消息 → 工人手机
│  (消息推送)     │
└────────────────┘

┌───────────────────┐     ┌─────────────────────┐
│ face-liveness-demo│     │    table-bot         │
│ FastAPI:8000      │     │  Flask:7860          │
│ 人脸检测+活体识别 │     │  表格机器人回调       │
│ BlazeFace         │     │  企微消息处理         │
│ FaceMesh 468点    │     │  XML加解密(WXBiz)     │
│ 余弦相似度 0.75   │     │                      │
└───────────────────┘     └─────────────────────┘
```

### 15.3 数据流向（企业微信消息全链路）

```
工人手机发送消息
       │
       ▼
企业微信服务器（公网回调）
       │
       ▼
内网 standalone_dispatch_server.py:5003
  → WXBizMsgCrypt解密(XML)
  → 指令匹配(cloud_matching)
  → 路由到对应handler
  → 写入容器中心(StorageLayer)
       │
       ▼
cloud_poller.py 轮询
       │
       ▼
wechat_cloud.py:5003 (云端)
  → 企业微信API主动推送
  → 模板消息发送
       │
       ▼
工人手机接收回复
```

---

## 十六、文件目录结构

### 16.1 项目总览

```
d:\yuan\
├── 不锈钢网带跟单系统3.01/     # 主软件 v3.01 (Tkinter桌面应用)
│   ├── main.py                 # 主入口（线程并行初始化）
│   ├── config.py               # 配置入口（兼容层）
│   ├── version.py              # 版本信息
│   ├── steel_belt_tracking.py  # 样式定义
│   ├── constants.py            # 常量定义
│   ├── core/                   # 核心模块
│   │   ├── __init__.py         # 统一导出
│   │   ├── app.py              # 应用初始化
│   │   ├── config.py           # 统一配置(路径/数据库/业务/API密钥/样式)
│   │   ├── database.py         # 数据库连接管理(with上下文)
│   │   ├── event_bus.py        # 事件驱动(6种事件类型)
│   │   ├── exceptions.py       # 统一异常定义
│   │   ├── logger.py           # 日志系统
│   │   ├── error_codes.py      # 错误码定义
│   │   └── error_handler.py    # 错误处理
│   ├── models/                 # 数据模型(DAO层)
│   │   ├── database.py         # 数据库连接池
│   │   ├── order.py            # 订单DAO(OrderDAO)
│   │   ├── production.py       # 生产工单DAO
│   │   ├── process.py          # 工序DAO
│   │   ├── quality.py          # 质检DAO
│   │   ├── inventory.py        # 库存DAO
│   │   ├── bom.py              # BOM表DAO
│   │   ├── operator.py         # 操作员DAO
│   │   ├── product_type.py     # 产品类型DAO
│   │   ├── material_rules.py   # 材料规则DAO
│   │   ├── quality_rule.py     # 质检规则DAO
│   │   ├── process_calc_rule.py # 工序计算规则DAO
│   │   ├── shipment.py         # 发货DAO
│   │   ├── alert.py            # 预警DAO
│   │   ├── order_log.py        # 订单日志DAO
│   │   ├── operation_log.py    # 操作日志DAO
│   │   ├── production_stats.py # 生产统计DAO
│   │   └── unit.py             # 单位DAO
│   ├── services/               # 业务服务层
│   │   ├── order_service.py    # 订单业务(OrderService)
│   │   ├── schedule_dispatch_service.py # 排产调度(ScheduleDispatchService)
│   │   ├── wechat_report_service.py     # 微信报工服务
│   │   ├── audit_service.py    # 审计服务
│   │   └── inventory_notifier.py        # 库存通知
│   ├── controllers/            # 控制器
│   ├── views/                  # Tkinter视图层
│   │   ├── main_window.py      # 主窗口
│   │   ├── order_view.py       # 订单视图
│   │   ├── production_view.py  # 生产视图
│   │   ├── process_view.py     # 工序视图
│   │   ├── quality_view.py     # 质检视图
│   │   ├── inventory_view.py   # 库存视图
│   │   ├── bom_view.py         # BOM视图
│   │   ├── kanban_view.py      # 看板视图
│   │   ├── dashboard_view.py   # 仪表盘
│   │   ├── settings_dialog.py  # 设置对话框
│   │   ├── wechat_report_view.py # 微信报工视图
│   │   └── ...                 # 其他视图
│   ├── utils/                  # 工具函数
│   │   ├── material_calculator.py # 材料计算器(安全求值)
│   │   ├── helpers.py          # 通用工具
│   │   ├── validators.py       # 验证器
│   │   ├── window_manager.py   # 窗口管理器
│   │   └── ...                 # 其他工具
│   ├── scripts/                # 脚本工具
│   │   ├── sync_orders.py      # 订单同步
│   │   ├── order_archive_manager.py # 订单归档
│   │   └── ...                 # 其他脚本
│   ├── security/               # 许可安全
│   │   ├── license_manager.py  # 许可证管理
│   │   ├── license_tool.py     # 许可证工具
│   │   └── machine_fingerprint.py # 机器指纹
│   └── data/                   # 数据文件
│       ├── steel_belt.db       # 业务SQLite库
│       └── window_config.json  # 窗口配置
│
├── 不锈钢网带跟单3.0/           # 后端微服务 (Flask)
│   └── mobile_api_ai/          # AI增强移动报工API
│       ├── app.py              # Flask应用工厂
│       ├── config.py           # 基础配置(BASE_DIR/端口/阈值/颜色)
│       ├── settings.py         # 统一配置管理(dataclass + .env)
│       ├── dispatch_center.py  # 调度中心(5783行)
│       ├── container_center_v5.py   # 容器中心v5核心(1323行)
│       ├── container_center_api.py  # 容器中心Flask API(2135行)
│       ├── container_center_client.py # 容器中心客户端(968行)
│       ├── storage_layer.py    # 存储抽象层(4127行)
│       ├── standalone_dispatch_server.py  # 企业微信内网服务（整合原 wechat_server.py）
│       ├── wechat_cloud.py     # 企业微信云端服务(1227行)
│       ├── cloud_matching.py   # 指令匹配引擎(32种命令)
│       ├── cloud_poller.py     # 云端轮询同步
│       ├── blueprint_registry.py # 蓝图注册(14个)
│       ├── config_center.py    # 配置中心(8大类29字段)
│       ├── container_config.py # 容器配置类(操作员/工序/数据类型/报修)
│       ├── enhanced_modules.py # 增强模块(7大组件)
│       ├── alert.py            # 告警通知(5级4渠道)
│       ├── data_integrity.py   # 数据完整性(SHA256+漂移检测)
│       ├── container_dashboard.py # 容器中心看板
│       ├── inventory_api_server.py # 库存API服务
│       ├── container_dashboard.py  # 容器中心看板
│       ├── constants.py        # 常量定义
│       ├── data/               # SQLite数据目录(17个库)
│       ├── logs/               # 日志目录
│       └── DAT/                # 数据备份目录
│
├── face-liveness-demo/         # 人脸识别考勤系统
│   └── server.py               # FastAPI服务(BlazeFace+FaceMesh)
│
├── table-bot/                  # 表格机器人
│   └── table_bot/
│       ├── app.py              # Flask企微回调服务器
│       ├── config.py           # 配置文件
│       └── wecom_crypto.py     # 企业微信加解密
│
└── 不锈钢网带跟单3.0/
    └── mobile_api/             # 移动报工API(v3兼容)
        └── api/
            └── scan.py         # 扫码API
```

### 16.2 后端微服务核心文件定位

| 功能 | 文件 | 行数 |
|------|------|------|
| 调度中心 | `mobile_api_ai/dispatch_center.py` | 5783 |
| 容器中心v5核心 | `mobile_api_ai/container_center_v5.py` | 1323 |
| 容器中心API | `mobile_api_ai/container_center_api.py` | 2135 |
| 容器中心客户端 | `mobile_api_ai/container_center_client.py` | 968 |
| 存储抽象层 | `mobile_api_ai/storage_layer.py` | 4127 |
| 微信内网服务 | `mobile_api_ai/standalone_dispatch_server.py` | 3068 |
| 微信云端服务 | `mobile_api_ai/wechat_cloud.py` | 1227 |
| 配置中心 | `mobile_api_ai/config_center.py` | 461 |
| 蓝图注册 | `mobile_api_ai/blueprint_registry.py` | 43 |
| 增强模块 | `mobile_api_ai/enhanced_modules.py` | 177 |
| 告警模块 | `mobile_api_ai/alert.py` | 281 |
| 统一配置 | `mobile_api_ai/settings.py` | 206 |
| 基础配置 | `mobile_api_ai/config.py` | 119 |
| 容器配置 | `mobile_api_ai/container_config.py` | 450 |

---

## 十七、关键技术栈

### 17.1 主软件 v3.01

| 技术 | 版本/用途 | 说明 |
|------|----------|------|
| **Python** | 3.10+ | 运行环境 |
| **Tkinter** | 标准库 | 桌面GUI框架 |
| **PyMySQL** | 数据库驱动 | MySQL连接 |
| **MySQL** | 8.0+ | 核心业务数据库 |
| **SQLite** | 标准库 | 本地存储 |
| **threading** | 标准库 | 并行初始化/后台任务 |
| **dataclasses** | 标准库 | 数据模型 |
| **PyInstaller** | 打包 | exe打包分发 |
| **企业微信API** | 回调+主动消息 | 报工通知集成 |

### 17.2 后端微服务

| 技术 | 版本/用途 | 说明 |
|------|----------|------|
| **Flask** | 2.x | Web框架 |
| **Flask-CORS** | 4.x | 跨域支持 |
| **Flask-SocketIO** | 5.x | WebSocket实时推送 |
| **MySQL** | 8.0+ | 核心业务数据库 |
| **SQLite** | 标准库 | 本地缓存(17个库) |
| **Redis** | 7.x | 缓存/队列(可选) |
| **WXBizMsgCrypt** | 企微官方 | XML消息加解密 |
| **requests** | 第三方 | HTTP调用 |
| **python-dotenv** | 1.x | .env文件加载 |
| **hashlib/hmac** | 标准库 | 签名认证 |
| **Gunicorn** | 21.x | WSGI服务器(生产) |
| **APScheduler** | 3.x | 定时任务(可选) |
| **concurrent.futures** | 标准库 | 线程池/进程池 |
| **PyInstaller** | 打包 | exe打包分发 |

### 17.3 人脸识别考勤

| 技术 | 版本/用途 | 说明 |
|------|----------|------|
| **FastAPI** | 0.100+ | Web框架 |
| **TensorFlow.js** | 4.x | BlazeFace人脸检测 |
| **FaceMesh** | MediaPipe | 468关键点提取 |
| **余弦相似度** | 阈值0.75 | 人脸比对 |
| **活体检测** | 自定义算法 | 防照片攻击 |
| **SQLite** | 标准库 | 考勤记录存储 |

### 17.4 表格机器人

| 技术 | 版本/用途 | 说明 |
|------|----------|------|
| **Flask** | 2.x | 企微回调服务器 |
| **WXBizMsgCrypt** | 企微官方 | XML加解密 |
| **企业微信API** | 回调 | 消息收发 |

---

## 十八、启动方式

### 18.1 主软件 v3.01

```bash
# 开发模式
cd d:\yuan\不锈钢网带跟单系统3.01
python main.py

# 打包分发
cd build_package
python scripts\build.py        # 普通打包
python scripts\build.py --clean # 清理后打包

# 诊断
python diagnose_startup.py
python diagnose_startup_full.py
```

### 18.2 后端微服务

```bash
cd d:\yuan\不锈钢网带跟单3.0\mobile_api_ai

# 启动容器中心 (端口5002)
python container_center_api.py

# 启动微信内网服务 (端口5003)
python standalone_dispatch_server.py

# 启动云端服务 (端口5003)
python wechat_cloud.py

# 启动调度中心 (端口5000)
python dispatch_center.py

# 启动库存API (端口5010)
python inventory_api_server.py

# 一键启动所有服务
python start_all.py

# 启动调度中心批处理
start 启动调度中心.bat

# 云端一键启动
start 云端一键启动.bat
```

### 18.3 人脸识别考勤

```bash
cd d:\yuan\face-liveness-demo
python server.py
# FastAPI 服务运行在 http://localhost:8000
```

### 18.4 表格机器人

```bash
cd d:\yuan\table-bot
python -m table_bot.app
# Flask 服务运行在 http://localhost:7860
```

### 18.5 环境要求

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.10 | 运行环境 |
| MySQL | >= 8.0 | 核心业务数据库 |
| Redis | >= 7.x (可选) | 缓存/队列 |
| Node.js | >= 18.x (可选) | 前端调试 |

**Python依赖安装**：

```bash
cd d:\yuan\不锈钢网带跟单3.0\mobile_api_ai
pip install -r requirements.txt

# 增强模块依赖（可选）
pip install -r enhanced_requirements.txt
```

---

> **文档维护说明**：
> - 本文档为系统核心架构参考，覆盖所有7个模块的整体架构、数据流动、推算逻辑、运算逻辑
> - 所有路径、端口、配置项均与源代码保持同步
> - 当架构发生重大变更时（如新增模块、端口变更、数据库结构变动、核心逻辑重构），必须同步更新本文档对应章节
> - 通过调度中心API可在线访问本文档：`GET /api/doc-center/documents/system-architecture`