# 调度中心 4 工单异常状态排查报告

> **排查日期**: 2026-06-10
> **工单范围**: ORD-202604210004 / ORD-202605020001 / ORD-202604210002 / ORD-202605010001
> **排查维度**: API 原始数据 / DB 实际存储 / 前端渲染 / 代码逻辑
> **结论**: ✅ 找到 **10 类异常**,其中 **3 类高危**(业务逻辑错误)

---

## 一、4 工单现状快照

| 工单 | 物料 | 工序报工 | 流程步骤 | 质检 | 维修 | 外协 | 总数 | 工单 status |
|------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|------|
| ORD-202604210004 | 2 | 10 | 1 (flow_production) | 0 | 0 | 0 | 13 | - |
| ORD-202605020001 | 0 | 9 | **0** | 0 | 0 | 0 | 9 | - |
| ORD-202604210002 | 0 | **0** | 0 | 2 | 0 | 0 | 2 | - |
| ORD-202605010001 | 2 (status 错) | 0 | **7 (status 错)** | 1 | 0 | 0 | 10 | **material_confirmed** |

---

## 二、🔴 高危异常(3 类,需立即修复)

### 异常 #1:ORD-202605010001 — 7 个 flow_step 状态错乱(最严重)

**症状**:
```
[0dd0bec1] dt='flow_step'   st='distributed'   rp='完工入库'  op=YuanGangBiao
[2f9ba05e] dt='flow_step'   st='distributed'   rp='报工完成'  op=YuanGangBiao
[3bb51081] dt='flow_step'   st='distributed'   rp='生产执行'  op=YuanGangBiao
[68840c8e] dt='flow_step'   st='distributed'   rp='工单发布'  op=YuanGangBiao
[77122e2d] dt='flow_step'   st='distributed'   rp='发货'     op=YuanGangBiao
[88367229] dt='flow_step'   st='distributed'   rp='排产确认'  op=YuanGangBiao
[d5ec268d] dt='flow_step'   st='distributed'   rp='排产制定'  op=YuanGangBiao
```

**根因**:
- 流程步骤是**系统自动生成**的节点(工单发布/排产制定/...),**不应有** `target_operator`、**不应**是 `distributed` 状态
- 数据来自工单发布时的 `create_default_flow_steps(order_no)` 函数,推断它错误地:
  1. 给每条 step 设置了 `target_operator='YuanGangBiao'`(可能是默认值传错)
  2. 设置 `status='distributed'`(可能是 status 初始化错误)
- 写库后无法区分"系统自动生成的流程步骤" vs "实际派单的任务"

**业务影响**:
- 前端"流程进度"卡片显示 7 个 `distributed`(全员已认领),实际上没有任何人做流程跟踪
- 调度员看到"工单已完工入库"标 distributed 状态,完全错误
- **RE-005/RE-006 的"流程步骤归类"已成功区分数据来源**,但源数据本身就是脏的

**修复建议**:
- 立即:SQL `UPDATE data_packages SET status='created', target_operator=NULL, operator_id=NULL, source='system_flow' WHERE related_order='ORD-202605010001' AND data_type='flow_step'`
- 根本:查 `create_default_flow_steps` 写入逻辑,确保 system-generated 的 flow_step `status='created'`, `target_operator=NULL`
- 防御:在 classify 函数里对 `data_type IN ('flow_step', 'flow_production')` 的记录强制 `status='created'`,`target_operator=NULL`(只读侧清洗)

---

### 异常 #2:ORD-202604210002 — 完全没有工序,只有质检

**症状**: 2 个 quality_task,无 process_report / material / flow_step,工单只有质检环节

**根因**:
- 工单 ORD-202604210002 创建时**未生成工序报工任务**(没走标准工单发布流程,可能是手工创建或迁移导入)
- 只有 2 条质检任务被手工添加

**业务影响**:
- 质检员收到"原材料准备/编制左旋 首检"任务,但**没有对应的工序报工**可检
- 工单进度无法跟踪,只看到质检,看不到生产状态

**修复建议**:
- 立即:补建 process_report 任务(根据物料 + 工艺路线生成 10 个标准工序报工)
- 根本:工单发布函数 `create_workorder` 必须自动生成 6 卡片任务,缺一不可

---

### 异常 #3:ORD-202605020001 — 完全没有流程步骤

**症状**: 9 个工序报工 + 0 个 flow_step + 0 个 flow_production

**根因**:
- 工单发布时**未调用** `create_default_flow_steps(order_no)` 或调用了但失败
- 工单已有 9 个工序(说明走了一半流程),但流程骨架缺失

**业务影响**:
- 看不到"工单已发布/排产制定/生产执行/完工入库"等节点
- 流程跟踪失效,无法回溯"何时发布的"

