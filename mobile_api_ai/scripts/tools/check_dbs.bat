@echo off
echo === container_center.db: process_records (WO-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT work_order_no, order_no, status, created_at FROM process_records WHERE work_order_no LIKE '%%202605008%%';"

echo.
echo === container_center.db: data_packages (WO-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT id, title, related_order, related_process, target_operator, status FROM data_packages WHERE related_order LIKE '%%202605008%%' OR title LIKE '%%202605008%%' LIMIT 5;"

echo.
echo === container_center.db: data_packages (ORD-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" "SELECT id, title, related_order, related_process, target_operator, status FROM data_packages WHERE related_order = 'ORD-202605008' LIMIT 5;"

echo.
echo === container_center.db: tables ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center.db" ".tables"

echo.
echo === wechat_container.db: process_records (WO-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT work_order_no, order_no, status, created_at FROM process_records WHERE work_order_no LIKE '%%202605008%%';"

echo.
echo === wechat_container.db: data_packages (ORD-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, title, related_order, related_process, target_operator, status FROM data_packages WHERE related_order = 'ORD-202605008' LIMIT 5;"

pause
