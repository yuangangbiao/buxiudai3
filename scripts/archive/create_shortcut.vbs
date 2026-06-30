Set WshShell = CreateObject("WScript.Shell")
DesktopPath = WshShell.SpecialFolders("Desktop")
Set Shortcut = WshShell.CreateShortcut(DesktopPath & "\库存管理系统完整版.lnk")
Shortcut.TargetPath = "python.exe"
Shortcut.Arguments = """" & "D:\yuan\不锈钢网带跟单3.0\inventory_manager_complete.py" & """"
Shortcut.WorkingDirectory = "D:\yuan\不锈钢网带跟单3.0"
Shortcut.Description = "宁津晨圣库存管理系统 V3.0"
Shortcut.Save
WScript.Echo "快捷方式创建成功！"
