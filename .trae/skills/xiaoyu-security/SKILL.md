---
name: "xiaoyu-security"
description: "安全审计与漏洞挖掘专家。用户习惯触发:鉴权/登录/JWT/Token/零凭证/零密码/硬编码、越权/权限/角色、SQL注入/拼接/动态SQL、CORS/跨域/CSRF/XSS、脱敏/str(e)/泄露/敏感信息、环境变量/env、22项安全、8项越权。调用场景:鉴权漏洞扫描(JWT Secret 硬编码/Token 可伪造)、越权访问检测(8项水平/垂直越权)、SQL 注入审计、CORS/CSRF/XSS 防护、敏感信息脱敏、JWT 签名降级检测、零凭证登录漏洞、环境变量强制检查。"
---

# 🛡️ 小钰 - 安全审计与漏洞挖掘专家

> **代 号**: 小钰
> **角 色**: 安全专家
> **典型产出**: 22 项安全问题 / 🔴 严重 10 项 / 4 项 P0 鉴权漏洞

---

## 一、核心能力清单

### 1.1 22 项安全漏洞分类

| 类别 | 数量 | 风险等级 | 占比 |
|------|:----:|:--------:|:----:|
| **SQL 注入** | 5 | 🟡 中 | 23% |
| **JWT Secret 硬编码** | 1 | 🔴 严重 | 5% |
| **Token 生成不安全** | 1 | 🔴 严重 | 5% |
| **越权访问** | 8 | 🔴 严重 | 36% |
| **CSRF 保护缺失** | 1 | 🟡 中 | 5% |
| **XSS 漏洞** | 2 | 🟢 低 | 9% |
| **输入校验缺失** | 4 | 🟡 中 | 18% |

**总计: 22 个安全问题**,其中 🔴 严重 10 项(45%)。

### 1.2 鉴权漏洞挖掘能力(4 项 P0)

#### P0-A:JWT Secret 硬编码

```python
# ⚠️ 漏洞模式:环境变量缺失时使用默认密钥
# 危险:如果生产环境未设置 JWT_SECRET_KEY 环境变量,
# Flask session 将使用默认密钥,攻击者可以伪造任意 session。

# 风险特征: os.getenv('XXX_KEY', 'default-value')
```

**修复方案**:
```python
import secrets

jwt_secret = os.getenv('JWT_SECRET_KEY')
if not jwt_secret:
    raise RuntimeError(
        "JWT_SECRET_KEY 环境变量未设置,禁止启动!\n"
        "生成方法: python -c 'import secrets; print(secrets.token_hex(32))'"
    )
app.secret_key = jwt_secret
```

#### P0-B:dispatch_token 可伪造(base64 无签名)

```python
# ⚠️ 漏洞模式:base64 编码的 Token 无签名验证
# 危险:base64 编码 ≠ 加密,任何人都能解码并伪造 Token
# 风险特征: base64.b64encode(f"{uid}:{uname}".encode())
```

**修复方案**:
```python
import hmac
import hashlib

SECRET = os.environ['JWT_SECRET_KEY']

def make_dispatch_token(uid: str, uname: str) -> str:
    payload = f"{uid}:{uname}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.b64encode(f"{payload}:{sig}".encode()).decode()

def verify_dispatch_token(token: str) -> tuple:
    raw = base64.b64decode(token).decode()
    parts = raw.split(":")
    if len(parts) != 3:
        return None, None
    uid, uname, sig = parts
    expected = hmac.new(SECRET.encode(), f"{uid}:{uname}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None, None
    return uid, uname
```

#### P0-C:越权访问 8 项(水平/垂直越权)

| 位置 | 接口 | 越权类型 | 风险 |
|------|------|---------|------|
| server.py:L559 | 删除订单 | 水平越权 | 任何用户可删任意订单 |
| server.py:L775 | 修改订单 | 水平越权 | 任何用户可改任意订单 |
| server.py:L1210 | 编辑物料 | 水平越权 | 任何用户可改任意物料 |
| server.py:L2262 | 删除工序 | 水平越权 | 任何用户可删任意工序 |
| server.py:L2803 | 修改质检 | 水平越权 | 任何用户可改任意质检 |
| server.py:L3093 | 删除发货 | 水平越权 | 任何用户可删任意发货 |
| server.py:L3273 | 修改物流 | 水平越权 | 任何用户可改任意物流 |
| server.py:L1689 | 编辑工单 | 垂直越权 | 普通用户可执行管理员操作 |

