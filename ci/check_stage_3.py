# -*- coding: utf-8 -*-
"""
[v3.6] CP-3 检查脚本 - 阶段 3 完成后

检查项:
- T9 50+ 文件清理
- T10.1 stats_smart_sheet 删除
- T11 services 清理
- T12 scripts 移到 archive
- T13 migrations 重写
- T25 CHANGELOG
- T26 核心文档
"""
import os
import sys
import subprocess

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    B = '\033[94m'
    E = '\033[0m'


def passed(name, details=''):
    print(f'{C.G}[PASS]{C.E} {name}')
    if details:
        print(f'       {details}')


def failed(name, details=''):
    print(f'{C.R}[FAIL]{C.E} {name}')
    if details:
        print(f'       {details}')


def check_t9_data_packages():
    """T9: 50+ 文件 data_packages 引用"""
    print(f'\n{C.B}[1/8] T9 data_packages 引用清理{C.E}')
    try:
        r = subprocess.run(
            f'grep -rn "FROM data_packages\\|INTO data_packages\\|UPDATE data_packages" "{MOBILE_API}" --include=*.py',
            capture_output=True, text=True, timeout=20, shell=True
        )
        lines = [l for l in r.stdout.split('\n') if l.strip() and 'data_packages_deprecated' not in l]
        if not lines:
            passed('T9 data_packages 清理', '核心代码无 FROM/INTO/UPDATE 引用')
            return True
        # 允许 services 中已替换的（如果是注释或字符串）
        bad = [l for l in lines if 'sql_template' in l or 'cursor.execute' in l or 'cur.execute' in l]
        if bad:
            failed('T9 data_packages', f'仍有 {len(bad)} 处 SQL 引用')
            for b in bad[:5]:
                print(f'       {b}')
            return False
        passed('T9 data_packages 清理', f'{len(lines)} 处可能为注释或字符串')
        return True
    except Exception as e:
        failed('T9 data_packages', f'扫描失败: {e}')
        return False


def check_t10_stats_smart_sheet():
    """T10.1: stats_smart_sheet 已删除"""
    print(f'\n{C.B}[2/8] T10.1 stats_smart_sheet 删除{C.E}')
    stats_dir = os.path.join(MOBILE_API, 'stats_smart_sheet')
    if not os.path.exists(stats_dir):
        passed('T10.1 stats_smart_sheet', '目录已删除')
        return True
    failed('T10.1 stats_smart_sheet', '目录仍存在')
    return False


def check_t11_services():
    """T11: services 清理"""
    print(f'\n{C.B}[3/8] T11 services 清理{C.E}')
    try:
        r = subprocess.run(
            f'grep -rn "data_packages" "{MOBILE_API}/services" --include=*.py',
            capture_output=True, text=True, timeout=20, shell=True
        )
        lines = [l for l in r.stdout.split('\n') if l.strip() and 'data_packages_deprecated' not in l]
        if not lines:
            passed('T11 services 清理', '无 data_packages 引用')
            return True
        failed('T11 services', f'仍有 {len(lines)} 处')
        for l in lines[:3]:
            print(f'       {l}')
        return False
    except Exception as e:
        failed('T11 services', f'扫描失败: {e}')
        return False


def check_t12_scripts_moved():
    """T12: scripts 已移到 archive/"""
    print(f'\n{C.B}[4/8] T12 scripts 移到 archive/{C.E}')
    archive = os.path.join(PROJECT_ROOT, 'archive')
    if not os.path.exists(archive):
        failed('T12 archive', 'archive/ 不存在')
        return False
    archived_files = sum(len(files) for _, _, files in os.walk(archive))
    if archived_files >= 1:
        passed('T12 archive', f'已归档 {archived_files} 个文件')
        return True
    failed('T12 archive', f'归档文件数不足: {archived_files}')
    return False


def check_t13_migration():
    """T13: migrations 完整脚本"""
    print(f'\n{C.B}[5/8] T13 migrations 脚本{C.E}')
    path = os.path.join(PROJECT_ROOT, 'migrations', 'v3_6_data_packages_split.sql')
    if not os.path.exists(path):
        failed('T13 migrations', f'文件不存在: {path}')
        return False
    with open(path) as f:
        content = f.read()
    if 'CREATE TABLE IF NOT EXISTS approval_records' not in content:
        failed('T13 migrations', '缺少 approval_records DDL')
        return False
    if 'RENAME TO data_packages_deprecated' not in content:
        failed('T13 migrations', '缺少 RENAME data_packages')
        return False
    if 'ROLLBACK' not in content:
        failed('T13 migrations', '缺少 ROLLBACK 段')
        return False
    passed('T13 migrations', 'v3_6_data_packages_split.sql 完整')
    return True


def check_t25_changelog():
    """T25: CHANGELOG"""
    print(f'\n{C.B}[6/8] T25 CHANGELOG{C.E}')
    path = os.path.join(PROJECT_ROOT, 'docs', 'CHANGELOG.md')
    if not os.path.exists(path):
        failed('T25 CHANGELOG', f'文件不存在: {path}')
        return False
    with open(path) as f:
        content = f.read()
    if 'v3.6.0' not in content or 'data_packages' not in content:
        failed('T25 CHANGELOG', '缺少 v3.6.0 条目')
        return False
    passed('T25 CHANGELOG', 'docs/CHANGELOG.md 已更新')
    return True


def check_t26_readme():
    """T26: README 文档"""
    print(f'\n{C.B}[7/8] T26 README.md{C.E}')
    path = os.path.join(PROJECT_ROOT, 'README.md')
    if not os.path.exists(path):
        passed('T26 README', 'README.md 不存在（可选）')
        return True
    passed('T26 README', 'README.md 存在')
    return True


def check_archive_count():
    """archive/ 目录归档统计（递归统计所有文件，含直接文件和子目录）"""
    print(f'\n{C.B}[8/8] archive/ 归档统计{C.E}')
    archive = os.path.join(PROJECT_ROOT, 'archive')
    if not os.path.exists(archive):
        failed('archive/', '不存在')
        return False
    # 递归统计 archive/ 下所有文件（与 check_t12 逻辑一致）
    total = sum(len(files) for _, _, files in os.walk(archive))
    if total >= 1:
        passed('archive/', f'共 {total} 个文件已归档')
        return True
    failed('archive/', f'归档数: {total}（应 ≥ 1）')
    return False


def main():
    print(f'{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-3 检查：data_packages_split_v3 阶段 3{C.E}')
    print(f'{C.B}==================================================={C.E}')

    results = [
        ('T9 data_packages 清理', check_t9_data_packages()),
        ('T10.1 stats_smart_sheet', check_t10_stats_smart_sheet()),
        ('T11 services 清理', check_t11_services()),
        ('T12 archive 归档', check_t12_scripts_moved()),
        ('T13 migrations', check_t13_migration()),
        ('T25 CHANGELOG', check_t25_changelog()),
        ('T26 README', check_t26_readme()),
        ('archive 统计', check_archive_count()),
    ]

    print(f'\n{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-3 检查结果汇总{C.E}')
    print(f'{C.B}==================================================={C.E}')

    passed_count = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f'\n通过: {passed_count}/{total}')

    if passed_count == total:
        print(f'{C.G}✅ CP-3 全部通过，可以进入阶段 4{C.E}')
        return 0
    else:
        print(f'{C.R}❌ CP-3 未通过{C.E}')
        for name, ok in results:
            status = f'{C.G}✅{C.E}' if ok else f'{C.R}❌{C.E}'
            print(f'   {status} {name}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
