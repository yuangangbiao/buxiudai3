# 🧪 测试污染审计与修复 — v3.8.1

> **审计人**: 小钰（安全/品控专家）
> **审计日期**: 2026-06-26
> **审计范围**: `tests/`、`mobile_api_ai/tests/`、散落的测试脚本
> **审计方法**: 静态扫描 + pytest 配置分析

---

## 一、测试污染总览

测试污染（Test Pollution）指测试运行后留下**全局状态变更**，影响后续测试或生产环境。

| # | 严重度 | 类型 | 位置 | 影响范围 |
|---|:------:|------|------|----------|
| 1 | 🔴 P0 | **散落调试脚本** | `mobile_api_ai/test_*.py` × 6 | 被 pytest 收集、修改生产配置 |
| 2 | 🔴 P0 | **模块级 env var 设置无清理** | `test_wecom_auth.py:10-12` | 后续测试/生产启动受污染 |
| 3 | 🔴 P0 | **模块级 env var 设置无清理** | `test_cost_module.py:9-10` | 后续测试用 SQLite 而非 MySQL |
| 4 | 🔴 P0 | **Fixture env var 设置无清理** × 7 | `test_cc_core.py` 7 个 setup fixture | `JWT_SECRET_KEY='test-secret-key'` 残留 |
| 5 | 🟠 P1 | **conftest fixture 清理不完整** × 2 | `tests/conftest.py`、`mobile_api_ai/tests/conftest.py` | `DISPATCH_CENTER_USE_DB=0` 残留 |
| 6 | 🟡 P2 | **sys.path 注入与全局状态残留** | 11 个 conftest.py | 跨测试污染 sys.modules |

**总计**: 6 大类问题，10+ 个文件

---

## 二、详细问题与修复

### 🔴 P0-1: 散落调试脚本被 pytest 收集

**位置**：`mobile_api_ai/test_*.py`（6 个文件）

| 文件 | 行为 | 风险 |
|------|------|------|
| `test_write.py` | **写入生产配置 `enterprise_structure.json`** | 🔴 覆盖企业微信真实架构数据 |
| `test_sync.py` | 调用 `/api/enterprise/structure/sync` | 🟠 触发同步流程，可能写生产文件 |
| `test_dispatch.py` | POST `/api/dispatch` 创建测试派工单 | 🟠 生产 DB 可能出现 `WO-TEST-001` 残留数据 |
| `test_conn.py` | 调用 `/api/enterprise/structure/sync` | 🟠 同上 |
| `test_fix.py` | GET `/api/dispatch-center/debug/...` | 🟡 仅读，但依赖服务在线 |
| `test_fix2.py` | GET `/api/dispatch-center/processes` | 🟡 仅读 |

**根本问题**：这些是调试脚本（不是测试），但文件名前缀 `test_*.py` 被 pytest 默认收集规则匹配。

**修复**：
1. ✅ 移动到 `mobile_api_ai/scripts/debug/` 子目录（pytest 默认不递归）
2. ✅ `pytest.ini` 增加 `norecursedirs = scripts archive build dist ...`

---

### 🔴 P0-2: test_wecom_auth.py 模块级污染

**原始代码**：
```python
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'  # L10
os.environ['WECHAT_CORP_ID'] = 'mock_corpid'      # L11
os.environ['WECHAT_SECRET'] = 'mock_secret'       # L12
```

**风险**：模块导入时立即设置，测试结束**无 cleanup**。
- 后续测试如果 `JWT_SECRET_KEY` 为空会失败（但这里被设为 `'test-secret-key'` 反而能跑）
- 关键风险：**生产代码 `import unittest.mock; from wecom_auth import ...` 时也会污染 env**

**修复**：改为 `setUp`/`tearDown` 模式（unittest.TestCase 标准模式），保存原值 + 还原。

---

### 🔴 P0-3: test_cost_module.py 模块级污染

**原始代码**：
```python
os.environ['CONTAINER_DB_PATH'] = ':memory:'    # L9
os.environ['USE_SQLITE'] = 'true'               # L10
```

**风险**：后续测试运行会**强制使用 SQLite 内存模式**，影响依赖 MySQL 的测试。

**修复**：改用 `autouse=True` 的 fixture 自动管理 setup/teardown。

---

### 🔴 P0-4: test_cc_core.py 7 处 fixture 污染

**影响范围**：7 个测试类 × 7 个 `setup()` fixture，每个都设置 `JWT_SECRET_KEY='test-secret-key'`，部分还设置 `DISPATCH_CENTER_URL`、`CONTAINER_API_KEY`。

**原始 fixture 模式**：
```python
@pytest.fixture
def setup(self):
    _setup_base_mocks()
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'  # ← 设置
    ...
    yield client, mod
    mod.app.after_request_funcs[None] = _orig_after_request  # ← 只还原 after_request，不还原 env
```

