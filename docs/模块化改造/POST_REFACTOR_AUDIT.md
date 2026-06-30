# POST_REFACTOR_AUDIT.md（架构改造后悲观审计）

> 文档版本：v1.0（2026-06-13 悲观审计）
> 审计范围：P0-1 跨库直查清理 + P0-2 trace_id 实施 + 5 个 CRITICAL 修复
> 审计原则：**假设每行新代码都有 bug**

---

## 一、悲观审计发现

### 🔴 CRITICAL（7 项）

| # | 问题 | 严重度 | 证据 |
|---|------|--------|------|
| **C1** | sync_bridge.py 无镜像表同步代码 | 🔴 | grep 无 INSERT INTO orders_local |
| **C2** | 5002 容器中心未注册 trace 中间件 | 🔴 | grep `init_trace_middleware` No matches |
| **C3** | 5003 调度中心未注册 trace 中间件 | 🔴 | 同上 |
| **C4** | 8008 同步桥未注册 trace 中间件 | 🔴 | 同上 |
| **C5** | `BASE_DIR` 路径算错 | 🔴 | `os.path.dirname(os.path.dirname(__file__))` 多算一级 |
| **C6** | 5002 无 `/api/orders/<order_no>` 路由 | 🔴 | C5 修复调用的接口不存在 |
| **C7** | `_sync_to_mysql` 写操作未消除 | 🔴 | UPDATE production_orders/orders 仍在 |

### 🟡 HIGH（5 项）

| # | 问题 | 严重度 |
|---|------|--------|
| H1 | 5002/5003/8008 `from core.config` 路径问题 | 🟡 |
| H2 | 镜像表无任何写路径（DDL 创建但永远空） | 🟡 |
| H3 | trace_id 中间件只在 5008 注册，跨服务不连续 | 🟡 |
| H4 | C5 修复的 `traced_request` 调不存在接口 → 实际等于关闭订单校验 | 🟡 |
| H5 | mark_report_dead 函数未测试 | 🟡 |

### 🟢 MEDIUM（3 项）

| # | 问题 | 严重度 |
|---|------|--------|
| M1 | `core/config.py` 缺少 dispatcher_url 完整配置 | 🟢 |
| M2 | 镜像表同步冲突解决（last-write-wins vs CRDT） | 🟢 |
| M3 | trace 日志格式未统一（各服务可能不一致） | 🟢 |

---

## 二、详细问题分析

### C1: sync_bridge.py 无镜像表同步代码

**问题描述**：DDL 创建了 `orders_local`、`production_orders_local` 等 5 个本地表，但**没有代码向这些表写入数据**。

**影响**：
- 所有跨库直查的"读"操作会读到**空表**
- `_get_customer_group_for_order()` 永远返回 ''
- `list_violations()` 永远返回 []
- `schedule_routes._query_mysql_workorders()` 永远返回 []

**修复方案**：
```python
# sync_bridge.py 改造
# 在每个写入 steel_belt 的函数里，添加镜像写入
def sync_to_steel_belt_with_mirror(table, data):
    # 1. 写 steel_belt
    steelbelt_conn.execute(...)
    # 2. 写 container_center 本地表
    cc_conn.execute(f'INSERT INTO {table}_local ...', ...)
```

### C2-C4: trace 中间件未在 5002/5003/8008 注册

**问题描述**：我只改了 5008 app.py，其他服务**没注册中间件**。

**影响**：
- 5008 生成 trace_id，透传到 5002/5003/8008
- 下游服务**收到 X-Trace-Id header 但不读取**
- 下游日志**没有 trace_id**（链路断裂）
- 调试时只能看到 5008 的日志，看不到下游

**修复方案**：在 5002/5003/8008 入口都注册：
```python
from utils.trace import init_trace_middleware
init_trace_middleware(app)
```

### C5: BASE_DIR 路径错误

**问题描述**：
```python
# 错
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# __file__ = D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core\config.py
# dirname = D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core
# dirname dirname = D:\yuan\不锈钢网带跟单3.0  ← 错！

# 对
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# = D:\yuan\不锈钢网带跟单3.0\mobile_api_ai  ← 对
```

