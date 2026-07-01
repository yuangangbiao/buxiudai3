# TASK-T5: 抽盘功能

## 输入契约

**前置依赖**：T1, T2
**输入数据**：DESIGN v2.0 模块 5
**环境依赖**：`stocktakes` / `stocktake_items` 表已存在

## 输出契约

**输出数据**：
- `inventory_web/services/stocktake_service.py` 实现 create/submit/adjust
- `inventory_web/routes_core.py` 新增 3 端点：
  - `POST /inventory/api/stocktake/create`
  - `POST /inventory/api/stocktake/<int:sid>/submit`
  - `POST /inventory/api/stocktake/<int:sid>/adjust`
- `inventory_web/routes_core.py` 新增 1 个页面：
  - `GET /inventory/stocktake`
- `inventory_web/templates/inventory/stocktake.html`（向导式）

**验收标准**：
- [ ] 抽盘创建：按 warehouse_id 生成预期数量列表
- [ ] 双重差值判断：`abs(diff_qty) > 1 AND abs(diff_qty) > expected * tolerance%`
- [ ] adjust：仅对 normal 状态项自动调整，abnormal 需审批
- [ ] 审计：每次操作走 log_operation

## 实现约束

- **技术栈**：Flask + Jinja2 + MySQL 事务
- **接口规范**：
  ```
  POST /inventory/api/stocktake/create
    {warehouse_id, tolerance_pct}
  POST /inventory/api/stocktake/<id>/submit
    {items: [{product_id, actual_qty}], remark}
  POST /inventory/api/stocktake/<id>/adjust
    {} (使用已 submit 的数据)
  ```
- **质量要求**：
  - 事务完整性（FOR UPDATE on stocktake_items）
  - 二次确认（adjust 时显示差异表 + 输入 "ADJUST" 确认）
  - 提交后 status 流转：draft → submitted → adjusted

## 依赖关系

**后置任务**：无
**并行任务**：T6/T7/T8
