# inventory_web 边界定义 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P2 文档，Week 1 明确边界即可
> **审计来源**: 4专家审计（小圣架构）→ H-1 + 小曦PM → C-3

---

## 一、现状

### 1.1 服务架构

```
端口 5008: mobile_api_ai/app.py（主API）
  └─ 使用 storage_layer（PooledDB连接池）✅

端口 5010: inventory_api_server.py（库存Web）
  └─ 使用 inventory_web/db_utils.py（Queue模拟连接池）⚠️
```

### 1.2 连接池现状对比

| 维度 | mobile_api_ai（5008） | inventory_web（5010） |
|------|----------------------|----------------------|
| **连接池方案** | PooledDB（DBUtils）✅ | queue.Queue（模拟）⚠️ |
| **连接管理** | 自动归还 | 手动管理 |
| **idle timeout** | PooledDB自动处理 | 无自动处理 |
| **最大连接数** | pool_size配置 | 无上限（内存决定） |
| **线程安全** | DBUtils保证 | queue.Queue保证 |
| **健康检查** | PooledDB ping | 无 |

### 1.3 依赖关系

```
inventory_web/
  db_utils.py
    └─ 用 queue.Queue 模拟连接池
    └─ 直接调用 pymysql.connect()（每次新建）
    └─ 无连接复用，超时手动补充

与主系统关系：
  └─ 5010 库存服务独立部署
  └─ 5008 app.py 的 inventory_external.bp 访问 5010 的 HTTP API
  └─ 无直接数据库共享（各用各的连接）
```

---

## 二、边界决策

### 2.1 关键问题

**问题**：Week 16 计划做"inventory_web连接池替换"，但 GAP-4 明确说"inventory_web独立服务，排除 Layer1"。

矛盾：
- 如果独立 → Week 16 优化什么？
- 如果不独立 → 为什么排除在 Layer1 之外？

### 2.2 决策方案

**推荐：保持独立，明确边界，纳入Phase4优化**

| 选项 | 描述 | 风险 | 决策 |
|------|------|------|------|
| **A：纳入v3.7.0统一改造** | 将inventory_web接入storage_layer | 改造工作量大（+2周），可能影响库存服务稳定性 | ❌ 排除 |
| **B：保持独立 + Phase4优化** | 保持独立服务，Week 16单独替换QueuePool为PooledDB | 架构不一致，但风险可控 | ✅ 推荐 |
| **C：完全不动** | QueuePool能跑就不管 | 技术债务持续积累 | ❌ 不推荐 |

**结论**：选择 **B** ——保持独立服务边界，Week 16做连接池优化，不纳入v3.7.0核心重构范围。

---

## 三、inventory_web 服务边界

### 3.1 职责边界

```
inventory_web（5010）负责：
  ✅ 库存产品管理（CRUD）
  ✅ 库存调拨
  ✅ 库存盘点
  ✅ 库存报表

inventory_web（5010）不负责：
  ❌ 生产订单（由5008负责）
  ❌ 工序管理（由5008负责）
  ❌ 质检管理（由5008负责）
  ❌ 发货物流（由5003负责）
```

### 3.2 数据边界

```
inventory_web 数据库（container_center）
  ✅ 独立表：products, inventory_transfers, stocktakes, inventory_reports

与5008的数据共享：
  ✅ 仅通过HTTP API访问，无直接数据库访问
  ✅ inventory_external.bp（app.py）→ 调用5010的HTTP接口
  ✅ 无跨库事务，保证数据最终一致
```

### 3.3 部署边界

```
独立部署：
  ✅ 独立进程：python inventory_api_server.py
  ✅ 独立端口：5010
  ✅ 独立日志：logs/inventory_api_server.log
  ✅ 独立健康检查：GET http://localhost:5010/health
  ✅ 独立重启：不影响5008/5003主服务
```

---

## 四、Week 16 Phase4 详细设计（inventory_web连接池优化）

> **注**：不纳入v3.7.0核心重构，单独作为Phase4任务在Week 16启动。

### 4.1 现状代码（db_utils.py）

```python
# inventory_web/db_utils.py
import queue, pymysql

_pool = queue.Queue(maxsize=10)

def get_connection():
    try:
        return _pool.get_nowait()
    except queue.Empty:
        return pymysql.connect(
            host=os.getenv('INVENTORY_DB_HOST', '127.0.0.1'),
            port=int(os.getenv('INVENTORY_DB_PORT', 3306)),
            user='root', password='xxx',
            database='container_center',
            connect_timeout=5
        )

def return_connection(conn):
    try:
        _pool.put_nowait(conn)
    except queue.Full:
        conn.close()  # 满了就丢弃，不优雅
```

**问题**：
- 连接超时后不自动补充（Queue为空的唯一解决方案是等待）
- maxsize=10 硬编码，无法动态调整
- return_connection 在 Queue.Full 时直接 close，下次新建
- 无idle timeout检测，长时间闲置连接可能已断