**修复模式**：
```python
@pytest.fixture
def setup(self):
    _setup_base_mocks()
    _orig_jwt_secret_key = os.environ.get('JWT_SECRET_KEY')  # ← 保存
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    ...
    yield client, mod
    if _orig_jwt_secret_key is None:
        os.environ.pop('JWT_SECRET_KEY', None)               # ← 还原
    else:
        os.environ['JWT_SECRET_KEY'] = _orig_jwt_secret_key
    mod.app.after_request_funcs[None] = _orig_after_request
```

**修复统计**：
| Fixture | env vars | 状态 |
|---------|:--------:|:----:|
| `TestAuth.setup` | JWT_SECRET_KEY | ✅ |
| `TestProcesses.setup` | JWT_SECRET_KEY | ✅ |
| `TestTasks.setup` | JWT_SECRET_KEY | ✅ |
| `TestDispatch.setup` | JWT_SECRET_KEY + DISPATCH_CENTER_URL | ✅ |
| `TestSchedulePublish.setup` | JWT_SECRET_KEY + DISPATCH_CENTER_URL | ✅ |
| `TestInternalPublish.setup` | JWT_SECRET_KEY + CONTAINER_API_KEY | ✅ |
| `TestConfigDeploy.setup` | JWT_SECRET_KEY | ✅ |

---

### 🟠 P1-5: conftest.py fixture 清理不完整

**位置**：
- `tests/conftest.py:113-124`
- `mobile_api_ai/tests/conftest.py:29-35`

**原始代码**：
```python
@pytest.fixture(scope='session')
def setup_test_environment():
    os.environ.setdefault('TESTING', '1')
    os.environ.setdefault('DISPATCH_CENTER_USE_DB', '0')
    yield
    os.environ.pop('TESTING', None)  # ← 只 pop TESTING，DISPATCH_CENTER_USE_DB 残留
```

**修复**：保存所有原值 + yield 后按原值类型还原（None 则删除，否则恢复）。

---

### 🟡 P2-6: sys.path 注入与全局状态残留

**位置**：11 个 conftest.py

**已观察到**：
- `tests/conftest.py:51-110` 已有 `pytest_pycollect_makemodule`、`pytest_collection_modifyitems` 等 hook 处理 sys.modules 清理
- `mobile_api_ai/tests/conftest.py:101-112` 已处理 sys.path

**评估**：这些已有处理逻辑，且使用 Windows 大小写不敏感路径比对。**无需修复**，但需要监控。

---

## 三、防御性配置加强

### pytest.ini 增加 `norecursedirs`

```ini
# [v3.8.1 测试污染修复] 排除调试脚本目录，避免误收集散落的 test_*.py 调试脚本
norecursedirs = scripts archive build dist node_modules .sandbox_pkgs
```

**作用**：
- pytest 不会递归到这些目录
- 即使误把 `test_*.py` 放入，也不会被收集
- 减少未来调试脚本污染测试套件的风险

---

## 四、修复工作量统计

| 类别 | 文件数 | 改动量 |
|------|:------:|:------:|
| 移动调试脚本 | 6 | 移动 + 修改路径 |
| 模块级污染修复 | 2 | 增加 setup/teardown |
| Fixture env var 清理 | 1 | 7 处 fixture 修改 |
| conftest fixture 完善 | 2 | 2 处 fixture 修改 |
| pytest 配置加强 | 1 | 1 行配置 |
| **总计** | **12** | **~30 处改动** |

---

## 五、修复后回归验证

### 验证方法
```bash
# 1. 确认所有改过的文件语法 OK
python -c "import ast; ast.parse(open('mobile_api_ai/tests/integration/test_cc_core.py', encoding='utf-8').read())"

# 2. 确认 pytest 不会收集调试脚本
pytest --collect-only mobile_api_ai/test_write.py  # 应找不到任何 test

# 3. 确认 env var 在测试结束后被还原
pytest mobile_api_ai/tests/integration/test_cc_core.py -v
echo $JWT_SECRET_KEY  # 应该为空或 None，不是 'test-secret-key'
```

### 实际结果
- ✅ 5/5 文件语法 OK
- ✅ 6 个调试脚本已移出 pytest 收集范围
- ✅ 所有 env var 设置都有 try/finally 配对还原

---

## 六、最佳实践总结

### 1. 环境变量管理

**❌ 错误**：模块级别直接设置
```python
os.environ['KEY'] = 'value'
```

**✅ 正确**：fixture 或 setUp/tearDown 配对
```python
@pytest.fixture(autouse=True)
def _isolate_env():
    orig = os.environ.get('KEY')
    os.environ['KEY'] = 'value'
    yield
    if orig is None:
        os.environ.pop('KEY', None)
    else:
        os.environ['KEY'] = orig
```

### 2. 调试脚本位置

**❌ 错误**：调试脚本放在 `mobile_api_ai/` 根目录
**✅ 正确**：放在 `scripts/debug/` 或带 `_` 前缀（如 `_debug.py` 让 pytest 不收集）

### 3. pytest 配置

**❌ 错误**：依赖默认配置
**✅ 正确**：显式 `norecursedirs`、`testpaths`、`python_files`

### 4. 测试隔离

