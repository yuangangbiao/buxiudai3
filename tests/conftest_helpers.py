# -*- coding: utf-8 -*-
"""
[v3.8.1] conftest 共享辅助模块

目的:
- 统一所有 conftest.py 的 sys.path / sys.modules / os.environ 清理模式
- 防止测试间相互污染
- 任何新增 conftest.py 应基于本模块实现

使用方式:
    # conftest.py
    from tests.conftest_helpers import (
        ensure_sys_path,
        pytest_pycollect_makemodule,
        pytest_collection_modifyitems,
        setup_test_environment,
        isolate_test_environment,
    )

设计原则:
1. sys.path 注入必须配对清理
2. sys.modules 中包含 'tests' 路径的模块必须清理
3. os.environ 修改必须保存原值 + yield 后还原
4. 大小写不敏感路径比对（Windows 兼容）
"""
import os
import sys
from typing import Iterable, List, Optional

# [v3.8.1] 已知会产生测试污染的模块名（应该从 sys.modules 清除）
_KNOWN_POLLUTING_MODULES = frozenset({
    'core', 'models', 'services', 'utils',
    'core.config', 'core.db', 'core.app',
    'models.database', 'models.order', 'models.base_dao',
    'constants',
})


def _norm_path(p: str) -> str:
    """标准化路径（Windows 大小写不敏感）"""
    return os.path.normcase(os.path.abspath(p)) if p else p


def ensure_sys_path(*paths: str, position: int = 0) -> List[str]:
    """注入路径到 sys.path（已存在则跳过），返回新增的路径列表

    Args:
        *paths: 要注入的路径
        position: 插入位置（0=最前, -1=最后）

    Usage:
        added = ensure_sys_path(_PROJECT_ROOT, _MOBILE_API_AI)
    """
    existing = {_norm_path(p) for p in sys.path if p}
    added = []
    for p in paths:
        if _norm_path(p) not in existing:
            sys.path.insert(position, p)
            existing.add(_norm_path(p))
            added.append(p)
    return added


def remove_sys_path(*paths: str) -> List[str]:
    """从 sys.path 移除指定路径，返回被移除的路径列表"""
    removed = []
    for p in paths:
        norm = _norm_path(p)
        while norm in {_norm_path(x) for x in sys.path}:
            for i, x in enumerate(sys.path):
                if _norm_path(x) == norm:
                    sys.path.pop(i)
                    removed.append(x)
                    break
    return removed


def clean_polluting_modules(modules: Optional[Iterable[str]] = None, clear_parents: bool = True) -> List[str]:
    """从 sys.modules 中清除包含 'tests' 路径或可疑污染的模块

    Args:
        modules: 要检查的模块名集合（默认 _KNOWN_POLLUTING_MODULES）
        clear_parents: 是否清理 core/models/services/utils 父包（默认 True）
                       ⚠️ 设为 False 可避免清理后重新 import 导致类对象不一致
                       场景：pytest_collection_modifyitems 应该传 False，
                       pytest_pycollect_makemodule 可以传 True

    Returns:
        被清除的模块名列表
    """
    if modules is None:
        modules = _KNOWN_POLLUTING_MODULES
    else:
        modules = frozenset(modules) | _KNOWN_POLLUTING_MODULES

    cleared = []
    for name in list(sys.modules.keys()):
        mod = sys.modules.get(name)
        if mod is None:
            continue

        # 检查 1：模块路径包含 'tests'
        try:
            mod_path = getattr(mod, '__file__', None) or ''
            if 'tests' in mod_path.replace('\\', '/').split('/'):
                del sys.modules[name]
                cleared.append(name)
                continue
        except (AttributeError, TypeError):
            pass

        # 检查 2：在已知污染模块列表中，且路径可疑
        if name in modules:
            try:
                mod_path = getattr(mod, '__path__', None)
                mod_file = getattr(mod, '__file__', None)
                if mod_path is None and mod_file is None:
                    # namespace package 无路径 → 清理
                    del sys.modules[name]
                    cleared.append(name)
                    continue
                # [v3.8.2 新增] 如果是父包(core/models/services/utils)且非 namespace package，
                # 也要清理！背景：test_operator.py 单文件 PASS，全量 FAILED
                # 根因：models.operator 被 patch 后，如果 models 父包没被清理，
                # 下个测试文件导入 models.operator 时会从 sys.modules 复用缓存的版本，
                # 导致 patch 失效（get_connection 绑定到旧的真实函数）
                # [v3.8.3 修改] 受 clear_parents 参数控制
                if clear_parents and name in {'core', 'models', 'services', 'utils'} and mod_file:
                    del sys.modules[name]
                    cleared.append(name)
                    continue
                if mod_path:
                    paths = list(mod_path) if hasattr(mod_path, '__iter__') else [mod_path]
                    if any('tests' in str(p).replace('\\', '/').split('/') for p in paths):
                        del sys.modules[name]
                        cleared.append(name)
            except (AttributeError, TypeError):
                pass

        # [v3.8.2 新增] 检查 2b：清理已知污染模块的子模块（防御性）
        # 背景：models.database, models.operator, models.order 等子模块在测试中被导入
        # 如果它们的 __file__ 来自 tests/ 目录，也要清理
        _PARENT_PACKAGES_LOCAL = {'core', 'models', 'services', 'utils'}
        for parent in _PARENT_PACKAGES_LOCAL:
            if name.startswith(parent + '.'):
                try:
                    mod_file = getattr(mod, '__file__', None)
                    if mod_file and 'tests' in mod_file.replace('\\', '/').split('/'):
                        del sys.modules[name]
                        cleared.append(name)
                except (AttributeError, TypeError):
                    pass

    # 检查 3：级联清理 mobile_api_ai.* namespace package（防御性）
    # 背景：test_process_code_classifier.py 第 12 行 sys.path.insert(0, mobile_api_ai/)
    # 会导致 mobile_api_ai 被加载为 namespace package，污染 sys.modules
    # 当它被加载时，会通过相对 import 触发 mobile_api_ai.services.__init__.py
    # 进而污染 sys.modules['services']，导致后续 services.schedule_dispatch_service 失败
    for name in list(sys.modules.keys()):
        if name == 'mobile_api_ai' or name.startswith('mobile_api_ai.'):
            try:
                del sys.modules[name]
                cleared.append(name)
            except KeyError:
                pass

    # [v3.8.3 关键修复] 清理父包前先清理其所有子模块
    # 背景: `from .exceptions import X` 在子模块已加载时不会重新设置 `core.exceptions` 属性
    # 导致清理 core 父包后，重新 import core 时 core.exceptions 属性不存在
    # 解决: 不管父包是否还在 sys.modules 中，都先清理所有以 parent. 开头的子模块
    if clear_parents:
        _PARENT_PACKAGES_FIXED = {'core', 'models', 'services', 'utils'}
        for parent in _PARENT_PACKAGES_FIXED:
            # 找出所有以 parent. 开头的子模块（包括深层）
            children_to_clear = [
                name for name in list(sys.modules.keys())
                if name.startswith(parent + '.')
            ]
            # 先删除子模块（按字母倒序，先删深层）
            for child in sorted(children_to_clear, reverse=True):
                try:
                    del sys.modules[child]
                    cleared.append(child)
                except KeyError:
                    pass

    return cleared