### 4.2 改造后代码（PooledDB标准）

```python
# inventory_web/db_utils.py
from DBUtils.PooledDB import PooledDB
import pymysql, os

INVENTORY_DB_CFG = {
    'host': os.getenv('INVENTORY_DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('INVENTORY_DB_PORT', 3306)),
    'user': 'root',
    'password': os.getenv('INVENTORY_DB_PASSWORD', ''),
    'database': 'container_center',
    'connect_timeout': 5,
    'read_timeout': 30,
    'charset': 'utf8mb4',
}

_pool = PooledDB(
    creator=pymysql,
    maxconnections=20,      # 最大20个连接（原Queue只有10）
    mincached=5,             # 最小保持5个空闲连接
    maxcached=10,           # 最多缓存10个空闲连接
    blocking=True,           # 获取不到连接时等待，不是抛异常
    maxusage=None,           # 单连接最大使用次数（None=无限）
    setsession=[],          # 连接建立后执行的SQL（如 SET NAMES utf8mb4）
    ping=1,                 # 取连接时检查连接是否有效
    **INVENTORY_DB_CFG
)

def get_connection():
    """从连接池获取连接，超时则抛异常"""
    return _pool.connection()

# 兼容旧API：旧代码调用 return_connection()，改为自动管理
def return_connection(conn):
    """保留此函数，旧代码迁移时不用改调用方"""
    conn.close()  # PooledDB的conn.close()是归还，不是真正关闭
```

### 4.3 改动清单

| # | 改动项 | 文件 | 行数 | 风险 |
|---|--------|------|:----:|:----:|
| 1 | 替换 PooledDB import | db_utils.py | 1 | 低 |
| 2 | 替换 _pool 初始化 | db_utils.py | ~15 | 中 |
| 3 | 修改 get_connection() | db_utils.py | 3 | 低 |
| 4 | 保留 return_connection()（兼容旧调用） | db_utils.py | 3 | 低 |
| 5 | 添加 INVENTORY_DB_CFG 配置 | db_utils.py | ~10 | 低 |

**注意**：inventory_web 是独立服务，改造时不影响5008主系统。

### 4.4 验收标准

| 指标 | 当前值 | 目标 | 验证方式 |
|------|:------:|:----:|---------|
| 连接复用率 | ~0% | ≥ 80% | 监控 Queue 消耗 vs 新建 |
| 库存服务P99 | 未知 | ≤ 1000ms | perf_baseline.py |
| 并发压测 | 未知 | 100并发×10轮零崩溃 | concurrency_test.py |
| 连接获取超时 | N/A | ≤ 2秒 | 压测观察 |

---

## 五、接口契约（5008 ↔ 5010）

### 5.1 当前HTTP接口

| 5008调用 | 5010提供 | 状态 |
|---------|---------|------|
| GET /api/inventory/products | GET /inventory/products | ✅ 已有 |
| POST /api/inventory/transfer | POST /inventory/transfer | ✅ 已有 |
| GET /api/inventory/stocktakes | GET /inventory/stocktakes | ✅ 已有 |

### 5.2 接口契约Schema（Week 16需完善）

```python
# 5008 调用 5010 的请求/响应规范

# GET /inventory/products
Request:
  Headers: Authorization: Bearer {token}
  Query: ?page=1&page_size=20

Response:
  {
    "code": 0,
    "data": {
      "items": [
        {
          "id": 1,
          "product_name": "不锈钢网带 A型",
          "spec": "2.0mm",
          "stock": 100,
          "unit": "米",
          "updated_at": "2026-06-28T10:00:00Z"
        }
      ],
      "total": 50,
      "page": 1,
      "page_size": 20
    }
  }
```

### 5.3 接口契约规则

1. **向后兼容**：5010的接口变更必须保证与5008兼容
2. **错误码统一**：5010的错误码格式必须与5008一致（code=0成功，code≠0失败）
3. **超时设置**：5008调用5010的HTTP请求超时 ≤ 5秒
4. **降级方案**：5010不可用时，5008的inventory_external.bp应返回友好错误（code=500，message="库存服务暂不可用"）

---

## 六、Phase4 实施计划

| 阶段 | 任务 | Week |
|------|------|:----:|
| Week 16 启动 | Phase4kickoff会议，确认db_utils.py改动范围 | 16 |
| Week 16 编码 | db_utils.py QueuePool→PooledDB改造 | 16 |
| Week 16 测试 | inventory_web独立压测 | 16 |
| Week 16 灰度 | 10%→30%→60%→100%放量（独立于G5） | 16 |
| Week 17 | Phase4验证 + 最终签字 | 17 |

---

## 七、签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | 确认边界 | ☐ |
| 架构（小圣） | 确认技术方案 | ☐ |
| PM（小曦） | 确认业务边界 | ☐ |

**决策**: 选择方案B（保持独立 + Phase4优化）
**最后更新**: 2026-06-28
