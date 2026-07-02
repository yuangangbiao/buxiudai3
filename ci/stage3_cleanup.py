# -*- coding: utf-8 -*-
"""
[v3.6] 阶段 3 清理脚本

T10.1: 删除 stats_smart_sheet/ 整个模块
T12: 把 scripts/tools/ 30+ 脚本移到 archive/
"""
import os
import shutil
from datetime import datetime

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
ARCHIVE_DIR = os.path.join(PROJECT_ROOT, 'archive')


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f'  📁 创建: {path}')


def backup_and_remove(src, archive_subdir):
    """备份并移动到 archive/"""
    if not os.path.exists(src):
        print(f'  ⚠️ 不存在: {src}')
        return False

    archive_path = os.path.join(ARCHIVE_DIR, archive_subdir)
    ensure_dir(archive_path)

    if os.path.isdir(src):
        # 移动整个目录
        dst = os.path.join(archive_path, os.path.basename(src))
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(src, dst)
        print(f'  ✅ 移动目录: {src} -> {dst}')
    else:
        # 移动单个文件
        dst = os.path.join(archive_path, os.path.basename(src))
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        print(f'  ✅ 移动文件: {src} -> {dst}')

    return True


def main():
    print('===== 阶段 3 清理 =====\n')

    # 1. T10.1: 删除 stats_smart_sheet/ 模块
    print('[T10.1] 删除 stats_smart_sheet/ 模块')
    stats_dir = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'stats_smart_sheet')
    if os.path.exists(stats_dir):
        backup_and_remove(stats_dir, f'stats_smart_sheet_{datetime.now().strftime("%Y%m%d")}')
        print(f'  ✅ stats_smart_sheet/ 已删除 + 备份')
    else:
        print('  ⚠️ stats_smart_sheet/ 不存在，跳过')

    # 2. T12: scripts/tools/ 移到 archive
    print('\n[T12] scripts/tools/ 移到 archive/')
    tools_dir = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'scripts', 'tools')
    if os.path.exists(tools_dir):
        count = len(os.listdir(tools_dir))
        backup_and_remove(tools_dir, f'scripts_tools_{datetime.now().strftime("%Y%m%d")}')
        print(f'  ✅ scripts/tools/ {count} 个文件已移到 archive/')

    # 3. scripts/archive/ 也移到 archive/
    print('\n[T12] scripts/archive/ 移到 archive/')
    archive_src = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'scripts', 'archive')
    if os.path.exists(archive_src):
        count = len(os.listdir(archive_src))
        backup_and_remove(archive_src, f'scripts_archive_{datetime.now().strftime("%Y%m%d")}')
        print(f'  ✅ scripts/archive/ {count} 个文件已移到 archive/')

    # 4. scripts/ 一级目录的 30+ 调试脚本
    print('\n[T12] mobile_api_ai/scripts/*.py 调试脚本移到 archive/')
    scripts_dir = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'scripts')
    moved = 0
    if os.path.exists(scripts_dir):
        for f in os.listdir(scripts_dir):
            full = os.path.join(scripts_dir, f)
            if os.path.isfile(full) and f.endswith('.py'):
                # 排除保留的
                if f in ('list_all_orders.py', 'list_all_orders3.py'):
                    continue
                backup_and_remove(full, f'scripts_misc_{datetime.now().strftime("%Y%m%d")}')
                moved += 1
        print(f'  ✅ scripts/*.py {moved} 个文件已移到 archive/')

    # 5. 列出 archive/ 汇总
    print('\n===== archive/ 当前内容 =====')
    if os.path.exists(ARCHIVE_DIR):
        for d in os.listdir(ARCHIVE_DIR):
            full = os.path.join(ARCHIVE_DIR, d)
            if os.path.isdir(full):
                count = sum(len(files) for _, _, files in os.walk(full))
                print(f'  📁 {d}: {count} 个文件')

    print('\n✅ 阶段 3 清理完成')


if __name__ == '__main__':
    main()
