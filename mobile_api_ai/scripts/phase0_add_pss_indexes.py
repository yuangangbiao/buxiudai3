# -*- coding: utf-8 -*-
"""
Phase 0: 添加 process_sub_steps 复合索引
执行前请确保：
1. pt-osc 可用（如使用 pt-osc 方案）
2. 在低峰期执行
3. 有备份

用法:
    py -3 scripts/phase0_add_pss_indexes.py [--dry-run]
"""
import sys
import os

import pymysql
import argparse


def get_mysql_cfg():
    """从 .env 文件获取 MySQL 配置（与 core/_config_infra.py 保持一致）"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    env = {}
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()

    host = env.get('MYSQL_HOST', 'localhost')
    port = int(env.get('MYSQL_PORT', '3306'))
    user = env.get('MYSQL_USER', 'root')
    password = env.get('MYSQL_PASSWORD', '')
    database = env.get('CONTAINER_MYSQL_DATABASE', 'container_center')
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
        'charset': 'utf8mb4',
    }, 10  # timeout


def check_existing_indexes(conn, table_name, db_name):
    """检查现有索引"""
    cur = conn.cursor()
    cur.execute("""
        SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, NON_UNIQUE
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """, (db_name, table_name))

    rows = cur.fetchall()
    index_map = {}
    for row in rows:
        idx_name, col, seq, non_unique = row
        if idx_name not in index_map:
            index_map[idx_name] = {'columns': [], 'unique': non_unique == 0}
        index_map[idx_name]['columns'].append(col)
    return index_map


def explain_query(conn, sql, params):
    """EXPLAIN 查询，分析索引使用情况"""
    cur = conn.cursor()
    cur.execute(f"EXPLAIN {sql}", params)
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))


def add_index_idempotent(conn, table_name, index_name, columns, index_type=''):
    """幂等添加索引"""
    cur = conn.cursor()

    exists = cur.execute("""
        SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        LIMIT 1
    """, (table_name, index_name))

    if exists:
        print(f"  ⏭️  索引 {index_name} 已存在，跳过")
        return False

    col_list = ', '.join(f'`{c}`' for c in columns)
    sql = f"ALTER TABLE `{table_name}` ADD {'UNIQUE ' if index_type == 'UNIQUE' else ''}INDEX `{index_name}` ({col_list})"
    print(f"  ➕ 执行: {sql}")
    cur.execute(sql)
    print(f"  ✅ 索引 {index_name} 创建成功")
    return True


def main():
    parser = argparse.ArgumentParser(description='Phase 0: 添加 process_sub_steps 复合索引')
    parser.add_argument('--dry-run', action='store_true', help='仅检查，不执行')
    parser.add_argument('--use-ptosc', action='store_true', help='使用 pt-online-schema-change')
    args = parser.parse_args()

    dry_run = args.dry_run

    try:
        cfg, timeout = get_mysql_cfg()
        print(f"📦 连接 MySQL: {cfg['host']}:{cfg['port']}/{cfg['database']}")
        conn = pymysql.connect(**cfg, connect_timeout=timeout)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ 无法连接 MySQL: {e}")
        print("💡 请确保 MySQL 服务正在运行")
        return

    try:
        db_name = cfg['database']
        table = 'process_sub_steps'

        print(f"\n{'='*60}")
        print(f"Phase 0: 添加 process_sub_steps 索引")
        print(f"{'='*60}\n")

        existing = check_existing_indexes(conn, table, db_name)
        print("📋 现有索引:")
        for idx_name, info in existing.items():
            cols = ', '.join(info['columns'])
            uniq = '(UNIQUE)' if info['unique'] else ''
            print(f"  - {idx_name} {uniq}: ({cols})")

        target_queries = [
            {
                'name': 'idx_order_step_qty',
                'columns': ['order_no', 'step_name', 'quantity'],
                'sql': "SELECT COALESCE(SUM(quantity), 0) FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND quantity>0",
                'params': ('ORD-202604210001', '焊接'),
                'desc': 'completed_qty 实时汇总查询'
            },
            {
                'name': 'idx_order_step_code',
                'columns': ['order_no', 'step_name', 'process_code'],
                'sql': "SELECT * FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND process_code=%s LIMIT 1",
                'params': ('ORD-202604210001', '焊接', 'P01'),
                'desc': '去重键覆盖索引'
            },
        ]

        print("\n📊 查询计划分析（加索引前）:")
        for q in target_queries:
            plan = explain_query(conn, q['sql'], q['params'])
            print(f"\n  [{q['name']}] {q['desc']}")
            print(f"  SQL: {q['sql']}")
            print(f"  EXPLAIN: type={plan.get('type','?')} key={plan.get('key','?')} rows={plan.get('rows','?')}")

        if dry_run:
            print("\n🟡 DRY-RUN 模式: 不执行任何更改")
            return

        print(f"\n{'='*60}")
        print("🔧 开始添加索引（幂等）")
        print(f"{'='*60}")

        added = []
        for q in target_queries:
            print(f"\n处理索引: {q['name']}")
            if add_index_idempotent(conn, table, q['name'], q['columns']):
                added.append(q['name'])

        if added:
            conn.commit()
            print(f"\n✅ 提交成功: {', '.join(added)}")
        else:
            print("\n⏭️  所有索引已存在，无更改")

        print("\n📊 查询计划验证（加索引后）:")
        for q in target_queries:
            plan = explain_query(conn, q['sql'], q['params'])
            key_used = plan.get('key', '?')
            idx_status = '✅ 索引命中' if key_used == q['name'] else f'⚠️ key={key_used}'
            print(f"\n  [{q['name']}] {idx_status}")
            print(f"  EXPLAIN: type={plan.get('type','?')} key={key_used} rows={plan.get('rows','?')}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 错误: {e}")
        raise
    finally:
        conn.close()
        print("\n🔌 连接已关闭")


if __name__ == '__main__':
    main()
