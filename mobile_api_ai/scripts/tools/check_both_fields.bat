@echo off
echo === wechat_container.db process_records (WO-202605008) ===
echo -- 查看 work_order_no 和 order_no 两个字段 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, work_order_no, order_no, product_name, status FROM process_records WHERE work_order_no='WO-202605008';"

echo.
echo === wechat_container.db data_packages (ORD-202605008) ===
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, title, related_order, related_process, target_operator FROM data_packages WHERE related_order='ORD-202605008' LIMIT 3;"

echo.
echo === 检查 schedule/publish 是否保存了 order_no ===
echo -- 查看 process_records 表的 order_no 列 --
sqlite3.exe "D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db" "SELECT id, work_order_no, order_no FROM process_records LIMIT 5;"

pause
