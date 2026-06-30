# -*- coding: utf-8 -*-
"""扫描项目中的所有 CREATE TABLE 语句，提取表结构"""
import re, os

REPO = r'd:\yuan\不锈钢网带跟单3.0'

def extract_tables_from_file(filepath):
    tables = []
    try:
        with open(filepath, encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return tables

    pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(content):
        table_name = m.group(1)
        start = m.end()
        depth = 0
        end = start
        for i in range(start, len(content)):
            c = content[i]
            if c == '(':
                depth += 1
            elif c == ')':
                if depth == 0:
                    end = i
                    break
                depth -= 1
        ddl_body = content[m.start():end+1].strip()
        tables.append((table_name, ddl_body, filepath))
    return tables

def parse_columns(ddl_body):
    """从 DDL body 解析字段列表"""
    inner = ddl_body.strip()
    if inner.startswith('('):
        inner = inner[1:]
    if inner.endswith(')'):
        inner = inner[:-1]

    lines = []
    current = ''
    depth = 0
    for ch in inner:
        if ch == '(':
            depth += 1
            current += ch
        elif ch == ')':
            depth -= 1
            current += ch
        elif ch == '\n':
            if current.strip():
                lines.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        lines.append(current.strip())

    fields = []
    skip_starts = ('KEY ', 'INDEX ', 'CONSTRAINT', 'PRIMARY ', 'FOREIGN ',
                   'UNIQUE ', 'ENGINE=', 'CHARSET=', 'AUTO_INCREMENT',
                   'DEFAULT CHARSET', 'COLLATE ', 'PARTITION')

    for line in lines:
        raw = line.strip().rstrip(',').strip()
        if not raw:
            continue
        if raw.startswith('--') or raw.startswith('#'):
            continue
        upper = raw.upper()
        if any(upper.startswith(s.upper()) for s in skip_starts):
            continue

        type_keywords = {'INT', 'VARCHAR', 'CHAR', 'TEXT', 'BLOB', 'DATE', 'DATETIME',
                         'TIMESTAMP', 'DOUBLE', 'DECIMAL', 'FLOAT', 'BIGINT', 'SMALLINT',
                         'TINYINT', 'JSON', 'ENUM', 'SET', 'BOOL', 'MEDIUMINT', 'REAL',
                         'NUMERIC', 'SERIAL'}
        if not any(kw in upper for kw in type_keywords):
            continue

        field_clean = re.sub(r'^[`"\[]|[`"\]]$', '', raw).strip()
        parts = re.split(r'\s+', field_clean, maxsplit=1)
        field_name = parts[0]
        rest = parts[1] if len(parts) >= 2 else ''

        # 提取 TYPE（到第一个 ATTR 关键字前）
        TYPE_END_KEYWORDS = ('NOT', 'NULL', 'DEFAULT', 'COMMENT', 'AUTO_INCREMENT',
                             'UNIQUE', 'PRIMARY', 'CHECK', 'COLLATE')
        type_parts = rest.split()
        field_type = rest
        for kw in TYPE_END_KEYWORDS:
            for i, tok in enumerate(type_parts):
                if tok.upper() == kw:
                    field_type = ' '.join(type_parts[:i])
                    break
            else:
                continue
            break

        # nullable
        raw_upper = raw.upper()
        if 'NOT NULL' in raw_upper:
            nullable = 'NO'
        elif ' NULL ' in raw_upper or raw_upper.endswith(' NULL'):
            nullable = 'YES'
        else:
            nullable = 'YES'

        # default
        default = ''
        m_def = re.search(r'DEFAULT\s+([^\s,]+|[\'"][^\'"]*[\'"])', raw, re.IGNORECASE)
        if m_def:
            default = m_def.group(1).strip("'\"")

        # comment
        comment = ''
        m_cmt = re.search(r"COMMENT\s+['\"]([^'\"]+)['\"]", raw, re.IGNORECASE)
        if m_cmt:
            comment = m_cmt.group(1)

        fields.append({
            'field': field_name,
            'type': field_type,
            'nullable': nullable,
            'default': default,
            'comment': comment,
        })
    return fields

def format_markdown(table_name, fields, source_file):
    md = [f'### {table_name}\n']
    md.append(f'**来源**: `{os.path.basename(source_file)}`\n')
    if fields:
        md.append('\n| 字段 | 类型 | 允许空 | 默认值 | 说明 |\n|------|------|--------|--------|------|')
        for f in fields:
            md.append(f"| {f['field']} | {f['type']} | {f['nullable']} | {f['default']} | {f['comment']} |")
    return '\n'.join(md)

SCAN_DIRS = [
    os.path.join(REPO, 'mobile_api_ai', 'dispatch_center'),
    os.path.join(REPO, 'mobile_api_ai', 'models'),
    os.path.join(REPO, 'mobile_api_ai', 'storage'),
    os.path.join(REPO, 'mobile_api_ai', 'migrations'),
    os.path.join(REPO, 'mobile_api_ai', 'sync'),
    os.path.join(REPO, 'mobile_api_ai', 'container_center'),
    os.path.join(REPO, 'mobile_api_ai', 'inventory_web'),
    os.path.join(REPO, 'scripts', 'migrations'),
    os.path.join(REPO, 'scripts', 'tools'),
]
SKIP_DIRS = {'backup', '__pycache__', '_archive', 'remote_backups',
             'field_sync_backups', 'debug', 'node_modules'}
SKIP_TABLES = {'table_name', 'sqlite_'}

all_tables = {}
for scan_dir in SCAN_DIRS:
    if not os.path.isdir(scan_dir):
        continue
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if not (fname.endswith('.py') or fname.endswith('.sql')):
                continue
            fpath = os.path.join(root, fname)
            for tname, ddl, src in extract_tables_from_file(fpath):
                if tname in SKIP_TABLES:
                    continue
                if tname not in all_tables:
                    all_tables[tname] = (ddl, src)
                else:
                    pass

print(f"找到 {len(all_tables)} 个不同的表:")
for tname in sorted(all_tables.keys()):
    src = os.path.basename(all_tables[tname][1])
    print(f"  {tname} ({src})")

header = [
    '# 数据库字典\n',
    '\n**生成时间**: 2026-06-20\n',
    '**来源**: 代码中 CREATE TABLE 语句扫描（SQL/Python DDL）\n',
    '**说明**: 本文档由 scan_ddl.py 自动生成，如有出入请以实际 DDL 文件为准\n',
    '\n---\n',
]
output_parts = [''.join(header)]

for tname in sorted(all_tables.keys()):
    ddl, src = all_tables[tname]
    fields = parse_columns(ddl)
    output_parts.append(format_markdown(tname, fields, src))
    output_parts.append('\n---\n')

out_file = os.path.join(REPO, 'docs', 'db_dict_dispatch_center.md')
with open(out_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_parts))

print(f"\n已写入: {out_file}")
print(f"表数量: {len(all_tables)}")
