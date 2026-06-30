---
name: "bug-hunter"
description: "真实客户体验找 Bug — 模拟真实用户操作桌面端+移动端所有功能，9阶段全流程覆盖，发现 UI/交互/数据 Bug。触发词：找bug、查问题、质量问题、系统检测、健康检查、挑毛病。"
---

# Bug Hunter — 全流程全功能客户体验找 Bug

## 核心原则

> **用真实客户的手，站在客户的角度，把每个功能用一遍。**

- **不用 API**，用真实浏览器操作
- **覆盖全架构**（9 阶段 × 桌面端 × 移动端 × 微信通知）
- **记录每个"不对劲"**：按钮点不动、报错红屏、数据显示不对、页面卡死
- **实时监控服务器日志**：每一步操作同步盯日志，发现日志中的 WARNING/ERROR/TRACE

---

## 日志监控工具（每个 Stage 全程运行）

### 启动日志监控

在开始找 Bug 前，先开两个日志监控终端：

```powershell
# 终端1: 调度中心日志 (5003)
python d:\yuan\不锈钢网带跟单3.0\core\dispatch_center.py 2>&1 | Select-String -Pattern "ERROR","WARNING","TRACE","Exception","Traceback" -Context 1,1

# 终端2: 移动端日志 (5008)
python d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py 2>&1 | Select-String -Pattern "ERROR","WARNING","TRACE","Exception","Traceback" -Context 1,1

# 终端3: 容器中心日志 (5002)
python d:\yuan\不锈钢网带跟单3.0\core\container_center_v5.py 2>&1 | Select-String -Pattern "ERROR","WARNING","TRACE","Exception","Traceback" -Context 1,1
```

### 日志关键词优先级

| 级别 | 关键词 | 含义 |
|:----:|--------|------|
| 🔴ERROR | `ERROR`, `Exception`, `Traceback`, `500 `, `OperationalError` | 必须记录 |
| 🟠WARNING | `WARNING`, `warn`, `deprecated` | 关注但不紧急 |
| 🟡TRACE | `TRACE`, `DEBUG` | 异常路径追踪 |
| ⚪INFO | `INFO`, `POST`, `GET` | 辅助理解流程 |

### 日志分析方法

```
每做一步操作，同步看日志输出
  ↓
日志出现 ERROR/WARNING → 立即截图 + 记录
  ↓
记录: [时间戳] [服务] [错误内容] [触发操作]
  ↓
继续操作，对比日志堆栈找根因
```

---

## 阶段划分

```
Stage1(订单) → Stage2(发布) → Stage3(排产) → Stage4(物料)
→ Stage5(工序) → Stage6(报工+质检循环) → Stage7(完成)
→ Stage8(入库) → Stage9(发货)
```

每个 Stage 内执行顺序：

```
① 监控日志（确认无旧 ERROR）→ ② 浏览器操作 → ③ 观察日志新增 → ④ 记录 Bug
```

---

## Stage 1: 桌面端 — 登录 & 订单视图

### 日志监控点

- 登录 API `/api/login` 是否返回 200
- orders 表查询是否有 SQL ERROR
- 新建订单写入是否有 ERROR

### 测试路径

1. 打开 `http://127.0.0.1:5003/`（桌面端）
2. 输入员工名登录
3. 进入**订单视图**（order_view.py）

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 1.1 | 登录页加载 | 刷新页面 | 无报错 | HTTP 500 / 白屏 | ERROR in app.py |
| 1.2 | 员工登录 | 输入姓名 → 点登录 | 跳转 dashboard | 报错/不跳转 | WARNING/ERROR |
| 1.3 | 订单列表 | 等待加载 | 显示订单列表 | 空列表/一直 loading | ERROR in query |
| 1.4 | 新建订单按钮 | 点击"新建订单" | 弹出表单 | 按钮无效/报错 | ERROR in render |
| 1.5 | 新建订单表单 | 填写必填项 → 提交 | 保存成功+列表刷新 | 报错/保存后列表不刷新 | ERROR in INSERT |
| 1.6 | 订单详情 | 点击订单 → 查看详情 | 显示完整信息 | 字段缺失/显示乱码 | WARNING null field |
| 1.7 | 订单状态流转 | 确认订单 | 状态变更+通知 | 状态不更新 | ERROR in UPDATE |

---

## Stage 2: 桌面端 — 生产视图（工单发布）

### 日志监控点

- `/api/processes` POST 返回状态
- `dispatch_document` 写入容器池
- `tmpl_task_assigned` 微信通知是否发送

### 测试路径

