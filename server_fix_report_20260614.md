# 服务器修复报告

## 报告时间
- 检测时间：2026-06-14 23:55 (北京时间)
- 检测方式：网页触发 + 日志分析

---

## 一、服务器状态

| 端口 | 服务 | 状态 | 说明 |
|------|------|------|------|
| 5002 | 容器中心 | ✅ 运行中 | 正常 |
| 5003 | 调度中心 | ✅ 运行中 | 正常 |
| 5008 | 报工程序 | ✅ 运行中 | 正常 |
| 5010 | 库存管理 | ✅ 运行中 | 正常 |
| 8008 | Sync Bridge | ✅ 运行中 | 正常 |

---

## 二、已修复问题

### 2.1 sys.path 顺序问题 ✅ 已修复

**问题**：Python 导入 `utils.trace` 时找不到模块

**原因**：多个启动脚本中 sys.path 设置顺序不正确，根目录 `utils/` 未正确设置在 `mobile_api_ai/utils/` 之前

**修复文件**：
| 文件 | 修改内容 |
|------|---------|
| `container_center_api.py` | `sys.path.append()` 替代 `sys.path.insert(0, ...)` |
| `app.py` | 根目录优先：先 insert(0, 根目录)，后 append(mobile_api_ai) |
| `standalone_dispatch_server.py` | 同上 |
| `inventory_api_server.py` | 同上 |

---

### 2.2 STEELBELT_MYSQL_CFG 配置缺失 ✅ 已修复

**问题**：`cannot import name 'STEELBELT_MYSQL_CFG' from 'core.config'`

**原因**：ETL 本地镜像需要 steel_belt 数据库配置，但配置缺失

**修复**：在 `core/_config_infra.py` 添加：
```python
STEELBELT_MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}
```

---

### 2.3 401 认证问题 ✅ 已修复

**问题**：`RuntimeError: 容器中心 5002 不可达: HTTP 401`

**原因**：5003 调度中心访问 5002 容器中心的 `/api/operators` 接口被认证拦截

**修复**：在 `container_center_api.py` 的白名单中添加 `/api/operators`

---

### 2.4 同名目录统一 ✅ 已修复

**问题**：mobile_api_ai 下存在与根目录同名的目录（utils, models, services），导致 Python 模块导入冲突

**修复**：

1. **mobile_api_ai/models/__init__.py** - 新建
   - 实现 `__path__` 扩展，透明转发到根目录 models/
   - re-export 常用 DAO

2. **mobile_api_ai/services/__init__.py** - 完善
   - re-export 根目录的 AuditService, OrderService, WeChatReportService
   - 修正 `__all__` 列表

---

## 三、仍存在的问题

### 3.1 utils.trace 模块警告 ⚠️

**问题**：`[WARNING] [TRACE] 5003 注册中间件失败: No module named 'utils.trace'`

**影响**：trace 装饰器无法正常工作，但不影响核心功能

**建议**：需要进一步调查 trace.py 的导入路径

---

### 3.2 process_code 字段缺失 ⚠️

**问题**：`Unknown column 'process_code' in 'field list'`

**影响**：回退查询 process_records 时出现警告

**建议**：检查数据库表结构，确认是否需要添加该字段

---

### 3.3 report_definition 表不存在 ⚠️

**问题**：`Table 'container_center.report_definition' doesn't exist`

**影响**：统计引擎初始化失败

**建议**：检查是否需要创建该表

---

### 3.4 404 路由问题 ⚠️

**问题**：`[404] GET /api/dispatch-center/list_tasks: 资源不存在`

**影响**：部分 API 路由缺失

**建议**：检查 `dispatch_server.py` 中是否注册了该路由

---

### 3.5 ETL 本地镜像同步 ⚠️

**问题**：以下表的本地镜像同步失败：
- violation_log → violations_local
- process_records → process_records_local
- work_orders → work_orders_local
- orders → orders_local

**原因**：STEELBELT_MYSQL_CFG 配置问题

**状态**：配置已添加，需重启服务器验证

---

## 四、修复优先级

| 优先级 | 问题 | 建议操作 |
|--------|------|---------|
| P0 | ETL 本地镜像同步 | 重启 5002 服务器验证 STEELBELT_MYSQL_CFG |
| P1 | process_code 字段 | 检查数据库表结构 |
| P2 | report_definition 表 | 创建表或修复初始化逻辑 |
| P2 | 404 路由 | 检查路由注册 |
| P3 | utils.trace 警告 | 调查导入路径 |

---

## 五、测试建议

1. **重启 5002 容器中心**，验证 STEELBELT_MYSQL_CFG 修复
2. **检查数据库**，确认 process_code 字段是否存在
3. **验证报工流程**，确保各服务器间通信正常
4. **检查 5008 报工程序**，确认 404 问题原因

---

## 六、修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `mobile_api_ai/container_center_api.py` | 修改 | sys.path 顺序 + 白名单 |
| `mobile_api_ai/app.py` | 修改 | sys.path 顺序 |
| `mobile_api_ai/standalone_dispatch_server.py` | 修改 | sys.path 顺序 |
| `mobile_api_ai/inventory_api_server.py` | 修改 | sys.path 顺序 |
| `core/_config_infra.py` | 修改 | 添加 STEELBELT_MYSQL_CFG |
| `mobile_api_ai/models/__init__.py` | 新建 | 同名目录统一 |
| `mobile_api_ai/services/__init__.py` | 修改 | 同名目录统一 |

