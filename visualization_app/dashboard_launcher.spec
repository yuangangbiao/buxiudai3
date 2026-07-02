# -*- coding: utf-8 -*-
"""
PyInstaller 打包配置 - 可视化大屏启动器
"""
import os
import sys

project_root = os.path.dirname(os.path.abspath(SPEC))
dist_dir = os.path.join(project_root, "dist", "可视化大屏启动器")
build_dir = os.path.join(project_root, "build", "可视化大屏启动器")

a = Analysis(
    [os.path.join(project_root, "visualization_app", "main.py")],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, "views", "dashboard", "templates"), "views/dashboard/templates"),
    ],
    hiddenimports=[
        "flask",
        "pymysql",
        "webbrowser",
        "socket",
        "threading",
        "json",
        "tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="可视化大屏启动器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="可视化大屏启动器",
    target_arch=None,
    manifest=None,
    contents_directory="Content",
)
