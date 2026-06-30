# -*- coding: utf-8 -*-
"""
创建桌面快捷方式
"""

import os
import sys
import win32com.client
import pythoncom


def create_desktop_shortcut():
    """创建桌面快捷方式"""
    try:
        # 初始化COM
        pythoncom.CoInitialize()
        
        # 创建Shell对象
        shell = win32com.client.Dispatch("WScript.Shell")
        
        # 获取桌面路径
        desktop_path = shell.SpecialFolders("Desktop")
        shortcut_path = os.path.join(desktop_path, "钢带订单追踪系统.lnk")
        
        # 创建快捷方式
        shortcut = shell.CreateShortcut(shortcut_path)
        
        # 设置快捷方式属性
        shortcut.TargetPath = "python.exe"
        shortcut.Arguments = r"D:\yuan\不锈钢网带跟单3.0\main.py"
        shortcut.WorkingDirectory = r"D:\yuan\不锈钢网带跟单3.0"
        shortcut.IconLocation = "python.exe,0"
        shortcut.Description = "钢带订单追踪系统 v3.1"
        
        # 保存快捷方式
        shortcut.Save()
        
        print(f"✅ 快捷方式已创建: {shortcut_path}")
        return True
        
    except Exception as e:
        print(f"❌ 创建快捷方式失败: {str(e)}")
        return False
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    create_desktop_shortcut()