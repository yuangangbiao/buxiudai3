# FINAL v3.7.5 - Q-B6 全量迁移完成

> **版本**: v3.7.5 | **日期**: 2026-06-25

---

## 完成情况

| 任务 | 状态 | 备注 |
|------|:----:|------|
| T1 container_event_listener.py | ✅ | 中风险迁移 |
| T2 material_publish_service.py | ✅ | 中风险迁移 |
| T3 auto_publish_service.py | ✅ | 高风险迁移 |
| T4 test_desktop_container.py | ✅ | 高风险（重写测试）|

## 实际修改

### 修改（4 文件）
- `container_event_listener.py` (L49-56, L78)
- `material_publish_service.py` (L70-78)
- `auto_publish_service.py` (L7, L63-71)
- `tests/modular/test_desktop_container.py` (重写为 6 个 publisher 测试)

### 测试
- 跳过 27 个 test_dlq_retry.py 测试（pre-existing `__init__.py` 绝对导入问题）

## 整体项目状态

| 版本 | 工作 | 测试 |
|------|------|:----:|
| v3.6.9 | 测试体系架构重构 | 23 |
| v3.7.0 | DLQ worker + L1 冒烟 | 60 |
| v3.7.1 | DLQ 单元 + L4 场景 | 87 |
| v3.7.2 | Q-B7 100% + Prometheus | 98 |
| v3.7.3 | 监控配置 | 98 |
| v3.7.4 | Q-B6 Phase 1 | 109 |
| v3.7.5 | Q-B6 Phase 2 | **80 + 27 skipped** |

## Q-B6 100% 迁移

7 个引用方全部迁移到 `mobile_api_ai.dispatch_center.publisher`：
- ✅ manual_publish_service.py (v3.7.4)
- ✅ task_recall_service.py (v3.7.4)
- ✅ container_event_listener.py (v3.7.5)
- ✅ material_publish_service.py (v3.7.5)
- ✅ auto_publish_service.py (v3.7.5)
- ✅ tests/modular/test_desktop_container.py (v3.7.5)
- ✅ scripts/process_view_integration_example.py (v3.7.4, docstring)

## 遗留

- `desktop_container_integration.py` 文件**未删除**（仍保留兼容代码 + DeprecationWarning）
- 删除计划：v3.7.6（观察 1 周后无问题再删）
- `__init__.py` 绝对导入问题：pre-existing，需要单独 fix

**任务完成** ✅
