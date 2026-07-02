# -*- coding: utf-8 -*-
"""
库存管理系统服务器端 - PyInstaller打包配置
"""
import os
import sys

block_cipher = None

hiddenimports = [
    # Flask相关
    'flask',
    'flask.app',
    'flask.blueprints',
    'flask.config',
    'flask.ctx',
    'flask.globals',
    'flask.helpers',
    'flask.json',
    'flask.logging',
    'flask.sessions',
    'flask.views',
    'flask.wrappers',
    'werkzeug',
    'werkzeug.wrappers',
    'werkzeug.wsgi',
    'werkzeug.exceptions',
    'werkzeug.routing',
    'werkzeug.serving',
    'werkzeug.test',
    'werkzeug.utils',
    'werkzeug.http',
    'werkzeug.datastructures',
    'jinja2',
    'jinja2.environment',
    'jinja2.template',
    'markupsafe',
    'itsdangerous',
    'click',
    # 数据库
    'pymysql',
    'pymysql.connections',
    'pymysql.cursors',
    'pymysql.converters',
    'pymysql.connections',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    # 标准库
    'json',
    'threading',
    'datetime',
    'logging',
    'functools',
    'contextlib',
    're',
    # SSL相关
    'ssl',
    'http.client',
    'http.cookiejar',
    'xml.etree.ElementTree',
    'pathlib',
    # 编码
    'encodings',
    'encodings.utf_8',
    'encodings.gbk',
    'encodings.ascii',
]

a = Analysis(
    ['inventory_server.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[
        ('server_config.json', '.'),
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
        'tkinter',
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
    name='库存管理服务器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    manifest=None,
    resources=None,
)
