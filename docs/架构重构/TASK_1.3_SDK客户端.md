# TASK 1.3：SDK 客户端 ContainerCenterClient

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T1.3 |
| 任务名称 | SDK 客户端 ContainerCenterClient |
| 所属阶段 | 第一阶段（P0） |
| 预估工时 | 0.5天 |
| 优先级 | P0（最高） |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.2 已完成且 API 端点已可访问
- [ ] requests 库已安装（或项目中已有的 HTTP 客户端）

### 输入数据
- T1.2 交付的全部 API 端点定义（路径 + 请求参数 + 响应格式）
- `container_center_v5.py` 中现有方法签名（确保兼容性）
- 映射表中调度中心全部直引用的方法签名

### 环境依赖
- Python 3.8+
- requests 库
- 项目中的 logger 配置

---

## 输出契约（Output Contract）

### 交付物

| 文件 | 职责 | 说明 |
|------|------|------|
| `container_center/client/__init__.py` | 模块初始化 | 导出 ContainerCenterClient |
| `container_center/client/container_client.py` | SDK 客户端 | ContainerCenterClient 类 |

### 核心接口

```python
class ContainerCenterClient:
    def __init__(self, base_url: str, secret: str): ...

    # ─── 通用文档 CRUD ───
    def query_documents(self, doc_type, status=None, q=None,
                        page=1, size=50, sort='-updated_at',
                        all=False) -> Dict: ...
    def get_document(self, doc_id: str) -> Dict: ...
    def create_document(self, doc_type: str, data: Dict) -> Dict: ...
    def update_document(self, doc_id: str, fields: Dict) -> Dict: ...
    def update_document_status(self, doc_id: str, status: str) -> Dict: ...
    def delete_document(self, doc_id: str) -> bool: ...

    # ─── 兼容方法（调度中心原有调用不改名）───
    def get_packages(self, doc_type='work_order', status=None, limit=100) -> List[Dict]: ...
    def get_package(self, pkg_id: str) -> Dict: ...
    def save_package(self, data: Dict) -> Dict: ...

    # ─── 消息发送 ───
    def send_message(self, content: str, to: str, msg_type: str = 'markdown') -> Dict: ...

    # ─── 分发 ───
    def distribute(self, task_id: str, operator_id: str) -> Dict: ...

    # ─── 配置 ───
    def get_operators(self, department=None) -> List[Dict]: ...
    def get_alert_rules(self) -> Dict: ...
    def update_alert_rules(self, rules: Dict) -> Dict: ...
    def get_alert_list(self, level=None, alert_type=None) -> List[Dict]: ...
    def dismiss_alert(self, alert_id: str) -> bool: ...
```

### 验收标准

1. **查询/CRUD 验收**：
   - [ ] `query_documents()` 返回格式与 T1.2 API 响应一致（data/page/size/total）
   - [ ] `create_document()` 正确 POST 数据，返回新建文档 id
   - [ ] `update_document()` 正确 PUT 局部更新
   - [ ] `delete_document()` 正确 DELETE

2. **兼容方法验收**：
   - [ ] `get_packages(limit=N)` 返回 `List[Dict]`，格式与原有 `cc.storage.get_packages()` 完全一致
   - [ ] `get_package(id)` 返回 `Dict` 格式兼容
   - [ ] `save_package(data)` 返回 id 语义一致

3. **消息发送验收**：
   - [ ] `send_message()` 正确调用消息 API，返回发送结果

4. **错误处理验收**：
   - [ ] 连接失败时抛出 `ContainerCenterConnectionError`
   - [ ] 鉴权失败时抛出 `ContainerCenterAuthError`
   - [ ] API 返回错误时抛出 `ContainerCenterAPIError`
   - [ ] 所有异常继承自 `ContainerCenterError` 基类

5. **测试验收**：
   - [ ] 使用 `responses` 或 `unittest.mock` 模拟 HTTP 请求进行测试
   - [ ] 测试每个方法的正常路径和异常路径
   - [ ] 测试兼容方法的返回格式与旧接口一致

---

## 实现约束

### 技术栈
- requests.Session（重用连接池）
- 自定义异常类层次结构
- 项目中已有的 logger

### 接口规范
- 方法签名与原有 `cc.storage.xxx()` 完全兼容（调用方不改名）
- 认证头自动注入（sha256 摘要）
- URL 拼接使用 `urljoin` 或字符串拼接（不含冗余 `/`）

### 质量要求
- 连接超时设置为 5s，读取超时 30s
- 所有请求自动重试（最多 3 次，指数退避）
- 响应状态码非 200 时抛出对应异常
- 禁止硬编码 URL

---

## 依赖关系

### 前置任务
- **T1.2** 容器中心 HTTP API（SDK 是对 HTTP API 的客户端封装）

### 后置任务
- **T1.4** 调度中心 P0 引用替换（SDK 是替换的载体）
- **T2.3** 调度中心 P1 引用替换（SDK 包含 P1 接口）

### 并行任务
- 无（T1.3 依赖 T1.2）

---

## 实施要点

1. **兼容性优先**：`get_packages()` / `get_package()` / `save_package()` 这些兼容方法的返回格式必须和现有 `cc.storage` 返回格式一致，调度中心代码无需修改即可替换
2. **异常层次**：定义 `ContainerCenterError` → `ContainerCenterConnectionError` / `ContainerCenterAuthError` / `ContainerCenterAPIError`
3. **配置文件读取**：`base_url` 和 `secret` 从环境变量读取，如 `os.environ['CONTAINER_CENTER_URL']`
