# -*- coding: utf-8 -*-
"""创建库存管理系统桌面快捷方式"""
import os
import sys
import subprocess

def create_inventory_shortcut():
    desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop_path, '库存管理系统完整版.lnk')

    try:
        from win32com.client import Dispatch
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = sys.executable
        shortcut.Arguments = r' "D:\yuan\不锈钢网带跟单3.0\inventory_manager_complete.py" '
        shortcut.WorkingDirectory = r'D:\yuan\不锈钢网带跟单3.0'
        shortcut.Description = '宁津晨圣库存管理系统 V3.0'
        shortcut.Save()
        print(f'快捷方式已创建成功: {shortcut_path}')
        return True
    except Exception as e:
        print(f'使用win32com方式创建失败: {e}')
        return create_powershell_shortcut(desktop_path, shortcut_path)

def create_powershell_shortcut(desktop_path, shortcut_path):
    try:
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "python.exe"
$Shortcut.Arguments = '"D:\\yuan\\不锈钢网带跟单3.0\\inventory_manager_complete.py"'
$Shortcut.WorkingDirectory = "D:\\yuan\\不锈钢网带跟单3.0"
$Shortcut.Description = "宁津晨圣库存管理系统 V3.0"
$Shortcut.Save()
'''
        result = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True)
        if result.returncode == 0:
            print(f'快捷方式已创建成功(PowerShell方式): {shortcut_path}')
            return True
        else:
            print(f'PowerShell创建失败: {result.stderr}')
            return False
    except Exception as e:
        print(f'PowerShell方式也失败: {e}')
        return False

if __name__ == '__main__':
    create_inventory_shortcut()
