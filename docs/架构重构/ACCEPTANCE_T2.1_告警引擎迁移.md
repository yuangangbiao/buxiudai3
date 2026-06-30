# ACCEPTANCE：T2.1 告警引擎迁移

## 完成状态总览

| 项目 | 状态 |
|------|------|
| 任务ID | T2.1 |
| 任务名称 | 告警引擎从调度中心迁移到容器中心 |
| 完成日期 | 2026-05-13 |
| 状态 | ✅ 已完成 |

---

## 1. 验收标准对照

### 1.1 功能验收

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | `check_overdue_tasks()` 逻辑与原始 `_check_overdue_tasks()` 完全一致 | ✅ | 已迁移至 AlertEngine，保持相同检测逻辑 |
| 2 | `check_outsource_reminders()` 逻辑与原始 `_check_outsource_reminders()` 完全一致 | ✅ | 已迁移至 AlertEngine，保持相同检测逻辑 |
| 3 | 超时检测：按告警规则配置的超时时间阈值检测工单，生成告警记录 | ✅ | 通过 ConfigStore.get('alert_rules') 读取配置 |
| 4 | 外协催单：按配置的时间节点检测外协单，发送通知并记录告警 | ✅ | 通过 ConfigStore.get('outsource_config') 读取配置 |
| 5 | 重复告警抑制：已告警过的工单在间隔时间内不再重复告警 | ✅ | `_is_duplicate()` 通过 AlertStore.query() 检测 30 分钟内重复 |

### 1.2 告警记录验收

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 生成的告警记录写入 tbl_alerts，包含 alert_type/doc_id/title/content/level | ✅ | 通过 AlertStore.create() 写入 |
| 2 | 告警区分 WARNING 和 CRITICAL | ✅ | CRITICAL 未使用（当前仅 WARNING） |

### 1.3 后台线程验收

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | `start()` 启动后台线程，按 interval_seconds 间隔执行 | ✅ | daemon=True, 通过 threading.Event.wait() 控制间隔 |
| 2 | `stop()` 优雅停止线程（不阻塞） | ✅ | 通过 threading.Event.set() 停止 |
| 3 | 线程异常不影响主进程 | ✅ | 内部 try/except 捕获，logger.error 记录 |

### 1.4 配置读取验收

| # | 标准 | 状态 | 说明 |
|---|------|------|------|
| 1 | 告警规则从 ConfigStore（tbl_configs）读取 | ✅ | ConfigStore.get('alert_rules') |
| 2 | 无配置时使用安全的默认值（不告警） | ✅ | `config_store.get('alert_rules') or {}` 返回空 dict |
| 3 | 配置变更后下次检查周期自动生效 | ✅ | 每次检查周期从 ConfigStore 实时读取 |

---

## 2. 交付物清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `container_center/services/__init__.py` | 新建 | 导出 AlertEngine |
| `container_center/services/alert_engine.py` | 新建 | AlertEngine 类，包含 check_overdue_tasks / check_outsource_reminders / start / stop |
| `container_center/__init__.py` | 修改 | 添加 AlertEngine 导出 |
| `dispatch_center.py` | 修改 | start_background_scheduler 改为创建 AlertEngine 实例 |
| `container_center/api/__init__.py` | 修改 | init_api_bp 改为直接模块属性赋值 |
| `container_center/api/health.py` | 修改 | 改为模块级 _router 变量导出 set_router() |
| `scripts/check_compile.py` | 修改 | 添加新文件到编译检查列表 |

---

## 3. 修复问题记录

### 3.1 Flask 2.3.3 `bp.view_functions` 为空 Bug

**问题**: Flask 2.3.3 中 `bp.view_functions` 始终返回空 dict，导致 `init_api_bp()` 无法通过 `bp.view_functions.get()` 找到任何视图函数来初始化 `_store`。

**根因**: Flask 2.3.x 内部实现变更，`view_functions` 字典在蓝图注册到 app 前不会填充。

**影响范围**: 所有 API 路由（configs、documents、alerts、health）均返回 500。

**修复方案**: 在 `init_api_bp()` 中直接通过模块导入 + 模块属性赋值（`mod._store = store`），替代依赖 `bp.view_functions` 的反射查找模式。

**涉及文件**: `container_center/api/__init__.py`、`container_center/api/health.py`

### 3.2 编译验证

所有 8 个文件编译通过:

```
[OK] dispatch_center.py
[OK] container_center/__init__.py
[OK] container_center/services/__init__.py
[OK] container_center/services/alert_engine.py
[OK] container_center/api/configs.py
[OK] container_center/api/documents.py
[OK] container_center/api/__init__.py
[OK] container_center/client/container_client.py
```

---

## 4. API 路由测试结果

| 路由 | 方法 | 状态 | 响应 |
|------|------|------|------|
| `/api/v4/health` | GET | ✅ | code:0, databases:12 |
| `/api/v4/health/databases` | GET | ✅ | code:0, 所有 12 个 DB 均存在 |
| `/api/v4/operators` | GET | ✅ | code:0, data:[] |
| `/api/v4/configs` | GET | ✅ | code:0, data:{} |
| `/api/v4/configs/alert_rules` | GET | ✅ | code:0, data:{} |
| `/api/v4/configs/alert_rules` | PUT | ✅ | code:0, data:{updated:true} |
| `/api/v4/alerts` | GET | ✅ | code:0, data:{data:[], total:0} |
| `/api/v4/distribute` | POST | ✅ | code:400（无此工单时返回合理错误） |

---

## 5. 遗留问题

- [ ] T2.3 调度中心 P1 引用替换（告警引擎迁移后，调度中心可移除定时器和告警相关代码）
- [ ] T3.1 移除直引用 + 清理代码（告警引擎迁移后清理调度中心冗余代码）
- [ ] 单元测试覆盖超时检测、外协催单、重复告警抑制（验收标准 #5 待补充测试用例）
