# -*- coding: utf-8 -*-
"""
窗口大小管理器
保存和恢复窗口大小配置
"""
import json
import os
from core.config import DB_PATHS


def get_window_config_path():
    """获取窗口配置文件路径"""
    return DB_PATHS['window_config']


def load_window_size(window_key: str, default_size: str = "800x600") -> str:
    """加载窗口大小配置"""
    config_path = get_window_config_path()
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(window_key, default_size)
    except Exception:
        pass
    return default_size


def save_window_size(window_key: str, size: str):
    """保存窗口大小配置"""
    config_path = get_window_config_path()
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        config[window_key] = size
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save window size: {e}")


def setup_resizable_window(window, window_key: str, default_size: str = "800x600"):
    """设置窗口为可调整大小，恢复上次保存的尺寸，首次打开时居中"""
    window.resizable(True, True)

    saved_size = load_window_size(window_key, default_size) or default_size

    # 首次打开时居中窗口（saved_size 不含位置信息）
    if "+" not in saved_size:
        window.update_idletasks()
        try:
            w_str, h_str = saved_size.split("x")
            w, h = int(w_str), int(h_str)
        except (ValueError, AttributeError):
            w, h = 800, 600
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        window.geometry(f"{w}x{h}+{x}+{y}")
    else:
        window.geometry(saved_size)

    def on_resize(event):
        if event.widget == window:
            geom = window.geometry()
            if geom:
                save_window_size(window_key, geom)

    window.bind("<Configure>", on_resize)

    return window