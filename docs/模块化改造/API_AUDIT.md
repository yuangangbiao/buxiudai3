# API_AUDIT.md（API 架构审计）

> 文档版本：v1.0（2026-06-13）
> 审计范围：5002 容器中心 71 个 API 路由
> 审计原则：**实测统计，不靠嘴**

---

## 一、统计总览

| 指标 | 当前 | 评分 |
|------|------|------|
| API 总数 | 71 | - |
| 有 try/except | 34 (47%) | 🟡 |
| 有鉴权 | 4 (5%) | 🔴 |
| 有审计日志 | 5 (7%) | 🔴 |
| 有 rate limit | 0 (0%) | 🔴 |
| 有响应统一格式 | ~50% | 🟡 |
| 有 OpenAPI 文档 | 0 | 🟡（H3 有 markdown）|
| 鉴权装饰器 import 失败时 | 降级为**无鉴权** | 🔴 |

---

## 二、10 个 J 编号问题

### 🔴 J1: 67 个 API 无任何鉴权（94%）

**实测**：
```python
# 71 个 @app.route
# 仅 4 个有 @require_api_key 装饰器
# 67 个（94%）完全开放！
```

**风险**：
- 任何人可以读订单 / 写工序 / 删除数据
- 唯一有鉴权的是 mirror + 3 个 sub_step 查询
- 即使是写操作 `api_material_create`, `api_rollback_sub_step` 都没有鉴权

**修复**：
- 全局 `@app.before_request` 加 API Key 校验
- 或所有 POST/PUT/DELETE 必须鉴权
- 读 API 鉴权可选

### 🔴 J2: require_api_key 默认是空装饰器

**位置**：`container_center_api.py:135-141`

```python
try:
    from api.decorators import require_api_key
except ImportError:
    def require_api_key(f):
        """降级：无 API Key 校验"""
        return f
```

**风险**：
- 如果 `api.decorators` 模块路径错（重构时）→ 所有 API 静默无鉴权
- 无启动检查（启动时不验证鉴权是否生效）

**修复**：
- fail-fast：导入失败时**拒绝启动** 5002
- 不接受降级

### 🔴 J3: 0 个 rate limit

**风险**：
- 单 IP 1 秒 1000 次请求可以
- 数据库被打爆
- 业务层无限循环调用无限制

**修复**：
- 用 flask-limiter
- 全局 100 QPS/IP
- 写 API 10 QPS/IP

### 🔴 J4: 审计日志覆盖率 7%

**实测**：
```python
if _server_audit_logger:
    _server_audit_logger.log(...)
```
- 仅出现在 5 个 API（L2029, 2130, 2353, 2398, 2421）
- 66 个 API 无审计日志
- 无法追溯谁调用了什么

**修复**：
- 全局 after_request 记录
- 或所有写 API 必须审计

### 🔴 J5: 47% API 无 try/except

**实测**：
- 34 个有 try/except
- 37 个无 try/except
- 抛异常时返回 Flask 默认 500 页面
- 前端拿到 HTML 而非 JSON → 解析失败

**修复**：
- 全局 `@app.errorhandler(Exception)` 统一返回 JSON
- 或所有 API 必须 try/except

### 🟡 J6: 响应格式不统一

**实测**：
- 部分 API 用 `success(data)` ✅
- 部分 API 用 `jsonify({'code': 0, 'data': ...})` 
- 部分 API 直接返回 `dict`
- 客户端解析混乱

**修复**：
- 全局强制 success/fail 函数
- 禁止直接 jsonify

### 🟡 J7: API URL 无版本号

**实测**：
- 71 个 API 都是 `/api/xxx`
- 没有 `/v1/api/xxx` 版本管理
- 重构时无法做兼容

**修复**：
- 加 `/v1/` 前缀
- 内部 API 用 `/internal/v1/`
- 外部 API 用 `/api/v1/`

### 🟡 J8: 写 API 重复

**实测**：
- `dispatch_task` (L1136) 和 `dispatch_task` (L1137) 同名，URL 不同
- `/api/dispatch` 和 `/api/wechat/dispatch` 重复
- `api_process_names` (L653) 和 `get_process_names` (L1077) 同名
- `api_get_sub_step_summary` (L2857) 和 `api_get_sub_step_summary_by_order` (L2868) 几乎一样

