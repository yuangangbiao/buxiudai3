# -*- coding: utf-8 -*-
"""gbd3.0 项目 PyInstaller 标准化打包脚本

依据: D:/yuan/.trae/skills/pyinstaller-packaging/SKILL.md
位置: D:/yuan/gbd3.0/packaging_template/scripts/build.py

用法:
    python packaging_template/scripts/build.py                 # 标准打包
    python packaging_template/scripts/build.py --no-auto-fix   # 禁用自动修复
    python packaging_template/scripts/build.py --console        # 显示控制台

说明:
    - 自动扫描 gbd3.0 项目所有 .py 模块
    - 解析所有 import 语句,构建 hidden_imports 列表
    - 生成 Spec 文件 → 调 PyInstaller 打包
    - 失败时自动从错误中提取缺失模块,重试打包(最多3次)
"""
import os
import re
import sys
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path


# 沙箱根锚定(避免 Path.cwd() 不稳)
PROJECT_ROOT = Path(r'D:\yuan\gbd3.0')
CONFIG_DIR = PROJECT_ROOT / 'packaging_template' / 'config'
LOG_DIR = PROJECT_ROOT / 'logs'
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'
SPEC_DIR = PROJECT_ROOT / 'specs'

IGNORE_DIRS = {
    '__pycache__', '.git', '.vscode', 'backups', 'dist', 'build',
    'build_package', 'packaging_template', 'venv', '.workbuddy',
    '.task', 'docs', 'tests', 'mobile_api_ai',
}
IGNORE_DIRS_IN_PACKAGING = IGNORE_DIRS | {'logs'}

# 基础模块清单(必须在 hidden_imports 显式声明)
BASE_MODULES = {
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
    'pymysql', 'sqlite3', 'cryptography', 'requests', 'dotenv',
    'pathlib', 'json', 'logging', 'datetime', 'threading',
    'PIL', 'PIL.Image', 'PIL.ImageTk',
}

EXCLUDE_MODULES = {
    'matplotlib', 'numpy', 'pandas', 'cv2', 'torch', 'tensorflow',
}


