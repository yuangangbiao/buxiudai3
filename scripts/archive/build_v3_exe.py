# -*- coding: utf-8 -*-
"""
不锈钢输送网带跟单系统 v3.1.0 - 打包脚本
生成完全无依赖的独立EXE文件
"""
import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'build_v3.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PYINSTALLER_PATH = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"

def clean_temp_dirs():
    """清理旧的临时目录"""
    temp_dirs = [
        os.path.join(BASE_DIR, "temp_spec_build"),
        os.path.join(BASE_DIR, "dist_main"),
        os.path.join(BASE_DIR, "build_main"),
    ]
    for td in temp_dirs:
        if os.path.exists(td):
            shutil.rmtree(td)
            logger.info(f"[CLEAN] 已删除: {td}")

def create_spec_file():
    """创建PyInstaller spec文件"""
    spec_content = r'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

hiddenimports = [
    'pymysql',
    'pymysql.connections',
    'pymysql.cursors',
    'pymysql.converters',
    'pymysql.optional_functions',
    'pymysql.constants',
    'pymysql.charset',
    'tkinter',
    'tkinter.ttk',
    'tkinter.tix',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.colorchooser',
    'tkinter.commondialog',
    'tkinter.constants',
    'tkinter.scrolledtext',
    'dotenv',
    'dotenv.main',
    'dotenv.parser',
    'logging',
    'logging.handlers',
    'logging.config',
    'json',
    'uuid',
    'datetime',
    'decimal',
    'collections',
    'functools',
    'itertools',
    'copy',
    'weakref',
    'gc',
    'traceback',
    'linecache',
    'io',
    'os',
    'sys',
    're',
    'math',
    'random',
    'hashlib',
    'hmac',
    'base64',
    'binascii',
    'struct',
    'csv',
    'xml',
    'xml.etree',
    'xml.etree.ElementTree',
    'html',
    'html.parser',
    'html.entities',
    'urllib',
    'urllib.parse',
    'urllib.request',
    'urllib.response',
    'urllib.error',
    'http',
    'http.client',
    'http.server',
    'socketserver',
    'threading',
    'queue',
    'concurrent',
    'concurrent.futures',
    'pathlib',
    'tempfile',
    'shutil',
    'zipfile',
    'tarfile',
    'gzip',
    'bz2',
    'lzma',
    'platform',
    'subprocess',
    'socket',
    'select',
    'selectors',
    'ssl',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    'urllib3.util',
    'urllib3.util.url',
    'urllib3.util.ssl_',
    'urllib3.util.timeout',
    'urllib3.util.retry',
    'urllib3.exceptions',
    'requests',
    'requests.utils',
    'requests.structures',
    'requests.models',
    'requests.api',
    'requests.auth',
    'requests.cookies',
    'requests.status_codes',
    'requests.exceptions',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageFont',
    'PIL.ImageDraw',
    'PIL._imaging',
    'cv2',
    'cv2.cv2',
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy.ndarray',
    'numpy.random',
    'pandas',
    'pandas.core',
    'pandas.core.frame',
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.cell',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.reader',
    'openpyxl.writer',
    'dateutil',
    'dateutil.parser',
    'dateutil.tz',
    'dateutil.relativedelta',
    'flask',
    'flask.app',
    'flask.blueprints',
    'flask.globals',
    'flask.helpers',
    'flask.json',
    'flask.templating',
    'flask.wrappers',
    'werkzeug',
    'werkzeug.routing',
    'werkzeug.wrappers',
    'werkzeug.utils',
    'jinja2',
    'jinja2.runtime',
    'jinja2.loaders',
    'matplotlib',
    'matplotlib.figure',
    'matplotlib.backends',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends.backend_agg',
    'fpdf',
    'fpdf.fpdf',
    'PIL.PngImagePlugin',
    'PIL.JpegImagePlugin',
    'PIL.BmpImagePlugin',
    'PIL.TiffImagePlugin',
    'PIL.GifImagePlugin',
    'PIL.TgaImagePlugin',
    'queue',
    '_queue',
    'security',
    'security.license_tool',
    'security.license_manager',
    'security.license_binding',
    'security.machine_fingerprint',
    'security.fingerprint_unlock_gui',
    'models.database',
    'views.db_settings_window',
    'utils.material_templates',
    'utils.material_calculator',
    'utils.process_templates',
    'utils.custom_types',
    'utils.app_init',
    'services.inventory_notifier',
    'services.order_service',
    'services.audit_service',
    'utils.helpers',
    'utils.op_logger',
    'utils.order_templates',
    'utils.logistics_companies',
    'utils.settings_manager',
    'utils.window_manager',
    'utils.validators',
    'utils.excel_utils',
    'utils.pagination',
    'utils.backup_manager',
    'utils.order_templates',
    'utils.copyable_widgets',
    'models.order',
    'models.production',
    'models.process',
    'models.quality',
    'models.quality_rule',
    'models.process_calc_rule',
    'models.product_type',
    'models.material_rules',
    'models.bom',
    'models.shipment',
    'models.order_log',
    'views.dialogs',
    'views.orders.list_view',
    'views.orders.confirm',
    'views.orders.new_order_dialog',
    'views.shipment_view',
    'views.quality_view',
    'views.quality_rule_view',
    'views.process_calc_rule_view',
    'views.material_rules_view',
    'views.bom_view',
    'views.finished_product_stats_view',
    'views.production_view',
    'views.main_window',

    # === 容器中心模块 ===
    # 桌面端容器集成
    'desktop_container_integration',
    'modular_config',
    'process_tracker',
    'material_publish_service',

    # mobile_api_ai 目录下的容器模块（通过 pathex 查找）
    'container_center_v5',
    'storage_layer',
    'container_center_client',
]

