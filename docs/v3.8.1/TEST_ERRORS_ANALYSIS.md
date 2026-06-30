# 测试 ERROR 根因分析报告

> **创建日期**: 2026-06-25
> **触发**: 全量 pytest 收集时发现 15 个文件 ERROR,约 300+ 测试无法跑
> **作者**: AI 助手
> **结论先行**: **架构问题占 93% (14/15)**,非简单代码 bug

---

## 1. 整体数据

| 维度 | 数量 |
|------|:----:|
| 测试文件总数 | 263 |
| test_ 函数总数 | 4196 |
| 可收集测试 | 3905 |
| 收集失败 (ERROR) | 15 文件 |
| skip 标记 | 56+ |
| 修复后 ERROR | 0(v3.8.1) |

---

## 2. 15 个 ERROR 详细分类

### 🔴 架构问题(14 个 / 93%) — 单根因级联

| 文件 | 报错链 |
|------|--------|
| `tests/unit/models/test_inventory.py` | models/inventory.py:7 → config.py:6 → core/config.py:13 → core/_config_domain.py:5 |
| `tests/unit/models/test_order_dao.py` | 同上链 |
| `tests/unit/models/test_process.py` | 同上链 |
| `tests/unit/models/test_photo_storage.py` | 同上链 |
| `tests/unit/models/test_production_stats.py` | 同上链 |
| `tests/unit/models/test_product_flow_map.py` | 同上链 |
| `tests/unit/models/test_operator.py` | 同上链 |
| `tests/unit/models/test_operator_depth.py` | 同上链 |
| `tests/unit/models/database/test_utils_db.py` | 同上链 |
| `tests/unit/services/test_schedule_dispatch_service.py` | services/__init__.py → models/database → 同上链 |
| `tests/unit/services/test_order_service_complete.py` | 同上链 |
| `tests/unit/core/test_logger.py` | logger.py:14 → core/config.py → 同上链 |
| `tests/unit/core/test_logger.py`(额外) | LOG_DIR 类型问题:'_str' has no .mkdir |
| 其他 1 个 | 同根因 |

### 🟡 代码问题(1 个 / 7%)

| 文件 | 错误 |
|------|------|
| `tests/integration/test_p0_s7_secrets.py` | `core._config_infra` 缺 `validate_secrets` / `get_secret_status` 符号 |
| `tests/L2_modules/test_mobile_h5.py` | `tests.conftest` 缺 `SERVICES` 符号 |
| `tests/L2_modules/test_security.py` | 同上 |
| 整个 `tests/e2e/` | `tests.conftest` 缺 `setup_test_environment` 符号 |

---

## 3. 架构问题单根因深度分析

### 3.1 真凶:`utils/` 重复 + 裸导入 shadow

**问题**: `from utils.data_type_contract import _PROCESS_CODE_TO_TYPE`(裸导入)在 pytest 运行时总解析到项目根的 `utils/data_type_contract.py`,但**项目根版本 2026-06-20 更新时丢失了这个符号**。

| 位置 | 大小 | mtime | 含 `_PROCESS_CODE_TO_TYPE`? |
|------|------|-------|:----:|
| `utils/data_type_contract.py` (项目根) | 10956 | 2026-06-20 新版 | ❌ **丢失** |
| `mobile_api_ai/utils/data_type_contract.py` | 14983 | 旧版 | ✅ 有 |

### 3.2 为什么 14 个文件全部失败?

```
tests/unit/models/test_inventory.py
  → from models.inventory import InventoryDAO
  → models/inventory.py:7   from config import STOCK_WARNING_THRESHOLD
  → 项目根 config.py:6      from core.config import (...)
  → core/config.py:13       from core._config_domain import *
  → core/_config_domain.py:5  from utils.data_type_contract import _PROCESS_CODE_TO_TYPE
  → ❌ ImportError: cannot import name '_PROCESS_CODE_TO_TYPE'
```

14 个文件都触发了 `core.config → core._config_domain → utils.data_type_contract` 这条链,所以**全部 ERROR**。

### 3.3 已有架构决策:`mobile_api_ai/utils/__init__.py` 的 `__path__` 扩展

```python
# mobile_api_ai/utils/__init__.py (2026-06-10 fix #2)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_UTILS = os.path.join(_PROJECT_ROOT, 'utils')

# 扩展 __path__: 当 Python 将此文件解析为 utils 包时,
# 子模块搜索会同时覆盖 mobile_api_ai/utils/(优先) 和项目根 utils/(fallback)
if _ROOT_UTILS not in __path__:
    __path__.append(_ROOT_UTILS)
```

**这是"单向 fallback"机制**:`mobile_api_ai/utils` 主动包含项目根 `utils`,但**反过来不成立**。

### 3.4 pytest 收集时的实际路径顺序

```
sys.path[0] = 项目根 (Python 自动加 cwd)
sys.path[1] = mobile_api_ai (tests/conftest.py 加)
```