def setup_logging():
    """配置日志(同时输出到文件 + 控制台)"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"packaging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def scan_python_modules(source_dir):
    """扫描 gbd3.0 项目所有 Python 模块。

    返回:
        (modules, data_files) = (sorted list of module names, list of data file paths)
    """
    modules = set()
    data_files = []
    data_extensions = {'.json', '.db', '.txt'}

    for root, dirs, files in os.walk(source_dir):
        # 过滤目录
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        for file in files:
            if file.startswith('.'):
                continue
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            try:
                rel = file_path.relative_to(source_dir)
            except ValueError:
                continue
            if ext == '.py':
                module_name = str(rel).replace('\\', '/').replace('/', '.').replace('.py', '')
                modules.add(module_name)
            elif ext in data_extensions or file == '.env':
                data_files.append(str(rel).replace('\\', '/'))

    return sorted(modules), data_files


def parse_imports(source_dir, base_modules=None):
    """解析所有 .py 文件的 import 语句。

    返回:
        sorted list of all imported module names
    """
    if base_modules is None:
        base_modules = set()
    all_imports = set(base_modules)
    import_patterns = [
        re.compile(r'from\s+([\w\.]+)\s+import'),
        re.compile(r'^\s*import\s+([\w\.]+)', re.MULTILINE),
    ]
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        for file in files:
            if not file.endswith('.py'):
                continue
            file_path = Path(root) / file
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for pat in import_patterns:
                for match in pat.findall(content):
                    if not match.startswith('_'):
                        all_imports.add(match)
    return sorted(all_imports)


def load_config():
    """从 packaging_config.yaml 加载配置(轻量 YAML 解析,避免引入 PyYAML 依赖)"""
    config_path = CONFIG_DIR / 'packaging_config.yaml'
    if not config_path.exists():
        return {}
    config = {}
    current_section = None
    current_subsection = None
    for raw in config_path.read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        if not line.startswith(' ') and line.endswith(':'):
            current_section = line[:-1].strip()
            config[current_section] = {}
            current_subsection = None
        elif line.startswith('  ') and not line.startswith('    ') and line.rstrip().endswith(':'):
            current_subsection = line.strip()[:-1]
            if current_section:
                config[current_section][current_subsection] = []
        elif line.strip().startswith('- '):
            item = line.strip()[2:].strip()
            if current_section and current_subsection:
                config[current_section][current_subsection].append(item)
        elif ':' in line and current_section is not None:
            k, _, v = line.strip().partition(':')
            v = v.strip().strip('"').strip("'")
            if current_subsection:
                config[current_section][current_subsection] = config[current_section].get(current_subsection, {})
                if not isinstance(config[current_section][current_subsection], dict):
                    config[current_section][current_subsection] = {}
                config[current_section][current_subsection][k] = v
            else:
                config[current_section][k] = v
    return config


def generate_spec_content(exe_name, main_entry, modules, data_files):
    """生成 .spec 文件内容"""
    hidden_imports_str = ",\n    ".join(f"'{m}'" for m in modules)
    excludes_str = ', '.join(f"'{m}'" for m in EXCLUDE_MODULES)
    return f'''# -*- coding: utf-8 -*-
# Auto-generated by packaging_template/scripts/build.py
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
import os
from pathlib import Path

PROJECT_ROOT = Path(r'D:\\yuan\\gbd3.0')

HIDDENIMPORTS = [
    {hidden_imports_str},
]

EXCLUDES = [{excludes_str}]


def get_data_files():
    datas = []
    data_extensions = {{'.json', '.db', '.txt'}}
    for root, dirs, files in os.walk(str(PROJECT_ROOT)):
        # 跳过干扰目录
        dirs[:] = [d for d in dirs if d not in {IGNORE_DIRS_IN_PACKAGING} and not d.startswith('.')]
        for file in files:
            if file.startswith('.'):
                continue
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            if ext in data_extensions:
                rel = str(file_path.relative_to(PROJECT_ROOT)).replace('\\\\', '/')
                datas.append((rel, '.'))
        # .env
        env_file = Path(root) / '.env'
        if env_file.exists():
            rel = str(env_file.relative_to(PROJECT_ROOT)).replace('\\\\', '/')
            datas.append((rel, '.'))
    return datas


a = Analysis(
    [str(PROJECT_ROOT / '{main_entry}')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=get_data_files(),
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{exe_name}',
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
'''


def save_auto_discovered(modules):
    """把自动发现的缺失模块追加到 packaging_config.yaml 的 auto_discovered"""
    config_path = CONFIG_DIR / 'packaging_config.yaml'
    if not modules:
        return
    existing = set()
    text = config_path.read_text(encoding='utf-8')
    if 'auto_discovered:' in text:
        # 解析已有 auto_discovered
        m = re.search(r'auto_discovered:\s*\n((?:\s*-\s+.+\n)*)', text)
        if m:
            for line in m.group(1).splitlines():
                item = line.strip().lstrip('- ').strip().strip('"').strip("'")
                if item:
                    existing.add(item)
    new_items = sorted(existing | set(modules))
    new_block_lines = ['  auto_discovered:']
    for item in new_items:
        new_block_lines.append(f'    - "{item}"')
    new_block = '\n'.join(new_block_lines) + '\n'
    new_text = re.sub(r'  auto_discovered:\s*\n(?:\s*-\s+.+\n)*', new_block, text, count=1)
    if '  auto_discovered:' not in new_text:
        new_text = new_text.rstrip() + '\n' + new_block
    config_path.write_text(new_text, encoding='utf-8')


def extract_missing_modules(stderr_output):
    """从 PyInstaller 错误输出提取缺失模块名"""
    missing = set()
    patterns = [
        r"ModuleNotFoundError: No module named '([^']+)'",
        r"ImportError: No module named '([^']+)'",
        r"hidden import '([^']+)' not found",
    ]
    for pat in patterns:
        for m in re.findall(pat, stderr_output):
            top = m.split('.')[0]
            if top not in EXCLUDE_MODULES and not top.startswith('_'):
                missing.add(m)
    return sorted(missing)


def build(auto_fix=True, console=False):
    """执行完整打包流程"""
    logger = setup_logging()
    config = load_config()
    exe_name = config.get('project', {}).get('name_exe', 'gbd3.0.exe') or 'gbd3.0.exe'
    main_entry = config.get('paths', {}).get('main_entry', 'main.py') or 'main.py'
    project_name = config.get('project', {}).get('name', 'gbd3.0')

    logger.info(f"=== gbd3.0 PyInstaller 打包 ===")
    logger.info(f"项目: {project_name}")
    logger.info(f"输出: {exe_name}")
    logger.info(f"入口: {main_entry}")

    # Step 1: 扫描模块
    logger.info("Step 1/4: 扫描源代码...")
    modules, data_files = scan_python_modules(str(PROJECT_ROOT))
    logger.info(f"  发现 {len(modules)} 个模块, {len(data_files)} 个数据文件")

    # Step 2: 解析 import
    logger.info("Step 2/4: 解析 import 语句...")
    base = BASE_MODULES | set(config.get('hidden_imports', {}).get('base_modules', []) or [])
    auto = set(config.get('hidden_imports', {}).get('auto_discovered', []) or [])
    imports = parse_imports(str(PROJECT_ROOT), base_modules=base | auto)
    logger.info(f"  发现 {len(imports)} 个 import")

    # Step 3: 生成 Spec
    logger.info("Step 3/4: 生成 Spec 文件...")
    spec_content = generate_spec_content(exe_name, main_entry, imports, data_files)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    spec_file = SPEC_DIR / 'gbd3.0.spec'
    spec_file.write_text(spec_content, encoding='utf-8')
    logger.info(f"  已生成: {spec_file}")

    # Step 4: 执行打包
    for attempt in range(1, 4):
        logger.info(f"Step 4/4: 执行 PyInstaller 打包 (第 {attempt}/3 次)...")
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)

        cmd = [
            sys.executable, '-m', 'PyInstaller',
            str(spec_file),
            '--workpath', str(BUILD_DIR),
            '--distpath', str(DIST_DIR),
        ]
        if console:
            cmd.append('--console')
        else:
            cmd.append('--windowed')
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding='utf-8')

        if result.returncode == 0:
            logger.info(f"打包成功! exe 在 {DIST_DIR}/{exe_name}")
            return 0

        logger.error(f"打包失败 (exit={result.returncode})")
        if not auto_fix or attempt == 3:
            logger.error(f"stderr (last 1000):\n{result.stderr[-1000:]}")
            return result.returncode

        missing = extract_missing_modules(result.stderr)
        if not missing:
            logger.error(f"无法自动修复, stderr:\n{result.stderr[-1000:]}")
            return result.returncode
        logger.info(f"自动修复: 发现缺失模块 {missing}")
        save_auto_discovered(missing)
        # 重新加载并继续
        config = load_config()
        auto = set(config.get('hidden_imports', {}).get('auto_discovered', []) or [])
        imports = parse_imports(str(PROJECT_ROOT), base_modules=base | auto)
        spec_content = generate_spec_content(exe_name, main_entry, imports, data_files)
        spec_file.write_text(spec_content, encoding='utf-8')

    return 1


if __name__ == '__main__':
    auto_fix = '--no-auto-fix' not in sys.argv
    console = '--console' in sys.argv
    sys.exit(build(auto_fix=auto_fix, console=console))
