"""对比多个 wechat_container.db 数据库文件"""
import sqlite3
import os
from datetime import datetime

DB_FILES = [
    r'D:\yuan\不锈钢网带跟单3.0\wechat_container.db',
    r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db',
    r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\wechat_container.db',
]

def get_db_info(db_path):
    """获取数据库信息"""
    info = {
        'path': db_path,
        'exists': os.path.exists(db_path),
        'size': 0,
        'tables': {},
        'record_counts': {},
        'last_modified': None
    }

    if not info['exists']:
        return info

    info['size'] = os.path.getsize(db_path)
    info['last_modified'] = datetime.fromtimestamp(os.path.getmtime(db_path))

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 获取所有表
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        info['tables'] = tables

        # 获取每个表的记录数
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                info['record_counts'][table] = count
            except:
                info['record_counts'][table] = 'ERROR'

        conn.close()
    except Exception as e:
        info['error'] = str(e)

    return info

def main():
    print("=" * 80)
    print("数据库文件对比")
    print("=" * 80)

    all_infos = []
    for db_path in DB_FILES:
        info = get_db_info(db_path)
        all_infos.append(info)

    # 1. 基本信息对比
    print("\n【1. 文件基本信息】")
    print("-" * 80)
    print(f"{'路径':<60} {'大小':>12} {'修改时间':<20}")
    print("-" * 80)
    for info in all_infos:
        if info['exists']:
            size_str = f"{info['size']:,} 字节"
            time_str = info['last_modified'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"{info['path']:<60} {size_str:>12} {time_str:<20}")
        else:
            print(f"{info['path']:<60} {'文件不存在':>12}")

    # 2. 表对比
    print("\n\n【2. 数据库表对比】")
    print("-" * 80)

    all_tables = set()
    for info in all_infos:
        all_tables.update(info['tables'])

    all_tables = sorted(all_tables)

    print(f"{'表名':<30}", end="")
    for info in all_infos:
        short_name = os.path.basename(os.path.dirname(info['path']))
        print(f"{short_name:>20}", end="")
    print()
    print("-" * 80)

    for table in all_tables:
        print(f"{table:<30}", end="")
        for info in all_infos:
            count = info['record_counts'].get(table, '-')
            print(f"{str(count):>20}", end="")
        print()

    # 3. 关键表详细对比
    print("\n\n【3. 关键表详细数据对比】")
    print("-" * 80)

    key_tables = ['process_sub_steps', 'process_records', 'data_packages', 'tasks']

    for table in key_tables:
        if table not in all_tables:
            continue

        print(f"\n>>> 表: {table}")
        print("-" * 60)

        for info in all_infos:
            if table not in info['tables']:
                continue

            short_path = f"{os.path.basename(os.path.dirname(info['path']))}\\{os.path.basename(info['path'])}"
            print(f"\n文件: {short_path}")

            try:
                conn = sqlite3.connect(info['path'])
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # 获取前5条记录
                cur.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 5")
                rows = cur.fetchall()

                if not rows:
                    print("  (空表)")
                else:
                    # 获取列名
                    columns = [desc[0] for desc in cur.description]
                    print(f"  总记录数: {info['record_counts'][table]}")
                    print(f"  最新5条记录:")

                    for row in rows:
                        # 只显示关键字段
                        row_data = dict(row)
                        print(f"    ID={row_data.get('id', '?')}", end="")

                        # 根据表的不同显示不同的字段
                        if table == 'process_sub_steps':
                            print(f" process_id={str(row_data.get('process_id', ''))[:15]}...", end="")
                            print(f" step={row_data.get('step_name', '')}", end="")
                            print(f" qty={row_data.get('quantity', 0)}", end="")
                            print(f" operator={row_data.get('operator', '')}")
                        elif table == 'process_records':
                            print(f" order_no={row_data.get('order_no', '')}", end="")
                            print(f" status={row_data.get('status_key', '')}", end="")
                            print(f" progress={row_data.get('progress', 0)}%")
                        elif table == 'data_packages':
                            print(f" type={row_data.get('data_type', '')}", end="")
                            content = str(row_data.get('content', ''))[:50]
                            print(f" content={content}...")
                        else:
                            # 通用显示
                            for key in list(row_data.keys())[:3]:
                                print(f" {key}={row_data.get(key, '')}", end="")
                            print()

                conn.close()
            except Exception as e:
                print(f"  读取错误: {e}")

    # 4. 总结
    print("\n\n【4. 总结】")
    print("=" * 80)

    # 找到最新最大的数据库
    valid_infos = [i for i in all_infos if i['exists'] and i.get('size', 0) > 0]

    if valid_infos:
        # 按大小排序
        valid_infos.sort(key=lambda x: x['size'], reverse=True)

        print(f"\n📊 数据库文件数量: {len(valid_infos)} 个有效文件")

        print(f"\n🏆 按大小排序:")
        for i, info in enumerate(valid_infos, 1):
            short_path = info['path'].replace('D:\\yuan\\不锈钢网带跟单3.0\\', '')
            print(f"   {i}. {short_path}")
            print(f"      大小: {info['size']:,} 字节")

            # 报工记录数
            if 'process_sub_steps' in info['record_counts']:
                count = info['record_counts']['process_sub_steps']
                print(f"      报工记录: {count} 条")

        print(f"\n💡 建议:")
        print(f"   应该统一使用最大的数据库文件: {valid_infos[0]['path']}")
        print(f"   其他较小的数据库可能是旧的或数据不完整的。")

if __name__ == '__main__':
    main()