**修复**：
- 删重复
- 保留一份作为正式 API

### 🟡 J9: GET 路由无 cache-control

**位置**：31 个 GET 路由

**问题**：
- 没有 `Cache-Control: max-age=60` 等头
- 客户端每次都重新请求
- 数据库压力大

**修复**：
- 静态数据（operators, process_names）加 `Cache-Control: max-age=3600`
- 动态数据（orders, tasks）加 `max-age=0, must-revalidate`

### 🟡 J10: 错误码落地率 9%

**实测**：
- 33 个错误码
- 业务层用 `fail('字符串', code=400)` 而非 `fail(ErrorCode.XXX[0], code=400)`
- 客户端无法按 code 路由

**修复**：
- fail() 函数签名改：`fail(message, code=ErrorCode.INTERNAL_ERROR[0])`
- 强制用错误码

---

## 三、API 风险矩阵

| 风险 | 影响 | 紧急度 |
|------|------|--------|
| 67 个 API 无鉴权 | 任何人可调 | 🔴 P0 |
| 0 个 rate limit | 易被攻击 | 🔴 P0 |
| 47% API 无 try/except | 500 错误暴露内部 | 🔴 P0 |
| 鉴权装饰器降级为 None | 静默安全漏洞 | 🔴 P0 |
| 审计日志 7% | 无法追溯 | 🟡 P1 |
| 响应格式不统一 | 客户端混乱 | 🟡 P1 |
| URL 无版本 | 难重构 | 🟢 P2 |
| 错误码 9% | 客户端路由困难 | 🟢 P2 |
| GET 无 cache | 性能浪费 | 🟢 P2 |
| 重复 API | 维护混乱 | 🟢 P2 |

---

## 四、修复优先级

| 优先级 | 项 | 工作量 | 严重度 |
|--------|-----|--------|--------|
| **P0** | J1 全局鉴权 | 2h | 🔴 |
| **P0** | J2 fail-fast 鉴权 | 30min | 🔴 |
| **P0** | J3 flask-limiter | 1h | 🔴 |
| **P0** | J5 全局 errorhandler | 30min | 🔴 |
| **P1** | J4 全局审计日志 | 1h | 🟡 |
| **P1** | J6 强制 success/fail | 1h | 🟡 |
| **P2** | J7 API 版本 | 2h | 🟢 |
| **P2** | J8 删重复 API | 1h | 🟢 |
| **P2** | J9 cache-control | 1h | 🟢 |
| **P2** | J10 错误码落地 | 2h | 🟢 |
| **总计** | - | **12.5h** | - |

---

## 五、API 完整列表（71 个）

| 分类 | 数量 |
|------|------|
| 健康/状态 | 6 |
| 工序 | 12 |
| 任务 | 6 |
| 外协 | 7 |
| 物料 | 6 |
| 报工 | 5 |
| 订单 | 1 |
| 内部/配置 | 4 |
| 微信/通知 | 5 |
| 企业架构 | 2 |
| 子步骤/审计 | 4 |
| 其他 | 11 |
| **合计** | **71** |

---

## 六、参考

- [API.md](./API.md) - API 文档（已写但缺鉴权说明）
- [ERROR_CODES.md](./ERROR_CODES.md) - 错误码字典
- [RUNBOOK.md](./RUNBOOK.md) - 运维手册

---

## 七、关键洞察

> **API 审计的核心是鉴权**：
>
> - 71 个 API 中 67 个无鉴权 = **任意人可读可写**
> - 业务再严谨，无鉴权 = **无安全**
> - 0 个 rate limit = **易被打爆**
> - 47% 无 try/except = **错误信息泄露**
>
> 之前所有 DDL/事务/性能工作，**都假设有鉴权**。
> 实际生产环境，**第一步应该是鉴权**。
>
> **真实评分**：
> - 数据严谨性：70-80%
> - **API 安全性：30%**（仅 4 个 API 有鉴权）
> - **API 健壮性：40%**（47% 无 try/except）
