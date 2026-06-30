@echo off
cd /d "d:\yuan\不锈钢网带跟单3.0"
"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe" --onefile --windowed --name=订单修复升级包v3 --distpath="d:\升级包" --workpath="d:\yuan\不锈钢网带跟单3.0\build" --clean --hidden-import=pymysql --hidden-import=tkinter --hidden-import=tkinter.messagebox 升级包/upgrade_v3_order_fix.py
pause
