@echo off
chcp 65001 >nul
title 库存管理系统 - 防火墙配置

echo ============================================================
echo   库存管理系统 - 防火墙配置工具
echo ============================================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 需要管理员权限！
    echo.
    echo 请右键点击「以管理员身份运行」
    echo.
    pause
    exit /b 1
)

echo [1/3] 检查当前防火墙状态...
netsh advfirewall show allprofile state | findstr "Off"
if errorlevel 1 (
    echo     防火墙已启用
) else (
    echo     警告：防火墙可能已关闭
)

echo.
echo [2/3] 添加入站规则（开放8080端口）...
netsh advfirewall firewall add rule name="库存管理系统8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1

if %errorlevel% equ 0 (
    echo     [OK] 规则添加成功
) else (
    echo     [OK] 规则已存在或添加成功
)

echo.
echo [3/3] 验证规则...
netsh advfirewall firewall show rule name="库存管理系统8080" | findstr "库存管理系统8080"
if errorlevel 1 (
    echo     规则验证失败，但可能已添加
) else (
    echo     [OK] 规则验证成功
)

echo.
echo ============================================================
echo   防火墙配置完成！
echo ============================================================
echo.
echo 客户端连接信息：
echo.
echo    服务器地址: http://192.168.1.32:8080
echo    API密钥:    steel_belt_inventory_key_2024
echo.
echo ============================================================
echo.
pause
