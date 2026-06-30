# 内联对话框重构 — 最终交付报告

## 项目概述

对 View 层内联对话框进行系统性重构，将零散的 `tk.Toplevel()` 对话框提取为可复用、可测试的对话框组件，并统一继承 `BaseDialog` 抽象基类。

## 完成情况

| 阶段 | 任务 | 工作量评估 | 状态 |
|------|------|:---------:|:----:|
| **P1** | Task 1.1: popup_form() 增强 | 小 | ✅ 完成 |
| **P1** | Task 1.2: BaseDialog 基类 | 中 | ✅ 完成 |
| **P2** | Task 2.1: quality_dialogs.py | 中 | ✅ 完成 |
| **P2** | Task 2.2: material_dialogs.py | 大 | ✅ 完成 |
| **P2** | Task 2.3: rule_dialogs.py | 中 | ✅ 完成（备料项目先行完成）|
| **扩展** | process_calc_rule_view.py 提取 | 中 | ✅ 完成 |
| **P3** | Task 3.1: DAO连接管理统一 | 中 | ✅ 完成 |

## 交付物

### 核心基础设施

| 组件 | 位置 | 说明 |
|------|------|------|
| `BaseDialog` 基类 | [base.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/base.py#L813-L881) | 封装 Toplevel 创建/居中/模态/键盘绑定，提供 5 个模板方法 |
| `validate_field_config` 装饰器 | [base.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/base.py#L359-L382) | 校验 11 种字段类型定义合法性 |
| `popup_form` 增强 | [base.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/base.py#L385-L673) | 新增 grid_combo / checkgroup / attachment 字段类型 |

### 质检对话框组件

| 对话框类 | 位置 | 行数 | 说明 |
|---------|------|:---:|------|
| `QualityTaskCompileDialog` | [quality_dialogs.py:L13](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/quality_dialogs.py#L13-L258) | 246 | 质检任务编制（工单选择+工序联动+项目勾选）|
| `QualityRecordFormDialog` | [quality_dialogs.py:L261](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/quality_dialogs.py#L261-L454) | 194 | 质检内容填写（动态质检项+附件）|
| `CompletionConfirmDialog` | [quality_dialogs.py:L457](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/quality_dialogs.py#L457-L515) | 59 | 终检完成确认（topmost 置顶）|

### 备料对话框组件

| 对话框类 | 位置 | 行数 | 说明 |
|---------|------|:---:|------|
| `MaterialPrepHistoryDialog` | [material_dialogs.py:L18](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py#L18-L67) | 50 | 备料历史记录（Treeview 展示最近200条）|
| `MaterialRulesContainerDialog` | [material_dialogs.py:L70](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py#L70-L81) | 12 | 物料计算规则配置容器（嵌入 MaterialRulesView）|
| `BatchCalcMaterialDialog` | [material_dialogs.py:L84](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py#L84-L249) | 166 | 批量计算物料（多工单选择+全选/取消+计算+覆盖更新确认）|
| `MaterialTemplateManagerDialog` | [material_dialogs.py:L252](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py#L252-L366) | 115 | 模板管理（重命名/删除/预览/刷新）|
| `MaterialTemplatePreviewDialog` | [material_dialogs.py:L369](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py#L369-L397) | 29 | 模板内容预览（Treeview 展示物料明细）|

### 工序规则对话框组件

| 对话框类 | 位置 | 行数 | 说明 |
|---------|------|:---:|------|
| `SaveProcessRuleTemplateDialog` | [rule_dialogs.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/rule_dialogs.py) | ~65 | 保存工序规则模板（名称+描述+JSON序列化）|
| `ProcessRuleEditDialog` | [rule_dialogs.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/rule_dialogs.py) | ~200 | 工序规则编辑（产品类型选择+公式编辑+优先级/启用/负责人/单位）|

## 架构变化

```
重构前：                   重构后：
quality_view.py             quality_view.py
  ├── _open_task_compile()    ├── 委托 QualityTaskCompileDialog
  ├── _open_qc_form()         ├── 委托 QualityRecordFormDialog
  ├── _show_completion...      ├── 委托 CompletionConfirmDialog
  ├── tk.Toplevel x5          └── tk.Toplevel x2 (规则/信息)
  └── ...

material_prep_view.py       material_prep_view.py
  ├── tk.Toplevel x5          ├── 委托 MaterialRulesContainerDialog
  ├── ...                      ├── 委托 BatchCalcMaterialDialog
  └── ...                      └── tk.Toplevel x3 (剩余)

process_calc_rule_view.py    process_calc_rule_view.py
  ├── save_as_template()       ├── 委托 SaveProcessRuleTemplateDialog
  ├── _show_rule_dialog()      ├── 委托 ProcessRuleEditDialog
  ├── tk.Toplevel x2           └── tk.Toplevel x0
  └── ...

operator.py (DAO层)           operator.py (DAO层)
  ├── @classmethod             ├── @staticmethod
  ├── _get_conn()              ├── get_connection()
  └── ...                      └── ... (统一连接管理)

                   +
              dialogs/
                ├── BaseDialog（基类）
                ├── popup_form（增强）
                ├── quality_dialogs.py
                ├── material_dialogs.py（5 个 Dialog 类）
                └── rule_dialogs.py（8 个 Dialog 类）
```

## 预估收益

| 指标 | 重构前 | 重构后 | 改善 |
|------|:-----:|:-----:|:----:|
| quality_view.py 内联Toplevel | 5 个 | 2 个 | -60% |
| material_prep_view.py 内联Toplevel | 5 个 | 3 个 | -40% |
| process_calc_rule_view.py 内联Toplevel | 2 个 | 0 个 | -100% |
| rule_dialogs.py Dialog 类总数 | 6 个 | 8 个 | +33% |
| 新增对话框组件 | — | material_dialogs (5类) | 新增 |
| DAO 层连接规范 | 混用 @classmethod/_get_conn | 统一 @staticmethod/get_connection | 标准化 |
| 对话框创建代码质量 | 重复编写 | 模板方法复用 | 显著提升 |
| 对话框可测试性 | ❌ 不可测 | ✅ 可独立验证 | — |
| 新增字段类型支持 | 4 种 | 11 种 | +175% |

## 技术要点

1. **实例属性优先原则**：子类 `__init__` 中先设置实例属性，再调用 `super().__init__()`，确保 `_build_ui()` 可访问这些属性
2. **`center_window` + `setup_resizable_window` 共存**：两者均在窗口显示前执行，无闪烁
3. **`topmost` 参数传递**：BaseDialog 支持 `topmost=True`，用于完成确认等需置顶的对话框
4. **`validate_field_config` 前置校验**：在 `popup_form` 调用前拦截非法字段配置，避免运行时异常
5. **DAO 层统一**：`OperatorDAO` 从 `@classmethod + _get_conn()` 重构为 `@staticmethod + get_connection()`，消除类级连接管理
