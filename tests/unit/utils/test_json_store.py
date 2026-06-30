# -*- coding: utf-8 -*-
"""
utils/storage/json_store.py 完整单元测试

覆盖模块:
- JsonStore
- load/save/update/clear
"""
import os
import sys
import json
import pytest


class TestJsonStoreExists:
    """JsonStore 存在性测试"""

    def test_json_store_module_exists(self):
        """测试json_store模块存在"""
        from utils.storage import json_store
        assert json_store is not None

    def test_json_store_class_exists(self):
        """测试JsonStore类存在"""
        from utils.storage.json_store import JsonStore
        assert JsonStore is not None


class TestJsonStoreInit:
    """JsonStore 初始化测试"""

    def test_init(self, tmp_path):
        """测试初始化"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        assert store.file_path == file_path

    def test_init_creates_dir(self, tmp_path):
        """测试初始化创建目录"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "subdir" / "test.json")
        store = JsonStore(file_path)
        assert os.path.exists(os.path.dirname(file_path))


class TestJsonStoreLoad:
    """load 方法测试"""

    def test_load_empty(self, tmp_path):
        """测试加载空文件"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "empty.json")
        store = JsonStore(file_path)
        result = store.load()
        assert result is None

    def test_load_existing(self, tmp_path):
        """测试加载已存在文件"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "data.json")
        store = JsonStore(file_path)
        data = {'key': 'value', 'num': 42}
        store.save(data)
        result = store.load()
        assert result == data

    def test_load_invalid_json(self, tmp_path):
        """测试加载无效JSON"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "invalid.json")
        with open(file_path, 'w') as f:
            f.write("not valid json{")
        store = JsonStore(file_path)
        result = store.load(default={})
        assert result == {}


class TestJsonStoreSave:
    """save 方法测试"""

    def test_save_dict(self, tmp_path):
        """测试保存字典"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        data = {'key': 'value', 'list': [1, 2, 3]}
        result = store.save(data)
        assert result is True
        assert os.path.exists(file_path)

    def test_save_list(self, tmp_path):
        """测试保存列表"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        result = store.save([1, 2, 3, 4, 5])
        assert result is True

    def test_save_chinese(self, tmp_path):
        """测试保存中文"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        result = store.save({'姓名': '张三', '年龄': 30})
        assert result is True
        # 验证内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '张三' in content


class TestJsonStoreUpdate:
    """update 方法测试"""

    def test_update_merge(self, tmp_path):
        """测试合并更新"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        store.save({'a': 1, 'b': 2})
        result = store.update({'c': 3}, merge=True)
        assert result is True
        data = store.load()
        assert data == {'a': 1, 'b': 2, 'c': 3}

    def test_update_replace(self, tmp_path):
        """测试替换更新"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        store.save({'a': 1, 'b': 2})
        result = store.update({'c': 3}, merge=False)
        assert result is True
        data = store.load()
        assert data == {'c': 3}


class TestJsonStoreClear:
    """clear 方法测试"""

    def test_clear(self, tmp_path):
        """测试清空"""
        from utils.storage.json_store import JsonStore
        file_path = str(tmp_path / "test.json")
        store = JsonStore(file_path)
        store.save({'key': 'value'})
        result = store.clear()
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