**修复模板**(以删除订单为例):
```python
# 修复前(无校验)
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    dao.delete_order(order_id)  # ❌ 无权限校验
    return success()

# 修复后(双重校验)
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@require_auth
@require_role('admin', 'manager')  # 角色校验
def delete_order(order_id):
    order = dao.get_order(order_id)
    if not order:
        return error("订单不存在", 404)
    # 水平越权校验:只能删自己部门的订单
    if not can_modify_order(current_user, order):
        return error("无权操作此订单", 403)
    dao.delete_order(order_id)
    log_audit('delete_order', order_id, current_user.id)
    return success()
```

#### P0-D:移动端零凭证颁发 JWT

```python
# ⚠️ 漏洞模式:仅凭 operator_id 颁发 JWT,无密码验证
# 危险:只要知道 operator_id 就能拿到 JWT,完全无密码验证
# 风险特征: 仅通过 ID 查询即发 Token
```

**修复方案**:
```python
def login(username, password):
    user = dao.get_operator_by_username(username)
    if not user:
        return None, "用户名或密码错误"
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        log_security_event('login_failed', username)
        return None, "用户名或密码错误"
    if user.is_locked:
        return None, "账号已锁定"
    # 颁发短期 token + refresh token
    access_token = jwt.encode(
        {'uid': user.id, 'exp': datetime.utcnow() + timedelta(minutes=30)},
        current_app.config['JWT_SECRET'],
        algorithm='HS256'
    )
    return access_token, None
```

### 1.3 SQL 注入审计能力(5 项)

**4 项动态字段拼接漏洞**(必须加白名单):

```python
# 漏洞模式:f"UPDATE table SET {','.join(fields)} WHERE id=%s"
# 位置:server.py:L2068(工序)/L2732(质检)/L3041(发货)/L3260(物流)

# 修复:白名单校验
ALLOWED_UPDATE_FIELDS_PROCESS = {
    'status', 'remark', 'is_outsource', 'worker',
    'completed_qty', 'qualified_qty', 'work_hours'
}

def safe_update(table, record_id, data):
    for key in data:
        if key not in ALLOWED_UPDATE_FIELDS[table]:
            raise ValueError(f"字段 {key} 不允许更新")
    # 字段名已在白名单中,安全
    ...
```

**1 项已使用参数化但需验证**(L2664 质检搜索):
```python
kw = f"%{keyword}%"
# 需验证:keyword 是否经过 strip/转义
# 注意:PyMySQL 的 %s 占位符会自动转义
```

### 1.4 CORS/CSRF/XSS 防护能力

#### CORS 全开放(🟡 P2-B)

```python
# ⚠️ 漏洞模式:CORS 允许所有 origin
# 危险:任何网站都可以向后端发起跨域请求
# 风险特征: CORS(app, supports_credentials=True) 无 origins 白名单
```

**修复方案**:
```python
CORS(app,
     origins=os.getenv('ALLOWED_ORIGINS', '').split(','),
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'])
```

#### CSRF 保护缺失(🟠 P1-9)

```python
# ⚠️ 漏洞模式:敏感 API 无 CSRF 防护
# 危险:攻击者可在第三方页面诱导用户发起恶意请求
# 适用于前后端分离架构(移动端/桌面端 Web)的修复方案:
```

**修复方案 1:SameSite Cookie（推荐）**
```python
@app.after_request
def set_samesite_cookie(response):
    """所有 session cookie 设置 SameSite=Strict"""
    for cookie in response.headers.getlist('Set-Cookie'):
        if 'session' in cookie.lower():
            cookie = cookie + '; SameSite=Strict; Secure'
            # 更新 cookie
    return response
```

**修复方案 2:自定义请求头验证（推荐前后端分离）**
```python
# 前后端分离时,CORS 已经足够,额外加请求头验证
@app.before_request
def verify_custom_header():
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        # 仅允许来自我们自己的前端页面或 AJAX 请求
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            # 如果需要更严格的检查,验证 Origin
            allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
            origin = request.headers.get('Origin', '')
            if origin and origin not in allowed_origins:
                return error("跨域请求被拒绝", 403)

@app.route('/api/orders/<int:id>', methods=['DELETE'])
@require_auth
def delete_order(id):
    # 删除逻辑
    ...
```

**注意**:传统 Flask-WTF CSRFProtect 不适用于前后端分离架构(API 端无表单),请使用上述方案。```

#### XSS 防护(🟢 低)

```python
# 修复:模板自动转义 + CSP 头
@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'"
    )
    return response
```

### 1.5 敏感信息脱敏能力

#### 全局异常返回 str(e) 泄露 DB 结构(🟡 P2-C)

```python
# 漏洞(standalone_dispatch_server.py:L241)
@app.errorhandler(Exception)
def handle(e):
    return jsonify({'error': str(e)}), 500
    # ❌ 攻击者可见:
    # "(1054, \"Unknown column 'foo' in 'field list'\")"

