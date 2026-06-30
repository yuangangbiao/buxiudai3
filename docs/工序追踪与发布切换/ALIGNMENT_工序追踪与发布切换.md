# -*- coding: utf-8 -*-
"""
对齐文档 - 工序追踪与手动/自动发布切换

需求时间: 2026-05-07
阶段: 阶段1 - Align
"""

ALIGNMENT_CONTENT = """
================================================================================
                     对齐文档
        工序追踪与手动/自动发布切换功能
================================================================================

一、项目背景
--------------------------------------------------------------------------------

基于已完成的模块化重构(3.1)，新增以下功能:
1. 工序追踪 - 实时跟踪订单在各工序的状态
2. 手动/自动发布切换 - 提供灵活的任务发布控制
3. 手动发布任务 - 支持用户手动触发任务发布

二、原始需求
--------------------------------------------------------------------------------

用户需求:
- 工序追踪：能够追踪订单在各工序的生产状态
- 手动/自动切换：支持手动发布和自动发布两种模式切换
- 手动发布按钮：在界面上提供手动发布任务的按钮
- 状态显示：显示当前发布模式（手动/自动）

三、需求边界确认
--------------------------------------------------------------------------------

[边界]
- 仅实现工序追踪的数据结构和查询接口
- UI层面的按钮和切换器需后续集成到主软件
- 不修改已完成的6个核心模块

[非边界]
- 不实现完整的工序管理功能
- 不实现复杂的生产排程
- 不实现UI界面（仅提供模块支持）

四、技术方案理解
--------------------------------------------------------------------------------

1. 工序追踪模块
   - 记录每个订单的工序进度
   - 支持按订单号查询工序状态
   - 支持时间线展示

2. 发布模式切换
   - 配置开关: manual_publish.enabled
   - 运行时切换: set_publish_mode(mode)
   - 状态查询: get_publish_mode()

3. 手动发布模块
   - ManualPublishService: 手动发布服务
   - 支持指定工序手动发布
   - 支持批量手动发布

五、接口契约
--------------------------------------------------------------------------------

1. ProcessTracker (工序追踪器)
   ```python
   class ProcessTracker:
       def track_process(self, order_no: str, process_name: str, status: str)
       def get_order_processes(self, order_no: str) -> List[Dict]
       def get_current_process(self, order_no: str) -> Optional[Dict]
   ```

2. PublishModeManager (发布模式管理器)
   ```python
   class PublishModeManager:
       def set_mode(self, mode: str)  # 'manual' or 'auto'
       def get_mode(self) -> str
       def is_manual_mode(self) -> bool
   ```

3. ManualPublishService (手动发布服务)
   ```python
   class ManualPublishService:
       def publish_single(self, order_no: str, process_name: str) -> bool
       def publish_batch(self, order_no: str, process_list: List[str]) -> List[str]
   ```

六、验收标准
--------------------------------------------------------------------------------

1. ProcessTracker模块
   - [ ] track_process方法能记录工序状态
   - [ ] get_order_processes能查询订单所有工序
   - [ ] get_current_process能获取当前工序

2. PublishModeManager模块
   - [ ] set_mode能切换发布模式
   - [ ] get_mode能获取当前模式
   - [ ] 模式变更触发事件通知

3. ManualPublishService模块
   - [ ] publish_single能发布单个工序任务
   - [ ] publish_batch能批量发布工序任务
   - [ ] 依赖DesktopContainerIntegration

4. 单元测试
   - [ ] 所有模块有对应测试
   - [ ] 测试覆盖率100%

================================================================================
"""

if __name__ == '__main__':
    print(ALIGNMENT_CONTENT)
