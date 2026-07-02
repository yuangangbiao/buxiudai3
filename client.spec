# -*- coding: utf-8 -*-
"""
库存管理系统客户端 - PyInstaller打包配置
"""
import os
import sys

block_cipher = None

# 收集所有需要的模块
hiddenimports = [
    # 核心模块
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'requests',
    'requests.packages.urllib3',
    'requests.packages.urllib3.util',
    'requests.packages.chardet',
    'requests.packages.idna',
    'requests.packages.certifi',
    'urllib3',
    'urllib3.util',
    'urllib3.exceptions',
    'idna',
    'charset_normalizer',
    'certifi',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'json',
    'threading',
    'datetime',
    # SSL相关
    'ssl',
    'http.client',
    'http.cookiejar',
    # Windows特定
    'xml.etree.ElementTree',
    'pathlib',
    # 编码相关
    'encodings',
    'encodings.utf_8',
    'encodings.gbk',
    'encodings.ascii',
]

a = Analysis(
    ['inventory_client.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[
        ('inventory_client_config.json', '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
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
    manifest=None,
    resources=None,
)
