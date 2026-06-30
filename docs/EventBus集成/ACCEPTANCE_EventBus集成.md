# ACCEPTANCE_EventBus集成.md

> 编制日期：2026-05-21
> 状态：✅ 已完成

## 验收清单

### TASK-001: events.py 新增 PROCESS_DELETED
- [x] `EventType.PROCESS_DELETED` 返回值 `'process:deleted'`
- [x] 编译通过：`python -m py_compile core/events.py` ✅

### TASK-002: process_view.py 事件埋点
- [x] `_add_process()` — `process:created` 事件发布
- [x] `submit_report()` — `process:reported` / `process:started` / `process:completed` 事件发布
- [x] `_quick_report()` — `process:reported` / `process:started` / `process:completed` 事件发布
- [x] `_delete_process()` — `process:deleted` 事件发布
- [x] 编译通过：`python -m py_compile views/process_view.py` ✅

### TASK-003: main.py 启动初始化
- [x] Phase 4（后台服务启动阶段）末尾调用 `init_container_listener()`
- [x] 失败时只记录 warning，不导致应用崩溃
- [x] 编译通过：`python -m py_compile main.py` ✅

### TASK-004: 验证测试
- [x] 所有修改文件整体编译通过 ✅
- [x] EventBus 常量导入正常 ✅
- [x] EventBus publish/subscribe 通信正常 ✅
- [x] ContainerEventListener 导入和初始化正常 ✅

## 整体验收

| 检查项 | 结果 |
|--------|------|
| 所有需求已实现 | ✅ |
| 验收标准全部满足 | ✅ |
| 项目编译通过 | ✅ |
| 实现与设计文档一致 | ✅ |
| 未引入技术债务 | ✅ — 纯增量代码，不改变现有逻辑 |
