# -*- coding: utf-8 -*-
"""
[v3.8.2] storage_layer.py 单元测试

storage_layer.py 是 v3.7.8 双轨 + F6 P7 物理清理的架构核心,
[历史] 之前 0 个测试保护,本测试补齐关键 API。

覆盖:
- StorageType 枚举 (3 个值: MYSQL/REDIS/MEMORY, SQLite 已物理移除)
- resolve_storage_type() 默认行为
- resolve_storage_type() 显式 CONTAINER_STORAGE_TYPE=mysql → MYSQL
- resolve_storage_type() 显式 CONTAINER_STORAGE_TYPE=sqlite → ValueError (F6 P7)
- create_storage() 默认创建 MySQL storage
- MemoryStorage 基本 CRUD
- BaseStorage 抽象类不能直接实例化
- StorageFactory 根据 config dict 创建对应后端

策略:
- 直接 importlib 加载 storage_layer.py (绕开 __init__.py 副作用)
- conftest.py 不存在时, sys.path 注入项目根
- 清理 CONTAINER_STORAGE_TYPE 环境变量确保测试隔离
"""
import os
import sys
import types
import importlib.util
from unittest.mock import MagicMock, patch

import pytest


# 真实 storage_layer.py 触发 core.config → core._config_domain → utils.data_type_contract
# (chain 已被 v3.8.1 锁定到 mobile_api_ai.utils.data_type_contract)
# 用 sys.modules 注入 fake core.config 简化测试隔离
# [v3.8.2 关键修复] 不要在模块顶部注入 sys.modules!
# 之前在顶部注入 fake core.config/db_compat 会污染其他测试文件
# (publisher_v378 测试用 fake core, 但 storage_layer 测试 setUp 时 core.config
#  已经被 storage_layer 的 fake 占据, 导致 publisher 后续行为异常)
# 改为: 在 fixture 内部做 fake 注入 + teardown 还原
#
# 必须做的事: 把 mobile_api_ai 加到 sys.path 让 storage_layer.py:1881
# `from storage.mysql_storage import` 能找到 mobile_api_ai/storage/
import os as _os
_PROJECT_ROOT_V382 = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_MOBILE_API_AI_V382 = _os.path.join(_PROJECT_ROOT_V382, 'mobile_api_ai')
if _MOBILE_API_AI_V382 not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI_V382)


