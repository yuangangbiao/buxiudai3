# 验收记录：企业微信 OAuth2 登录

## 实现功能

### 后端
- [x] `POST /api/wecom/login` — 用 code 换 UserId，匹配操作员，返回 JWT
- [x] 企业微信 API 异常处理（token 失败、用户信息失败）
- [x] 操作员匹配逻辑（按 `wechat_userid` 字段）
- [x] 操作员禁用检查
- [x] JWT 签发（含 userid/op_id/name/exp）

### 前端
- [x] `GET /mobile_login.html` — 登录页面
  - [x] 自动从 URL 提取 `?code=xxx`
  - [x] 调后端登录接口
  - [x] 存 token/operator 到 localStorage
  - [x] 自动跳转首页 `/`
  - [x] 无 code 时提示"请在企业微信中打开"
  - [x] 加载中 / 成功 / 失败状态显示

### 配置
- [x] `WECHAT_CORP_ID` 和 `WECHAT_SECRET` 从 `.env` 读取
- [x] config.py 新增企业微信配置项

## 测试结果

| 测试用例 | 结果 |
|---------|------|
| code 参数缺失 → 400 | ✅ |
| 获取 token 失败 → 500 | ✅ |
| 获取用户信息失败 → 500 | ✅ |
| 操作员不匹配 → 401 | ✅ |
| 操作员被禁用 → 403 | ✅ |
| 正常登录 → 200 + token | ✅ |
| wechat_userid 为空 → 401 | ✅ |

## 路由验证

| 路由 | 状态 |
|------|------|
| `/api/wecom/login` (POST) | ✅ 200 |
| `/mobile_login.html` (GET) | ✅ 200 |

## 修复记录

1. 测试代码: `bp.test_request_context()` 不存在 → 改用 `app.test_client()`
2. `container_config.get_operators()` 不存在 → 改为 `get_all_operators()`
3. `datetime.utcnow()` 废弃 → 改为 `datetime.now(timezone.utc)`