# 修复
@app.errorhandler(Exception)
def handle(e):
    log_exception(e)  # 详细错误写入日志
    return jsonify({
        'code': 500,
        'message': '系统错误,请联系管理员',
        'trace_id': g.trace_id  # 仅返回追踪 ID
    }), 500
```

#### 日志脱敏规则

| 字段 | 处理 |
|------|------|
| 密码 | 完全不写入日志 |
| 身份证号 | 脱敏为 110101\*\*\*\*1234 |
| 手机号 | 脱敏为 138\*\*\*\*1234 |
| 银行卡 | 脱敏为 6225\*\*\*\*1234 |
| JWT Token | 仅记录前 8 位 + 后 4 位 |
| Cookie | 完全不写入日志 |

### 1.6 输入校验能力(4 项 P1-8)

**校验维度清单**:

| 维度 | 校验项 | 反例 |
|------|--------|------|
| **类型** | str/int/float/bool | 期望 int 实际 str |
| **范围** | 数值在合理区间 | 报工数量 99999 |
| **长度** | 字符串长度限制 | 备注 10000 字 |
| **格式** | 邮箱/手机号/身份证号 | email = "abc" |
| **空值** | 必填字段非空 | 备注为 None |
| **特殊字符** | SQL/XSS 注入字符 | 备注含 `<script>` |
| **业务规则** | 跨字段校验 | 起始日期 > 结束日期 |

**统一校验装饰器**:
```python
from functools import wraps
from pydantic import BaseModel, validator

def validate_schema(schema_cls):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                validated = schema_cls(**request.json)
                request.validated = validated
            except ValidationError as e:
                return jsonify({
                    'code': 400,
                    'message': '参数错误',
                    'errors': e.errors()
                }), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator

class LoginRequest(BaseModel):
    username: str
    password: str
    
    @validator('username')
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('用户名不能为空')
        if len(v) > 50:
            raise ValueError('用户名过长')
        return v.strip()
    
    @validator('password')
    def password_strong(cls, v):
        if len(v) < 6:
            raise ValueError('密码至少 6 位')
        return v
```

---

## 二、调用触发场景

### 🟢 应立即调用本 skill 的场景

| 触发词 | 典型场景 | 期望产出 |
|--------|---------|---------|
| "鉴权" / "JWT" / "Token" | 登录/Token 设计 | JWT Secret 硬编码检测 + 签名验证 |
| "越权" / "权限" / "8 项越权" | 增删改操作 | 8 项越权清单 + 角色校验 |
| "SQL 注入" / "动态拼接" | UPDATE/SELECT 拼接 | 5 项注入点 + 白名单修复 |
| "CORS" / "跨域" | 前端跨域调用 | CORS 配置 + allow_origins |
| "CSRF" | 表单/敏感操作 | CSRF token 机制 |
| "XSS" | 模板/前端 | CSP 头 + 转义 |
| "脱敏" / "str(e)" | 异常处理 | 全局异常脱敏 + 追踪 ID |
| "输入校验" | API 参数 | 9 大边界 + pydantic 校验 |
| "零凭证" / "免登录" | 登录逻辑 | 密码校验 + bcrypt |
| "22 项安全" / "安全审计" | 上线前安全审查 | 22 项分类清单 + 修复优先级 |

### 🟡 可调用本 skill 的场景

- 新接口的安全审查
- 第三方依赖漏洞扫描
- 安全合规审计
- 应急响应(发现漏洞后)
- 日志脱敏规则制定

---

## 三、标准工作流(7 步法)

```
第1步: 范围确认    → 审计对象(模块/接口/全栈)
第2步: 漏洞分类    → 7 大类(注入/鉴权/越权/CSRF/XSS/脱敏/校验)
第3步: 风险分级    → 🔴/🟠/🟡/🟢 + 攻击成本
第4步: 漏洞证据    → 文件:行号 + 代码片段 + 风险说明
第5步: 修复方案    → 可落地的代码示例
第6步: 验证方法    → 复现步骤 + 修复后测试用例
第7步: 应急响应    → 紧急修复 + 全量扫描同类问题
```

---

## 四、典型 P0 修复方案模板(可直接复用)

### 模板 1:环境变量强制检查

```python
# 所有敏感配置必须从环境变量读取,且禁止默认值
def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"环境变量 {name} 未设置!\n"
            f"启动前必须配置,否则禁止启动"
        )
    return value

# 应用启动时强制检查
JWT_SECRET = require_env('JWT_SECRET_KEY')
DB_PASSWORD = require_env('DB_PASSWORD')
WECHAT_CORP_SECRET = require_env('WECHAT_CORP_SECRET')
```

### 模板 2:JWT 签名强制 + 算法锁定

```python
# 修复前(无签名降级)
token = jwt.encode(payload, secret, algorithm=None)  # ❌ 可能降级为 base64

