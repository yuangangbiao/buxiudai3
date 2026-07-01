@echo off
echo === 调度中心 5003: 查询 WO-202605008 ===
curl.exe -s "http://localhost:5003/api/dispatch-center/tasks?page=1&size=5"
pause
