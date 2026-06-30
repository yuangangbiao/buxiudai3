# P0-G 安全修复方案 - 测试用户后门

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 Week 0 P0紧急任务
> **漏洞评级**: 🔴 CRITICAL（P0最高优先级）
> **审计来源**: 4专家审计（小钰安全）
> **预计工时**: 30分钟（含测试验证）
> **修复责任人**: AI团队

---

## 一、漏洞描述

### 1.1 漏洞位置

[standalone_dispatch_server.py:96-104](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/standalone_dispatch_server.py#L96-L104)

```python
# 测试用户兜底 (便于 admin 路径测试)        ← ← ← ← ← ← ← ← ← ← ← ←
if username == '测试':                          # ← 任何人输入"测试"即可绕过
    return jsonify({'code': 0, 'data': {
        'id': 0,                                # ← id=0，非真实用户
        'name': '测试',                          # ← mock数据
        'department': '测试部',
        'username': '测试',
        'wechat_userid': 'test_user',
        'role': 'admin',                        # ← 直接给admin权限！无任何验证！
    }})                                         # ← 无签名/无Token/无环境判断
```

### 1.2 漏洞危害

| 危害维度 | 详情 | 风险 |
|---------|------|:----:|
| **垂直越权** | 任何人以"测试"登录即获admin身份 | 🔴 极高 |
| **数据破坏** | admin可删除/修改所有订单/工序/质检数据 | 🔴 极高 |
| **生产中断** | 恶意删除排产后，生产全面停工 | 🔴 极高 |
| **无审计** | id=0的mock数据，无任何操作记录 | 🔴 极高 |

### 1.3 攻击路径

```
1. 攻击者访问 POST /api/auth/login
2. body: {"username": "测试", "password": "任意值"}
3. 服务端直接返回admin身份
4. 攻击者用返回的admin身份 → DELETE /api/orders/1 → 订单消失
```

---

## 二、修复方案

### 2.1 方案选择

**推荐方案：完全删除 + 开发环境隔离**

将测试后门代码完全删除。开发环境需要测试admin路径时，使用专门的**测试账号注入环境变量**，而非硬编码在代码中。

### 2.2 修复代码

#### 步骤1：删除后门代码（standalone_dispatch_server.py:95-104）

**修改前**：
```python
        # 测试用户兜底 (便于 admin 路径测试)
        if username == '测试':
            return jsonify({'code': 0, 'data': {
                'id': 0,
                'name': '测试',
                'department': '测试部',
                'username': '测试',
                'wechat_userid': 'test_user',
                'role': 'admin',
            }})
```

**修改后**：直接删除整段代码，登录逻辑从行93直接跳到行106的`try:`。

#### 步骤2（可选）：开发环境测试账号

如果开发环境确实需要测试admin路径，通过**环境变量注入**：

```python
# standalone_dispatch_server.py 行93后新增（仅DEBUG模式有效）
import os

TEST_ADMIN_USERNAME = os.getenv('TEST_ADMIN_USERNAME', '')
TEST_ADMIN_PASSWORD = os.getenv('TEST_ADMIN_PASSWORD', '')

if os.getenv('FLASK_ENV') == 'development' and username == TEST_ADMIN_USERNAME:
    if password == TEST_ADMIN_PASSWORD:
        return jsonify({'code': 0, 'data': {
            'id': -1,
            'name': '开发测试账号',
            'department': '开发部',
            'username': TEST_ADMIN_USERNAME,
            'wechat_userid': 'dev_test',
            'role': 'admin',
            'note': '[仅开发环境有效]',
        }})
    else:
        return jsonify({'code': 401, 'message': '用户名或密码错误'})
```

**使用方式**：
```bash
# .env.development
FLASK_ENV=development
TEST_ADMIN_USERNAME=test_dev
TEST_ADMIN_PASSWORD=DevTest@2026

# 生产环境：无 FLASK_ENV=development 变量 → 后门完全不生效
```

---

## 三、修复后验证

### 3.1 功能验证

| 测试用例 | 操作 | 预期结果 |
|---------|------|---------|
| 正常用户登录 | POST /api/auth/login {"username":"张三","password":"xxx"} | 正常返回用户数据 |
| "测试"登录（生产） | POST /api/auth/login {"username":"测试","password":"任意值"} | **返回401** "用户名或密码错误" |
| "测试"登录（开发） | POST /api/auth/login {"username":"test_dev","password":"DevTest@2026"} | 返回id=-1的管理员（带[仅开发环境有效]标识） |

### 3.2 安全验证

| 验证项 | 操作 | 预期结果 |
|--------|------|---------|
| admin路由保护 | 用"测试"账号的返回token调用 GET /api/dispatch-center/orders | **403 Forbidden** |
| 数据库无id=0记录 | SELECT * FROM operators_local WHERE id=0 | 空结果 |
| 日志审计 | 搜索日志中"测试"登录 | 出现警告或拒绝记录 |

---

## 四、相关安全检查

修复P0-G后，同步检查同文件中是否还有其他后门或测试逻辑：

| 位置 | 检查内容 | 状态 |
|------|---------|------|
| standalone:96-104 | 测试用户后门 | ← 修复对象 |
| standalone:1033 | IP硬编码 fallback | ⚠️ N5任务 |
| standalone:109-110 | operators_local查询（已正确使用参数化） | ✅ 无问题 |
| standalone全局 | 其他 `username == '测试'` 或 `username == 'admin'` | 待grep确认 |

---

## 五、修复清单

| # | 动作 | 状态 | 验收标准 |
|---|------|:----:|---------|
| 1 | 删除 standalone:95-104 测试后门代码 | ⬜ | 代码中无 `username == '测试'` 判断 |
| 2 | 添加开发环境测试账号（可选，FLASK_ENV判断） | ⬜ | 仅development模式生效 |
| 3 | 功能验证：正常用户登录正常 | ⬜ | 返回真实用户数据 |
| 4 | 安全验证："测试"登录被拒绝 | ⬜ | 返回401错误 |
| 5 | 日志检查：无id=0的admin操作记录 | ⬜ | grep日志无id=0 admin记录 |
| 6 | 全文件grep：确认无其他测试后门 | ⬜ | 代码中无其他username硬编码判断 |
| 7 | bandit安全扫描：无新HIGH漏洞引入 | ⬜ | CI bandit 0 HIGH |
| 8 | 4-gate门禁全通过 | ⬜ | pytest≥95% + 100并发通过 |

---

## 六、修复后签字

| 签字人 | 签字 | 日期 |
|--------|------|------|
| 开发负责人 | ☐ | ____ |
| 安全（小钰） | ☐ | ____ |
| PM（小曦） | ☐ | ____ |
| 品控（小贺） | ☐ | ____ |

---

**修复状态**: 未开始
**修复期限**: Week 0 第1天必须完成
**最后更新**: 2026-06-28
