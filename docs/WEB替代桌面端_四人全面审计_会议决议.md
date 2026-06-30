# Web端全面替代桌面端 — 四人全面审计会议决议

> 日期：2026-06-22
> 与会：小袁（前端）+ 小圣（后端）+ 小钰（数据库）+ 小贺（测试）

---

## 一、各自审计问题汇总

### 小袁审计（前端视角，22项）
- 🔴 发货API已实现（9端点）→ T2/T3可省
- 🔴 所有表已存在 → 无需DDL
- 🔴 Excel无事务策略
- 🟡 shared.css缺失
- 🟡 页面风格不统一
- 🟡 甘特图无分页
- 🟢 API错误码不统一

### 小圣审计（后端视角，20项）
- 🔴 Excel导入事务缺失
- 🔴 PDF打印权限未校验
- 🔴 甘特图跨表查询无索引
- 🔴 订单软删除关联数据处理不清
- 🟡 微信同步无降级方案
- 🟡 分页参数不统一
- 🟡 操作日志无索引

### 小钰审计（数据库视角，18项）
- 🔴 shipments表已存在（shipment_routes.py L201）
- 🔴 bom_list表已存在（_database_legacy.py L808）
- 🔴 inventory表已存在（_database_legacy.py L571）
- 🔴 alert_records表已存在（_database_legacy.py L854）
- 🔴 operation_logs表已存在（_database_legacy.py L760）
- 🟡 shipments表无显式索引
- 🟡 shipment_tracks表无显式索引
- 🟡 operation_logs表无显式索引

### 小贺审计（测试视角，18项）
- 🔴 Excel边界测试用例全部缺失（6类）
- 🔴 发货CRUD无测试覆盖
- 🔴 PDF打印无视觉回归
- 🔴 工序甘特图无性能测试
- 🟡 订单软删除无关联测试
- 🟡 多用户并发场景未覆盖
- 🟢 微信同步降级未测试

---

## 二、会议决议

### 决议1：推翻原计划假设（一致通过）

**原假设 vs 实际情况**

| 假设 | 实际情况 | 节省工作量 |
|------|---------|---------|
| 发货表需新建 | shipments表已存在，API已有9端点 | T1+T2+T3 省 3个任务 |
| BOM表需新建 | bom_list表已存在 | 省 1个DDL任务 |
| 库存表需新建 | inventory表已存在 | 省 1个DDL任务 |
| 预警表需新建 | alert_records表已存在 | 省 1个DDL任务 |
| 日志表需新建 | operation_logs表已存在 | 省 1个DDL任务 |

**行动**：删除所有 DDL 任务，修订计划文档。

### 决议2：Excel 导入规范（一致通过）

```
规范：POST /api/orders/import
1. 前端：文件大小 ≤ 2MB，超过提示分批
2. 后端：每行校验，错误收集，全部处理完返回错误报告
3. 事务：全部成功才COMMIT，失败则ROLLBACK
4. 响应格式：{ code: 0, data: { success: N, failed: M, errors: [{row, field, msg}] }}
```

### 决议3：UI 规范文件（一致通过）

```
文件：desktop_web/static/css/shared.css（新建）

规范内容：
- 按钮：.btn .btn-primary .btn-success .btn-warning .btn-danger
- 表格：.data-table .data-table th .data-table td
- 弹窗：.modal-overlay .modal-box .modal-title .modal-actions
- 状态标签：.status-tag .badge-blocked .badge-new
- 进度条：.progress-bar .progress-fill .progress-text
- 输入框：.form-input .form-select .form-textarea
- 卡片：.card .card-header .card-body
```

### 决议4：PDF打印权限（一致通过）

```
规范：所有 /api/*/print 端点
1. 后端必须校验 X-Dispatch-Token
2. 打印记录写入 operation_logs（operator_id, action='PRINT', target_type, target_id）
3. 价格/成本字段默认不显示
```

### 决议5：索引补充（一致通过）

```sql
-- shipments 表补充索引
ALTER TABLE shipments ADD INDEX idx_order_id (order_id);
ALTER TABLE shipments ADD INDEX idx_status_time (status, shipped_at);

-- shipment_tracks 表补充索引
ALTER TABLE shipment_tracks ADD INDEX idx_shipment_id (shipment_id);

-- operation_logs 表补充索引
ALTER TABLE operation_logs ADD INDEX idx_operator_time (operator_id, created_at);
ALTER TABLE operation_logs ADD INDEX idx_action_type (action, target_type);
```

### 决议6：甘特图性能（一致通过）

```
规范：GET /api/process-timeline/<order_id>
1. 必须有时间范围参数：?from=2026-01-01&to=2026-12-31
2. 默认只查90天内数据
3. 超过500条工序返回错误，提示缩小范围
4. 前端实现虚拟滚动（只渲染可视区域）
```

### 决议7：分页规范（一致通过）

```
规范：所有列表 API 统一分页参数
GET /api/xxx/list?page=1&size=20

响应格式：
{
  "code": 0,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

### 决议8：测试分批策略（一致通过）

| 阶段 | 测试重点 | 边界用例 |
|------|---------|---------|
| 阶段一 | 发货CRUD + 打印 | 状态流转：待发货→已发货→已收货 |
| 阶段二 | 工序追踪 + 甘特图 | 0工序/1工序/100+工序性能 |
| 阶段三 | 订单查询/删除/详情 | 删除有报工订单（应拒绝） |
| 阶段四 | Excel导入导出 | 空/1行/1000行/>2MB/格式错误/必填缺失 |
| 阶段五 | 操作员CRUD + 微信同步 | 同步失败降级 |
| 阶段六 | BOM + 库存 | 材料计算准确性 |
| 阶段七 | 辅助功能 | 预警触发条件 |
| 阶段八 | 全量回归 | 全部功能端到端 |

---

## 三、修订后计划

### 3.1 工作量对比

| 项目 | 原计划 | 修订后 | 变化 |
|------|--------|--------|------|
| 新建页面 | 9 个 | 9 个 | 不变 |
| 增强页面 | 2 个 | 2 个 | 不变 |
| 新建 API | 25 个 | ~8 个 | -17 个（复用 dispatch_center） |
| DDL 任务 | 1 个 | 0 个 | 删除（T1） |
| 总任务数 | 41 个 | ~28 个 | -13 个（27%减少） |
| 预估工期 | 11 天 | 7-8 天 | 节省 3-4 天 |

### 3.2 新增决议任务

| # | 任务 | 类型 | 来源 |
|---|------|------|------|
| NT1 | 制定 shared.css 规范 | [UI规范] | 小袁 |
| NT2 | 补充 shipments/index 索引 | [DDL] | 小钰 |
| NT3 | 补充 shipment_tracks/index 索引 | [DDL] | 小钰 |
| NT4 | 补充 operation_logs/index 索引 | [DDL] | 小钰 |
| NT5 | Excel 导入统一事务规范 | [逻辑] | 小圣 |
| NT6 | PDF 打印权限校验 | [逻辑] | 小圣 |
| NT7 | 分页规范统一 | [逻辑] | 小圣 |

---

> 会议时长：约 30 分钟
> 决议数：8 项
> 问题闭环：22 项 → 18 项立即解决 + 4 项延后

**是否按此决议执行？**
