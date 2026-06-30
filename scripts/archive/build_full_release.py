# -*- coding: utf-8 -*-
"""
不锈钢网带跟单系统 - 固定版本打包程序
生成完整的可部署版本，包含所有必要文件
"""

import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime
import zipfile

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from version import VERSION, BUILD_DATE

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'build_full.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PYINSTALLER_PATH = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"

def clean_build():
    """清理旧的构建目录"""
    dirs_to_clean = [
        os.path.join(BASE_DIR, "build_full"),
        os.path.join(BASE_DIR, "dist_full"),
        os.path.join(BASE_DIR, "release"),
    ]
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
            logger.info(f"[CLEAN] 已清理目录: {d}")

def build_main_exe():
    """构建主程序EXE"""
    logger.info(f"\n[BUILD] 开始构建主程序 v{VERSION}")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

hiddenimports = [
    'pymysql',
    'pymysql.connections',
    'pymysql.cursors',
    'dotenv',
    'json',
    'uuid',
    'hashlib',
    'datetime',
    'sqlite3',
    'decimal',
    'threading',
    'queue',
    'time',
    'math',
    'functools',
    'operator',
    'collections',
    'itertools',
    're',
    'csv',
    'io',
    'base64',
    'zlib',
]

a = Analysis(
    ['main.py'],
    pathex=['{BASE_DIR.replace("\\\\", "\\\\\\\\")}'],
    binaries=[],
    datas=[
        ('data/', 'data/'),
        ('.env.example', '.'),
        ('version.py', '.'),
        ('config.py', '.'),
        ('constants.py', '.'),
        ('db_config.py', '.'),
        ('CODING_STANDARDS.md', '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='不锈钢网带跟单系统v{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/app.ico'
)
'''
    spec_path = os.path.join(BASE_DIR, f"build_full_spec_{VERSION}.spec")
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    cmd = f'"{PYINSTALLER_PATH}" --clean --noconfirm "{spec_path}"'
    logger.info(f"[BUILD] 执行命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"[ERROR] 构建失败: {result.stderr}")
        raise Exception(f"构建失败: {result.stderr}")
    
    logger.info(f"[BUILD] 主程序构建成功")
    return True

def create_deployment_package():
    """创建部署包目录结构"""
    release_dir = os.path.join(BASE_DIR, "dist", "部署包", f"不锈钢网带跟单系统_v{VERSION}")
    os.makedirs(release_dir, exist_ok=True)
    
    # 复制主程序
    dist_dir = os.path.join(BASE_DIR, "dist")
    if os.path.exists(dist_dir):
        for item in os.listdir(dist_dir):
            src = os.path.join(dist_dir, item)
            dst = os.path.join(release_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    
    # 复制配置文件
    config_files = ['.license_binding', '.license_salt', '.fingerprint_cache']
    for cf in config_files:
        src = os.path.join(BASE_DIR, cf)
        if os.path.exists(src):
            shutil.copy2(src, release_dir)
    
    # 复制数据目录
    data_dir = os.path.join(BASE_DIR, "data")
    if os.path.exists(data_dir):
        shutil.copytree(data_dir, os.path.join(release_dir, "data"), dirs_exist_ok=True)
    
    # 创建.env文件
    env_content = f'''# 不锈钢网带跟单系统 v{VERSION} 配置文件
# 请根据实际环境修改以下配置
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=steel_belt

# 版本信息
APP_VERSION={VERSION}
BUILD_DATE={BUILD_DATE}
'''
    with open(os.path.join(release_dir, ".env"), 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    # 创建升级包目录
    upgrade_dir = os.path.join(release_dir, "升级包")
    os.makedirs(upgrade_dir, exist_ok=True)
    
    # 创建升级程序
    create_upgrade_program(upgrade_dir)
    
    logger.info(f"[BUILD] 部署包创建完成: {release_dir}")
    return release_dir

def create_upgrade_program(upgrade_dir):
    """创建内置升级程序"""
    # 创建升级脚本
    upgrade_bat = '''@echo off
chcp 65001 >nul
echo ============================================================
echo  不锈钢网带跟单系统 - 升级程序
echo ============================================================
echo.

set "APP_DIR=%~dp0.."
set "UPGRADE_DIR=%~dp0"

echo [信息] 应用目录: %APP_DIR%
echo [信息] 升级包目录: %UPGRADE_DIR%
echo.

REM 检查是否有新版本升级包
if not exist "%UPGRADE_DIR%upgrade_info.json" (
    echo [错误] 未找到升级信息文件
    pause
    exit /b 1
)

echo [步骤1] 读取升级信息...
for /f "delims=" %%a in (%UPGRADE_DIR%upgrade_info.json) do set "INFO=%%a"
echo %INFO%

echo.
echo [步骤2] 开始升级...

REM 复制升级文件
for /r "%UPGRADE_DIR%files" %%f in (*.py) do (
    set "REL_PATH=%%f"
    set "REL_PATH=!REL_PATH:%UPGRADE_DIR%files\=!"
    echo 正在复制: !REL_PATH!
    xcopy /Y "%%f" "%APP_DIR%\!REL_PATH!" >nul
)

echo.
echo [步骤3] 清理缓存...
for /d /r "%APP_DIR%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo.
echo ============================================================
echo  升级完成！请重启主软件。
echo ============================================================
pause
'''
    with open(os.path.join(upgrade_dir, "执行升级.bat"), 'w', encoding='utf-8') as f:
        f.write(upgrade_bat)
    
    # 创建升级信息文件
    upgrade_info = f'''{{
    "version": "{VERSION}",
    "build_date": "{BUILD_DATE}",
    "files_count": 0,
    "description": "初始版本"
}}
'''
    with open(os.path.join(upgrade_dir, "upgrade_info.json"), 'w', encoding='utf-8') as f:
        f.write(upgrade_info)
    
    # 创建files目录
    os.makedirs(os.path.join(upgrade_dir, "files"), exist_ok=True)
    
    logger.info(f"[BUILD] 升级程序创建完成")

def main():
    """主打包流程"""
    logger.info(f"\n{'='*70}")
    logger.info(f"  不锈钢网带跟单系统 v{VERSION} 完整打包程序")
    logger.info(f"  构建日期: {BUILD_DATE}")
    logger.info(f"{'='*70}")
    
    try:
        # 1. 清理旧构建
        logger.info("\n[STEP 1/3] 清理旧构建...")
        clean_build()
        
        # 2. 构建主程序
        logger.info("\n[STEP 2/3] 构建主程序...")
        build_main_exe()
        
        # 3. 创建部署包
        logger.info("\n[STEP 3/3] 创建部署包...")
        release_dir = create_deployment_package()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"  打包完成！")
        logger.info(f"  版本: v{VERSION}")
        logger.info(f"  位置: {release_dir}")
        logger.info(f"{'='*70}")
        
    except Exception as e:
        logger.error(f"[ERROR] 打包失败: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