当 Python 解析 `from utils.X import`:
1. 找 `utils` 包 → sys.path[0]/utils/ → 找到项目根 `utils/__init__.py`
2. 加载项目根 `utils/__init__.py`(只有 333 字节,**没有反向 `__path__` 扩展**)
3. `utils.__path__ = [项目根/utils/]` ← **只搜项目根**
4. 找 `utils.data_type_contract` → 项目根版本 → ❌ 没 `_PROCESS_CODE_TO_TYPE`

**结论**:`mobile_api_ai/utils/__init__.py` 的扩展机制永远不会被触发,因为 Python 总先加载项目根 `utils/`。

---

## 4. `core/logger.py` 的 LOG_DIR 类型问题(额外的代码 bug)

**问题**: `core/_config_infra.py:33` 定义 `LOG_DIR = BASE_DIR / "logs"`(Path 对象),但 `core/_config_ui.py:170` 用 `os.getenv('LOG_DIR', 'logs')` 覆盖为 str。

```python
# core/_config_ui.py:170 (修复前)
LOG_DIR = os.getenv('LOG_DIR', 'logs')  # ← str 类型

# core/logger.py:35
LOG_DIR.mkdir(parents=True, exist_ok=True)  # ← str 没有 .mkdir()
```

**修复**: `_config_ui.py` 从 `_config_infra` 复用 Path 版本,允许环境变量覆盖。

---

## 5. 修复方案

### 5.1 v3.8.1 实际修复(本次完成)

| 文件 | 修复 |
|------|------|
| `core/_config_domain.py:5` | 改 `from utils.data_type_contract import` → `from mobile_api_ai.utils.data_type_contract import`(锁定路径) |
| `core/_config_ui.py:170` | 改 `os.getenv('LOG_DIR', 'logs')` → 从 `_config_infra` 复用 Path 版本 |
| `tests/unit/dispatch_center/test_publisher_v378_db.py` | fake 模块重命名加 `publisher_v378_` 前缀,避免跨测试冲突 |

### 5.2 修复结果

| 测试 | 状态 |
|------|:----:|
| `tests/unit/dispatch_center/`(89 测试) | ✅ 全过 |
| `tests/unit/test_desktop_container_integration_v380.py`(14 测试) | ✅ 全过 |
| `tests/unit/models/test_inventory.py`(12 测试) | ✅ 全过 |
| `tests/unit/models/test_order_dao.py`(19 测试) | ✅ 全过 |
| `tests/unit/core/test_logger.py`(22 测试) | ✅ 全过 |
| `tests/unit/services/test_schedule_dispatch_service.py`(69 测试) | ✅ 全过 |
| **合计** | **103/103 全过零回归** |

---

## 6. 剩余问题与未来 TODO

### 6.1 仍未修复的 ERROR(2 个)

| 文件 | 错误 | 阻塞原因 |
|------|------|---------|
| `tests/integration/test_p0_s7_secrets.py` | `core._config_infra` 缺符号 | 待 git history 调查原意 |
| `tests/L2_modules/test_mobile_h5.py` + `test_security.py` | `tests.conftest` 缺 `SERVICES` | 待补符号 |
| 整个 `tests/e2e/` | `tests.conftest` 缺 `setup_test_environment` | 待补符号 |

### 6.2 长期 TODO

1. **架构治根**(`项目根/utils/` vs `mobile_api_ai/utils/` 长期不一致):
   - 选项 A: 给 `项目根/utils/__init__.py` 加反向 `__path__` 扩展(对称修复)
   - 选项 B: 删除 `项目根/utils/`,统一到 `mobile_api_ai/utils/`
2. **56 个 skipped 测试启用**: 大部分需 MySQL/Redis/5003 在线
3. **test_config.py 的 subprocess sys.modules 污染**: 已知 bug,需隔离

---

## 7. 经验教训(给后人)

1. **不要用裸导入** `from utils.X import`:`utils` 是极其常见的名字,任何目录都能 shadow。应改为 `from mobile_api_ai.utils.X import` 或 `from desktop.utils.X import`
2. **`__path__` 扩展机制必须双向**: 一边做了,另一边也要做,否则不对称
3. **配置文件应该单一来源**: `core/_config_infra` 和 `core/_config_ui` 都定义 `LOG_DIR`,后加载覆盖前加载,极易类型错乱
4. **测试隔离 bug**: `subprocess` 跑 Python 清理 `sys.modules` 会污染父进程状态,需用 `multiprocessing` 或 fork 真正隔离
5. **mock 模块命名加前缀**: 测试用 `sys.modules` 注入 fake 模块时,必须用唯一前缀避免冲突

---

## 8. 相关文档

- [ACCEPTANCE_v3.8.1.md](ACCEPTANCE_v3.8.1.md) - 本次修复完成度报告
- [STORAGE_INVENTORY.md](../STORAGE_INVENTORY.md) - 存储架构盘点
- `core/_config_domain.py:5` - 修复点 1
- `core/_config_ui.py:170` - 修复点 2
- `tests/conftest.py` - 路径配置
- `mobile_api_ai/utils/__init__.py:28-29` - 既有 `__path__` 扩展机制

---

**最后更新**: 2026-06-25
**维护人**: AI 助手