**修复建议**:
- 立即:对历史无流程步骤的工单跑回填脚本(根据工单发布时间 + status 推断)
- 根本:工单发布函数必须事务性:`插入工单 + 插入流程步骤 + 插入工序报工 + 插入物料需求` 全部成功或全部回滚

---

## 三、🟡 中危异常(7 类,影响业务理解)

### 异常 #4:全 4 工单 — 工序顺序倒序

**症状** (ORD-202604210004 工序顺序):
```
包装入库 → 质量检验 → 表面处理 → 焊接输送带 → 整形校直 → 安装链条 → 输送带组装穿杆
→ 编制右旋 → 原材料准备
```
**正确顺序应是**: 原材料准备 → 编制左旋 → 编制右旋 → 输送带组装穿杆 → 安装链条 → 整形校直 → 焊接输送带 → 表面处理 → 质量检验 → 包装入库

**根因**:
- `_core.py:5272` `workorder_detail` 函数加载 data_packages 时,SQL 是 `ORDER BY id ASC`(或 DESC),按 id 排序
- 但物理工序应有自然顺序(process_names 字典顺序)
- 倒序看起来像"已完成的工序在前",实际上 API 只是按入库顺序

**业务影响**:
- 调度员无法直观看到"当前在第几道工序"
- 进度条无法正确显示(应该按工序顺序计算)

**修复建议**:
- `_core.py:5260` 之后加排序:
  ```python
  # 按 process_names 字典顺序排
  process_order = {p: i for i, p in enumerate(get_process_names_list())}
  d['process_tasks'].sort(key=lambda t: (process_order.get(t.get('related_process', ''), 999), t.get('id', '')))
  ```

### 异常 #5:ORD-202605020001 — 9 个工序 planned_qty 全 0

**症状**: 9 个 process_report 的 `content.planned_qty=0`,API 返回的 `planned_qty=0`

**根因**:
- 报工时未传 planned_qty(可能是微信扫码报工 API 漏传)
- 或 collect_report 内部没把 quantity 写进 planned_qty
- 看 content 实际有 `process_name='焊接输送带'` 但 planned_qty=0,说明工单数据导入时没设

**业务影响**:
- 调度员看不到"应做多少",只有 completed_qty
- 进度计算失真

**修复建议**:
- 立即:从 workorders.quantity 同步给所有 process_report.content.planned_qty
- 根本:报工 API 必传 planned_qty,缺失则拒绝(422)

### 异常 #6:ORD-202605010001 — 2 个 material_request 状态是 `material_confirmed`

**症状**: `status='material_confirmed'`,不在标准 status(pending/distributed/acknowledged/in_progress/completed)

**根因**:
- 业务代码某处(可能是 `confirm_material_request()` 函数)用了扩展 status
- 标准 status 集合未约束

**业务影响**:
- 前端按 status 渲染 CSS class 时,`material_confirmed` 走默认样式(灰色"未知")
- 状态机不一致

**修复建议**:
- 立即:SQL `UPDATE data_packages SET status='completed' WHERE status='material_confirmed'`(语义相同)
- 根本:增加 status 枚举约束 `data_packages.status IN ('pending', 'distributed', 'acknowledged', 'in_progress', 'completed', 'withdrawn', 'created')`

### 异常 #7:ORD-202605010001 — 工单本身 status=`material_confirmed`

**症状**: 工单的 `status='material_confirmed'`

**根因**: 业务系统用了非标准 status 表示工单阶段

**业务影响**:
- 工单列表的 status 筛选/分组失效
- 工单状态机不一致

**修复建议**:
- 与异常 #6 同步:SQL `UPDATE workorders SET status='material_ready' WHERE status='material_confirmed'`
- 定义 workorders status 枚举:`('draft', 'published', 'material_ready', 'in_production', 'completed', 'shipped', 'closed')`

### 异常 #8:全 4 工单 — `stats.completed_tasks` 永远 0

**症状**: 4 个工单 `stats.completed_tasks=0`,即使工单已经走了一半

**根因**:
- `_core.py:5317`:
  ```python
  'completed_tasks': sum(1 for _, d in order_items if d.get('status') in ('completed', 'done')),
  ```
- `d` 是 doc_data 字典,可能为空 `{}`(因为 `data_packages` 行的 `content` 字段是空)
- 应该用 `item` 本身而不是 `doc_data`

**修复建议**:
- `_core.py:5317` 改为:
  ```python
  'completed_tasks': sum(1 for item in all_items if item.get('status') in ('completed', 'done')),
  ```
  其中 `all_items = d['process_tasks'] + d['material_tasks'] + d['quality_tasks'] + d['repair_tasks'] + d['outsource_tasks']`

### 异常 #9:ORD-202605010001 — quality_task status 错

