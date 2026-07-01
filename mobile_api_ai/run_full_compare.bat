@echo off
chcp 65001 >nul
echo ========================================
echo 数据库详细对比分析
echo ========================================
echo.

cd /d D:\yuan\不锈钢网带跟单3.0\mobile_api_ai
python scripts\tools\full_db_compare.py

echo.
echo ========================================
echo 对比完成！请查看上方输出
echo ========================================
pause
