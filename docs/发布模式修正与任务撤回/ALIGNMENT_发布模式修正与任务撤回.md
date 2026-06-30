# -*- coding: utf-8 -*-
"""
对齐文档 - 发布模式修正与任务撤回功能

需求时间: 2026-05-07
阶段: 阶段1 - Align
"""

ALIGNMENT_CONTENT = """
================================================================================
                     对齐文档
        发布模式修正与任务撤回功能
================================================================================

一、项目背景
--------------------------------------------------------------------------------

基于已实现的工序追踪与发布切换功能，修正以下问题：
1. 自动发布模式下，物料备料和工序模块应自动发布任务，不能手动发布
2. 新增已发出任务撤回功能

二、原始需求
--------------------------------------------------------------------------------

用户需求:
1. 修正发布逻辑：
   - 自动发布模式时：物料备料模块、工序模块都自动发布任务
   - 手动发布模式时：可通过手动按钮发布任务

2. 新增任务撤回功能：
   - 支持撤回已发布的任务
   - 撤回后任务状态更新

三、需求边界确认
--------------------------------------------------------------------------------

[边界]
- 仅修改 AutoPublishService 和 MaterialPublishService 在自动模式下的行为
- 任务撤回功能依赖容器中心的撤回接口
- 不修改 ProcessTracker 和 PublishModeManager 的核心逻辑

[非边界]
- 不实现复杂的审批撤回流程
- 不实现任务状态的完整生命周期

四、技术方案理解
--------------------------------------------------------------------------------

1. 发布模式修正

   AutoPublishService:
   - 自动模式：自动发布任务 ✓ (已有)
   - 手动模式：不应自动发布，等待手动触发

   MaterialPublishService:
   - 自动模式：自动发布任务 ✓ (已有)
   - 手动模式：不应自动发布，等待手动触发

   ManualPublishService:
   - 自动模式：拒绝发布 ✓ (已有)
   - 手动模式：允许发布 ✓ (已有)

2. 任务撤回功能

   TaskRecallService:
   - recall_task(task_id): 撤回指定任务
   - get_task_status(task_id): 获取任务状态
   - 依赖 desktop_container_integration

五、接口契约
--------------------------------------------------------------------------------

1. AutoPublishService 修正
   ```python
   def should_auto_publish(self, event: str) -> bool:
       # 仅在自动模式下返回True
       return self.is_auto_mode() and self._is_trigger_event(event)
   ```

2. MaterialPublishService 修正
   ```python
   def handle_material_prepared(self, event, data):
       if not self.is_auto_mode():
           return  # 手动模式下不自动发布
       # 发布逻辑...
   ```

3. TaskRecallService (新增)
   ```python
   class TaskRecallService:
       def recall_task(self, task_id: str) -> bool
       def get_recallable_statuses(self) -> List[str]
   ```

六、验收标准
--------------------------------------------------------------------------------

1. 发布模式修正
   - [ ] AutoPublishService 在手动模式下不自动发布
   - [ ] MaterialPublishService 在手动模式下不自动发布
   - [ ] ManualPublishService 在自动模式下拒绝发布

2. 任务撤回功能
   - [ ] recall_task 方法能撤回指定任务
   - [ ] 撤回后任务状态更新
   - [ ] 获取可撤回状态列表

================================================================================
"""

if __name__ == '__main__':
    print(ALIGNMENT_CONTENT)
