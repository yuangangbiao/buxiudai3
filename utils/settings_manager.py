# -*- coding: utf-8 -*-
"""
设置管理模块 - 管理字体颜色等用户自定义设置
"""
import os
import json

# 设置文件路径
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'settings.json')

# 默认颜色设置
DEFAULT_COLORS = {
    # 主色调
    "primary": "#1E3A5F",
    "primary_light": "#2E5A8F",
    "accent": "#4A90D9",
    
    # 背景色
    "bg_main": "#F0F2F5",
    "bg_card": "#FFFFFF",
    "bg_sidebar": "#1E3A5F",
    
    # 文字颜色
    "text_primary": "#1A1A2E",
    "text_secondary": "#666666",
    "text_white": "#FFFFFF",
    
    # 状态颜色
    "success": "#4CAF50",
    "warning": "#FF9800",
    "danger": "#F44336",
    "info": "#2196F3",
    
    # 表格颜色
    "table_header": "#F5F5F5",
    "table_row_odd": "#FFFFFF",
    "table_row_even": "#F9F9F9",
}

# 默认字体设置
DEFAULT_FONTS = {
    "family": "微软雅黑",
    "size": {
        "title": 14,
        "subtitle": 12,
        "body": 10,
        "small": 9,
        "large": 18,
    }
}

class SettingsManager:
    """设置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_settings()
        return cls._instance
    
    def _load_settings(self):
        """加载设置文件"""
        self.settings = {
            "colors": DEFAULT_COLORS.copy(),
            "fonts": DEFAULT_FONTS.copy()
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.settings["colors"].update(saved.get("colors", {}))
                    self.settings["fonts"].update(saved.get("fonts", {}))
            except Exception:
                pass
    
    def save_settings(self):
        """保存设置到文件"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Settings] 保存设置失败: {e}")
            return False
    
    def get_color(self, key):
        """获取颜色值"""
        return self.settings["colors"].get(key, DEFAULT_COLORS.get(key, "#000000"))
    
    def set_color(self, key, value):
        """设置颜色值"""
        if key in DEFAULT_COLORS:
            self.settings["colors"][key] = value
            return True
        return False
    
    def get_font_size(self, size_type):
        """获取字体大小"""
        return self.settings["fonts"]["size"].get(size_type, 10)
    
    def set_font_size(self, size_type, value):
        """设置字体大小"""
        if size_type in self.settings["fonts"]["size"]:
            self.settings["fonts"]["size"][size_type] = value
            return True
        return False
    
    def get_font_family(self):
        """获取字体名称"""
        return self.settings["fonts"]["family"]
    
    def set_font_family(self, family):
        """设置字体名称"""
        self.settings["fonts"]["family"] = family
        return True
    
    def reset_to_default(self):
        """重置为默认设置"""
        self.settings["colors"] = DEFAULT_COLORS.copy()
        self.settings["fonts"] = DEFAULT_FONTS.copy()
        return self.save_settings()
    
    def get_all_colors(self):
        """获取所有颜色设置"""
        return self.settings["colors"].copy()
    
    def get_all_fonts(self):
        """获取所有字体设置"""
        return self.settings["fonts"].copy()

# 全局设置管理器实例
settings_manager = SettingsManager()