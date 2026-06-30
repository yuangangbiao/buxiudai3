# -*- coding: utf-8 -*-
"""
设计文档 - 工序追踪与手动/自动发布切换

设计时间: 2026-05-07
阶段: 阶段2 - Architect
"""

DESIGN_CONTENT = """
================================================================================
                     设计文档
        工序追踪与手动/自动发布切换功能
================================================================================

一、整体架构图
--------------------------------------------------------------------------------

    ┌─────────────────────────────────────────────────────────────────┐
    │                      UI Layer (待集成)                          │
    │   [工序追踪面板]  [模式切换]  [手动发布按钮]  [状态显示]         │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Service Layer                                │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
    │  │  ProcessTracker  │  │ PublishModeMgr  │  │ManualPublishSvc│ │
    │  └─────────────────┘  └─────────────────┘  └────────────────┘ │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Integration Layer                            │
    │           desktop_container_integration.py                     │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Core Modules (已存在)                        │
    │  container_center_v5.py  │  event_bus.py  │  modular_config.py   │
    └─────────────────────────────────────────────────────────────────┘

二、分层设计
--------------------------------------------------------------------------------

1. Service Layer (服务层)
   - ProcessTracker: 工序追踪器
   - PublishModeManager: 发布模式管理器
   - ManualPublishService: 手动发布服务

2. Integration Layer (集成层)
   - 复用已实现的 desktop_container_integration.py

3. Core Layer (核心层)
   - 复用已实现的 modular_config.py, event_bus.py

三、模块详细设计
--------------------------------------------------------------------------------

1. ProcessTracker (工序追踪器)
   --------------------

   职责: 追踪订单在各工序的生产状态

   类名: ProcessTracker

   接口:
   - track_process(order_no, process_name, status, operator_id, **kwargs)
     记录工序状态变更

   - get_order_processes(order_no)
     获取订单所有工序列表

   - get_current_process(order_no)
     获取订单当前工序

   - get_process_history(order_no, process_name)
     获取指定工序历史记录

   数据结构:
   ```python
   {
       'order_no': str,          # 订单号
       'process_name': str,       # 工序名称
       'status': str,             # 状态: pending/in_progress/completed
       'start_time': datetime,   # 开始时间
       'end_time': datetime,     # 结束时间
       'operator_id': str,       # 操作员ID
       'operator_name': str,     # 操作员名称
       'remarks': str,           # 备注
       'quantity': int,          # 数量
       'completed_qty': int      # 完成数量
   }
   ```

2. PublishModeManager (发布模式管理器)
   --------------------

   职责: 管理手动/自动发布模式切换

   类名: PublishModeManager

   接口:
   - set_mode(mode: str) -> bool
     设置发布模式 ('manual' 或 'auto')

   - get_mode() -> str
     获取当前模式

   - is_manual_mode() -> bool
     检查是否为手动模式

   - is_auto_mode() -> bool
     检查是否为自动模式

   配置存储:
   - 使用 modular_config.json 中的 manual_publish 配置节

3. ManualPublishService (手动发布服务)
   --------------------

   职责: 处理手动发布任务逻辑

   类名: ManualPublishService

   接口:
   - publish_single(order_no, process_name, **kwargs) -> bool
     发布单个工序任务

   - publish_batch(order_no, process_list) -> List[str]
     批量发布工序任务

   - get_publishable_processes(order_no) -> List[Dict]
     获取可发布的工序列表

四、事件定义
--------------------------------------------------------------------------------

新增事件类型:
- PROCESS_TRACKED = 'process:tracked'
- MODE_CHANGED = 'mode:changed'
- MANUAL_PUBLISH_REQUESTED = 'manual:publish_requested'

五、配置项
--------------------------------------------------------------------------------

modular_config.json 新增配置:
```json
{
    "manual_publish": {
        "enabled": true,
        "default_mode": "manual",
        "confirm_before_publish": true
    },
    "process_tracker": {
        "enabled": true,
        "retention_days": 90,
        "auto_complete_threshold": 0.95
    }
}
```

六、依赖关系
--------------------------------------------------------------------------------

ProcessTracker:
- modular_config.py (配置读取)
- event_bus.py (事件通知)

PublishModeManager:
- modular_config.py (配置读写)
- event_bus.py (模式变更事件)

ManualPublishService:
- desktop_container_integration.py (发布任务)
- modular_config.py (配置读取)

七、异常处理策略
--------------------------------------------------------------------------------

1. ProcessTracker
   - 数据库异常: 记录日志，返回None
   - 无数据异常: 返回空列表

2. PublishModeManager
   - 无效模式: 抛出ValueError
   - 配置异常: 使用默认值

3. ManualPublishService
   - 发布失败: 记录日志，返回False
   - 容器不可用: 抛出RuntimeError

八、设计原则
--------------------------------------------------------------------------------

1. 单一职责: 每个类只负责一个功能
2. 开闭原则: 对扩展开放，对修改关闭
3. 依赖倒置: 依赖抽象，不依赖具体实现
4. 接口隔离: 提供最小接口，避免臃肿

================================================================================
"""

if __name__ == '__main__':
    print(DESIGN_CONTENT)
