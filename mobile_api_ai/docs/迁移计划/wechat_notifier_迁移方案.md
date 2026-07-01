# WeChatNotifier 弃用迁移方案

## 现状
- `integration/wechat_notifier.py` 已标记 `@deprecated`，启动时打印两行弃用警告
- `container_center_v5.py` 通过 `from integration import wechat_notifier` 引用旧实例
- 新旧两个 WeChatNotifier 并行存在，互不干扰

## 迁移目标
删除 `integration/wechat_notifier.py`，所有调用改用 `services.notifier.WeChatNotifier`

## 改动清单

### 1. 改导入（container_center_v5.py 顶部）

```python
# 删除：
from integration import wechat_notifier, desktop_callback_manager
WECHAT_NOTIFIER_AVAILABLE = True

# 改为：
from services.notifier import WeChatNotifier
```

### 2. 新增初始化

```python
# 在 container_center_v5 初始化处（确保 message_hub 已就绪后）
from services.notifier import WeChatNotifier
notifier = WeChatNotifier()
notifier.initialize(message_hub=message_hub, container_center=self)
```

### 3. 替换 3 处调用

| 位置 | 旧调用 | 新调用 |
|------|--------|--------|
| L343 `notify_low_stock` | `wechat_notifier.notify_low_stock({material_name, current_stock, ...})` | `notifier.notify_low_stock({material_name, current_stock, ...})`（签名兼容） |
| L708 `notify_task_assigned` | `wechat_notifier.notify_task_assigned(task_id=pkg.id, operator_id=..., task_title=..., related_order=...)` | `notifier.notify_task_assigned({'task_id': pkg.id, 'order_no': pkg.related_order, 'process': pkg.title, 'planned_qty': 0}, operator_id=pkg.target_operator)` |
| L961 `notify_task_completed` | `wechat_notifier.notify_task_completed(task_id=..., operator_id=..., task_title=..., result=...)` | `notifier.notify_task_completed({'task_id': package_id, 'order_no': ..., 'process': ..., 'completed_qty': 0})` |

### 4. 清理

- 删除 `integration/wechat_notifier.py`
- 删除 `integration/__init__.py` 中 WeChatNotifier 相关导出
- 删除 `container_center_v5.py` 中 `WECHAT_NOTIFIER_AVAILABLE` 和 `DESKTOP_CALLBACK_AVAILABLE` 相关变量

## 注意事项

- 新 notifier 的 `notify_task_assigned`/`notify_task_completed` 依赖 `message_hub` 初始化，**必须先调 `.initialize()`**，否则通知会静默失败
- `notify_low_stock` 新旧签名完全兼容，无感迁移
- 旧 notifier `operator_mapping`（张三/李四/王五...）写死在代码里，新 notifier 不用这个映射，如果依赖此功能需额外处理

## 风险等级

| 风险 | 说明 |
|------|------|
| 通知丢失 | 新 notifier 初始化顺序不当会导致消息发不出（高） |
| 功能回归 | 旧 notifier 注释后可安全删除（低） |
| 改动量 | 2 个文件，约 30 行（低） |
