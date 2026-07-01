# TASK-T3: CRUD 完整性（5 实体 × 4 操作 = 20 端点）

## 输入契约

**前置依赖**：T1, T2
**输入数据**：DESIGN v2.0 模块 1 的端点清单
**环境依赖**：`inventory_web/routes_data.py` 已有 `register_routes_data()`

## 输出契约

**输出数据**：
- `inventory_web/routes_data.py` 新增 update 端点
- `inventory_web/routes_data.py` 新增 warehouse 完整 CRUD（4 端点）
- `inventory_web/routes_data.py` 补齐 supplier/category/base 的 list/update/delete（9 端点）
- `inventory_web/db_utils.py` 新增 `_do_update()` 公共函数
- `inventory_web/db_utils.py` 新增 `_soft_delete()` 公共函数

**验收标准**：
- [ ] 20 个端点全部就位
- [ ] 所有 write 端点带 `@admin_required` + `@require_csrf`
- [ ] 软删除：list 默认 `WHERE deleted_at IS NULL`
- [ ] 引用检查：warehouse 删除时若有 inventory 引用则拒绝

## 实现约束

- **技术栈**：复用 `_do_create` / `_check_field_lengths` / `admin_auth` 装饰器
- **接口规范**：
  ```
  PATCH /inventory/api/{entity}/<int:eid>/update
  DELETE /inventory/api/{entity}/<int:eid>/delete
  GET /inventory/api/{entity}/list
  ```
- **质量要求**：
  - 严格保持与现有 add 端点同款参数/返回
  - 二次确认：批量删除要求 "DELETE {count}"（T8 实现）

## 依赖关系

**后置任务**：T4（依赖 update 能力）
**并行任务**：T5/T6（独立）
