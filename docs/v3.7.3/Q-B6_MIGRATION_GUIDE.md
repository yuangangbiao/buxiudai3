# Q-B6 desktop_container_integration.py 迁移指南

> **创建日期**: 2026-06-25
> **状态**: 待实施
> **计划实施**: v3.7.4+

---

## 背景

`desktop_container_integration.py` 已废弃（v3.7.0），加 DeprecationWarning（v3.7.1）。
本指南说明如何将 7 个引用方迁移到 `mobile_api_ai.dispatch_center` 中的对应实现。

## 引用方清单

| # | 文件 | import 数 | 类引用 | 优先级 |
|---|------|:---------:|:------:|:------:|
| 1 | `auto_publish_service.py` | 1 | 4 | 🔴 高 |
| 2 | `container_event_listener.py` | 1 | 2 | 🟡 中 |
| 3 | `manual_publish_service.py` | 1 | 0 | 🟢 低 |
| 4 | `material_publish_service.py` | 1 | 3 | 🟡 中 |
| 5 | `task_recall_service.py` | 1 | 0 | 🟢 低 |
| 6 | `scripts/process_view_integration_example.py` | 1 | 0 | 🟢 低 |
| 7 | `tests/modular/test_desktop_container.py` | 4 | 7 | 🔴 高 |

## 迁移函数映射

| 旧 API | 新 API |
|--------|--------|
| `DesktopContainerIntegration()` | `mobile_api_ai.dispatch_center.publisher.ReportPublisher()` |
| `integration.publish_report_task(...)` | `publisher.publish(...)` |
| `integration.publish_material_task(...)` | `material_publisher.publish(...)` |
| `get_integration()` | `get_publisher()` |

## 迁移步骤

### Phase 1: 添加 shim 层（向后兼容）
```python
# mobile_api_ai/dispatch_center/_publisher_shim.py（新增）
"""
[Q-B6 v3.7.4] 兼容层
让旧代码继续可用，但警告用户已废弃
"""
import warnings

def get_publisher():
    warnings.warn(
        "get_integration() 已废弃，请改用 dispatch_center.get_publisher()",
        DeprecationWarning, stacklevel=2
    )
    from mobile_api_ai.dispatch_center.publisher import get_publisher as _new
    return _new()
```

### Phase 2: 逐个迁移引用方（按优先级）

#### 迁移 1: manual_publish_service.py / task_recall_service.py / scripts/（低风险）
```python
# 旧
from desktop_container_integration import get_integration
integration = get_integration()
integration.xxx()

# 新
from mobile_api_ai.dispatch_center.publisher import get_publisher
publisher = get_publisher()
publisher.xxx()
```

#### 迁移 2: container_event_listener.py（中风险）
- 涉及事件监听
- 需要测试事件传递链路

#### 迁移 3: material_publish_service.py（中风险）
- 物料发布逻辑
- 需要测试物料同步

#### 迁移 4: auto_publish_service.py（高风险）
- 报工发布
- 7 引用方中最关键
- 需完整回归测试

#### 迁移 5: tests/modular/test_desktop_container.py（高风险）
- 7 处类引用
- 单元测试需重写
- 需重新设计测试用例

### Phase 3: 删除 desktop_container_integration.py
所有引用方迁移完成后：
1. 搜索全文确认 0 引用
2. 删除文件
3. git commit 记录迁移完成
4. 通知相关团队

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 旧 API 行为不一致 | 完整单元测试覆盖 |
| 性能差异 | 性能基准测试 |
| 业务理解偏差 | 业务方 review |
| 测试覆盖不足 | 灰度发布 |

## 回滚方案

每个引用方迁移后保留 1 周观察期，确认无问题后再迁移下一个。
发现严重问题立即回滚到上一版本。

## 验收标准

- [ ] 7 引用方全部迁移
- [ ] desktop_container_integration.py 文件删除
- [ ] 全部测试通过
- [ ] 灰度发布 2 周无问题
- [ ] 性能不低于基线
