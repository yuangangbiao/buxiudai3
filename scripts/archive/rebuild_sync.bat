@echo off
cd /d "d:\yuan\不锈钢网带跟单3.0"
"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe" --onefile --windowed --name=数据库表结构同步工具 --distpath=d:\升级包 --workpath=d:\yuan\不锈钢网带跟单3.0\build_sync --clean --exclude-module=cryptography --noconfirm "d:\升级包\数据库表结构同步工具.py"
pause
