# 不锈钢网带跟单 3.0 — 缓存架构文档

> **文档版本**: v1.0
> **创建日期**: 2026-06-21
> **适用范围**: 全部 5 个服务（5002 容器中心 / 5003 调度中心 / 5008 移动端 / 5010 库存 / 8008 Sync Bridge）
> **维护人**: AI 助手
> **审计方式**: `python scripts/tools/cache_audit_static.py` + `python scripts/tools/cache_metrics.py`

---

## 一、整体架构

### 1.1 分层结构

```
┌────────────────────────────────────────────────────────────────┐
│  客户端层（Desktop Tkinter / 移动端 H5）                          │
│  ├─ 窗口配置     data/window_config.json       (本地 JSON)       │
│  ├─ 用户偏好     localStorage 等价物                            │
│  └─ 草稿暂存     IndexedDB 等价物（draft_service）              │
├────────────────────────────────────────────────────────────────┤
│  服务端层（Flask 5002/5003/5008/5010/8008）                       │
│  ├─ L1 内存缓存  字典+TTL（per Flask 规范）                       │
│  ├─ L2 Redis     mobile_api_ai/cache.py（分布式共享）           │
│  ├─ L3 预热      cache_warmup.py（7 个 key 启动加载）           │
│  ├─ 分布式锁     cache.py DistributedLock（SETNX+Lua）          │
│  ├─ 限流器       cache.py RateLimiter                            │
│  └─ 事件总线     core/redis_event_bus.py                         │
├────────────────────────────────────────────────────────────────┤
│  数据库层（MySQL）                                                │
│  └─ 真值源，缓存失效/穿透时回源                                    │
└────────────────────────────────────────────────────────────────┘
```

### 1.2 与云端 ERP 模式对比

| 维度 | 金蝶云/用友 YonBIP | 本项目 | 评价 |
|------|-------------------|--------|------|
| 客户端形态 | 浏览器 | Tkinter 桌面 + 移动端 H5 | ✅ 场景适配 |
| 浏览器缓存 | Service Worker + IndexedDB | 无（桌面端）/ draft_service（移动端） | ✅ 等价覆盖 |
| 共享缓存 | Redis | Redis | ✅ 一致 |
| 边缘缓存 | CDN | 无 | ⚠️ 内部系统可省 |
| 预热 | 服务端预热 | 启动 7 key 预热 | ✅ 简化版 |
| 离线 | Service Worker | draft_service | ✅ 等价 |
| 命中率监控 | 商业 APM | 已有（`cache_metrics.py`） | ✅ 自建 |

---

## 二、缓存使用清单

### 2.1 现状统计（来自 `cache_audit_static.py`）

```
扫描接口总数:        500
已用缓存:            4  (0.8%)
可缓存但未缓存:      100 (20%)
```

### 2.2 `cache.py` 直接调用方

| 模块 | 用途 | key 命名 | TTL |
|------|------|---------|-----|
| `wechat_server.py` | 微信回调幂等 | `wxname:{user_id}`, `confirm:{operator}` | 3600s |
| `container_center/storage/redis_cache.py` | 容器中心数据缓存 | 自定义 | 自定义 |
| `api_validators.py` | API 幂等校验 | `idem:{key}` | 60s |

### 2.3 进程内字典缓存（短 TTL）

| 缓存名 | 文件:行 | TTL | 用途 |
|--------|---------|-----|------|
| `_operators_cache` | dispatch_center/_core.py:995 | 300s | 操作员列表 |
| `_pd_cache` | dispatch_center/_core.py:1910 | 300s | 流程定义 |
| `_processes_cache` | dispatch_center/_core.py:3573 | 30s | 工序列表 |
| `_ssot_cache` | dispatch_center/_core.py:5099 | 10s | SSOT 状态查询 |
| `_customer_group_cache` | dispatch_center/_operators.py:38 | 300s | 客户分组 |
| `_mirror_auth_warn_cache` | container_center_api.py:2612 | 300s | IP 限频 |
| `_dedup_cache` | services/flow_type_alert.py:60 | 自定义 | 告警去重 |

### 2.4 启动预热（`cache_warmup.py`）

