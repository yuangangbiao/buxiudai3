import os, re, sys

project_root = r'D:\yuan\不锈钢网带跟单3.0'

exclude_dirs = {'.git', '__pycache__', 'node_modules', '.sandbox_pkgs', '.venv', 'venv', 'env', '.idea', '.vscode', '归档备份'}
check_exts = {'.py', '.js', '.ts', '.html', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.bat', '.ps1', '.sh', '.env', '.example', '.txt', '.md'}

patterns = [
    (r'[A-Za-z]:\\[^\\\n\'\"\s)]+', 'Windows absolute path (backslash)'),
    (r'/home/[^/\n\'\"\s)]+', 'Unix /home/ path'),
    (r'/root/[^/\n\'\"\s)]+', 'Unix /root/ path'),
    (r'/Users/[^/\n\'\"\s)]+', 'macOS /Users/ path'),
    (r'/tmp/[^/\n\'\"\s)]+', 'Unix /tmp/ path'),
    (r'/var/[^/\n\'\"\s)]+', 'Unix /var/ path'),
    (r'/etc/[^/\n\'\"\s)]+', 'Unix /etc/ path'),
]

results = []
total_files = 0
skipped_binary = 0

for dirpath, dirnames, filenames in os.walk(project_root):
    parts = dirpath.replace('\\', '/').split('/')
    if any(d in parts for d in exclude_dirs):
        continue
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    
    for f in filenames:
        ext = os.path.splitext(f)[1].lower()
        if ext not in check_exts:
            continue
        
        filepath = os.path.join(dirpath, f)
        relpath = os.path.relpath(filepath, project_root)
        total_files += 1
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
                content = fh.read()
        except Exception:
            skipped_binary += 1
            continue
        
        for pattern, desc in patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                matched_text = match.group()
                results.append((relpath, line_num, matched_text, desc))

output = []
output.append(f'Scanned: {total_files} files')
output.append(f'Skipped (binary): {skipped_binary}')
output.append(f'Matches found: {len(results)}')
output.append('')

if not results:
    output.append('No hardcoded absolute paths found!')
else:
    by_file = {}
    for r in results:
        by_file.setdefault(r[0], []).append(r)

    for filepath in sorted(by_file.keys()):
        items = by_file[filepath]
        for r in items:
            output.append(f'{r[0]}:{r[1]}  [{r[3]}]  {r[2][:150]}')

    output.append('')
    output.append(f'Total files with hardcoded paths: {len(by_file)}')
    output.append(f'Total matches: {len(results)}')

out_path = r'D:\yuan\不锈钢网带跟单3.0\scripts\tools\absolute_paths_scan_result.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print('Results written to: ' + out_path)
for line in output:
    print(line)