def _load_storage_layer():
    """加载 mobile_api_ai/storage_layer.py"""
    if 'storage_layer_v382' in sys.modules:
        return sys.modules['storage_layer_v382']
    # tests/unit/test_xxx.py → tests/unit/ → tests/ → 项目根
    tests_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(tests_dir, 'mobile_api_ai', 'storage_layer.py')
    spec = importlib.util.spec_from_file_location("storage_layer_v382", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sl():
    """加载 storage_layer 模块, fixture 内 fake core 注入 + teardown 还原"""
    backup = os.environ.pop('CONTAINER_STORAGE_TYPE', None)

    # 记录 core.* 子模块加载前状态 (用于 teardown 还原)
    _core_modules_before = {
        k for k in sys.modules
        if k == 'core' or k.startswith('core.')
    }

    # 在 fixture 内注入 fake core.config / core.db_compat
    # (避免模块顶部注入污染其他测试文件)
    _fake_config = types.ModuleType('storage_layer_test_fake_config_v382')
    _fake_config.CONTAINER_MYSQL_CFG = {
        'host': 'localhost', 'port': 3306, 'user': 'test',
        'password': '', 'database': 'test_db', 'charset': 'utf8mb4'
    }
    _fake_config.DB_PATHS = {
        'container_center': '/tmp/test_container_center.db',
        'steel_belt': '/tmp/test_steel_belt.db',
    }
    sys.modules['core.config'] = _fake_config

    _fake_db_compat = types.ModuleType('storage_layer_test_fake_db_compat_v382')
    _fake_db_compat.get_conn = MagicMock()
    sys.modules['core.db_compat'] = _fake_db_compat

    try:
        sl_mod = _load_storage_layer()
        yield sl_mod
    finally:
        # teardown: 只删除 storage_layer 加载触发的真实 core 子模块,
        # 保留我自己注入的 fake core.config / core.db_compat (其他测试 fixture 会覆盖)
        _triggered = {
            k for k in sys.modules
            if (k == 'core' or k.startswith('core.'))
            and k not in _core_modules_before
            and k not in ('core.config', 'core.db_compat')
        }
        for k in _triggered:
            sys.modules.pop(k, None)
        # 还原环境变量
        if backup is not None:
            os.environ['CONTAINER_STORAGE_TYPE'] = backup


# ============ StorageType 枚举 ============

class TestStorageTypeEnum:
    """StorageType 枚举值验证"""

    def test_storage_type_has_mysql(self, sl):
        assert hasattr(sl.StorageType, 'MYSQL')

    def test_storage_type_has_redis(self, sl):
        assert hasattr(sl.StorageType, 'REDIS')

    def test_storage_type_has_memory(self, sl):
        assert hasattr(sl.StorageType, 'MEMORY')

    def test_storage_type_sqlite_legacy_exists(self, sl):
        """[F6 P7] StorageType.SQLITE 枚举值仍存在 (向后兼容),
        但 create_storage({'type': 'sqlite'}) 会抛 ValueError (见 test_create_storage_sqlite_type_raises)
        这是 F6 P7 的设计:枚举保留作为'已知类型', 但物理实现已移除
        """
        # 枚举值存在, 但 factory 已无法创建实例
        assert hasattr(sl.StorageType, 'SQLITE')
        assert sl.StorageType.SQLITE.value == 'sqlite'


# ============ resolve_storage_type() ============

class TestResolveStorageType:
    """[F6 P7] resolve_storage_type 默认返回 MYSQL"""

    def test_default_returns_mysql(self, sl):
        """未设置 CONTAINER_STORAGE_TYPE 时返回 MYSQL"""
        os.environ.pop('CONTAINER_STORAGE_TYPE', None)
        result = sl.resolve_storage_type()
        assert result == sl.StorageType.MYSQL

    def test_explicit_mysql_returns_mysql(self, sl):
        """CONTAINER_STORAGE_TYPE=mysql 返回 MYSQL"""
        os.environ['CONTAINER_STORAGE_TYPE'] = 'mysql'
        try:
            assert sl.resolve_storage_type() == sl.StorageType.MYSQL
        finally:
            os.environ.pop('CONTAINER_STORAGE_TYPE', None)

    def test_explicit_sqlite_raises(self, sl):
        """[F6 P7] CONTAINER_STORAGE_TYPE=sqlite 应抛 ValueError"""
        os.environ['CONTAINER_STORAGE_TYPE'] = 'sqlite'
        try:
            with pytest.raises(ValueError) as exc_info:
                sl.resolve_storage_type()
            assert 'SQLiteStorage 已物理移除' in str(exc_info.value)
        finally:
            os.environ.pop('CONTAINER_STORAGE_TYPE', None)

    def test_explicit_sqlite_uppercase_raises(self, sl):
        """大写 SQLITE 也抛 ValueError"""
        os.environ['CONTAINER_STORAGE_TYPE'] = 'SQLITE'
        try:
            with pytest.raises(ValueError):
                sl.resolve_storage_type()
        finally:
            os.environ.pop('CONTAINER_STORAGE_TYPE', None)


# ============ MemoryStorage 基本 CRUD ============

class TestMemoryStorage:
    """MemoryStorage 是 BaseStorage 的内存实现, 可独立测试"""

    def test_memory_storage_basic_crud(self, sl):
        """MemoryStorage 增删改查"""
        storage = sl.MemoryStorage()
        # save
        storage.save_labor_unit_price('拉丝', 5.5, '米')
        storage.save_labor_unit_price('焊接', 8.0, '件')
        # get
        prices = storage.get_all_labor_prices()
        assert len(prices) == 2
        assert any(p['process_name'] == '拉丝' and p['unit_price'] == 5.5 for p in prices)
        assert any(p['process_name'] == '焊接' and p['unit_price'] == 8.0 for p in prices)

    def test_memory_storage_update_same_process(self, sl):
        """同名工序后保存覆盖"""
        storage = sl.MemoryStorage()
        storage.save_labor_unit_price('拉丝', 5.5, '米')
        storage.save_labor_unit_price('拉丝', 6.0, '米')  # 覆盖
        prices = storage.get_all_labor_prices()
        assert len(prices) == 1
        assert prices[0]['unit_price'] == 6.0


# ============ BaseStorage 抽象类 ============

class TestBaseStorageAbstract:
    """BaseStorage 是抽象类, 不能直接实例化"""

    def test_base_storage_cannot_instantiate(self, sl):
        """BaseStorage 有抽象方法, 直接实例化抛 TypeError"""
        with pytest.raises(TypeError):
            sl.BaseStorage()


# ============ create_storage() 工厂 ============

class TestCreateStorage:
    """create_storage() 工厂函数"""

    def test_create_storage_default_is_mysql(self, sl):
        """create_storage() 不传 config 应调用 StorageFactory.create(MYSQL)
        (无需真正创建 MySQL 连接, 通过 mock StorageFactory 验证)
        """
        os.environ.pop('CONTAINER_STORAGE_TYPE', None)
        # mock StorageFactory.create 避免真连 MySQL
        mock_storage = MagicMock(name='mock_mysql_storage')
        with patch.object(sl.StorageFactory, 'create', return_value=mock_storage) as mock_create:
            storage = sl.create_storage()
            assert storage is mock_storage
            # 验证调用时传 StorageType.MYSQL
            args = mock_create.call_args[0]
            assert args[0] == sl.StorageType.MYSQL

    def test_create_storage_with_memory_type(self, sl):
        """config={'type': 'memory'} 创建 MemoryStorage"""
        os.environ.pop('CONTAINER_STORAGE_TYPE', None)
        storage = sl.create_storage({'type': 'memory'})
        assert isinstance(storage, sl.MemoryStorage)

    def test_create_storage_sqlite_type_raises(self, sl):
        """config={'type': 'sqlite'} 应抛 ValueError (F6 P7 物理清理)"""
        os.environ.pop('CONTAINER_STORAGE_TYPE', None)
        with pytest.raises((ValueError, RuntimeError)) as exc_info:
            sl.create_storage({'type': 'sqlite'})
        assert 'SQLiteStorage' in str(exc_info.value) or '物理移除' in str(exc_info.value)


# ============ 集成 ============

class TestStorageLayerIntegration:
    """resolve + create 集成"""

    def test_resolved_type_matches_factory(self, sl):
        """resolve_storage_type() 返回值能被 factory 使用"""
        os.environ.pop('CONTAINER_STORAGE_TYPE', None)
        resolved = sl.resolve_storage_type()
        # 验证返回值与 StorageType.MYSQL 一致
        assert resolved is sl.StorageType.MYSQL

        # 验证 factory 能识别该 type
        # 但直接 create_storage 默认走 MySQL, 会试图连 DB
        # 所以只验证枚举对应关系
        assert resolved.value == sl.StorageType.MYSQL.value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])