# -*- coding: utf-8 -*-
"""
直接打包EXE的脚本
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "client_build_exe")

print("=" * 60)
print("  库存管理客户端 - EXE打包")
print("=" * 60)
print()

# 检查PyInstaller
print("[1/4] 检查PyInstaller...")
try:
    import PyInstaller
    print(f"    [OK] PyInstaller {PyInstaller.__version__}")
except ImportError:
    print("    正在安装PyInstaller...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "pyinstaller",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
    ])
    print("    [OK] PyInstaller安装完成")

# 创建spec文件
print()
print("[2/4] 创建打包配置...")
os.makedirs(BUILD_DIR, exist_ok=True)

spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['{os.path.join(BASE_DIR, 'inventory_client.py')}'],
    pathex=['{BASE_DIR}'],
    binaries=[],
    datas=[],
    hiddenimports=['requests', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox'],
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
)
'''

spec_path = os.path.join(BUILD_DIR, 'inventory_client.spec')
with open(spec_path, 'w', encoding='utf-8') as f:
    f.write(spec_content)
print("    [OK] 配置文件已创建")

# 执行打包
print()
print("[3/4] 开始打包...")
print("    注意：打包过程需要2-5分钟，请耐心等待...")
print()

import subprocess
os.chdir(BUILD_DIR)

try:
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller", "--clean", spec_path
    ], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    if result.returncode == 0:
        print("    [OK] 打包成功！")
        
        # 检查生成的EXE
        exe_path = os.path.join(BUILD_DIR, 'dist', '库存管理客户端.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"    [OK] EXE文件已生成: {exe_path}")
            print(f"    文件大小: {size_mb:.2f} MB")
        else:
            print("    [WARN] 未找到EXE文件，检查dist目录")
            
    else:
        print("    [ERROR] 打包失败")
        if result.stderr:
            print("    错误信息:")
            print(result.stderr[-500:])
            
except Exception as e:
    print(f"    [ERROR] 打包异常: {e}")

# 创建部署包
print()
print("[4/4] 创建零依赖部署包...")
DEPLOY_DIR = os.path.join(BASE_DIR, "零依赖EXE部署包")
if os.path.exists(DEPLOY_DIR):
    import shutil
    shutil.rmtree(DEPLOY_DIR)
os.makedirs(DEPLOY_DIR)

# 复制EXE
exe_src = os.path.join(BUILD_DIR, 'dist', '库存管理客户端.exe')
if os.path.exists(exe_src):
    import shutil
    shutil.copy2(exe_src, DEPLOY_DIR)
    print("    [OK] EXE已复制")

# 复制配置文件
config_src = os.path.join(BASE_DIR, 'inventory_client_config.json')
if os.path.exists(config_src):
    shutil.copy2(config_src, DEPLOY_DIR)
    print("    [OK] 预配置文件已复制")

# 创建说明
with open(os.path.join(DEPLOY_DIR, "使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write('''# 零依赖EXE客户端 - 使用说明

## 超级简单！只需要两步

### 1. 复制到目标电脑
将「零依赖EXE部署包」整个文件夹复制到目标电脑

### 2. 双击运行
直接双击「库存管理客户端.exe」

就这么简单！零依赖！

---

## 配置说明

### 首次使用需要配置

1. 启动后点击「设置」
2. 服务器地址：http://服务器IP:8080
   例如：http://192.168.1.100:8080
3. API密钥：steel_belt_inventory_key_2024
4. 保存 → 刷新

### 如何获取服务器IP

在服务器电脑上：
- 按 Win+R
- 输入 cmd
- 输入 ipconfig
- 找到 IPv4 地址

### 预配置（可选）

如果有 inventory_client_config.json：
- 将此文件放在EXE同一目录
- 启动会自动加载配置

---

## 常见问题

Q: 点击EXE没反应？
A: 请稍等几秒钟，首次启动较慢

Q: 无法连接服务器？
A: 检查：
   - 服务器是否已启动
   - IP地址是否正确
   - API密钥是否一致
   - 防火墙是否允许连接

---

## 文件说明

- 库存管理客户端.exe  → 主程序（核心）
- inventory_client_config.json → 预配置（可选）
- 使用说明.txt → 本文档
''')
print("    [OK] 说明文档已创建")

with open(os.path.join(DEPLOY_DIR, "快速配置.txt"), 'w', encoding='utf-8') as f:
    f.write('''# 快速配置 - 3步

## 第一步：获取服务器IP
在服务器电脑上：
1. Win+R → 输入 cmd → 回车
2. 输入 ipconfig → 回车
3. 找到 IPv4 地址（类似：192.168.1.100）

## 第二步：启动客户端
在目标电脑上双击「库存管理客户端.exe」

## 第三步：配置连接
1. 点击「设置」
2. 服务器地址：http://服务器IP:8080
3. API密钥：steel_belt_inventory_key_2024
4. 点击「保存」→ 点击「刷新」

完成！
''')
print("    [OK] 快速配置文档已创建")

print()
print("=" * 60)
print("  [OK] EXE打包完成！")
print("=" * 60)
print()
print(f"零依赖部署包位置：{DEPLOY_DIR}")
print()
print("包含文件：")
for item in sorted(os.listdir(DEPLOY_DIR)):
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        size_kb = os.path.getsize(item_path) / 1024
        print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 60)
print("  您只需要做的")
print("=" * 60)
print()
print("1. 将「零依赖EXE部署包」整个文件夹")
print("   复制到U盘或目标电脑")
print()
print("2. 在目标电脑双击「库存管理客户端.exe」")
print()
print("就这么简单！零依赖！")
print()
print("=" * 60)

# 尝试打开目录
try:
    os.startfile(DEPLOY_DIR)
except:
    pass
