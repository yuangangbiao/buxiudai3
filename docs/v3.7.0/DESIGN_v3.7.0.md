# DESIGN v3.7.0 - 业务代码 P0 + L1 冒烟测试

> **版本**: v3.7.0
> **阶段**: 6A 阶段 2 (Architect)
> **日期**: 2026-06-25

---

## 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│  业务架构（v3.7.0 增量）                                      │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  调度中心 5003                                         │  │
│  │  ┌──────────────────┐    ┌──────────────────┐         │  │
│  │  │ _reconcile.py    │    │ _dlq_retry.py ★  │         │  │
│  │  │ (缓存对账)       │    │ (DLQ 重试 v3.7)  │         │  │
│  │  └──────────────────┘    └──────────────────┘         │  │
│  │         ↓                       ↓                       │  │
│  │  ┌────────────────────────────────────────┐            │  │
│  │  │  _core.py (9635 行, 暂不拆分)         │            │  │
│  │  │  修复 5+ 处 logger.error → exception  │            │  │
│  │  └────────────────────────────────────────┘            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  MySQL container_center.dlq 表                         │  │
│  │  ┌─────┬─────────┬────────────┬───────────┐           │  │
│  │  │ id  │ payload │ retry_count│ next_retry│           │  │
│  │  │  1  │ {...}   │     0      │  NULL     │           │  │
│  │  │  2  │ {...}   │     2      │  1700000  │           │  │
│  │  └─────┴─────────┴────────────┴───────────┘           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  tests/L1_smoke/  ★ 新增 5 文件                        │  │
│  │  test_login / test_order_create / test_process_publish│  │
│  │  test_quality_check / test_shipment                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2. 模块依赖关系

```
new:
  _dlq_retry.py → _db.py → MySQL
  tests/L1_smoke/test_*.py → tests/core/* (fixtures)

modify:
  standalone_dispatch_server.py: + start_dlq_retry_worker()
  _core.py: 修复 5+ 处 logger.error → logger.exception

delete:
  desktop_container_integration.py
```

## 3. 接口契约

### 3.1 DLQ retry worker API

```python
def start_dlq_retry_worker() -> bool:
    """启动 DLQ 重试 worker（幂等）"""
    # 1. 启动线程
    # 2. 注册到调度中心
    # 3. 返回启动状态


def _dlq_retry_loop() -> None:
    """主循环（每 N 秒）"""
    while True:
        time.sleep(interval)
        try:
            _dlq_retry_once()
        except Exception:
            logger.exception('[dlq_retry] 重试失败')


def _dlq_retry_once() -> int:
    """单次执行"""
    # 1. SELECT * FROM dlq WHERE next_retry_at <= NOW() LIMIT 100
    # 2. 对每条记录尝试重新发送
    # 3. 成功: DELETE
    # 4. 失败: UPDATE retry_count = retry_count + 1, next_retry_at = NOW() + 2^retry_count
    # 返回成功数量
```

### 3.2 L1 测试 API

```python
# tests/L1_smoke/conftest.py
@pytest.fixture(scope='module')
def l1_db():
    """L1 测试用内存数据库或 mock"""
    return MockDB()

# tests/L1_smoke/test_login.py
def test_admin_login(l1_db):
    """管理员登录冒烟测试"""
    # 不依赖真实服务
    # 验证业务逻辑
```

## 4. 数据流向图

### 4.1 DLQ 重试数据流

```
┌─────────────────┐
│  业务失败        │
│  (send failed)  │
└────────┬────────┘
         │ INSERT INTO dlq
         ↓
┌─────────────────┐
│  MySQL dlq 表   │ ← retry_count=0, next_retry_at=NOW()
└────────┬────────┘
         │ SELECT WHERE next_retry_at <= NOW()
         ↓
┌─────────────────┐
│  DLQ retry worker│ ← 独立线程，每 30s 一次
└────────┬────────┘
         │
    ┌────┴────┐
    │ 重试成功? │
    └────┬────┘
    是   │   否
    ↓    ↓   ↓
DELETE   UPDATE retry_count+=1
         next_retry_at = NOW() + 2^retry_count
```

## 5. 异常处理策略

### 5.1 DLQ retry worker

| 场景 | 处理 |
|------|------|
| MySQL 不可用 | 记录错误，下次重试 |
| 单条记录处理失败 | 跳过该条，继续其他 |
| 重试次数 ≥ 5 | 标记为 poison message，告警 |
| 进程被 kill | 下次启动时自然恢复 |

### 5.2 L1 测试

| 场景 | 处理 |
|------|------|
| Mock 失效 | pytest.fail + 截图 |
| 业务逻辑错误 | assert 失败信息 |
| 超时 | pytest timeout 30s |

## 6. 性能考虑

- DLQ retry worker 30s 间隔，每批 100 条
- 指数退避防止雪崩
- L1 测试每个 ≤30s，总 ≤5min

---

**下一阶段**: [TASK_v3.7.0.md](TASK_v3.7.0.md)
