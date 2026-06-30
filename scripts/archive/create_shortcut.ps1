$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\钢带订单追踪系统.lnk")
$Shortcut.TargetPath = "D:\yuan\不锈钢网带跟单3.0\启动钢带订单系统.bat"
$Shortcut.WorkingDirectory = "D:\yuan\不锈钢网带跟单3.0"
$Shortcut.IconLocation = "D:\yuan\不锈钢网带跟单3.0\icon.ico, 0"
$Shortcut.Description = "钢带订单追踪系统 v2.0.0"
$Shortcut.Save()