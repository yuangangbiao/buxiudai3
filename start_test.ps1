# 服务器启动脚本
$python = "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$script = "d:\yuan\不锈钢网带跟单3.0\server_test_runner.py"
$ErrorActionPreference = "Continue"

Write-Host "启动服务器..."
Write-Host "Python: $python"
Write-Host "脚本: $script"

& $python $script

Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
