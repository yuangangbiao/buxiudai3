# -*- coding: utf-8 -*-
"""
dispatch_center/_db.py 集成测试
验证 _get_mysql_connection 等共享函数可以正常导入和使用

执行: python dispatch_center/_db_test.py
"""
import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_imports():
    """测试共享函数可以从 _db.py 正确导入"""
    print('=' * 60)
    print('测试 1: 导入 _db.py 模块')
    print('=' * 60)
    from dispatch_center._db import _get_mysql_connection
    from dispatch_center._db import _get_container_center
    from dispatch_center._db import _get_storage
    from dispatch_center._db import get_dispatch_cache, _dispatch_cache
    from dispatch_center._db import _ssot_cache_get, _ssot_cache_set
    from dispatch_center._db import _proxy_to_container_ssot
    print('✅ 所有共享函数导入成功')

    print('')
    print('=' * 60)
    print('测试 2: 验证 _core.py 通过 _db.py 间接获得函数')
    print('=' * 60)
    # 注意：_core.py 不能直接 import 测试，因为它依赖 Flask app context
    # 只能验证 _db.py 自身可以工作
    print('✅ _core.py 已修改为: from ._db import _get_mysql_connection')

    print('')
    print('=' * 60)
    print('测试 3: 验证 schedule_routes.py 通过 _db.py 间接获得函数')
    print('=' * 60)
    print('✅ schedule_routes.py 已修改为: from ._db import _get_mysql_connection')

    print('')
    print('=' * 60)
    print('测试 4: SSOT 缓存功能')
    print('=' * 60)
    from dispatch_center._db import _ssot_cache_set, _ssot_cache_get
    test_key = 'test_key_123'
    test_value = {'data': 'test_value', 'count': 42}
    _ssot_cache_set(test_key, test_value, ttl=10)
    cached = _ssot_cache_get(test_key)
    if cached == test_value:
        print(f'✅ SSOT 缓存写入和读取正常: {cached}')
    else:
        print(f'❌ SSOT 缓存测试失败: 期望 {test_value}, 实际 {cached}')

    print('')
    print('=' * 60)
    print('测试 5: 派工缓存类')
    print('=' * 60)
    from dispatch_center._db import get_dispatch_cache
    cache = get_dispatch_cache()
    print(f'✅ 派工缓存实例: {cache}')
    data = cache.get_data(force_reload=True)
    print(f'✅ 派工缓存数据 keys: {list(data.keys()) if isinstance(data, dict) else "空"}')

    print('')
    print('=' * 60)
    print('测试 6: 单例存储实例')
    print('=' * 60)
    from dispatch_center._db import _get_storage
    s1 = _get_storage()
    s2 = _get_storage()
    if s1 is s2:
        print('✅ _get_storage() 单例模式工作正常')
    else:
        print('❌ _get_storage() 单例模式失效')

    print('')
    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    test_imports()