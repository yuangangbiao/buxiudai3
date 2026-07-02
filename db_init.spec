# -*- coding: utf-8 -*-
"""
库存管理系统 - 数据库初始化工具打包配置
"""
import os
import sys

block_cipher = None

hiddenimports = [
    'pymysql',
    'pymysql.connections',
    'pymysql.cursors',
    'pymysql.converters',
    'cryptography',
    'json',
    'datetime',
]

a = Analysis(
    ['inventory_db_init.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'flask',
        'requests',
        'matplotlib',
        'numpy',
        'pandas',
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
    name='数据库初始化工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)
