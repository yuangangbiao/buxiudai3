# ACCEPTANCE：架构重构（综合验收）

## 完成状态总览

| 阶段 | 任务 | 状态 |
|------|------|:----:|
| P0 | T1.1 存储层基础（router / 4 stores） | ✅ |
| P0 | T1.2 HTTP API 路由 | ✅ |
| P0 | T1.3 SDK 客户端 | ✅ |
| P0 | T1.4 dispatch/wechat 存储直引替换 | ✅ |
| P1 | T2.1 告警引擎迁移 | ✅ |
| P1 | T2.2 告警规则配置 API | ✅ |
| P1 | T2.3 调度中心引用替换 | ✅ |
| P1 | **P1 收尾：`_send_wechat_via_cloud` 替换** | ✅ |
| P1 | **P1 收尾：wechat_server distributor 替换** | ✅ |
| P2 | T3.1 清理死代码 | ✅ |
| P2 | **删除 `integration/timeout_reminder.py`** | ✅ |

---

## 1. T3.1 死代码清理明细

### 1.1 dispatch_center.py 已删除

| 删除内容 | 行号 | 原因 |
|---------|------|------|
| `_send_wechat_via_cloud()` | 原 39-45 | 已被 3 处直接 `_get_client().send_message()` 替换 |
| `_check_overdue_tasks()` | 原 1725-1772 | 已迁移至 AlertEngine |
| `_check_outsource_reminders()` | 原 1775-1828 | 已迁移至 AlertEngine |

### 1.2 dispatch_center.py 已替换

| 替换内容 | 说明 |
|---------|------|
| `_send_wechat_message()` | 从 `_send_wechat_via_cloud()` 改为 `_get_client().send_message()` |
| `_send_wechat_app_message()` | 同上 |
| `_send_to_department_members()` | 同上（line 372） |

### 1.3 wechat_server.py 已替换

| 替换内容 | 说明 |
|---------|------|
| `_container_center.distributor.distribute()` | 改为 `_get_client().distribute()` |

### 1.4 已删除文件

| 文件 | 原因 |
|------|------|
| `integration/timeout_reminder.py` | 功能已由 AlertEngine 取代 |

### 1.5 已更新文件

| 文件 | 操作 |
|------|------|
| `integration/__init__.py` | 移除 `timeout_reminder` 导入和 `__all__` 条目 |

---

## 2. 编译验证

```
[OK] dispatch_center.py
[OK] container_center/__init__.py
[OK] container_center/services/__init__.py
[OK] container_center/services/alert_engine.py
[OK] container_center/api/configs.py
[OK] container_center/api/documents.py
[OK] container_center/api/__init__.py
[OK] container_center/client/container_client.py
[OK] integration/__init__.py
(9 files)
```

---

## 3. API 路由测试结果

| 路由 | 方法 | 状态 |
|------|------|:----:|
| `/api/v4/health` | GET | ✅ |
| `/api/v4/operators` | GET | ✅ |
| `/api/v4/configs` | GET | ✅ |
| `/api/v4/configs/alert_rules` | GET | ✅ |

---

## 4. 已知残留（下一阶段处理）

| 残留 | 位置 | 说明 |
|------|------|------|
| `_container_center` 对象 | wechat_server.py 全局 | 仍有多处使用，不可一次性删除，需逐步分离 |
| `from container_center_v5 import ContainerCenter as cc` | wechat_server.py:187 | 待完全消除 `_container_center` 后删除 |
| `_get_container_center()` | --- | 已于之前阶段删除 ✅ |