1. 进入**生产视图**（production_view.py）
2. 选择一个订单 → 点击"发布任务"

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 2.1 | 生产视图加载 | 切换到生产视图 tab | 正常显示 | 500 错误/空白 | ERROR in production_view |
| 2.2 | 待发布工单列表 | 查看列表 | 有待发布订单 | 空/报 API 错误 | ERROR in GET /api/work_order |
| 2.3 | 发布任务按钮 | 选择订单 → 点击发布 | 弹窗确认/成功提示 | 无响应/报错 | ERROR in POST /api/processes |
| 2.4 | 发布后状态 | 发布完成 | 状态变为"已发布" | 状态不变/重复提示 | WARNING status not changed |
| 2.5 | 微信通知触发 | 发布完成 | 微信群收到通知 | 无通知/通知内容错误 | WARNING send_to_wechat failed |

---

## Stage 3: 移动端 — 排产确认

### 日志监控点

- `/api/scan-info` 扫码结果查询
- `/api/workorder/confirm_schedule` 确认排产
- 微信消息接收处理日志

### 测试路径

1. 打开 `http://127.0.0.1:5008/`（晨圣报工小程序/移动端）
2. 登录（员工名）
3. 找到"排产确认"入口

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 3.1 | 移动端首页加载 | 访问 `/` | 显示生产看板 | HTTP 500（`static_hash` 报错） | ERROR in Jinja2 |
| 3.2 | 登录 | 输入姓名 → 点登录 | 跳转 dashboard | 不跳转/报错 | ERROR in /api/login |
| 3.3 | 排产确认入口 | 找"排产"或"工序任务" | 显示待确认列表 | 无入口/列表为空 | WARNING empty list |
| 3.4 | 扫码确认 | 扫码 → 确认排产 | 成功提示+微信通知 | 扫码失败/确认无效 | ERROR in confirm_schedule |
| 3.5 | 微信回复确认 | 微信回复"确认"关键词 | 流程自动确认 | 无响应/重复处理 | WARNING duplicate trigger |

---

## Stage 4: 桌面端 — 物料备料视图

### 日志监控点

- `/api/material/requirements` 查询
- `tmpl_material_shortage` 短缺告警
- `tmpl_material_arrival` 到货通知

### 测试路径

1. 进入**物料备料视图**（material_prep_view.py）

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 4.1 | 物料视图加载 | 切换 tab | 显示物料需求 | 空白/报错 | ERROR in material view |
| 4.2 | 物料短缺提示 | 查看是否有短缺预警 | 显示短缺项 | 应显示不显示 | WARNING shortage not detected |
| 4.3 | 物料到货查询 | 查询到货状态 | 显示到货信息 | 无数据/数据滞后 | ERROR in arrival query |
| 4.4 | 物料发布 | 点击"发布物料需求" | 发送成功 | 报错/无响应 | ERROR in POST material |
| 4.5 | 微信缺料通知 | 物料短缺时 | 微信群收到告警 | 不通知/通知内容错 | WARNING wechat send failed |

---

## Stage 5: 桌面端 — 工序发布

### 日志监控点

- 工序计算规则匹配（product_type → flow）
- `/api/process-tasks/send` 发送
- `tmpl_task_assigned` / `tmpl_process_start` 通知

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 5.1 | 工序列表 | 查看工序列表 | 按顺序显示工序 | 工序缺失/顺序错乱 | WARNING process order wrong |
| 5.2 | 工序计算规则 | 触发工序计算 | 按 product_type 匹配 | 规则不匹配/工序重复 | ERROR in flow matching |
| 5.3 | 发送工序按钮 | 点击"发送" | 成功+微信通知 | 无响应/报错 | ERROR in POST process-tasks |
| 5.4 | 工序任务推送 | 发送后 | 任务进容器池+通知 | 任务不推送 | WARNING dispatch failed |

---

## Stage 6: 移动端 — 扫码报工 + 质检（最核心）

### 日志监控点

- `/api/scan-info` 查询
- `/api/process_sub_step` 报工写入
- `tmpl_sub_step_created` 报工通知
- `/api/quality` 质检结果

### 测试路径

1. 移动端 → 点击"扫码报工"
2. 用 JS 模拟扫码（`handleScanResult('ORD-XXXXX')`）
3. 选择工序 → 填数量 → 提交

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 6.1 | 扫码入口 | 点击"扫码报工" | 显示扫描界面 | 入口不存在/点不动 | WARNING element not found |
| 6.2 | 扫码结果处理 | 扫码/模拟扫码 | 识别成功+跳转报工表单 | 识别后不跳转/工序列表为空 | ERROR in scan-info |
| 6.3 | 搜索结果点击 | 输入工单号搜索 → 点击结果 | 跳转报工表单 | 只跳详情页不跳报工 | WARNING goToOrder no showReport |
| 6.4 | 报工表单加载 | 报工表单显示 | 显示订单信息+工序列表 | 订单信息空/工序列表空 | WARNING process list empty |
| 6.5 | 工序选项 | 查看下拉工序 | 显示所有工序+进度 | 工序缺失/进度数字错误 | ERROR in process query |
| 6.6 | 数量输入 | 填写完成数量 | 正常填入 | 无法输入/输入后消失 | WARNING input lost |
| 6.7 | 提交报工 | 点击"提交报工" | 保存成功+表单关闭 | 不响应/报错/表单不关闭 | ERROR in process_sub_step INSERT |
| 6.8 | 重复报工 | 同一工序报工两次 | 累加数量或提示 | 数据覆盖/报工丢失 | WARNING duplicate overwrite |
| 6.9 | 报工后刷新 | 再次扫码同一订单 | 数量已更新 | 数量不变/显示旧数据 | WARNING data not refreshed |
| 6.10 | 微信报工通知 | 提交报工 | 微信收到报工详情 | 无通知/通知格式错 | WARNING wechat failed |
| 6.11 | 扫码质检入口 | 扫码质检 | 显示质检表单 | 入口不存在 | ERROR in quality page |
| 6.12 | 质检通过 | 扫码 → 填写质检 → 通过 | 记录保存 | 不保存/不通知 | ERROR in quality INSERT |
| 6.13 | 质检不通过 | 扫码 → 填写质检 → 不通过 | 触发异常告警 | 无告警/告警内容错 | WARNING alert not sent |

