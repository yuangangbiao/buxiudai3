@echo off
echo === 检查 wechat_container.db 的 process_records (008) ===
echo.
echo -- process_records 中 WO-202605008 的记录 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, work_order_no, order_no, product_name, status, created_at FROM process_records WHERE work_order_no='WO-202605008';"

echo.
echo -- process_records 总数 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT COUNT(*) FROM process_records;"

echo.
echo -- data_packages 中 ORD-202605008 的记录 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, title, related_order, related_process, target_operator, status FROM data_packages WHERE related_order='ORD-202605008' LIMIT 5;"

echo.
echo === 检查 container_center.db 的 process_records (008) ===
echo.
echo -- container_center.db process_records 总数 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT COUNT(*) FROM process_records;"

echo.
echo -- container_center.db process_records (008) --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT id, work_order_no, order_no FROM process_records WHERE work_order_no='WO-202605008';"

echo.
echo -- container_center.db data_packages (ORD-202605008) --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT id, title, related_order FROM data_packages WHERE related_order='ORD-202605008' LIMIT 3;"

pause
