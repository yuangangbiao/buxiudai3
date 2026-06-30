# ULTRA_PESSIMISTIC_AUDIT.md（最悲观水分审计 v2）

> 文档版本：v1.0（2026-06-13）
> 审计方法：脚本实际运行 / grep 查证
> 审计原则：**实测找问题，不靠嘴**

---

## 一、实测发现的 4 个新水分

### 🔴 Q8: F12 quantity NaN 抛异常（实测 BUG）

**实测**：
```python
from decimal import Decimal
def _validate_quantity(value):
    try:
        q = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False, '非法'
    ...

# 测试：
_validate_quantity(float('nan'))  
# → InvalidOperation 异常（str(nan)='nan' → Decimal('nan') 失败）
# 但异常被外层 except 捕获了吗？
```

**位置**：`container_center_api.py:2590-2600` 内部 `try/except` 只捕获 `InvalidOperation`，但**外层**没用 try/except。

**实际**：业务传 NaN → 500 错误 → 前端体验差。

**修复**：
```python
try:
    q = Decimal(str(value))
    if q.is_nan() or q.is_infinite():
        return False, 'quantity 不能为 NaN/inf'
except (InvalidOperation, TypeError, ValueError):
    return False, '非法'
```

### 🔴 Q9: outbox worker 初始调用未捕获异常

**位置**：`outbox_worker.py:248`

```python
def _worker():
    logger.info(f'[OUTBOX Worker] 启动，处理间隔 {interval_sec}s')
    # 启动时立即处理一次
    _process_outbox_once()  # ← 如果这行抛异常，整个 _worker 抛出
    while not _outbox_stop.is_set():
        for _ in range(int(interval_sec * 2)):
            if _outbox_stop.is_set():
                break
            time.sleep(0.5)
        if not _outbox_stop.is_set():
            try:
                _process_outbox_once()
            except Exception as e:
                logger.warning(f'[OUTBOX Worker] 异常: {e}')
```

**问题**：
- 第一次 `_process_outbox_once()`（L248）**在 while 外面**
- 抛异常 → `_worker` 抛 → **线程静默死亡**
- 5002 启动 OK，outbox 实际**不工作**
- 死信永远不处理
- P4 修复的"启动告警"**也救不了**

**修复**：
```python
def _worker():
    try:
        logger.info(...)
        _process_outbox_once()
    except Exception as e:
        logger.error(f'[OUTBOX Worker] 初始失败: {e}', exc_info=True)
        # 告警
        return
    while not _outbox_stop.is_set():
        ...
```

### 🔴 Q10: outbox worker 死亡后无人重启

**问题**：
- daemon 线程死了就死了
- 5002 一直运行但 outbox 不工作
- 没有 watchdog 定期检查"outbox worker 还在吗？"
- 没有"最后处理时间"指标

**修复**：
- 5002 启动时记 `_outbox_last_run_at`
- 定时任务：若 `now - _outbox_last_run_at > 60s` → 告警
- 或：worker 自动重启（with retry）

### 🔴 Q11: IP 白名单被 X-Forwarded-For 绕过

**位置**：`container_center_api.py:1823`

```python
remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
# ↑ 优先用 X-Forwarded-For！
```

**真实风险**：
- 远程攻击者设 `X-Forwarded-For: 127.0.0.1` → IP 白名单通过
- 只有共享密钥能拦住
- 但 P3 修复让密钥强制从环境变量读
- **如果密钥没配，密钥校验也失败**（`provided != _MIRROR_SHARED_SECRET` 因为后者是空字符串，前者也是空字符串 → 等于 → 通过！）

**真实 BUG！** 让我测试：