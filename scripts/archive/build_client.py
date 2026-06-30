# -*- coding: utf-8 -*-
"""
库存管理系统客户端 - 打包配置
使用 PyInstaller 打包成独立exe文件
"""

import os
import sys

try:
    import PyInstaller
except ImportError:
    print("正在安装 PyInstaller...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "client_package")
os.makedirs(CLIENT_DIR, exist_ok=True)

SPEC_CONTENT = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['{os.path.join(BASE_DIR, "inventory_client.py")}'],
    pathex=['{BASE_DIR}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests',
        'tkinter',
        'tkinter.ttk',
    ],
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
    name='库存管理客户端',
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
    icon=None,
)
"""

spec_file = os.path.join(CLIENT_DIR, "inventory_client.spec")
with open(spec_file, 'w', encoding='utf-8') as f:
    f.write(SPEC_CONTENT)

print(f"PyInstaller spec文件已创建: {spec_file}")
print()
print("使用以下命令打包:")
print(f"cd {CLIENT_DIR}")
print(f"pyinstaller --clean inventory_client.spec")
