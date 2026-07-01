# TASK-T7: 图表 + 报表

## 输入契约

**前置依赖**：T1, T2
**输入数据**：DESIGN v2.0 模块 7
**环境依赖**：Chart.js（CDN 引入）

## 输出契约

**输出数据**：
- `inventory_web/services/report_service.py` 实现 stock_trend / inbound_outbound_flow / top_low_stock / category_distribution
- `inventory_web/routes_api.py` 新增 4 端点：
  - `GET /inventory/api/report/stock-trend?months=6`
  - `GET /inventory/api/report/io-flow?weeks=12`
  - `GET /inventory/api/report/top-low-stock?limit=10`
  - `GET /inventory/api/report/category-distribution`
- `inventory_web/templates/inventory/reports.html`
- `inventory_web/templates/inventory/dashboard.html` 升级（4 个 chart canvas）

**验收标准**：
- [ ] 4 个图表数据正确（用现有 inventory 数据核对）
- [ ] 图表渲染时间 < 1s
- [ ] 报表支持时间段筛选
- [ ] 不引入重量级 BI（仅 Chart.js）

## 实现约束

- **技术栈**：Chart.js v4（CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0`）
- **接口规范**：
  ```
  GET /inventory/api/report/stock-trend?months=6
  返回: [{month: "2025-12", total_qty: 12345}, ...]
  ```
- **质量要求**：
  - 数据聚合查询走索引
  - 限制时间范围（max 24 月）
  - 报表页面无敏感字段暴露
  - 库存价值需明确单价格式（先用 0 占位，避免误导）

## 依赖关系

**后置任务**：T8
**并行任务**：T5/T6