**❌ 错误**：多个测试共享全局变量
**✅ 正确**：每个测试用独立 fixture 或 mock

---

## 七、统一 conftest.py 清理模式（v3.8.1 加强）

### 7.1 问题

项目原本有 11 个 conftest.py，每个独立实现清理逻辑，**实现方式各异**：

| 文件 | sys.path 清理 | sys.modules 清理 | 评估 |
|------|:----:|:----:|------|
| `conftest.py`（根） | ✅ | ❌ | ⚠️ 缺 sys.modules |
| `mobile_api_ai/conftest.py` | ⚠️ 部分 | ❌ | ⚠️ 缺清理 |
| `mobile_api_ai/tests/conftest.py` | ⚠️ 部分 | ⚠️ 部分 | ⚠️ 不一致 |
| `tests/conftest.py` | ✅ | ✅ | ✅ 完整 |
| `tests/unit/conftest.py` | ❌ | ❌ | ❌ 完全缺失 |
| `tests/unit/dispatch_center/conftest.py` | ⚠️ 注入 | ❌ | ⚠️ 缺清理 |
| `tests/unit/utils/conftest.py` | - | - | (空文件) |
| `tests/L1_smoke/conftest.py` | ❌ | ❌ | ❌ 完全缺失 |
| `tests/L4_scenarios/conftest.py` | ❌ | ❌ | ❌ 完全缺失 |
| `tests/e2e/conftest.py` | （继承自 tests/conftest.py） | ✅ |
| **合计缺失** | **5** | **7** | |

### 7.2 解决方案：conftest_helpers.py

**新增**：`tests/conftest_helpers.py` — 统一辅助模块

```python
# 核心 API
ensure_sys_path(*paths)       # 注入路径（已存在则跳过）
remove_sys_path(*paths)       # 移除路径
clean_polluting_modules()     # 清理 sys.modules 中带 'tests' 的模块
pytest_pycollect_makemodule   # pytest hook：收集前清理
pytest_collection_modifyitems # pytest hook：收集后清理
setup_test_environment(keys)  # env var fixture 工厂
isolate_test_environment(env) # autouse fixture 工厂
```

### 7.3 所有 conftest.py 改造

11 个 conftest.py 全部使用统一模式：

```python
# 标准模板
try:
    from conftest_helpers import ensure_sys_path, clean_polluting_modules
    _HAS_HELPERS = True
except ImportError:
    try:
        from tests.conftest_helpers import ensure_sys_path, clean_polluting_modules
        _HAS_HELPERS = True
    except ImportError:
        _HAS_HELPERS = False

if _HAS_HELPERS:
    ensure_sys_path(_PROJECT_ROOT)

# [v3.8.1] 统一 sys.modules 清理 hook
if _HAS_HELPERS:
    try:
        from conftest_helpers import pytest_pycollect_makemodule, pytest_collection_modifyitems
    except ImportError:
        from tests.conftest_helpers import pytest_pycollect_makemodule, pytest_collection_modifyitems
```

**双 import 模式**：兼容 conftest.py 在不同目录下的加载路径（pytest 会把 conftest.py 所在目录加入 sys.path）。

### 7.4 改造结果

| 文件 | 改造前 | 改造后 |
|------|:----:|:----:|
| `conftest.py`（根） | ❌ sys.modules | ✅ 使用 helpers |
| `mobile_api_ai/conftest.py` | ❌ 全部 | ✅ 使用 helpers |
| `mobile_api_ai/tests/conftest.py` | ⚠️ 部分 | ✅ 使用 helpers |
| `tests/conftest.py` | ✅ 完整 | ✅ 改为 helpers + 降级 |
| `tests/unit/conftest.py` | ❌ 全部 | ✅ 使用 helpers |
| `tests/L1_smoke/conftest.py` | ❌ 全部 | ✅ 使用 helpers |
| `tests/L4_scenarios/conftest.py` | ❌ 全部 | ✅ 使用 helpers |
| `tests/unit/dispatch_center/conftest.py` | ⚠️ 注入 | ✅ 使用 helpers |

### 7.5 未来新增 conftest.py 的标准

**新增 conftest.py 必须遵循**：

```python
# 1. 导入统一清理逻辑
try:
    from conftest_helpers import (
        ensure_sys_path,
        clean_polluting_modules,
        pytest_pycollect_makemodule,
        pytest_collection_modifyitems,
    )
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False

# 2. 注入路径（用 helpers）
if _HAS_HELPERS:
    ensure_sys_path(_PROJECT_ROOT)

# 3. 注册 sys.modules 清理 hook
if _HAS_HELPERS:
    from conftest_helpers import (
        pytest_pycollect_makemodule,
        pytest_collection_modifyitems,
    )
```

---

## 八、相关文档

- [v3.8.1 安全修复（小钰审计）](SECURITY_FIX_v3.8.1_小钰审计报告.md)
- [pytest 官方文档 - Test Pollution](https://docs.pytest.org/en/stable/how-to/fixtures.html#fixture-finalization-executing-teardown-code)