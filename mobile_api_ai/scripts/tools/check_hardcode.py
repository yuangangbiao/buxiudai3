"""容器中心 & 调度中心 硬代码/规范检查"""

import re
import sys
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent

TARGET_FILES = [
    'dispatch_center.py',
    'container_center_api.py',
    'container_center/__init__.py',
    'container_center/client/__init__.py',
    'container_center/client/container_client.py',
    'container_center/services/alert_engine.py',
    'container_center/storage/document_store.py',
    'container_center/storage/config_store.py',
    'container_center/storage/alert_store.py',
    'container_center/storage/router.py',
    'container_center/api/documents.py',
    'container_center/api/configs.py',
    'container_center/api/alerts.py',
    'container_center/api/health.py',
]

results = []
errors = []

def check(label, condition, detail=''):
    status = 'OK' if condition else 'FAIL'
    results.append((status, label, detail))
    if not condition:
        errors.append(label)

def check_file(filepath):
    if not filepath.exists():
        return None
    return filepath.read_text('utf-8', errors='replace')

def scan_ip_hardcode(text, name):
    """扫描硬编码 IP 地址"""
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
    # 过滤常见非硬编码 IP
    allowed = {'0.0.0.0', '127.0.0.1', '255.255.255.255'}
    hardcoded = [ip for ip in ips if ip not in allowed]
    check(f'[{name}] 无硬编码 IP ({len(hardcoded)} 个)', len(hardcoded) == 0,
          f'发现: {hardcoded}' if hardcoded else '')

def scan_url_hardcode(text, name):
    """扫描硬编码 URL (含端口)"""
    urls = re.findall(r'https?://[^\s"\'`<>)]+', text)
    # 允许 localhost 和 127.0.0.1
    allowed_patterns = ['localhost', '127.0.0.1', 'example.com']
    hardcoded = [u for u in urls if not any(p in u for p in allowed_patterns)]
    check(f'[{name}] 无硬编码外部 URL ({len(hardcoded)} 个)', len(hardcoded) == 0,
          f'发现: {hardcoded}' if hardcoded else '')

