# TASK 1.1：第四代文档桶存储层（含分库路由）

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T1.1 |
| 任务名称 | 第四代文档桶存储层实现 |
| 所属阶段 | 第一阶段（P0） |
| 预估工时 | 1天 |
| 优先级 | P0（最高） |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] DESIGN_第四代存储+解耦合.md 已审批通过
- [ ] container_center_v5.py 现有存储逻辑已阅读并理解
- [ ] container_center/ 目录结构已创建
- [ ] data/ 目录已创建（分库文件存放目录）

### 输入数据
- `container_center_v5.py` 中 `SqliteStorage` 类的全部方法签名和实现逻辑
- DESIGN 文档中定义的 4 张表结构（tbl_documents / tbl_indexes / tbl_configs / tbl_alerts）
- DESIGN 文档中定义的 12 库路由表（DB_FILE_MAP + ROUTING_TABLE）
- DESIGN 文档中 `DatabaseRouter` 完整代码参考

### 环境依赖
- Python 3.8+
- sqlite3（内置模块）
- 现有项目中的 config.py（读取 CC_DATA_DIR 等配置）
- 现有项目日志规范（logging 模块）

---

## 输出契约（Output Contract）

### 交付物

| 文件 | 职责 | 说明 |
|------|------|------|
| `container_center/storage/__init__.py` | 模块初始化 | 导出全部 Store 类 |
| `container_center/storage/router.py` | 分库路由 | DatabaseRouter 类 |
| `container_center/storage/document_store.py` | 文档桶 CRUD | DocumentStore 类 |
| `container_center/storage/index_store.py` | 索引管理 | IndexStore 类 |
| `container_center/storage/config_store.py` | 配置存储 | ConfigStore 类 |
| `container_center/storage/alert_store.py` | 告警记录 | AlertStore 类 |
| `scripts/migrate_to_v4_storage.py` | 数据迁移脚本 | 从 tbl_packages 迁移到 tbl_documents |

### 验收标准

1. **DatabaseRouter 验收标准**：
   - [ ] 根据 doc_type 正确路由到 12 个独立 .db 文件
   - [ ] 未知 doc_type 自动降级到 system.db
   - [ ] 懒加载连接，相同 db_path 复用连接
   - [ ] 每个库独立 Lock 写锁，contextmanager 自动 commit/rollback
   - [ ] WAL 模式已启用
   - [ ] 通过 `CC_DATA_DIR` 环境变量控制数据目录
   - [ ] `close_all()` 正常关闭所有连接

2. **DocumentStore 验收标准**：
   - [ ] `create_document(doc_type, data) → id` 正常创建文档并写入 JSON
   - [ ] `get_document(doc_id) → dict` 正常返回（含 doc_data 自动反序列化）
   - [ ] `query_documents(doc_type, filters, page, size, sort)` 支持分页/排序/过滤
   - [ ] `update_document(doc_id, fields)` 局部更新 doc_data JSON
   - [ ] `update_document_status(doc_id, status)` 更新 status 字段
   - [ ] `delete_document(doc_id)` 软删除或硬删除

3. **兼容性验收标准**：
   - [ ] `get_packages(doc_type='work_order', status=None, limit=100)` → List[dict] 返回格式与原有 `SqliteStorage.get_packages()` 一致
   - [ ] `get_package(pkg_id)` → dict 返回格式兼容
   - [ ] `save_package(pkg)` → id 语义一致
   - [ ] `update_package(id, fields)` 语义一致
   - [ ] `update_package_status(id, status)` 语义一致

4. **索引验收标准**：
   - [ ] 创建文档时自动为已注册的高频字段建立索引
   - [ ] 通过 `tbl_indexes` 支持 `key_name + key_value` 快速查询
   - [ ] 删除文档时自动清理关联索引

5. **测试验收**：
   - [ ] 单元测试覆盖 DatabaseRouter 的 12 库路由逻辑
   - [ ] 单元测试覆盖 DocumentStore 全部 CRUD 操作
   - [ ] 单元测试覆盖索引自动管理
   - [ ] 测试使用独立临时目录，不影响现有数据

---

## 实现约束

### 技术栈
- Python 3.8+ 标准库（仅 sqlite3 / threading / contextlib / os）
- 禁止引入第三方数据库 ORM
- 复用现有项目中 `config.py` 的日志配置
- 严格遵循项目现有异常处理模式（logging + contextmanager）

### 接口规范
- DatabaseRouter 对外暴露 `get_db_cursor(doc_type)` 作为唯一 cursor 获取入口
- DocumentStore 通过 DatabaseRouter 操作数据库，禁止直接创建连接
- 所有 store 类返回 dict 而非 ORM 对象
- doc_data 统一为 JSON 字符串存储，Python 侧为 dict

### 质量要求
- 每个 Store 类必须有独立单元测试文件
- 异常路径全覆盖（连接失败、SQL 错误、数据不存在等）
- 禁止 `except: pass`，所有异常必须记录日志
- 禁止 print，统一使用 logger

---

## 依赖关系

### 前置任务
- 无（本项目第一个实现任务）

### 后置任务
- **T1.2** 容器中心 HTTP API（必须等待 T1.1 完成，API 层调存储层）
- **T1.3** SDK 客户端（间接依赖，通过 T1.2 间接依赖 T1.1）
- **T5** 数据迁移（必须等待 T1.1 完成才能运行迁移脚本）

### 并行任务
- 无（T1.1 是第一阶段基石任务）

---

## 实施要点

1. **优先复用**：检查 `container_center_v5.py` 中 `SqliteStorage` 的现有代码，将可复用的逻辑保留，只做架构拆分而非重写
2. **DatabaseRouter** 使用 `os.environ.get('CC_DATA_DIR', 'data')` 读取配置，禁止硬编码路径
3. **迁移脚本** 使用"就地迁移"策略：逐个读取 tbl_packages → 转换为 doc_data JSON → 写入 tbl_documents
4. **迁移期间** 两个表共存，读取时先查 tbl_documents，不存在回退到 tbl_packages
