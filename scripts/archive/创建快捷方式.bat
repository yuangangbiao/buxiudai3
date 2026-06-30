@echo off
chcp 65001 >nul
echo ======================================
echo   创建库存管理系统桌面快捷方式
echo ======================================
echo.

cd /d "%~dp0"

echo 正在创建桌面快捷方式...
powershell -ExecutionPolicy Bypass -Command "
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\库存管理系统完整版.lnk')
$Shortcut.TargetPath = 'python.exe'
$Shortcut.Arguments = '\"D:\yuan\不锈钢网带跟单3.0\inventory_manager_complete.py\"'
$Shortcut.WorkingDirectory = 'D:\yuan\不锈钢网带跟单3.0'
$Shortcut.Description = '宁津晨圣库存管理系统 V3.0'
$Shortcut.Save()
Write-Host '快捷方式创建成功！'
"

echo.
echo 按任意键退出...
pause >nul
