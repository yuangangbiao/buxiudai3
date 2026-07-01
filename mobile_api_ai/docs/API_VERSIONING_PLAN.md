# API 版本控制规划

> 创建时间: 2026-05-14
> 状态: 规划中

---

## 1. 当前API现状

### 1.1 当前端点列表

| 模块 | 路径 | 方法 | 说明 |
|------|------|------|------|
| auth | `/api/auth/login` | POST | 登录 |
| auth | `/api/auth/verify` | POST | 验证 |
| process | `/api/process/my-tasks` | GET | 我的任务 |
| process | `/api/process/<id>/report` | POST | 提交报工 |
| process | `/api/process/history` | GET | 历史记录 |
| quality | `/api/quality/list` | GET | 质检列表 |
| quality | `/api/quality/create` | POST | 创建质检 |
| approval | `/api/approval/pending` | GET | 待审批 |
| approval | `/api/approval/approve` | POST | 审批通过 |
| approval | `/api/approval/reject` | POST | 审批拒绝 |
| message | `/api/message/list` | GET | 消息列表 |
| ai | `/api/ai/speech-report` | POST | 语音报工 |
| ai | `/api/ai/analyze-image` | POST | 图像分析 |
| ai | `/api/ai/chat` | POST | AI对话 |

### 1.2 当前问题

1. **无版本控制** - 无法保证向后兼容
2. **破坏性变更** - 修改API可能影响已有客户端
3. **难以追踪** - 不知道哪些端点被哪些版本使用

---

## 2. 版本控制策略

### 2.1 版本格式

```
/api/v{major}/{resource}/{action}
```

示例：
- `/api/v1/process/report` (当前版本)
- `/api/v2/process/report` (未来版本)

### 2.2 版本规则

| 场景 | 主版本号 | 说明 |
|------|---------|------|
| 破坏性变更 | +1 | 旧客户端可能不兼容 |
| 新增端点 | 不变 | 向后兼容 |
| 新增可选参数 | 不变 | 向后兼容 |
| Bug修复 | 不变 | 向后兼容 |
| 废弃端点 | 通知 | 至少保留2个主版本 |

### 2.3 响应头

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Deprecation: true
X-API-Sunset: Sat, 31 Dec 2027 23:59:59 GMT
```

---

## 3. 迁移计划

### 3.1 第一阶段：双版本共存

```
当前:    /api/process/report
新增:    /api/v1/process/report
```

1. 在路由层添加版本前缀
2. 保持新旧端点同时可用
3. 通过响应头标识当前版本

### 3.2 第二阶段：标记废弃

```python
# 旧端点添加废弃头
@app.route('/api/process/report', methods=['POST'])
def old_report():
    response = new_report()
    response.headers['X-API-Deprecation'] = 'true'
    response.headers['X-API-Sunset'] = '2027-12-31'
    return response
```

### 3.3 第三阶段：移除旧版本

在废弃日期后，从代码中移除旧端点。

---

## 4. 实现示例

### 4.1 版本化Blueprint

```python
# api/v1/__init__.py
from flask import Blueprint

v1_bp = Blueprint('v1', __name__, url_prefix='/api/v1')

from . import process, quality, approval
```

### 4.2 响应格式统一

```python
# api/responses.py
def api_response(code: int, message: str, data=None, version: str = 'v1'):
    response = {
        'code': code,
        'message': message,
        'data': data,
        'version': version
    }
    resp = jsonify(response)
    resp.headers['X-API-Version'] = version
    return resp
```

### 4.3 废弃检测中间件

```python
# api/middleware.py
@app.before_request
def check_api_version():
    if request.path.startswith('/api/') and not request.path.startswith('/api/v'):
        # 无版本前缀，添加警告头
        response = make_response()
        response.headers['X-API-Warning'] = '请使用版本化API: /api/v1/...'
        return response
```

---

## 5. 行动计划

| 阶段 | 任务 | 预估工时 | 状态 |
|------|------|---------|------|
| 1 | 创建 api/v1 目录结构 | 2小时 | 待开始 |
| 2 | 迁移现有端点到v1 | 4小时 | 待开始 |
| 3 | 添加版本响应头 | 1小时 | 待开始 |
| 4 | 添加废弃检测中间件 | 2小时 | 待开始 |
| 5 | 更新API文档 | 2小时 | 待开始 |
| 6 | 测试新旧端点并存 | 2小时 | 待开始 |

**总计预估**: 13小时

---

## 6. 相关资源

- [REST API Design Best Practices](https://www.amazon.com/REST-API-Design-Handbook-Best-Practices/dp/1449319798)
- [API Versioning Best Practices](https://docs.microsoft.com/en-us/azure/architecture/best-practices/api-design)
