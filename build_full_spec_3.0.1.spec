# -*- mode: python ; coding: utf-8 -*-
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
    pathex=['D:\yuan\不锈钢网带跟单3.0'],
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
    hooksconfig={},
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
    name='不锈钢网带跟单系统v3.0.1',
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
