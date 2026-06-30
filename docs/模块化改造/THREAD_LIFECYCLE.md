<!-- ⚠️ ARCHITECTURE_AUDIT_WARNING_START -->

> **⚠️ 本文档部分内容已过期（2026-06-20 架构审计）**
>
> **审计报告**: [`docs/架构文档审计/ARCHITECTURE_AUDIT_REPORT.md`](../../架构文档审计/ARCHITECTURE_AUDIT_REPORT.md)
>
> 本文档含以下已过期内容（**不应直接采信**）：
>
> - 引用了已删除的入口文件（`wechat_work_bot_v2.py` / `dispatch_center.py` / `dashboard_server.py` / `inventory_*.py` 等）
> - 描述 SQLite 容器池（`wechat_container.db`），实际已迁移到 MySQL `container_center` 库
> - 端口描述可能与 `start_*.py` 启动脚本不一致
> - 5006 直连违反 `.trae/rules/云端通信架构规范.md`（必须通过 5003 转发）
>
> 涉及**启动入口 / 端口 / 服务名 / 数据库连接**时，**以以下真值为准**：
>
> - 入口：`mobile_api_ai/{standalone_dispatch_server.py, app.py, container_center_api.py, inventory_api_server.py, sync_bridge_server.py}`
> - 启动：`start_{5002,5003,5008,5010,8008}.py`
> - 配置：`core/_config_infra.py` + `.env`
> - 容器池：`CONTAINER_STORAGE_TYPE=mysql`（默认）
>
> 保留原因：文档中**部分设计/决策/业务流程**仍有参考价值。

<!-- ⚠️ ARCHITECTURE_AUDIT_WARNING_END -->



# THREAD_LIFECYCLE.md（线程管理规范）

> 文档版本：v1.0（2026-06-13）
> 关联：H2 修复

---

## 一、问题

当前 `thread_lifecycle.py` 已存在但**未集成**，存在以下问题：

- `dispatch_center.py` 中的后台线程未注册到 `thread_lifecycle` 管理器
- `atexit` 调用 `shutdown_all()` 但找不到线程
- 进程退出时线程未优雅关闭

---

## 二、规范

### 2.1 必须注册的后台线程

| 位置 | 线程名 | 用途 |
|------|--------|------|
| `dispatch_center/_core.py:828` | `dispatch_scheduler` | 持久化调度 |
| `dispatch_center/_core.py:4158-4159` | `sync_status` | 状态同步 |
| `dispatch_center/_core.py:4480` | `ack_async` | 异步确认 |
| `dispatch_center/_core.py:7032` | `outbox_consumer` | outbox 消费 |
| `sync_bridge.py:613` | `status_changer` | 状态变更 |
| `cloud_poller.py` | `cloud_poll` | 云端轮询 |

### 2.2 注册规范

```python
from thread_lifecycle import register_thread, create_daemon_thread

# ✅ 正确：使用 create_daemon_thread 自动注册
def start_scheduler():
    def _run():
        while not is_shutting_down():
            do_work()
    
    thread = create_daemon_thread(
        name='dispatch_scheduler',
        target=_run,
    )
    return thread

# ❌ 错误：直接创建 Thread
import threading
thread = threading.Thread(target=_run)  # 未注册，无法管理
```

### 2.3 优雅关闭

```python
from thread_lifecycle import is_shutting_down, shutdown_all

def _run():
    while not is_shutting_down():
        try:
            do_work()
        except Exception as e:
            logger.exception(f'线程异常: {e}')

# 进程退出时
atexit.register(shutdown_all, timeout=10.0, force=False)
```

---

## 三、API

### 3.1 `register_thread(name, thread, cleanup_func=None)`

注册线程到管理器。

```python
register_thread(
    name='my_thread',
    thread=thread_obj,
    cleanup_func=lambda: cleanup(),  # 优雅关闭时调用
)
```

### 3.2 `unregister_thread(name)`

