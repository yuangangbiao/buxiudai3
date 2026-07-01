"""详细对比所有 wechat_container.db 数据库"""
import sqlite3
import os
from datetime import datetime

DB_FILES = [
    ('ROOT', r'D:\yuan\不锈钢网带跟单3.0\wechat_container.db'),
    ('MOBILE_AI', r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'),
    ('DATA', r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\wechat_container.db'),
]

def get_db_schema(db_path):
    """获取数据库完整结构"""
    schema = {
        'path': db_path,
        'exists': os.path.exists(db_path),
        'size': 0,
        'tables': {}
    }

    if not schema['exists']:
        return schema

    schema['size'] = os.path.getsize(db_path)
    schema['mtime'] = datetime.fromtimestamp(os.path.getmtime(db_path))

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 获取所有表
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        for table in tables:
            # 获取表结构和数据
            table_info = {
                'columns': [],
                'column_types': {},
                'row_count': 0,
                'sample_data': []
            }

            # 获取列信息
            cur.execute(f"PRAGMA table_info({table})")
            for col in cur.fetchall():
                table_info['columns'].append(col['name'])
                table_info['column_types'][col['name']] = col['type']

            # 获取记录数
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            table_info['row_count'] = cur.fetchone()[0]

            # 获取样例数据（前3条）
            if table_info['row_count'] > 0:
                try:
                    cur.execute(f"SELECT * FROM {table} LIMIT 3")
                    table_info['sample_data'] = [dict(r) for r in cur.fetchall()]
                except:
                    pass

            schema['tables'][table] = table_info

        conn.close()
    except Exception as e:
        schema['error'] = str(e)

    return schema

def main():
    print("=" * 100)
    print(" " * 30 + "数据库详细对比报告")
    print("=" * 100)

    # 读取所有数据库
    schemas = []
    for name, path in DB_FILES:
        print(f"\n读取 {name}...")
        schema = get_db_schema(path)
        schema['name'] = name
        schemas.append(schema)

    # 1. 文件信息
    print("\n" + "=" * 100)
    print("【1. 文件基本信息】")
    print("=" * 100)
    print(f"{'名称':<15} {'路径':<60} {'大小':>12} {'修改时间':<20}")
    print("-" * 107)

    for s in schemas:
        if s['exists']:
            size_str = f"{s['size']:,} B"
            time_str = s['mtime'].strftime('%Y-%m-%d %H:%M:%S') if s.get('mtime') else '-'
            print(f"{s['name']:<15} {s['path']:<60} {size_str:>12} {time_str:<20}")
        else:
            print(f"{s['name']:<15} {'文件不存在':<60}")

    # 2. 表列表对比
    print("\n" + "=" * 100)
    print("【2. 数据库表列表对比】")
    print("=" * 100)

    all_tables = set()
    for s in schemas:
        all_tables.update(s['tables'].keys())

    all_tables = sorted(all_tables)

    print(f"\n{'表名':<30}", end="")
    for s in schemas:
        print(f"{s['name']:>25}", end="")
    print()
    print("-" * 105)

    for table in all_tables:
        print(f"{table:<30}", end="")
        for s in schemas:
            count = s['tables'].get(table, {}).get('row_count', '-')
            print(f"{str(count):>25}", end="")
        print()

    # 3. 关键表详细对比
    key_tables = ['process_sub_steps', 'process_records', 'data_packages', 'tasks', 'products', 'operators']

    print("\n" + "=" * 100)
    print("【3. 关键表结构对比】")
    print("=" * 100)

    for table in key_tables:
        # 检查哪些数据库有此表
        tables_with_it = [s for s in schemas if table in s['tables']]
        if not tables_with_it:
            continue

        print(f"\n>>> 表: {table}")
        print("-" * 100)

        # 列对比
        all_columns = set()
        for s in tables_with_it:
            all_columns.update(s['tables'][table]['columns'])

        all_columns = sorted(all_columns)

        print(f"\n列结构:")
        print(f"{'列名':<25}", end="")
        for s in tables_with_it:
            print(f"{s['name']:>15}", end="")
        print()
        print("-" * 70)

        for col in all_columns:
            print(f"{col:<25}", end="")
            for s in tables_with_it:
                col_type = s['tables'][table]['column_types'].get(col, '-')
                print(f"{col_type:>15}", end="")
            print()

        # 数据对比
        print(f"\n数据样例:")
        for s in tables_with_it:
            print(f"\n  [{s['name']}] {s['path']}")
            samples = s['tables'][table]['sample_data']
            if not samples:
                print("    (无数据)")
            else:
                for i, row in enumerate(samples, 1):
                    print(f"  记录 {i}:")
                    for key, value in row.items():
                        if value is not None and str(value).strip():
                            value_str = str(value)[:50]
                            if len(str(value)) > 50:
                                value_str += "..."
                            print(f"    {key}: {value_str}")

    # 4. 报工表详细对比
    print("\n" + "=" * 100)
    print("【4. process_sub_steps 表详细对比】")
    print("=" * 100)

    for s in schemas:
        if 'process_sub_steps' not in s['tables']:
            continue

        table_info = s['tables']['process_sub_steps']
        print(f"\n>>> [{s['name']}] {s['path']}")
        print(f"    总记录数: {table_info['row_count']}")

        # 最新记录
        try:
            conn = sqlite3.connect(s['path'])
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT id, process_id, step_name, quantity, operator,
                       equipment_name, remark, created_at, batch_no
                FROM process_sub_steps
                ORDER BY id DESC
                LIMIT 5
            """)

            rows = cur.fetchall()
            if rows:
                print(f"\n    最新5条报工记录:")
                print(f"    {'ID':<6} {'工序':<20} {'数量':<8} {'操作员':<10} {'设备':<15} {'时间':<20}")
                print(f"    {'-'*6} {'-'*20} {'-'*8} {'-'*10} {'-'*15} {'-'*20}")

                for row in rows:
                    step = (row['step_name'] or '')[:18]
                    op = (row['operator'] or '')[:8]
                    eq = (row['equipment_name'] or '')[:13]
                    time = (row['created_at'] or '')[:19]
                    print(f"    {row['id']:<6} {step:<20} {row['quantity']:<8} {op:<10} {eq:<15} {time:<20}")

            conn.close()
        except Exception as e:
            print(f"    读取错误: {e}")

    # 5. process_records 表详细对比
    print("\n" + "=" * 100)
    print("【5. process_records 表详细对比】")
    print("=" * 100)

    for s in schemas:
        if 'process_records' not in s['tables']:
            continue

        table_info = s['tables']['process_records']
        print(f"\n>>> [{s['name']}] {s['path']}")
        print(f"    总记录数: {table_info['row_count']}")

        try:
            conn = sqlite3.connect(s['path'])
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT id, order_no, product_name, quantity, progress,
                       status_key, current_step, created_at
                FROM process_records
                ORDER BY id DESC
                LIMIT 5
            """)

            rows = cur.fetchall()
            if rows:
                print(f"\n    最新5条流程记录:")
                print(f"    {'ID':<6} {'工单号':<20} {'产品':<15} {'进度':<8} {'状态':<10} {'当前步骤':<15}")
                print(f"    {'-'*6} {'-'*20} {'-'*15} {'-'*8} {'-'*10} {'-'*15}")

                for row in rows:
                    order = (row['order_no'] or '')[:18]
                    product = (row['product_name'] or '')[:13]
                    status = (row['status_key'] or '')[:8]
                    step = (row['current_step'] or '')[:13]
                    print(f"    {row['id']:<6} {order:<20} {product:<15} {row['progress']:<8} {status:<10} {step:<15}")

            conn.close()
        except Exception as e:
            print(f"    读取错误: {e}")

    # 6. 总结
    print("\n" + "=" * 100)
    print("【6. 对比总结】")
    print("=" * 100)

    print("\n🏆 各数据库报工记录数:")
    for s in schemas:
        if 'process_sub_steps' in s['tables']:
            count = s['tables']['process_sub_steps']['row_count']
            print(f"   {s['name']:<15}: {count} 条")

    print("\n🏆 各数据库流程记录数:")
    for s in schemas:
        if 'process_records' in s['tables']:
            count = s['tables']['process_records']['row_count']
            print(f"   {s['name']:<15}: {count} 条")

    print("\n💡 分析结论:")
    root_schema = next((s for s in schemas if s['name'] == 'ROOT'), None)
    mobile_schema = next((s for s in schemas if s['name'] == 'MOBILE_AI'), None)

    if root_schema and mobile_schema:
        root_count = root_schema['tables'].get('process_sub_steps', {}).get('row_count', 0)
        mobile_count = mobile_schema['tables'].get('process_sub_steps', {}).get('row_count', 0)

        if mobile_count > root_count:
            print(f"   ⚠️  MOBILE_AI 数据库包含更多报工记录 ({mobile_count} vs {root_count})")
            print(f"   ⚠️  这意味着旧的报工数据可能在 mobile_api_ai 目录的数据库中")
            print(f"   💡 建议：将两个数据库合并，或者确认哪个是主数据库")

if __name__ == '__main__':
    main()