| # | Key | 数据 | TTL |
|---|-----|------|-----|
| 1 | `system:config` | 系统配置 | 600s |
| 2 | `product:types` | 产品类型 | 300s |
| 3 | `process:list` | 工序列表 | 300s |
| 4 | `operators:list` | 操作员 | 180s |
| 5 | `orders:active` | 活跃订单 | 60s |
| 6 | `material:rules` | 物料规则 | 300s |
| 7 | `templates:messages` | 消息模板 | 600s |

**调用入口**: `app.py:2515-2516`（5008 移动端异步预热）

---

## 三、cache.py 设计要点

### 3.1 惰性连接（`_LazyCacheProxy`）

```python
class _LazyCacheProxy:
    """首次调用方法时才连接 Redis"""
    def __getattr__(self, name):
        c = self._get_real_cache()
        return getattr(c, name)
```

**优点**：
- ✅ 启动不阻塞（不连 Redis 也能跑）
- ✅ 健康检查失败自动降级为内存后备
- ✅ 测试无需 Redis

### 3.2 三级降级

```
尝试 Redis → 失败 → MemoryCache → 失败 → 返回 None（业务层容错）
```

### 3.3 分布式锁

```python
class DistributedLock:
    """SETNX + Lua 脚本（释放时校验 token 防误删）"""
    with DistributedLock('order_123', timeout=10):
        # 临界区
        ...
```

### 3.4 限流器

```python
limiter = RateLimiter(key='login_ip', max_requests=10, window=60)
if not limiter.is_allowed():
    return '请求过于频繁', 429
```

---

## 四、命中率监控（`scripts/tools/cache_metrics.py`）

### 4.1 使用方法

```python
# 1. 在 cache.py 集成探针
from scripts.tools.cache_metrics import init_metrics
metrics = init_metrics()

class RedisCache:
    def get(self, key, default=None):
        start = time.time()
        try:
            value = self.client.get(key)
            if value is None:
                metrics.miss(key=key, elapsed_ms=(time.time()-start)*1000)
                return default
            metrics.hit(key=key, elapsed_ms=(time.time()-start)*1000)
            return json.loads(value)
        except Exception as e:
            metrics.error(op='get', key=key)
            return default

# 2. 暴露端点
@app.route('/api/metrics/cache')
def cache_metrics():
    return jsonify(metrics.snapshot())
```

### 4.2 输出示例

```json
{
  "overall": {
    "hits": 1234,
    "misses": 56,
    "errors": 0,
    "total_gets": 1290,
    "hit_rate_pct": 95.66
  },
  "by_prefix": [
    {"prefix": "operator", "total": 200, "hit_rate_pct": 99.5},
    {"prefix": "order", "total": 800, "hit_rate_pct": 92.0}
  ],
  "diagnosis": [
    {"level": "ok", "message": "总命中率 >= 60%，健康"}
  ]
}
```

### 4.3 诊断规则

| 指标 | 阈值 | 建议 |
|------|------|------|
| 总命中率 | < 30% | 🔴 TTL 过短或频繁失效 |
| 总命中率 | 30-60% | 🟡 有优化空间 |
| 总命中率 | >= 60% | 🟢 健康 |
| 某前缀命中率 | < 20% 且调用>=10 | 🟡 建议加缓存或延长 TTL |
| 错误率 | > 5% | 🔴 Redis 连接不稳 |

---

## 五、客户端缓存（桌面端 + 移动端）

### 5.1 桌面端（Tkinter）

| 机制 | 文件 | 用途 |
|------|------|------|
| 窗口尺寸/位置 | `data/window_config.json` | 重启恢复 |
| 用户偏好 | `BaseDialog` + `setup_resizable_window` | 持久化 |
| 自动刷新 | `utils/auto_refresh_mixin.py` | 5 分钟轮询重载 |

> ⚠️ **限制**：Tkinter 没有浏览器级缓存能力，故无 Service Worker / IndexedDB。

