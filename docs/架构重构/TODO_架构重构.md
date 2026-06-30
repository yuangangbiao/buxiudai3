# TODO：架构重构（剩余事项）

## 已完成工作总结

### P0 阶段
- ✅ 存储层基础（router, document_store, config_store, alert_store, index_store）
- ✅ HTTP API 路由蓝图（configs, documents, alerts, health）
- ✅ SDK 客户端 ContainerCenterClient
- ✅ dispatch_center.py 存储直引 → SDK 客户端
- ✅ wechat_server.py 存储直引 → SDK 客户端

### P1 阶段
- ✅ 告警引擎 AlertEngine 迁移（`container_center/services/alert_engine.py`）
- ✅ 告警规则配置 API（`get_alert_rules`, `update_alert_rules`, `list_operators`）
- ✅ `dispatch_center.py` 中 `cc.distributor` / `cc.config` / `cc.collect_outsource` → SDK
- ✅ `_send_wechat_via_cloud()` 全部 3 处调用 → `_get_client().send_message()` 直接调用
- ✅ `wechat_server.py` 中 `_container_center.distributor.distribute()` → `_get_client().distribute()`

### 清理工作
- ✅ 删除 `_send_wechat_via_cloud()` 函数定义
- ✅ 删除 `_check_overdue_tasks()` 旧函数
- ✅ 删除 `_check_outsource_reminders()` 旧函数
- ✅ 删除 `integration/timeout_reminder.py`
- ✅ 清理 `integration/__init__.py` 中 timeout_reminder 导入

---

## 待办事项

> 以下为**需要你决策**或**可后续优化**的事项

### 需要你处理的

| # | 事项 | 说明 | 操作指引 |
|---|------|------|---------|
| 1 | 无 — 本次不需要配置变更 | ALIGNMENT/ 修改完成了全部的 `_send_wechat_via_cloud` 替换和死代码清理，无新增配置项 | — |

### 后续优化建议

| 优先级 | 事项 | 说明 |
|:------:|------|------|
| P3 | 告警规则配置前端页面 | 在 `templates/dispatch_center.html` 中新增告警规则可视化配置区域 |
| P3 | wechat_server.py `_container_center` 完全消除 | 仍有 7 处引用，需逐步替换为 SDK 客户端，最后删除 `container_center_v5` 直接依赖 |
| P3 | 单元测试补充 | 为 AlertEngine (check_overdue_tasks, check_outsource_reminders, _is_duplicate) 和 API 路由编写测试 |

---

## 验证方式

### 编译检查
```bash
cd mobile_api_ai
python scripts/check_compile.py
```
输出应为全部 9 个文件 `[OK]`。

### API 路由测试
```bash
# 终端 1: 启动蓝图服务
python -m container_center.api.app

# 终端 2: 测试路由
curl http://127.0.0.1:5002/api/v4/health
curl http://127.0.0.1:5002/api/v4/configs
curl http://127.0.0.1:5002/api/v4/operators
```

### 主应用启动测试
```bash
python dispatch_center.py
```
确认无 ImportError / AttributeError，`start_background_scheduler()` 正常创建 AlertEngine。
