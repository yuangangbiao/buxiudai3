# -*- coding: utf-8 -*-
"""
[C 方案 C.3] 验证 6 个核心生产文件的 data_packages 实际调用路径
策略：用 ast 模块静态分析每个文件的调用链
"""
import os
import ast
import re
from collections import defaultdict

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

# 6 个核心生产文件
CORE_FILES = [
    'container_center_api.py',
    'api/process.py',
    'api/process_v2.py',
    'api/quality_inspection.py',
    'dispatch_center/_core.py',
    'sync_bridge.py',
    'wechat_work_bot_bp.py',
    'api/legacy_routes.py',
    'api/report_record_admin.py',
    'app.py',
    'container_center/v5_compatible_client.py',
    'standalone_dispatch_server.py',
    'storage/mysql_storage.py',
]


def analyze_file(path):
    """分析单文件：找所有 SQL 含 data_packages 的位置"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # 跳过注释
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        # 跳过空行
        if not stripped:
            continue

        # 找 SQL 中的 data_packages
        if 'data_packages' in line and 'data_packages_deprecated' not in line:
            # 区分是注释还是代码
            # 如果行内有 .execute / SELECT / FROM / INTO / UPDATE / JOIN / cur.execute / cursor.execute
            is_sql = any(kw in line for kw in [
                '.execute', 'SELECT', 'FROM', 'INTO', 'UPDATE', 'JOIN',
                'cur.', 'cursor.', 'sql', 'SQL'
            ])
            is_comment = line.lstrip().startswith('#') or '"""' in line[:20]
            severity = '🟡 注释' if is_comment else ('🔴 SQL' if is_sql else '🟠 字符串')

            issues.append({
                'line': i,
                'content': line.strip()[:120],
                'severity': severity,
            })

    return issues


def main():
    print('===== C.3 核心生产文件 data_packages 实际调用路径分析 =====\n')

    summary = []
    for rel in CORE_FILES:
        path = os.path.join(MOBILE_API, rel)
        if not os.path.exists(path):
            print(f'⚠️ 不存在: {rel}')
            continue
        issues = analyze_file(path)
        sql_count = sum(1 for i in issues if 'SQL' in i['severity'])
        comment_count = sum(1 for i in issues if '注释' in i['severity'])
        str_count = sum(1 for i in issues if '字符串' in i['severity'])

        summary.append({
            'file': rel,
            'total': len(issues),
            'sql': sql_count,
            'comment': comment_count,
            'str': str_count,
            'issues': issues,
        })

        status = '🟢 无' if not issues else f'🔴 {sql_count} SQL | 🟡 {comment_count} 注释'
        print(f'📄 {rel}: {status}')

    # 输出重点文件详情
    print(f'\n===== 核心 SQL 调用详情（必须修改）=====\n')
    for s in summary:
        if s['sql'] > 0:
            print(f'📄 {s["file"]} ({s["sql"]} 处 SQL):')
            for iss in s['issues']:
                if 'SQL' in iss['severity']:
                    print(f'   L{iss["line"]}: {iss["content"]}')
            print()

    # 输出决策矩阵
    print(f'\n===== 决策矩阵 =====')
    print(f'{"文件":<45} {"SQL":<6} {"注释":<6} {"策略":<10}')
    print('-' * 80)
    for s in summary:
        if s['sql'] > 0:
            strategy = '🔴 必须改'
        elif s['comment'] > 0:
            strategy = '🟡 清理注释'
        else:
            strategy = '🟢 不动'
        print(f'{s["file"]:<45} {s["sql"]:<6} {s["comment"]:<6} {strategy}')


if __name__ == '__main__':
    main()
