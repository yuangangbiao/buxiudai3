@echo off
echo === /api/dashboard ===
curl.exe -s "http://localhost:5008/api/dashboard"

echo.
echo.
echo === /api/sub_step_records?order_no=ORD-202605008 ===
curl.exe -s "http://localhost:5008/api/sub_step_records?order_no=ORD-202605008"

echo.
echo.
echo === /api/scan-info?code=WO-202605008 ===
curl.exe -s "http://localhost:5008/api/scan-info?code=WO-202605008"

pause
