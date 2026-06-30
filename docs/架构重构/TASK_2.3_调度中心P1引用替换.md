# TASK 2.3：调度中心 P1 级直引用替换

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T2.3 |
| 任务名称 | 调度中心 P1 级直引用替换为 SDK 调用 |
| 所属阶段 | 第二阶段（P1） |
| 预估工时 | 0.5天 |
| 优先级 | P1 |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.4 调度中心 P0 引用替换已完成
- [ ] T2.1 告警引擎已迁移完成
- [ ] T2.2 告警规则配置 API 已完成
- [ ] `dispatch_center.py` 中 P1 级引用的全部位置已梳理清晰

### 输入数据
- DESIGN 文档 3.1 节映射表中 P1 级直引用清单
- 现有 `dispatch_center.py` 中 P1 功能的调用位置和代码上下文
- T1.3 ContainerCenterClient SDK 客户端
- T2.1 AlertEngine（告警引擎已迁移到容器中心）
- T2.2 配置 API 端点

### 环境依赖
- Python 3.8+
- `dispatch_center.py` 工程文件
- T1.3 SDK client 模块

---

## 输出契约（Output Contract）

### 交付物
- 改造 `dispatch_center.py`

### P1 替换范围

| 原直引用 | 出现次数 | 替换为 |
|---------|:-------:|--------|
| `cc.distributor.distribute(task_id, operator_id)` | 4处 | `client.distribute(task_id, operator_id)` |
| `cc.config.get_all_operators()` | 1处 | `client.get_operators()` |
| `cc.config.get_operators_by_department(dept)` | 1处 | `client.get_operators(department=dept)` |
| `cc.collect_outsource(...)` | 1处 | `client.create_document(doc_type='outsource', data=...)` |
| `_check_overdue_tasks()` | 定时器 | 删除调用（已迁移到容器中心） |
| `_check_outsource_reminders()` | 定时器 | 删除调用（已迁移到容器中心） |
| 告警列表查询 | 1处 | `client.get_alert_list(level, alert_type)` |
| 告警忽略操作 | 1处 | `client.dismiss_alert(alert_id)` |

### 验收标准

1. **引用替换验收**：
   - [ ] 全部 4 处 `cc.distributor.distribute()` 替换为 `client.distribute()`
   - [ ] 全部 2 处操作员配置读取替换完成
   - [ ] 全部 1 处外协采集替换完成
   - [ ] 告警列表查询和告警忽略替换完成
   - [ ] 调度中心定时器不再调用 `_check_overdue_tasks()` 和 `_check_outsource_reminders()`

2. **兼容性验收**：
   - [ ] 替换后调度中心功能与替换前完全一致
   - [ ] 派单/转派功能正常
   - [ ] 操作员列表显示正常
   - [ ] 告警列表显示正常
   - [ ] 告警忽略操作正常

3. **代码质量验收**：
   - [ ] 不再使用 `cc.distributor`
   - [ ] 不再使用 `cc.config` 读取操作员
   - [ ] 不再使用 `cc.collect_outsource`
   - [ ] 定时器线程已移除告警相关的检查

4. **测试验收**：
   - [ ] 调度中心单元测试全部通过
   - [ ] 调度中心冒烟测试通过（完整任务流程）

---

## 实现约束

### 技术栈
- 纯文本替换 + 人工校验（同 T1.4）

### 接口规范
- 调度中心的方法名和参数顺序保持与原来一致
- 禁止修改现有业务逻辑，仅替换调用方式

### 质量要求
- 逐行审查替换结果
- 替换后运行调度中心全部测试用例
- 异常处理不降级

---

## 依赖关系

### 前置任务
- **T1.4** 调度中心 P0 引用替换（P0 是基础，P1 在其之上）
- **T2.1** 告警引擎迁移（删除定时器调用前需要确保告警引擎已就绪）
- **T2.2** 告警规则配置 API（告警配置/告警列表依赖配置 API）

### 后置任务
- **T3.1** 移除直引用 + 清理代码（所有引用替换完成后统一清理）

### 并行任务
- 无（T2.3 依赖 T2.1 + T2.2 + T1.4）

---

## 实施要点

1. **分批替换**：先替换分发/配置/外协等无需等待 API 的引用，最后再处理告警相关的引用
2. **定时器清理**：告警检查功能已由容器中心 AlertEngine 接管，调度中心中对应的定时器调用必须移除
3. **不做功能重构**：本次仅替换调用方式，不改变业务逻辑
