@echo off
cd /d "%~dp0"
start /b python.exe container_center_api.py > cc.log 2>&1
start /b python.exe app.py > app.log 2>&1
start /b python.exe wechat_server.py > wx.log 2>&1
