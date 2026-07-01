@echo off
chcp 65001 >nul
echo ========================================
echo 企业微信应用机器人 - 代码打包工具
echo ========================================
echo.

set SOURCE_DIR=%~dp0
set OUTPUT_FILE=%SOURCE_DIR%wechat_bot_deploy.zip

echo 源目录: %SOURCE_DIR%
echo 输出文件: %OUTPUT_FILE%
echo.

echo 正在打包以下文件...
echo.

cd /d "%SOURCE_DIR%"

powershell -Command "
Write-Host '开始打包...' -ForegroundColor Green

# 创建临时目录
$tempDir = Join-Path $env:TEMP 'wechat_deploy_temp'
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
New-Item -ItemType Directory -Path $tempDir | Out-Null

# 需要打包的文件和目录
$items = @(
    'wechat_server.py',
    '云端一键启动.bat',
    'start_wechat_cloud.bat',
    'stop_all.bat',
    'container_center_api.py',
    'operators.json',
    'data/enterprise_structure.json',
    'bots',
    'commands',
    'services',
    'WW_verify_PWFveCpOUtSmyNnB.txt'
)

# 检查.env文件是否存在
if (Test-Path '.env') {
    $items += '.env'
    Write-Host '[+] .env (配置文件)'
}

# 复制文件到临时目录
foreach ($item in $items) {
    if (Test-Path $item) {
        Copy-Item $item -Destination $tempDir -Recurse -Force
        Write-Host ('[+] ' + $item) -ForegroundColor Cyan
    } else {
        Write-Host ('[!] 跳过: ' + $item + ' (不存在)') -ForegroundColor Yellow
    }
}

# 打包
$zipPath = Join-Path $SOURCE_DIR 'wechat_bot_deploy.zip'
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Compress-Archive -Path (Join-Path $tempDir '*') -DestinationPath $zipPath -Force

# 清理临时目录
Remove-Item $tempDir -Recurse -Force

# 显示结果
$fileInfo = Get-Item $zipPath
Write-Host ''
Write-Host '========================================' -ForegroundColor Green
Write-Host '打包完成!' -ForegroundColor Green
Write-Host ('文件: ' + $zipPath) -ForegroundColor White
Write-Host ('大小: ' + [math]::Round($fileInfo.Length / 1MB, 2) + ' MB') -ForegroundColor White
Write-Host '========================================' -ForegroundColor Green
"

echo.
echo 打包完成！
echo.
echo 上传到服务器后，解压到同一目录即可使用（如 C:\Users\Administrator\Desktop\云端部署包）
echo.
pause
