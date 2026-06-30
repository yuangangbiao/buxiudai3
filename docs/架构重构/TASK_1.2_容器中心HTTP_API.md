# TASK 1.2：容器中心 HTTP API

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T1.2 |
| 任务名称 | 容器中心 HTTP API 层实现 |
| 所属阶段 | 第一阶段（P0） |
| 预估工时 | 1天 |
| 优先级 | P0（最高） |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.1 已完成（API 层调 DocumentStore / DatabaseRouter）
- [ ] `container_center_v5.py` 中现有 API 路由已了解
- [ ] Flask 框架已在项目中安装并配置

### 输入数据
- DESIGN 文档第 2.5 节跨库查询策略
- DESIGN 文档中定义的 P0 级 API 端点列表
- T1.1 的 DocumentStore / ConfigStore 接口签名
- 现有 `container_center_api.py` 中的 API 路由（改造复用）

### 环境依赖
- Python 3.8+
- Flask（项目中已使用）
- T1.1 交付的 storage 模块（document_store / config_store / alert_store）

---

## 输出契约（Output Contract）

### 交付物

| 文件 | 职责 | 说明 |
|------|------|------|
| `container_center/api/__init__.py` | API 模块初始化 | 注册蓝图 |
| `container_center/api/data_api.py` | 数据 CRUD API | 分页/排序/通用过滤/跨库查询 |
| `container_center/api/message_api.py` | 消息发送 API | 发送微信消息 |
| `container_center/api/distribute_api.py` | 分发 API | 派单/转派接口 |
| 改造 `container_center_api.py` | 注册新 API 蓝图 | 引入新模块 |

### API 端点清单

```
# ──────── 文档 CRUD ────────
POST   /api/container/data                              # 创建文档
GET    /api/container/data?doc_type=&status=&q=&page=&size=&sort=&all=  # 通用查询
GET    /api/container/data/<id>                         # 查询单个文档
PUT    /api/container/data/<id>                         # 更新文档字段（局部更新 doc_data）
PUT    /api/container/data/<id>/status                  # 更新文档状态
DELETE /api/container/data/<id>                         # 删除文档

# ──────── 消息发送 ────────
POST   /api/container/message/send                      # 发送微信消息

# ──────── 分发 ────────
POST   /api/container/distribute                        # 派单/转派
```

### 验收标准

1. **数据 API 验收**：
   - [ ] `POST /api/container/data` 传入 doc_type + data，返回 `{"id": "uuid", "status": "created"}`
   - [ ] `GET /api/container/data?doc_type=work_order` 返回分页结果（含 data/page/size/total/total_pages）
   - [ ] `GET /api/container/data?all=true&q=keyword` 跨库查询返回合并结果
   - [ ] `GET /api/container/data/<id>` 返回完整文档数据（doc_data 自动展开为 JSON）
   - [ ] `PUT /api/container/data/<id>` 局部更新 fields 到 doc_data JSON
   - [ ] `PUT /api/container/data/<id>/status` 仅更新 status 字段
   - [ ] `DELETE /api/container/data/<id>` 删除文档
   - [ ] 分页参数默认值正确（page=1, size=50）
   - [ ] sort 参数支持 `-field_name` 倒序格式

2. **消息 API 验收**：
   - [ ] `POST /api/container/message/send` 接收 content + to + msg_type，返回 `{"status": "sent"}`
   - [ ] 内部调用 CloudPoller 发送消息

3. **分发 API 验收**：
   - [ ] `POST /api/container/distribute` 接收 task_id + operator_id，返回 `{"status": "distributed"}`

4. **通用验收**：
   - [ ] 所有端点统一返回 JSON 格式
   - [ ] 错误返回 `{"error": "message", "code": "ERROR_CODE"}`
   - [ ] 跨库查询 `all=true` 时忽略 doc_type 参数，遍历所有 12 个库
   - [ ] API 鉴权已实现（X-Auth-Token 校验）

5. **测试验收**：
   - [ ] 使用 Flask test client 测试每个 API 端点的正常路径
   - [ ] 测试跨库查询的合并去重逻辑
   - [ ] 测试分页边界（page=0, size=0, size=超大值）
   - [ ] 测试鉴权失败场景

---

## 实现约束

### 技术栈
- Flask Blueprint 注册 API 路由
- 复用项目中现有的 Flask app 实例
- 文档 CRUD 调 T1.1 的 DocumentStore，禁止直写数据库

### 接口规范
- 统一响应格式：成功 `{"data": ..., "page": ..., "size": ..., "total": ...}`
- 统一错误格式：`{"error": "描述", "code": "ERROR_CODE"}`
- HTTP 状态码：200 成功 / 400 参数错误 / 401 鉴权失败 / 404 不存在 / 500 异常
- doc_data 在 API 层自动 JSON 序列化/反序列化

### 质量要求
- 参数校验完整（doc_type 必填校验、分页参数范围校验）
- 鉴权中间件已实现（读取 X-Auth-Token header，比对 SHA256(SHARED_SECRET)）
- 所有异常路径返回合理错误信息
- 禁止在 API 层直接操作数据库

---

## 依赖关系

### 前置任务
- **T1.1** 第四代文档桶存储层（API 层依赖 DocumentStore 提供服务）

### 后置任务
- **T1.3** SDK 客户端（SDK 是对 HTTP API 的封装，API 必须先就绪）
- **T1.4** 调度中心 P0 引用替换（依赖 API 就绪才能替换）
- **T2.1** 告警引擎（依赖数据 API 查询数据）
- **T2.2** 告警规则配置 API（依赖数据 API 存储规则）

### 并行任务
- 无（T1.2 依赖 T1.1，且是 T1.3/T1.4 的前置任务）

---

## 实施要点

1. **优先复用**：检查 `container_center_api.py` 中现有路由代码，改造而非重写
2. **跨库查询**：调用 `router.get_all_db_names()` 遍历，每个库按业务 doc_type 范围查询，合并后排序
3. **API 鉴权**：使用 Flask `@app.before_request` 或装饰器统一处理
4. **分页安全**：限制最大 size（如 max_size=200），防止恶意大分页