def get_hiddenimports():
    return hiddenimports

a = Analysis(
    ['main.py'],
    pathex=[r'{BASE_DIR}', r'{BASE_DIR}/mobile_api_ai'],
    binaries=[],
    datas=[
        ('{BASE_DIR}/views/dashboard/templates', 'views/dashboard/templates'),
        ('{BASE_DIR}/visualization_app', 'visualization_app'),
        ('{BASE_DIR}/data', 'data'),
    ],
    hiddenimports=get_hiddenimports(),
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib.tests',
        'numpy.tests',
        'pandas.tests',
        'PIL.tests',
        'cv2.tests',
        'numpy.f2py',
        'numpy.distutils',
        'numpy.linalg.lapack_lite',
        'numpy.fft',
        'test',
        'unittest',
        'doctest',
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
    name='不锈钢网带跟单系统v3.1',
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
'''.format(BASE_DIR=BASE_DIR)

    spec_file = os.path.join(BASE_DIR, '不锈钢网带跟单系统v3.1.spec')
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    logger.info(f"[SPEC] 已创建: {spec_file}")
    return spec_file

def build_exe():
    """执行PyInstaller打包"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("  正在打包 不锈钢输送网带跟单系统 v3.1.0")
    logger.info("=" * 70)
    logger.info("")

    spec_file = os.path.join(BASE_DIR, '不锈钢网带跟单系统v3.1.spec')

    cmd = [
        PYINSTALLER_PATH,
        "--clean",
        "--noconfirm",
        spec_file
    ]

    logger.info(f"[BUILD] 执行命令: {' '.join(cmd)}")
    logger.info("")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='gbk',
        cwd=BASE_DIR
    )

    logger.info("=" * 70)
    if result.returncode == 0:
        logger.info("[SUCCESS] 打包成功！")
        logger.info("=" * 70)

        dist_dir = os.path.join(BASE_DIR, 'dist_main')
        exe_files = [f for f in os.listdir(dist_dir) if f.endswith('.exe')]

        if exe_files:
            exe_path = os.path.join(dist_dir, exe_files[0])
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            logger.info(f"  文件位置: {exe_path}")
            logger.info(f"  文件大小: {size_mb:.2f} MB")
            logger.info("")
            logger.info("=" * 70)
            logger.info("  [SUCCESS] 打包完成！")
            logger.info("=" * 70)
            return exe_path
        else:
            logger.error("[FAIL] 未找到EXE文件！")
            return None
    else:
        logger.error("[FAIL] 打包失败！")
        logger.error("")
        logger.error("STDERR:")
        logger.error(result.stderr)
        return None

def copy_to_target(exe_path):
    """复制到目标位置"""
    target_dir = r"F:\智能跟单系统\v3.0"
    os.makedirs(target_dir, exist_ok=True)

    target_exe = os.path.join(target_dir, "不锈钢网带跟单系统v3.0.exe")

    if os.path.exists(target_exe):
        os.remove(target_exe)

    shutil.copy2(exe_path, target_dir)

    logger.info(f"[COPY] 已复制到: {target_exe}")

    config_files = ['.env', 'config.py', 'db_config.py']
    for cf in config_files:
        src = os.path.join(BASE_DIR, cf)
        if os.path.exists(src):
            dst = os.path.join(target_dir, cf)
            shutil.copy2(src, dst)
            logger.info(f"[COPY] 已复制: {cf}")

    logger.info("")
    logger.info(f"[SUCCESS] 所有文件已复制到: {target_dir}")

def main():
    logger.info("=" * 70)
    logger.info("  不锈钢输送网带跟单系统 v3.0.0 打包工具")
    logger.info("=" * 70)
    logger.info("")

    logger.info("[STEP 1/3] 清理临时目录...")
    clean_temp_dirs()
    logger.info("")

    logger.info("[STEP 2/3] 创建spec配置文件...")
    create_spec_file()
    logger.info("")

    logger.info("[STEP 3/3] 执行打包...")
    exe_path = build_exe()

    if exe_path:
        logger.info("")
        logger.info("[EXTRA] 复制文件到目标目录...")
        copy_to_target(exe_path)

if __name__ == "__main__":
    main()