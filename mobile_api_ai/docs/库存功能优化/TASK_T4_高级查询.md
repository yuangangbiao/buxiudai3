# TASK-T4: 高级查询 + 软删除回滚

## 输入契约

**前置依赖**：T3
**输入数据**：DESIGN v2.0 模块 3
**环境依赖**：所有产品/分类/供应商/基地/仓库表已有 `deleted_at`

## 输出契约

**输出数据**：
- `inventory_web/routes_data.py` 增强所有 list 端点（分页/筛选/排序/模糊）
- `inventory_web/routes_data.py` 新增 `GET /inventory/api/recycle-bin/list`
- `inventory_web/routes_data.py` 新增 `POST /inventory/api/recycle-bin/<id>/restore`
- `inventory_web/db_utils.py` 新增 `parse_pagination()` 工具

**验收标准**：
- [ ] list 支持：`page` / `page_size` / `search` / `category_id` / `warehouse_id` / `min_qty` / `max_qty` / `low_stock_only` / `sort_by` / `order`
- [ ] list 默认 `WHERE deleted_at IS NULL`
- [ ] 回收站：列已软删除的 5 实体
- [ ] 恢复：将 `deleted_at` 改回 NULL
- [ ] 软删除 + 唯一约束：恢复时不与现有 `code` 冲突

## 实现约束

- **技术栈**：MySQL LIKE + ORDER BY + LIMIT
- **接口规范**：
  ```
  GET /inventory/api/product/list?page=1&page_size=20&search=abc&category_id=1
  GET /inventory/api/recycle-bin/list?entity=product
  POST /inventory/api/recycle-bin/<entity>/<int:id>/restore
  ```
- **质量要求**：
  - 参数化查询（防 SQL 注入）
  - 模糊匹配用 `LIKE %s%` + 转义 `%`
  - 分页计算 `offset = (page-1) * page_size`
  - 软删除唯一约束冲突：恢复时提示"code 已被占用"

## 依赖关系

**后置任务**：T5/T6
**并行任务**：T7/T8
