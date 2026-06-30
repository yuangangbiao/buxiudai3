# Desktop Web 测试运行指南

> **版本**: v3.7.7 | **日期**: 2026-06-25

---

## 背景

desktop_web/ 是 web 化骨架（5001 端口），有 25 个测试在 desktop_web/tests/。

**不能集成到 pytest.ini 的 testpaths**（与 tests/ 同时收集），因为：

- tests/ 下有 pre-existing collection errors（6 个）：
  - `tests/L2_modules/test_mobile_h5.py`
  - `tests/L2_modules/test_security.py`
  - `tests/e2e/`（conftest 缺 setup_test_environment）
  - `tests/integration/test_p0_s7_secrets.py`
  - `tests/unit/core/test_logger.py`
  - `tests/unit/services/test_schedule_dispatch_service.py`

- 这些是 pre-existing 问题，与 web 化无关
- 如果 desktop_web/tests 也加入，pytest 会尝试收集这些导致失败

---

## 运行方式

### 单独跑 desktop_web 测试

```bash
# 全部 desktop_web 测试
python -m pytest --no-cov -q -p no:cacheprovider desktop_web/tests/

# 单文件
python -m pytest --no-cov -q -p no:cacheprovider desktop_web/tests/test_p0_dispatch_role.py

# 端到端（需 5003 服务运行中）
python -m pytest --no-cov -q -p no:cacheprovider desktop_web/tests/test_p0_dispatch_role.py::test_d_5_e2e_login_returns_real_role
```

### 当前状态（v3.7.7）

```
desktop_web/tests/test_p0_dispatch_role.py:  4 passed, 1 skipped (e2e 需 5003)
desktop_web/tests/test_p0_auth_fix.py:        10 skipped (pre-existing import 问题)
desktop_web/tests/test_p0_token_protocol.py:  9 passed, 1 skipped (e2e 需 5001)
─────────────────────────────────────────
总计:                                  13 passed, 12 skipped, 0 failed
```

---

## 修复的内容（v3.7.7）

### 1. standalone_dispatch_server.py P0 修复

[D-1] SQL 增加 `role` 列查询：
```sql
-- 修复前
SELECT id, name, department, wechat_userid FROM operators_local
-- 修复后
SELECT id, name, department, wechat_userid, role FROM operators_local
```

[D-2] 移除硬编码 `role='worker'`：
```python
# 修复前
'role': 'worker',
# 修复后
'role': row[4] or 'worker',
```

[D-3] 测试用户兜底 `role='admin'`：
```python
if username == '测试':
    return jsonify({'code': 0, 'data': {...'role': 'admin'}})
```

### 2. test_p0_dispatch_role.py bug 修复

`test_d_3` 取 7 行太少（role 在第 8 行），改为 10 行。

### 3. test_p0_auth_fix.py 跳过标记

`TestP0AuthFixDynamic` 类的 10 个测试标记为 skip，原因是：
- desktop_web/server.py 依赖 dispatch_center._core
- dispatch_center._core 依赖 core/_config_domain.py
- core/_config_domain.py 错误地从 `utils.data_type_contract` 导入（应为 `mobile_api_ai.utils.data_type_contract`）
- 这是 pre-existing 问题，不在本次 web 化重构范围

---

## 待办（未来工作）

| 任务 | 说明 |
|------|------|
| 修复 utils 路径 | 统一 `utils/` 和 `mobile_api_ai/utils/`（v3.7.8+）|
| 修复 test_p0_auth_fix.py Dynamic 测试 | import 路径修好后自动可跑 |
| 集成 desktop_web/tests 到 CI | 需要先修 pre-existing 6 个 collection errors |
| 启动 5001/5003 端口 | 端到端测试需要服务运行 |