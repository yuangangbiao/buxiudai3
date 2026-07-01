# TASK-T6: 调拨功能

## 输入契约

**前置依赖**：T1, T2
**输入数据**：DESIGN v2.0 模块 6
**环境依赖**：`transfers` / `transfer_items` 表已存在

## 输出契约

**输出数据**：
- `inventory_web/services/transfer_service.py` 实现 create/complete/cancel
- `inventory_web/routes_core.py` 新增 4 端点：
  - `POST /inventory/api/transfer/create`
  - `POST /inventory/api/transfer/<int:tid>/complete`
  - `POST /inventory/api/transfer/<int:tid>/cancel`
  - `GET /inventory/api/transfer/list`
- `inventory_web/templates/inventory/transfer.html`（向导式）

**验收标准**：
- [ ] 调拨创建：调出仓 FOR UPDATE 扣减，在途 +N
- [ ] 调拨完成：调入仓 FOR UPDATE 增加，在途 -N
- [ ] 调拨取消：调出仓回滚 +N，在途 -N
- [ ] 死信防护：定时任务（scripts/transfer_reaper.py）扫描 in_transit > 24h 自动取消
- [ ] 并发安全：10 并发调拨不出现超扣

## 实现约束

- **技术栈**：Flask + MySQL 事务 + FOR UPDATE
- **接口规范**：
  ```
  POST /inventory/api/transfer/create
    {from_warehouse_id, to_warehouse_id, items: [{product_id, qty}], remark}
  POST /inventory/api/transfer/<id>/complete
    {}
  POST /inventory/api/transfer/<id>/cancel
    {reason}
  GET /inventory/api/transfer/list?status=in_transit
  ```
- **质量要求**：
  - 2 步事务：每步独立事务（避免长事务）
  - 在途状态用 `inventory_transactions` 表的 `ref_no` 关联
  - in_transit 状态校验：完成时只在 status=in_transit 时可操作
  - **高风险**：必须先写并发测试

## 依赖关系

**后置任务**：无
**并行任务**：T5/T7/T8