# ============== pytest hooks (供 conftest.py 直接 re-export) ==============

def pytest_pycollect_makemodule(module_path, parent):
    """每个测试模块收集前清理 sys.path 和 sys.modules 缓存

    [v3.8.5] 移除废弃的 path: py.path.local 参数（pytest 9.0+ 会将警告升为错误）

    在 conftest.py 中:
        from tests.conftest_helpers import pytest_pycollect_makemodule
    """
    clean_polluting_modules()


def pytest_collection_modifyitems(session, config, items):
    """collection 完成后再次清理 sys.modules，防止跨目录污染

    [v3.8.3 修复] clear_parents=False 避免清理父包
    原因: collection 完成后清理父包会导致：
    1. test 模块顶部 `from core.exceptions import X` 绑定的类对象 CLASS_A 被清理
    2. 测试函数内 `from services.X import Y` 触发 services.X 加载
    3. services.X 内 `from core.exceptions import Z` → 重新加载 → CLASS_B
    4. test 模块和 sos 模块中的 ValidationException 是不同对象
    5. pytest.raises(ValidationException) 匹配失败

    在 conftest.py 中:
        from tests.conftest_helpers import pytest_collection_modifyitems
    """
    clean_polluting_modules(clear_parents=False)


# ============== 通用 fixture 模板 ==============

def setup_test_environment(test_keys: Optional[Iterable[str]] = None):
    """测试环境变量 fixture 工厂

    Usage:
        @pytest.fixture(scope='session')
        def setup_test_environment():
            from tests.conftest_helpers import setup_test_environment
            yield from setup_test_environment(['TESTING', 'DISPATCH_CENTER_USE_DB'])

    Args:
        test_keys: 本次 fixture 设置的环境变量 key 列表

    Yields:
        None (fixture 协议)
    """
    if test_keys is None:
        test_keys = ('TESTING',)

    _orig = {k: os.environ.get(k) for k in test_keys}
    for k in test_keys:
        os.environ.setdefault(k, '1')
    try:
        yield
    finally:
        for k, v in _orig.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def isolate_test_environment(env_overrides: Optional[dict] = None, autouse: bool = False):
    """autouse 环境隔离 fixture 工厂

    Usage:
        @pytest.fixture(autouse=True)
        def _isolate():
            from tests.conftest_helpers import isolate_test_environment
            yield from isolate_test_environment({'UNIT_TEST_MODE': 'true'})

    Args:
        env_overrides: dict[env_key, env_value]，设置为强制值（非 setdefault）
        autouse: 是否 autouse（占位参数，实际在装饰器侧指定）
    """
    overrides = env_overrides or {}
    _orig = {k: os.environ.get(k) for k in overrides}
    for k, v in overrides.items():
        os.environ[k] = v
    try:
        yield
    finally:
        for k, v in _orig.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v