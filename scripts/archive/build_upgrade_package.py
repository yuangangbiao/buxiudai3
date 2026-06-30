# -*- coding: utf-8 -*-
"""
不锈钢网带跟单系统 - 升级包生成工具
生成增量升级包，只需复制到升级包目录即可完成升级
"""

import os
import sys
import shutil
import json
import hashlib
from datetime import datetime

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from version import VERSION, UPGRADE_FILES, UPGRADE_DIR, EXCLUDE_FILES

def calculate_md5(file_path):
    """计算文件MD5值"""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def generate_upgrade_package(description="修复漏洞", output_dir=None):
    """
    生成升级包
    
    Args:
        description: 升级描述
        output_dir: 输出目录，默认为项目根目录的升级包目录
    
    Returns:
        升级包路径
    """
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, UPGRADE_DIR)
    
    # 创建升级包目录
    upgrade_package_dir = os.path.join(output_dir, f"upgrade_v{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}")
    files_dir = os.path.join(upgrade_package_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    
    # 复制升级文件
    copied_files = []
    for rel_path in UPGRADE_FILES:
        src_path = os.path.join(BASE_DIR, rel_path)
        
        if not os.path.exists(src_path):
            print(f"[WARN] 文件不存在，跳过: {rel_path}")
            continue
        
        # 检查是否排除
        should_exclude = False
        for exclude in EXCLUDE_FILES:
            if exclude in src_path:
                should_exclude = True
                break
        
        if should_exclude:
            continue
        
        # 创建目标目录
        dst_path = os.path.join(files_dir, rel_path)
        dst_dir = os.path.dirname(dst_path)
        os.makedirs(dst_dir, exist_ok=True)
        
        # 复制文件
        shutil.copy2(src_path, dst_path)
        copied_files.append({
            "path": rel_path,
            "md5": calculate_md5(src_path)
        })
        print(f"[COPY] {rel_path}")
    
    # 生成升级信息文件
    upgrade_info = {
        "version": VERSION,
        "build_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_count": len(copied_files),
        "description": description,
        "files": copied_files
    }
    
    with open(os.path.join(upgrade_package_dir, "upgrade_info.json"), 'w', encoding='utf-8') as f:
        json.dump(upgrade_info, f, ensure_ascii=False, indent=4)
    
    # 生成升级脚本
    upgrade_script = f'''@echo off
chcp 65001 >nul
echo ============================================================
echo  不锈钢网带跟单系统 - 升级程序 v{VERSION}
echo ============================================================
echo.

setlocal enabledelayedexpansion

set "APP_DIR=%%~dp0.."
set "UPGRADE_DIR=%%~dp0"

echo [信息] 应用目录: %%APP_DIR%%
echo [信息] 升级包目录: %%UPGRADE_DIR%%
echo.

echo [步骤1] 读取升级信息...
type "%%UPGRADE_DIR%%upgrade_info.json"
echo.

echo [步骤2] 开始升级...

REM 复制升级文件
for /r "%%UPGRADE_DIR%%files" %%f in (*.py) do (
    set "REL_PATH=%%f"
    set "REL_PATH=!REL_PATH:%%UPGRADE_DIR%%files\\=!"
    echo 正在复制: !REL_PATH!
    xcopy /Y "%%f" "%%APP_DIR%%\\!REL_PATH!" >nul
)

echo.
echo [步骤3] 清理Python缓存...
for /d /r "%%APP_DIR%%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /d /r "%%APP_DIR%%" %%d in (.pytest_cache) do @if exist "%%d" rmdir /s /q "%%d"

echo.
echo ============================================================
echo  升级完成！请重启主软件。
echo ============================================================
pause
'''
    
    with open(os.path.join(upgrade_package_dir, "执行升级.bat"), 'w', encoding='utf-8') as f:
        f.write(upgrade_script)
    
    # 创建README文件
    readme_content = f'''# 不锈钢网带跟单系统升级包 v{VERSION}

## 升级说明

### 升级步骤:
1. 将此目录下的所有文件复制到主软件的"升级包"目录
2. 双击"执行升级.bat"运行升级
3. 升级完成后重启主软件

### 升级内容:
{description}

### 包含文件 ({len(copied_files)}个):
{chr(10).join([f"- {f['path']}" for f in copied_files])}

### 版本信息:
- 版本号: v{VERSION}
- 构建日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
'''
    
    with open(os.path.join(upgrade_package_dir, "README.txt"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n[DONE] 升级包生成完成: {upgrade_package_dir}")
    print(f"[INFO] 包含 {len(copied_files)} 个文件")
    
    return upgrade_package_dir

def main():
    """主函数"""
    print(f"\n{'='*60}")
    print(f"  升级包生成工具 v{VERSION}")
    print(f"{'='*60}")
    
    # 获取升级描述
    description = input("\n请输入升级描述 (默认: 修复漏洞): ").strip()
    if not description:
        description = "修复漏洞"
    
    # 生成升级包
    upgrade_dir = generate_upgrade_package(description)
    
    print(f"\n{'='*60}")
    print(f"  升级包已生成:")
    print(f"  {upgrade_dir}")
    print(f"{'='*60}")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