---

## Stage 7: 桌面端 — 报工完成判断

### 日志监控点

- `completed_qty ≥ order_qty` 完成判断
- `Event: process:completed` 事件触发
- `tmpl_process_advance` 完成通知

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 7.1 | 完成判断 | completed_qty ≥ order_qty | 自动触发完成 | 判断错误/提前/延后触发 | WARNING completion logic wrong |
| 7.2 | 完成通知 | 报工完成 | 微信收到完成通知 | 无通知/通知时机错 | ERROR in process:completed |

---

## Stage 8: 桌面端 — 成品入库

### 日志监控点

- `current_step → warehousing` 状态变更
- `tmpl_warehousing_notify` 入库通知

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 8.1 | 入库入口 | 报工完成后 → 点击"确认入库" | 显示入库确认 | 无入口/入口被隐藏 | WARNING button hidden |
| 8.2 | 自动入库判断 | 达到入库条件 | 自动入库 | 不自动/判断错误 | WARNING auto warehousing skip |
| 8.3 | 手动确认入库 | 点击"确认入库" | 状态变更+微信通知 | 无响应/状态不变 | ERROR in warehousing UPDATE |
| 8.4 | 入库微信通知 | 入库完成 | 微信收到入库通知 | 无通知 | WARNING wechat send failed |

---

## Stage 9: 桌面端 — 发货视图

### 日志监控点

- `orders.status → shipped` 状态变更
- `tmpl_process_complete` 完成通知
- 云端同步 `CC_CLOUD` 状态

### 客户体验检查点

| # | 检查项 | 操作 | 预期 | 异常表现 | 日志关键词 |
|---|--------|------|------|---------|-----------|
| 9.1 | 发货视图加载 | 切换到发货视图 | 显示待发货列表 | 空白/报错 | ERROR in shipment view |
| 9.2 | 发货按钮 | 点击"发货" | 确认弹窗 | 按钮无效 | WARNING button disabled |
| 9.3 | 确认发货 | 点击"确认发货" | 状态→已发货+通知 | 不变更/报错 | ERROR in shipped UPDATE |
| 9.4 | 发货后状态 | 发货完成 | 状态为 shipped | 状态未更新 | WARNING status not changed |
| 9.5 | 发货微信通知 | 发货完成 | 微信收到完成通知 | 无通知 | ERROR in wechat send |
| 9.6 | 云端同步 | 发货完成 | 云端同步成功 | 不同步/同步延迟 | WARNING cloud sync failed |

---

## Bug 记录格式（含日志）

找到 Bug 后，按以下格式记录：

```markdown
## Bug #[N]: <标题>

**阶段**: Stage X — <阶段名>
**页面**: <页面路径>
**严重程度**: 🔴P0 / 🟠P1 / 🟡P2 / ⚪P3

### 发现过程
<具体操作步骤>

### 预期行为
<应该怎样>

### 实际行为
<实际怎样>

### 日志证据
```
[时间戳] [服务] <日志内容>
[时间戳] [服务] <堆栈信息>
```

### 证据
- 截图: stepN_description.png
- 错误信息: <console/network 错误>
- 代码位置: <文件:L行号>

### 根因分析
<为什么会出现这个 Bug>

### 影响范围
<哪些用户/哪些场景受影响>
```

---

## 修复优先级

| 级别 | 定义 | 行动 |
|:----:|------|------|
| 🔴P0 | 崩溃/数据丢失/安全漏洞 | 立即修 |
| 🟠P1 | 功能异常/严重影响体验 | 尽快修 |
| 🟡P2 | UI 不规范/提示不清 | 计划修 |
| ⚪P3 | 边界情况/优化建议 | 可选修 |

---

## 底线

- 每个 Stage 至少用截图记录当前状态
- **每个操作同步盯日志**，日志出现 ERROR/WARNING 立即记录
- 不在报告里写"推测"——必须有截图 + 日志 + 操作步骤证据
- 优先找**真实用户会遇到的**问题，不找极端边界