### 5.2 移动端（draft_service）

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/draft/save` | POST | 暂存草稿 |
| `/api/draft/list` | GET | 列草稿 |
| `/api/draft/<id>` | GET | 读单条 |
| `/api/draft/<id>` | DELETE | 删除 |
| `/api/draft/submit/<id>` | POST | 提交一条 |
| `/api/draft/sync_all` | POST | 批量同步 |
| `/api/draft/stats` | GET | 统计 |
| `/api/draft/cleanup` | POST | 清理已同步 |

**设计**：
- Redis 热存（TTL 7 天）+ MySQL 冷备（`report_drafts` 表）
- 状态机：`pending` → `syncing` → `synced` / `failed`
- 自动重试 3 次，失败保留草稿
- 38 个单元测试覆盖

---

## 六、改进路线（按 ROI 排序）

### 6.1 P0 立即做（影响大，成本低）

1. **给 100 个可缓存但未缓存的接口加缓存**（列表见 `cache_audit_report.md`）
   - 优先：`/api/orders/full-status/*`（5008 高频）
   - 优先：`/api/all-process-tasks`（调度中心首页）
   - 优先：`/api/report_record/list`（报工记录分页）

2. **集成 `cache_metrics` 探针到 `cache.py`**
   - 加 hit/miss 计数（参考 §4.1 代码）
   - 暴露 `/api/metrics/cache` 端点
   - 接入现有 Grafana

3. **写操作后主动失效缓存**
   - 在 `process_sub_step` 成功后清 `_PROCESS_TASKS_CACHE`
   - 在 `report_record/update` 成功后清相关 key

### 6.2 P1 短期（1-2 周）

1. **草稿系统集成到 `app.py` 报工流程**
   - 移动端报工失败自动 `POST /api/draft/save`
   - 网络恢复自动 `POST /api/draft/sync_all`
   - 给操作员"未同步草稿"红点提示

2. **缓存 key 命名规范**
   - 统一前缀：`{业务域}:{实体}:{id}` 例如 `order:full:WO-2024-001`
   - 已在 cache_warmup.py 实践（`system:config` 等）

3. **CDN/反向代理缓存静态资源**
   - 当前 Flask 直接服务，建议加 nginx

### 6.3 P2 中期（1 月+）

1. **ETag 协商缓存**
   - Flask `make_conditional` 装饰器
   - 适用：报表导出、字典

2. **服务间缓存共享**
   - 调度中心派单后，通过 Redis pub/sub 通知其他服务清缓存
   - 已有 `redis_event_bus.py` 基础

3. **接入 Redis Cluster**
   - 单点 Redis 容量风险
   - 当前 1 实例够用，但预留迁移能力

---

## 七、运维手册

### 7.1 日常检查

```bash
# 1. 缓存命中率（每小时）
curl http://localhost:5008/api/metrics/cache | jq '.overall.hit_rate_pct'

# 2. Redis 内存
redis-cli info memory | grep used_memory_human

# 3. 草稿积压
curl http://localhost:5008/api/draft/stats | jq '.data.by_status.pending'
```

### 7.2 故障处理

| 症状 | 排查 | 解决 |
|------|------|------|
| 命中率 < 30% | `_PROCESS_TASKS_CACHE` 是否被频繁清 | 检查 `clear_*_cache()` 调用点 |
| Redis 报错 | `_is_port_reachable` | 检查 6379 端口、密码 |
| 内存占满 | 草稿/字典 key 过多 | 调 `DRAFT_TTL_SECONDS`、清 `clear_pattern('dict:*')` |
| 报工丢数据 | 草稿服务未启动 | 检查 `draft_service.register_draft_routes` 是否调用 |

### 7.3 容量规划

| 资源 | 当前 | 上限 | 建议扩容触发 |
|------|------|------|-------------|
| Redis 内存 | ~50MB | 1GB | 700MB |
| 字典缓存 | 7 keys | 50 keys | 30 keys |
| 草稿/天 | 0 | 10000 | 5000 |

---

## 八、相关文件清单

| 文件 | 角色 |
|------|------|
| `mobile_api_ai/cache.py` | Redis 缓存核心（带内存降级） |
| `mobile_api_ai/cache_warmup.py` | 启动预热（7 个 key） |
| `mobile_api_ai/draft_service.py` | 草稿/离线队列服务 |
| `core/redis_event_bus.py` | 跨服务事件总线 |
| `core/circuit_breaker.py` | 熔断器 |
| `scripts/tools/cache_audit_static.py` | 静态覆盖率审计 |
| `scripts/tools/cache_metrics.py` | 运行时命中率探针 |
| `tests/unit/test_draft_service.py` | 38 个草稿服务测试 |
| `.trae/rules/Flask开发规范.md` | 进程内缓存规范 |

---

## 九、变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-21 | v1.0 | 初版（基于 5 服务审计 + 草稿服务） |
| 2026-06-15 | v0.9 | Flask 规范沉淀（字典缓存模式） |
| 2026-06-14 | v0.5 | cache.py 引入 DistributedLock + RateLimiter |
