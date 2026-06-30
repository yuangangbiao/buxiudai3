"""
检查 MySQL dispatch_center 相关表的列完整性
"""
import os, sys, json

MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD'),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
}

TABLES = {
    'dispatch_rules': [
        'rule_key', 'rule_value', 'updated_at',
    ],
    'flow_matching_rules': [
        'id', 'name', 'match_field', 'match_value', 'flow_type',
        'priority', 'enabled', 'created_at', 'updated_at',
    ],
    'flow_templates': [
        'id', 'name', 'category', 'channels_json', 'title',
        'content', 'receivers_json', 'sort_order', 'is_default',
        'created_at', 'updated_at',
    ],
    'message_history': [
        'id', 'msg_id', 'template_id', 'content_preview',
        'channels_json', 'receivers_json', 'results_json', 'errors_json',
        'sent_at',
    ],
    'material_requirements': [
        'id', 'work_order_no', 'material_id', 'material_name', 'spec',
        'required_qty', 'prepared_qty', 'shortage_qty', 'unit', 'status',
        'source', 'remark', 'created_at', 'updated_at',
    ],
}

print('=' * 60)
print('MySQL 表列完整性检查')
print('=' * 60)
print(f'Host: {MYSQL_CFG["host"]}:{MYSQL_CFG["port"]}')
print(f'Database: {MYSQL_CFG["database"]}')
print(f'User: {MYSQL_CFG["user"]}')
print()

if not MYSQL_CFG['password']:
    print('[WARN] MYSQL_PASSWORD 环境变量未设置，尝试无密码连接...')

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print('[FAIL] 请先安装 pymysql: pip install pymysql')
    sys.exit(1)

try:
    conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=5)
    c = conn.cursor()
    print('[OK] MySQL 连接成功\n')
except Exception as e:
    print(f'[FAIL] MySQL 连接失败: {e}')
    sys.exit(1)

all_ok = True

for table_name, expected_cols in TABLES.items():
    print(f'--- {table_name} ---')
    try:
        c.execute(f"SHOW COLUMNS FROM {table_name}")
        actual_cols = {row['Field'] for row in c.fetchall()}
        expected_set = set(expected_cols)
        actual_set = actual_cols

        missing = expected_set - actual_set
        extra = actual_set - expected_set

        if missing:
            all_ok = False
            print(f'  [FAIL] 缺失列 ({len(missing)}):')
            for col in sorted(missing):
                print(f'         - {col}')
        else:
            print(f'  [OK] 所有列完整 ({len(actual_set)} 列)')

        if extra:
            print(f'  [INFO] 额外列 ({len(extra)}): {", ".join(sorted(extra))}')
        print()
    except pymysql.err.ProgrammingError as e:
        all_ok = False
        print(f'  [FAIL] 表不存在: {e}')
        print()

# 额外检查：production_orders 和 orders（外部表，仅列出字段供参考）
for ext_table in ['production_orders', 'orders']:
    try:
        c.execute(f"SHOW COLUMNS FROM {ext_table}")
        cols = [row['Field'] for row in c.fetchall()]
        print(f'--- {ext_table} (外部表) ---')
        print(f'  列 ({len(cols)}): {", ".join(cols)}')
        print()
    except pymysql.err.ProgrammingError:
        print(f'--- {ext_table} ---')
        print(f'  [INFO] 表不存在（可能由其他模块创建）')
        print()

conn.close()

print('=' * 60)
if all_ok:
    print('结论: 所有调度中心 MySQL 表列完整，无缺失！')
else:
    print('结论: 存在缺失列，请根据上面 [FAIL] 提示补充')
print('=' * 60)
