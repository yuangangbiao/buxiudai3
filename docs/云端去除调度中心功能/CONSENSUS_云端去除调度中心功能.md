# CONSENSUS — 云端去除调度中心功能

> 阶段 1: Align（对齐阶段）· 共识文档
> 时间：2026-06-08
> 状态：已对齐，待进入阶段 2 (Architect)

---

## 一、明确的需求描述

将 15003 云端 wechat_server.py 中 22 个 `/api/sync/*` 业务 API 中的 16 个真新增端点，迁移到本地 5003 standalone_dispatch_server.py 的新蓝图 `sync_bp` 下；3 个真重复端点不迁移，让调用方改打 5003 已有的等价端点；1 个云端专属端点（report/wechat）不加；3 个真重复对应的本地等价端点（schedule_bp / dispatch_center_bp）需补注册。

---

## 二、技术实现方案

### 2.1 技术栈

| 维度 | 选型 |
|------|------|
| 蓝图框架 | Flask Blueprint（已有模式） |
| HTTP 客户端 | requests（容器中心 5002 通信） |
| 容器中心 SDK | container_center_api 模块的 SDK 客户端 |
| 8008 桥调用 | bridge.sync_client.send() 统一入口 |
| MySQL 直读 | pymysql + .env 读密码（已有 db_config.py） |
| 加密/校验 | hashlib（SHA256）、re（正则） |
| 单例 | 模块级变量（_circuit_breaker, _queue） |

### 2.2 集成方案

| 集成点 | 集成方式 |
|--------|----------|
| Flask 蓝图注册 | standalone_dispatch_server.py:90 之后补 5 行 |
| 容器中心 SDK | from container_center_api import _get_container_center |
| 8008 桥 | from bridge.sync_client import send |
| MySQL 读 | from db_config import get_db_config + pymysql |
| 熔断器/队列 | 模块内单例（_CircuitBreaker 类） |
| 操作日志读 | from operation_log import get_operation_log_db |

### 2.3 技术约束

- **不动** container_center_api.py / desktop_container_integration.py / wechat_server.py 业务逻辑
- **不动** 8008 已有 4 端点
- **不引入** 新的第三方库（requests / pymysql / flask 已存在）
- **必须**遵循 jgs7.md 规范（无硬编码密码/路径/阈值；logger 不用 print；context manager 用 get_db_cursor）
- **必须**给所有 16 个端点函数加 docstring（功能/参数/返回值/异常）

### 2.4 集成方案（数据流）

```
                 5003 dispatch-center
                       │
   ┌───────────────────┼───────────────────┐
   ↓                   ↓                   ↓
业务操作类 (11个)    数据落库类 (1个)     读类 (4个)
调容器中心 SDK       调 8008 桥          直读 MySQL
   ↓                   ↓                   ↓
5002 容器中心      8008 sync_bridge    MySQL steel_belt
   ↓ 容器中心自己
8008 桥
   ↓
MySQL
```

---

## 三、任务边界限制

### 3.1 代码改动范围

| 文件 | 改动类型 | 行数 |
|------|---------|------|
| mobile_api_ai/sync_bp.py | **新建** | ~600 行 |
| mobile_api_ai/standalone_dispatch_server.py | 改 1 处（补 3 蓝图注册） | +15 行 |
| mobile_api_ai/sync_bridge.py | 改 1 处（新增 1 端点） | +50 行 |
| .trae/rules/wechat_server_cloud_only.md | 改（规则更新） | +10 行 |
| docs/云端去除调度中心功能/* | **新建** 4 文档 | ~1500 行 |
| d:\yuan\构想文件\云端去除调度中心功能/* | **新建** 4 文档副本 | ~1500 行 |

### 3.2 不改动范围（边界外）

- 容器中心 5002 / 桌面端 5000 / 8008 已有 4 端点
- miniprogram-v2（已归档）
- desktop_container_integration.py
- wechat_server.py 业务逻辑（仅改规则文件说明允许改动）

### 3.3 不可绕过的前置

- F1（operation_logs.direction 列）由云端修复，本地不操作
- F2（订单号正则）本地按正确正则 `^ORD-\d{8,}$` 写
- F3（Content-Type）本地先 try JSON，再 try form

---

## 四、验收标准（与 ALIGNMENT 第六章一致）

详见 [ALIGNMENT_云端去除调度中心功能.md §六](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/docs/%E6%9C%8D%E5%8A%A1%E7%AB%AF%E5%8E%BB%E9%99%A4%E8%B0%83%E5%BA%A6%E4%B8%AD%E5%BF%83%E5%8A%9F%E8%83%BD/ALIGNMENT_%E4%BA%91%E7%AB%AF%E5%8E%BB%E9%99%A4%E8%B0%83%E5%BA%A6%E4%B8%AD%E5%BF%83%E5%8A%9F%E8%83%BD.md)

汇总：
- 16 端点全部注册（AC-1, AC-3）
- 补注册 schedule_bp + workorder_bp（AC-2）
- 8008 report-confirm 可用（AC-4）
- report/confirm 走 8008 桥（AC-5）
- 业务操作类调容器中心 SDK（AC-6）
- 校验/熔断/队列内存正确（AC-7, AC-8, AC-9）
- F1 依赖端点返 500 而非 404（AC-10）
- 4 文档齐备（AC-11）
- 规则更新（AC-12）
- 函数级注释完整（AC-13）
- 同步到构想文件（AC-14）
- 桌面端/容器中心/8008 已有端点 0 改动（AC-15, AC-16, AC-17）
- 重复 3 端点不在 5003（AC-18）

---

## 五、已解决的不确定性

| 编号 | 问题 | 答案 |
|------|------|------|
| Q-1 | 端点数量 | 16（22-3 真重复-1 云端专属-2 schedule_bp 等价后被吸收） |
| Q-2 | 路径前缀 | /api/sync/*（保留原命名空间，与 15003 兼容） |
| Q-3 | 实现路径 | 3 类：调容器中心 SDK / 调 8008 桥 / 直读 MySQL |
| Q-4 | 错误码 | 沿用现有约定：200 成功 / 400 入参错 / 404 资源不存在 / 500 服务异常 |
| Q-5 | 鉴权 | 沿用容器中心 SDK 内置 require_api_key（如果适用） |
| Q-6 | 限流 | 沿用 standalone_dispatch_server.py 全局 Limiter 1000/天 300/小时 |
| Q-7 | CORS | 沿用 init_cors(app, default_origins=...) |
| Q-8 | 日志 | 沿用 logger = logging.getLogger('sync_bp') |
| Q-9 | 异常处理 | 沿用全局 handle_global_exception（standalone_dispatch_server.py:127） |
| Q-10 | 错误响应格式 | {'code': int, 'message': str, 'data': ...}（与 15003 一致） |

---

## 六、达成共识

- ✅ 任务范围清晰
- ✅ 技术方案与现有架构对齐
- ✅ 验收标准具体可测试
- ✅ 所有关键假设已确认
- ✅ 项目特性规范已对齐

**进入阶段 2: Architect（生成 DESIGN 文档）**