def scan_password(text, name):
    """扫描硬编码密码/key"""
    patterns = [
        r'["\']password["\']\s*[:=]\s*["\'][^"\']+["\']',
        r'["\']api_key["\']\s*[:=]\s*["\'][^"\']+["\']',
        r'["\']secret["\']\s*[:=]\s*["\'][^"\']+["\']',
        r'os\.getenv\([^)]+,\s*["\'][^"\']+["\']\)',
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    check(f'[{name}] 无硬编码密码/密钥 ({len(found)} 处)', len(found) == 0,
          f'发现: {found}' if found else '')

def scan_hardcoded_path(text, name):
    """扫描硬编码文件路径"""
    patterns = [
        r'["\'](?:[A-Za-z]:\\[^"\']+)["\']',
        r'["\'](?:/data/|/app/|/home/|/root/|/var/)[^"\']+["\']',
        r'open\(["\'][^"\']+["\']\)',
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, text)
        found.extend(m for m in matches if 'BASE_DIR' not in m and 'os.path.' not in m and '__file__' not in m)
    check(f'[{name}] 无硬编码路径 ({len(found)} 处)', len(found) == 0,
          f'发现: {found}' if found else '')

def scan_hardcoded_port(text, name):
    """扫描硬编码端口号"""
    ports = re.findall(r':(\d{4,5})["\'/\s]', text)
    allowed_ports = {'5000', '5001', '5002', '5003', '5004', '5005', '8080', '443', '8443'}
    hardcoded = [p for p in ports if p not in allowed_ports]
    # 也检查 5000-5005 等端口是否在 URL 中硬编码
    url_ports = re.findall(r':(500[0-9])', text)
    check(f'[{name}] 无硬编码端口 ({len(hardcoded)} 个非标准)', len(hardcoded) == 0,
          f'发现: {hardcoded}' if hardcoded else '')

def scan_print_statements(text, name):
    """扫描 print 语句"""
    lines = text.split('\n')
    prints = [f'L{i+1}' for i, l in enumerate(lines)
              if l.strip().startswith('print(') and '# noqa' not in l]
    check(f'[{name}] 无 print 调试 ({len(prints)} 处)', len(prints) == 0,
          f'发现: {prints}' if prints else '')

def scan_bare_except(text, name):
    """扫描裸 except"""
    lines = text.split('\n')
    bare = [f'L{i+1}: {l.strip()}' for i, l in enumerate(lines)
            if re.match(r'^\s*except\s*:', l) or re.match(r'^\s*except\s*$', l)]
    check(f'[{name}] 无裸 except ({len(bare)} 处)', len(bare) == 0,
          f'发现: {bare}' if bare else '')

def scan_hardcoded_threshold(text, name):
    """扫描硬编码阈值"""
    patterns = [
        r'TIMEOUT\s*=\s*\d{2,}',
        r'MAX_CONNECTIONS\s*=\s*\d+',
        r'RETRY_LIMIT\s*=\s*\d+',
        r'timeout\s*=\s*\d+',
        r'max_retries\s*=\s*\d+',
        r'limit=\d{3,}',
        r'size=\d{3,}',
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, text)
        found.extend(matches)
    check(f'[{name}] 阈值管理 ({len(found)} 处)', True,
          f'阈值: {found}' if found else '无明确阈值')

def scan_sys_path(text, name):
    """扫描 sys.path 重复插入"""
    count = len(re.findall(r'sys\.path\.(insert|append)', text))
    check(f'[{name}] sys.path 管理 ({count} 次)', count <= 1,
          f'sys.path 操作 {count} 次' if count > 1 else '')

def scan_hardcoded_color(text, name):
    """扫描硬编码颜色值"""
    colors = re.findall(r'#[0-9a-fA-F]{3,6}', text)
    check(f'[{name}] 颜色值 ({len(colors)} 处)', True,
          f'颜色: {colors[:10]}...' if colors else '')

def scan_hardcoded_db_config(text, name):
    """扫描数据库硬编码配置"""
    patterns = [
        r'host\s*=\s*["\'][^"\']+["\']',
        r'port\s*=\s*\d{4,5}',
        r'database\s*=\s*["\'][^"\']+["\']',
        r'db_name\s*=\s*["\'][^"\']+["\']',
        r'user\s*=\s*["\'][^"\']+["\']',
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, text)
        found.extend(matches)
    check(f'[{name}] 数据库配置方式', True,
          f'配置项: {found}' if found else '无或从环境变量读取')

def scan_magic_number(text, name):
    """扫描魔术数字"""
    lines = text.split('\n')
    found = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('import') or stripped.startswith('from'):
            continue
        nums = re.findall(r'\b(?:if|elif|return|==|!=)\s+(\d{3,})\b', stripped)
        for n in nums:
            found.append(f'L{i+1}: {stripped[:80]}')
    check(f'[{name}] 魔术数字检查 ({len(found)} 处)', len(found) == 0,
          f'发现: {found[:5]}' if found else '')


def main():
    print('=' * 60)
    print('  容器中心 & 调度中心 硬代码/规范检查')
    print('=' * 60)
    print()

    for rel in TARGET_FILES:
        fp = BASE / rel
        name = f'[container]' if 'container' in rel else '[dispatch]' if 'dispatch' in rel else f'[{rel}]'
        text = check_file(fp)
        if text is None:
            print(f'  - {rel}: 文件不存在，跳过')
            print()
            continue
        print(f'--- {rel} ({len(text)} chars) ---')
        scan_ip_hardcode(text, name)
        scan_url_hardcode(text, name)
        scan_password(text, name)
        scan_hardcoded_path(text, name)
        scan_hardcoded_port(text, name)
        scan_print_statements(text, name)
        scan_bare_except(text, name)
        scan_hardcoded_threshold(text, name)
        scan_sys_path(text, name)
        scan_hardcoded_color(text, name)
        scan_hardcoded_db_config(text, name)
        scan_magic_number(text, name)
        print()

    # 前端文件额外检查
    print('--- 前端静态文件 ---')
    frontend_files = [
        ('dispatch_center.html', BASE / 'templates' / 'dispatch_center.html'),
        ('dispatch_center.js', BASE / 'static' / 'js' / 'dispatch_center.js'),
        ('dispatch_center.css', BASE / 'static' / 'css' / 'dispatch_center.css'),
    ]
    for name, fp in frontend_files:
        text = check_file(fp)
        if text is None:
            print(f'  - {name}: 文件不存在，跳过')
            continue
        print(f'  [{name}] ({len(text)} chars)')
        scan_ip_hardcode(text, f'[{name}]')
        scan_url_hardcode(text, f'[{name}]')
        scan_hardcoded_port(text, f'[{name}]')
        scan_hardcoded_color(text, f'[{name}]')
        print()

    # 汇总
    print('=' * 60)
    print(f'  检查结果汇总')
    print('=' * 60)
    ok_count = sum(1 for s, _, _ in results if s == 'OK')
    fail_count = sum(1 for s, _, _ in results if s == 'FAIL')
    print(f'  通过: {ok_count}  |  失败: {fail_count}  |  总计: {len(results)}')
    print()

    if errors:
        print('--- 需要修复的问题 ---')
        for e in errors:
            for s, label, detail in results:
                if s == 'FAIL' and label == e:
                    print(f'  {label}: {detail}')
                    break
        print()
        print(f'共 {len(errors)} 个问题需要处理')
        return 1
    else:
        print('全部检查通过!')
        return 0

if __name__ == '__main__':
    sys.exit(main())
