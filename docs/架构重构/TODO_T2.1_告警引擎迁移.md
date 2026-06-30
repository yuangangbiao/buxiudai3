# TODO：T2.1 告警引擎迁移

## 已完成工作

### 核心交付
- ✅ `container_center/services/alert_engine.py` — AlertEngine 类（告警引擎）
- ✅ `container_center/services/__init__.py` — services 包初始化
- ✅ `dispatch_center.py` — `start_background_scheduler()` 改为使用 AlertEngine

### Bug 修复
- ✅ Flask 2.3.3 `bp.view_functions` 为空 → 所有 API 路由 500
  - 修复方案：`init_api_bp()` 直接模块属性赋值（`mod._store = store`）
  - 涉及文件：`container_center/api/__init__.py`、`container_center/api/health.py`
- ✅ 编译验证：所有 8 个文件通过
- ✅ API 路由验证：health、operators、configs、alerts、distribute 均正常

---

## 待办事项

### 需要你处理的

> 无 — 本次改动不涉及配置变更

### 后续任务（下一阶段）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P1 | T2.3 调度中心 P1 引用替换 | `dispatch_center.py` 中的旧 `_check_overdue_tasks()` 和 `_check_outsource_reminders()` 可移除 |
| P2 | T3.1 清理冗余代码 | 清理调度中心中不再使用的导入和辅助函数 |
| P3 | 单元测试 | 为 AlertEngine 编写 `check_overdue_tasks`、`check_outsource_reminders`、`_is_duplicate` 的测试用例 |

---

## 验证方式

1. 启动蓝图服务：`python -m container_center.api.app`
2. 验证路由：
   ```bash
   curl http://127.0.0.1:5002/api/v4/health
   curl http://127.0.0.1:5002/api/v4/operators
   curl http://127.0.0.1:5002/api/v4/configs/alert_rules
   curl http://127.0.0.1:5002/api/v4/alerts
   ```
3. 启动主应用：`python dispatch_center.py`（确认 `start_background_scheduler` 正常创建 AlertEngine）
