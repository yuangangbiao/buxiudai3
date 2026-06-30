# -*- coding: utf-8 -*-
"""
设计文档 - 发布模式修正与任务撤回功能

设计时间: 2026-05-07
阶段: 阶段2 - Architect
"""

DESIGN_CONTENT = """
================================================================================
                     设计文档
        发布模式修正与任务撤回功能
================================================================================

一、整体架构图
--------------------------------------------------------------------------------

    ┌─────────────────────────────────────────────────────────────────┐
    │                    Service Layer                                │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
    │  │ AutoPublishSvc  │  │MaterialPublishSvc│  │ManualPublishSvc│ │
    │  │  (模式修正)     │  │   (模式修正)     │  │    (已有)      │ │
    │  └────────┬────────┘  └────────┬────────┘  └────────────────┘ │
    └───────────┼────────────────────┼────────────────────────────────┘
                │                    │
                ▼                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │              PublishModeManager (发布模式管理器)                   │
    └─────────────────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │              TaskRecallService (任务撤回服务) - 新增               │
    └─────────────────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │           desktop_container_integration.py                        │
    └─────────────────────────────────────────────────────────────────┘

二、修正设计方案
--------------------------------------------------------------------------------

1. AutoPublishService 修正
   --------------------

   现状: should_auto_publish() 只检查事件类型，不检查发布模式

   修正: 增加模式检查，仅在自动模式下返回True

   修改方法: should_auto_publish()
   ```python
   def should_auto_publish(self, event: str) -> bool:
       if not self.is_auto_publish_enabled():
           return False
       if not self.is_auto_mode():  # 新增：检查是否为自动模式
           return False
       return self._is_trigger_event(event)
   ```

   修改方法: handle_production_confirmed()
   ```python
   def handle_production_confirmed(self, event, data):
       if not self.should_auto_publish(event):  # 使用修正后的方法
           return
       # 发布逻辑...
   ```

2. MaterialPublishService 修正
   --------------------

   现状: handle_material_prepared() 直接发布，不检查模式

   修正: 增加模式检查，仅在自动模式下自动发布

   修改方法: handle_material_prepared()
   ```python
   def handle_material_prepared(self, event, data):
       if not self.is_auto_mode():  # 新增：手动模式下不自动发布
           return
       # 发布逻辑...
   ```

三、任务撤回服务设计
--------------------------------------------------------------------------------

1. TaskRecallService
   --------------------

   职责: 撤回已发布的任务

   类名: TaskRecallService

   接口:
   - recall_task(task_id: str) -> bool
     撤回指定任务

   - get_recallable_statuses() -> List[str]
     获取可撤回的状态列表

   - get_task_info(task_id: str) -> Optional[Dict]
     获取任务详情

   - can_recall(task_id: str) -> bool
     检查任务是否可撤回

   可撤回状态:
   - pending (待分配)
   - distributed (已分配待确认)

   不可撤回状态:
   - acknowledged (已确认)
   - completed (已完成)

四、事件定义
--------------------------------------------------------------------------------

新增事件类型:
- TASK_RECALLED = 'task:recalled'
- TASK_RECALL_FAILED = 'task:recall_failed'

五、依赖关系
--------------------------------------------------------------------------------

TaskRecallService:
- desktop_container_integration.py (任务操作)
- modular_config.py (配置读取)
- event_bus.py (事件通知)

================================================================================
"""

if __name__ == '__main__':
    print(DESIGN_CONTENT)