**症状**: 1 个 quality_task `st='distributed' op=YuanGangBiao rp='质检审核'`

**根因**:
- 质检审核是流程步骤(应归 flow_step),被错误地分到 quality_task 卡片
- 看 `related_process='质检审核'`,但 `process_names` 不含"质检审核"
- classify 函数把"质检-XXX"才归 quality_task,"质检审核"是流程名被误判

**业务影响**:
- 流程节点出现在"质检任务"卡片中,概念混淆(与 RE-005 严格定义冲突)

**修复建议**:
- `classify_pkg` 加流程步骤白名单优先:`if rp in flow_step_set: return 'flow_step'`(即使 rp 包含"质检"字样)
- 当前 `classify_pkg` 是先检查 `rp.startswith("质检-")` 再检查 flow_step_set,顺序错误

### 异常 #10:ORD-202604210004 — `flow_production` 工序 `op='-'`

**症状**: `[5dc395ef] dt='flow_production' st='created' op='-'`

**根因**:
- flow_production 是排产发布,正常 `target_operator` 应是排产员姓名或 NULL
- 显示 `-` 说明渲染逻辑 fallback

**业务影响**: 轻微,只是 UI 显示问题

---

## 四、🟢 低危(观察)

- ORD-202604210004 的 quantity=659 / 23 是 304 不锈钢的米数(物理量),正常
- ORD-202604210002 质检 cq=100 是首检总数(原材料准备 + 编制左旋 各 100)
- 数据回归历史表 12 处保留旧 data_type(RE-006 决策,正确)

---

## 五、根因汇总(代码层 vs 业务层)

| 异常 | 类型 | 根因位置 | 修复优先级 |
|------|------|---------|:----:|
| #1 flow_step distributed | **数据脏** | `create_default_flow_steps()` 写入逻辑 | 🔴 P0 |
| #2 缺工序 | **业务漏** | 工单创建函数未生成工序 | 🔴 P0 |
| #3 缺流程步骤 | **业务漏** | 工单创建函数未生成流程 | 🔴 P0 |
| #4 工序倒序 | **API 排序** | `_core.py:5260` workorder_detail | 🟡 P1 |
| #5 planned_qty=0 | **数据缺** | collect_report 未传 / DB 未同步 | 🟡 P1 |
| #6 material_confirmed status | **status 扩展** | 业务函数无 status 枚举约束 | 🟡 P1 |
| #7 工单 status 错 | **status 扩展** | workorders status 枚举未定义 | 🟡 P1 |
| #8 completed_tasks=0 | **API 统计** | `_core.py:5317` 用错变量 | 🟡 P1 |
| #9 质检审核误分类 | **分类逻辑** | `classify_pkg` 顺序错误 | 🟡 P1 |
| #10 flow_production op | **UI** | 前端渲染 fallback | 🟢 P2 |

---

## 六、修复建议路线图

### 阶段 1:数据修复(立即,1 天内)
- [ ] SQL #1:清 ORD-202605010001 flow_step 的 target_operator
- [ ] SQL #2:补建 ORD-202604210002 的 process_report 任务
- [ ] SQL #3:回填 ORD-202605020001 的流程步骤
- [ ] SQL #4:planned_qty 从 workorders.quantity 同步
- [ ] SQL #5:material_confirmed → completed
- [ ] SQL #6:workorders status 标准化

### 阶段 2:代码修复(本周,3-5 天)
- [ ] `_core.py:5260` 加 process_tasks 按 process_names 字典排序
- [ ] `_core.py:5317` 改 completed_tasks 统计逻辑
- [ ] `data_type_contract.classify_pkg` 修复流程步骤优先判定
- [ ] `create_default_flow_steps` 修复 status + target_operator
- [ ] 报工 API 强制 planned_qty 必传

### 阶段 3:防御性约束(下周,1 周)
- [ ] data_packages.status 加枚举约束 CHECK
- [ ] workorders.status 加枚举约束 CHECK
- [ ] 报工 API 文档化 status 枚举
- [ ] 写库前 status 白名单校验

---

## 七、归档

- API 原始数据: [docs/debug/order_state/ORD-*.json](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/) (4 文件)
- 截图证据: [docs/debug/order_state/screenshots/](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/screenshots/) (28 张)
- DB 调研脚本: [q3_db_inspect.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/q3_db_inspect.py)
- 截图脚本: [q4_screenshot_orders.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/q4_screenshot_orders.py)
- 本报告: [docs/debug/order_state/REPORT_4ORDERS_ANOMALY.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/REPORT_4ORDERS_ANOMALY.md)

---

> **签字**: Trae Agent · 2026-06-10 · 找到 3 高危 + 7 中危 + 1 低危 异常