**影响**：
- `DB_PATHS` 指向 `D:\yuan\不锈钢网带跟单3.0\data\...` 而非 `D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\...`
- `ENTERPRISE_STRUCTURE_PATH` 路径错误

### C6: 5002 无 `/api/orders/<order_no>` 路由

**问题描述**：C5 修复调用了 `GET http://127.0.0.1:5002/api/orders/{order_no}`，但 5002 容器中心**没有这个路由**。

**影响**：
- 报工时订单校验 100% 返回 404（不是我以为的 200）
- C5 修复**实际上禁用了订单校验**（try/except pass 兜底）

### C7: `_sync_to_mysql` 写操作未消除

**问题描述**：
```python
# 修复后
conn = pymysql.connect(**CONTAINER_MYSQL_CFG)  # 连 container_center
c.execute("SELECT ... FROM production_orders_local")  # 读本地表 ✅
# 但下面还有：
c.execute("UPDATE production_orders SET status=...")  # 写原表 ❌
c.execute("UPDATE orders SET status=...")  # 写原表 ❌
```

**影响**：
- 写操作会写 `container_center.production_orders`（不是 `_local`）
- 这张表**根本不存在**（DDL 也没创建）
- 写入会失败，但被 except 吞掉

---

## 三、修复前后对比

| 指标 | 修复前 | "修复后"（乐观）| 实际（悲观） |
|------|--------|----------------|--------------|
| 跨库直查业务代码 | 8 处 | 0 处 | **0 处** ✅ |
| 镜像表有数据 | - | 应该有 | **❌ 永远空** |
| 订单校验可用 | ✅ | ✅ | **❌ 实际不可用** |
| trace_id 跨服务 | ❌ | ✅ | **❌ 仅 5008** |
| BASE_DIR 正确 | - | ✅ | **❌ 错** |
| `_sync_to_mysql` 写 | ✅ | ✅ | **❌ 会失败** |
| mark_report_dead | - | ✅ | **🟡 未测试** |
| **架构评分** | 80% | 90% | **真实 75%** |

---

## 四、累计修复成本

| 项 | 状态 | 实际工作量 |
|----|------|-----------|
| P0-1 跨库直查读路径 | 表面完成 | 实际 + 镜像表同步 **+16h** |
| P0-2 trace_id 实施 | 表面完成 | 实际 + 其他 3 服务注册 **+4h** |
| C5 core/config.py | 部分 | + 路径修正 + 加 5002 路由 **+4h** |
| C7 _sync_to_mysql 写 | 未做 | + 写路径改造 **+8h** |
| **总计** | **10h（乐观）** | **42h（悲观）** |

---

## 五、风险评估

| 风险 | 概率 | 影响 |
|------|------|------|
| 镜像表永远空，业务查不到数据 | 100% | 🔴 高 |
| 订单校验 100% 失效 | 100% | 🟡 中 |
| trace 跨服务不可用 | 100% | 🟡 中 |
| `_sync_to_mysql` 写失败被吞 | 100% | 🔴 高 |
| BASE_DIR 错导致路径问题 | 100% | 🟢 低 |

---

## 六、重新审计评分

| 维度 | 乐观 | 悲观 |
|------|------|------|
| 跨库直查读路径 | 18/20 | **15/20**（读改对，写未改） |
| 镜像表同步 | 18/20 | **0/20**（完全缺失） |
| trace 跨服务 | 16/20 | **6/20**（仅 5008） |
| 订单校验 | 18/20 | **0/20**（C5 修复不工作） |
| BASE_DIR | 18/20 | **10/20**（路径错） |
| 写操作事务 | 16/20 | **8/20**（破坏事务） |
| 错误处理 | 17/20 | **14/20**（C5 异常被吞） |
| **总分** | **121/160（76%）** | **53/160（33%）** |

---

## 七、必须立即修复

1. **C6**：5002 加 `/api/orders/<order_no>` 路由
2. **C7**：`_sync_to_mysql` 写路径改造（最复杂）
3. **C1**：sync_bridge 加镜像表同步
4. **C2-C4**：5002/5003/8008 注册 trace 中间件
5. **C5**：修正 BASE_DIR

---

## 八、参考

- [ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md) - 改造前审计
- [DAL_DESIGN.md](./DAL_DESIGN.md) - DAL 设计
- [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md) - 同步桥协议