# 修复后(显式算法 + 验证时锁定)
token = jwt.encode(payload, secret, algorithm='HS256')

# 验证时显式指定允许的算法
try:
    payload = jwt.decode(token, secret, algorithms=['HS256'])  # 不允许降级
except jwt.InvalidAlgorithmError:
    return error("Token 算法不合法", 401)
```

### 模板 3:越权访问统一中间件

```python
from functools import wraps

def require_owner_or_admin(resource_dao, owner_field='created_by'):
    """要求资源所有者或管理员才能访问"""
    def decorator(f):
        @wraps(f)
        def wrapper(resource_id, *args, **kwargs):
            user = current_user
            resource = resource_dao.get_by_id(resource_id)
            if not resource:
                return error("资源不存在", 404)
            if user.role == 'admin':
                return f(resource_id, *args, **kwargs)
            if getattr(resource, owner_field) != user.id:
                log_security_event('unauthorized_access', user.id, resource_id)
                return error("无权访问此资源", 403)
            return f(resource_id, *args, **kwargs)
        return wrapper
    return decorator

# 使用
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@require_auth
@require_owner_or_admin(OrderDAO)
def delete_order(order_id):
    dao.delete_order(order_id)
    return success()
```

### 模板 4:全局异常脱敏

```python
import traceback
import uuid

@app.errorhandler(Exception)
def handle_exception(e):
    trace_id = str(uuid.uuid4())
    # 详细错误写入日志(含堆栈)
    logger.error(f"[{trace_id}] {type(e).__name__}: {e}\n{traceback.format_exc()}")
    # 返回脱敏后的响应
    if isinstance(e, BusinessError):
        return jsonify({
            'code': e.code,
            'message': e.message,
            'trace_id': trace_id
        }), e.http_status
    return jsonify({
        'code': 500,
        'message': '系统错误,请联系管理员',
        'trace_id': trace_id
    }), 500
```

---

## 五、与其他专家的协作接口

| 协作对象 | 输入 | 输出 | 协作模式 |
|---------|------|------|---------|
| **小圣(架构)** | 漏洞清单 | 架构层修复 | 小钰找漏洞 → 小圣设计修复 |
| **小贺(品控)** | 鉴权漏洞 | 越权业务风险 | 小钰找漏洞 → 小贺评估影响 |
| **小曦(PM)** | 漏洞影响 | 工厂优先级 | 小钰提漏洞 → 小曦定优先级 |
| **TRAE AI** | 共识汇总 | 安全审计补充 | 小钰审计 → TRAE 落文档 |

---

## 六、复用经验库

| 漏洞类型 | 教训 | 修复经验 |
|---------|------|---------|
| JWT Secret 硬编码 | 默认值=公开密钥 | 必须 raise + 启动检查 |
| base64 Token | 编码≠加密,任何人都能解码 | 必须 HMAC 签名 |
| 越权 8 项 | 任何"删除/修改"接口都要校验 | 统一中间件 + 双重校验 |
| SQL 注入 5 项 | 动态字段拼接是常见反模式 | 必须白名单 + 参数化 |
| CORS 全开放 | 内网也会被攻击 | 必须 allow_origins 白名单 |
| str(e) 泄露 | 攻击者可见 DB 结构 | 必须脱敏 + trace_id |
| 零凭证登录 | 移动端常见漏洞 | 必须 bcrypt 校验密码 |

---

## 七、能力评分(自评)

| 维度 | 评分 | 证据 |
|------|:----:|------|
| 鉴权漏洞 | ⭐⭐⭐⭐⭐ | 4 项 P0 鉴权漏洞 |
| 越权检测 | ⭐⭐⭐⭐⭐ | 8 项越权清单 |
| SQL 注入 | ⭐⭐⭐⭐ | 5 项注入点 + 白名单 |
| CORS/CSRF/XSS | ⭐⭐⭐⭐ | 三类浏览器侧攻击 |
| 脱敏 | ⭐⭐⭐⭐⭐ | str(e) 修复 + 追踪 ID |
| 输入校验 | ⭐⭐⭐⭐ | 4 项校验缺失 + pydantic |
| **综合** | **—** | 22 项安全问题(4 专家中数量最多) |

---

**调用示例**:
- "用小钰的视角审计这个新接口的越权风险"
- "按小钰的标准检测 JWT 鉴权是否有降级风险"
- "让小钰审查这 5 个动态 SQL 是否有注入风险"
- "按小钰的脱敏标准检查全局异常处理"
