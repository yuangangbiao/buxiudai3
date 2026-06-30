# -*- coding: utf-8 -*-
"""
JSON文件存储工具
"""

import os
import json
from typing import Any, Optional


class JsonStore:
    """JSON文件存储封装"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保目录存在"""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    def load(self, default: Any = None) -> Any:
        """加载数据"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default
        return default
    
    def save(self, data: Any) -> bool:
        """保存数据"""
        try:
            self._ensure_dir()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, TypeError) as e:
            print(f"保存失败: {e}")
            return False
    
    def update(self, updates: dict, merge: bool = True) -> bool:
        """更新数据"""
        if merge:
            data = self.load({})
            if isinstance(data, dict):
                data.update(updates)
            else:
                data = updates
        else:
            data = updates
        return self.save(data)
    
    def clear(self) -> bool:
        """清空数据"""
        return self.save(None)