从管理器注销线程。

### 3.3 `get_thread(name) -> Optional[ThreadInfo]`

获取线程信息。

### 3.4 `list_threads() -> List[ThreadInfo]`

列出所有已注册线程。

### 3.5 `stop_thread(name, timeout=5.0) -> bool`

停止单个线程。

```python
stop_thread('dispatch_scheduler', timeout=5.0)
```

### 3.6 `shutdown_all(timeout=10.0, force=False) -> Dict[str, bool]`

停止所有线程。

```python
result = shutdown_all(timeout=10.0, force=False)
# {'dispatch_scheduler': True, 'sync_status': True, ...}
```

### 3.7 `create_daemon_thread(name, target, args=(), kwargs=None) -> Thread`

**推荐**：创建并自动注册守护线程。

```python
def _worker():
    while not is_shutting_down():
        do_work()

thread = create_daemon_thread(
    name='my_worker',
    target=_worker,
)
```

### 3.8 `is_shutting_down() -> bool`

检查是否正在关闭（线程内部循环应检查此标志）。

---

## 四、集成清单

### 4.1 调度中心集成

**位置**：`dispatch_center/_core.py`

```python
# 之前
import threading
self.scheduler_thread = threading.Thread(target=self._run_scheduler)
self.scheduler_thread.daemon = True
self.scheduler_thread.start()

# 之后
from thread_lifecycle import create_daemon_thread
self.scheduler_thread = create_daemon_thread(
    name='dispatch_scheduler',
    target=self._run_scheduler,
)
self.scheduler_thread.start()
```

### 4.2 Sync Bridge 集成

**位置**：`sync_bridge.py`

```python
# 之后
from thread_lifecycle import create_daemon_thread
self.status_thread = create_daemon_thread(
    name='status_changer',
    target=self._status_changer_loop,
)
self.status_thread.start()
```

### 4.3 云端服务集成

**位置**：`cloud_poller.py`

```python
# 之后
from thread_lifecycle import create_daemon_thread
self.poll_thread = create_daemon_thread(
    name='cloud_poll',
    target=self._poll_loop,
)
self.poll_thread.start()
```

---

## 五、测试

### 5.1 单元测试

```python
def test_thread_registration():
    def _run():
        while not is_shutting_down():
            time.sleep(0.1)
    
    thread = create_daemon_thread('test_thread', _run)
    thread.start()
    time.sleep(0.5)
    
    threads = list_threads()
    assert any(t.name == 'test_thread' for t in threads)
    
    stop_thread('test_thread')
    time.sleep(0.5)
    
    threads = list_threads()
    assert not any(t.name == 'test_thread' for t in threads)
```

### 5.2 集成测试

```python
def test_shutdown_all():
    def _worker1():
        while not is_shutting_down():
            time.sleep(0.1)
    
    def _worker2():
        while not is_shutting_down():
            time.sleep(0.1)
    
    t1 = create_daemon_thread('worker1', _worker1)
    t2 = create_daemon_thread('worker2', _worker2)
    t1.start()
    t2.start()
    time.sleep(0.5)
    
    result = shutdown_all(timeout=2.0)
    assert result['worker1'] is True
    assert result['worker2'] is True
```

---

## 六、监控

### 6.1 线程数监控

```python
@app.route('/api/perf/threads', methods=['GET'])
def perf_threads():
    return jsonify({
        'code': 0,
        'data': {
            'count': len(list_threads()),
            'threads': [
                {'name': t.name, 'alive': t.is_alive()}
                for t in list_threads()
            ]
        }
    })
```

### 6.2 告警

| 指标 | 阈值 | 告警 |
|------|------|------|
| 线程数 | > 20 | WARNING |
| 线程存活时间 | > 1 小时（不健康） | WARNING |
| 线程停止失败 | - | ERROR |

---

## 七、参考

- `mobile_api_ai/thread_lifecycle.py`（已存在，需集成）
- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md)
