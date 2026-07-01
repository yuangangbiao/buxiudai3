# 待办事项 — 操作员ID与工时单位统一改造

## 🔴 高优先级

### 1. MySQL 数据库配置（必须配置后才能启动）
TASK-07 新增了 MySQL `operators` 表自动创建逻辑，需要 MySQL 连接。

- [ ] 复制 `.env.example` 为 `.env`
- [ ] 配置 MySQL 连接参数：
  ```
  USE_SQLITE=false
  MYSQL_HOST=localhost
  MYSQL_PORT=3306
  MYSQL_USER=root
  MYSQL_PASSWORD=<实际密码>
  MYSQL_DATABASE=steel_belt
  ```
- **相关代码**：`dispatch_center.py:_ensure_operators_table()`, `storage_mysql.py:MYSQL_CFG`
- **注意**：`.env` 文件不存在（仅 `.env.example`），目前可能使用 SQLite 模式

### 2. 存量数据库字段迁移
`overtime_minutes` 已改为 `overtime_hours`（INTEGER→REAL），存量表需迁移。

- [ ] SQLite 迁移：`ALTER TABLE sub_steps ADD COLUMN overtime_hours REAL DEFAULT 0;`
- [ ] 迁移存量数据：`UPDATE sub_steps SET overtime_hours = overtime_minutes / 60.0 WHERE overtime_minutes > 0;`
- [ ] 可选清理旧列：`ALTER TABLE sub_steps DROP COLUMN overtime_minutes;`（SQLite 3.35+ 支持）
- **影响范围**：`schema_auto.py`（DDL已改）, `storage_layer.py`, `storage_mysql.py`, `sync/handlers/sub_step_handler.py`

### 3. 云端部署同步
dispatch_center.py 所有修改须同步到云端 standalone_dispatch_server.py。

- [x] v3.8.1 重构：wechat_server.py 已废弃，功能合并到 standalone_dispatch_server.py（sync_bp + wechat_work_bot_bp）
- [ ] 确认 TASK-07 的 EventBus 事件处理器在云端注册正常
- [ ] 确认 TASK-08 的 `_get_dynamic_operators()` 在云端有 container_config 可用

## 🟡 中优先级

### 4. EventBus 事件处理器验证
TASK-07 注册了 OperatorConfigChanged/OperatorRemoved 事件的 MySQL 同步处理器。

- [ ] 确认 EventBus 模块已导入且正常运行
- [ ] 验证操作员新增/修改/删除时，MySQL operators 表同步成功
- [ ] 验证首次启动时 `_migrate_operators_to_mysql()` 历史数据迁移成功

### 5. 容器中心动态加载验证
TASK-08 用动态加载替代了硬编码 OPERATORS 列表。

- [ ] 确认 `container_config.get_all_operators()` 能正常返回所有操作员
- [ ] 确认容器中心操作员选择下拉框数据正确
- [ ] 确认操作员信息加载失败时有降级处理（返回空列表）

### 6. 离职访问控制三入口确认
TASK-09 在三个报工入口注入离职检查：

- [ ] **dispatch_center.py** `create_process_sub_step()` — L7614 调用 `_check_operator_enabled()`
- [ ] **container_center_api.py** `api_create_sub_step()` — L2501-2502 内联检查
- [ ] **legacy_routes.py** `api_create_sub_step()` — L510-515 内联检查
- [ ] 验证已离职操作员在所有入口均被阻止报工

### 7. 操作员管理前端过滤验证
TASK-10 修改了操作员管理列表。

- [ ] 确认操作员管理页面使用 `GET /operators?include_disabled=1` 获取全量数据
- [ ] 确认已离职操作员显示"已离职"标签（非"禁用"）
- [ ] 确认调度中心其他模块（任务分配等）仍只显示在职操作员

## 🟢 低优先级

### 8. 综合测试用例
建议对核心改造路径编写测试用例：

- [ ] 操作员 CRUD 全链路测试（操作员创建→修改→同步MySQL→离职→前端显示）
- [ ] 工时 overtime_hours 读写测试（新建报工→查询→确认浮点数精度）
- [ ] 离职访问控制测试（在职操作员正常报工 / 离职操作员被阻止）

### 9. 兼容层清理（可选）
`scripts/tools/sync_container_to_cs.py` 中仍使用 `overtime_minutes` 旧字段名。

- [ ] 评估是否需要改造该脚本（当前为兼容层，不影响生产逻辑）
- [ ] 如需改造：将 `overtime_minutes` → `overtime_hours`，列类型 `INTEGER` → `REAL`

---

> 生成时间：2026-05-26
> 关联文档：[TASK_操作员ID与工时单位统一改造.md](file:///d:/yuan/现实文件/批次改造方案/TASK_操作员ID与工时单位统一改造.md)
> 关联文档：[DESIGN_操作员ID与工时单位统一改造.md](file:///d:/yuan/现实文件/批次改造方案/DESIGN_操作员ID与工时单位统一改造.md)
