"""R13 历史数据回填: process_records.process_code + orders.salesperson

逻辑:
- process_records.process_code: 从 PROCESS_CODES 标准字典找 process_name,
  没找到再查 process_code_registry, 仍没找到则留空并报告
- orders.salesperson: R13 新字段, 从 operator_logs / updated_by / created_by 反查,
  实在找不到填 '未知' 并报告
"""
import os
import sys
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.config import PROCESS_CODES

DB = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': 'steel_belt',
    'charset': 'utf8mb4',
}
BATCH = datetime.now().strftime('%Y%m%d_%H%M%S')


def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 0. 备份
    for tbl, tag in [('process_records', 'pr'), ('orders', 'ord')]:
        bak = f'_bak_{tag}_process_code_{BATCH}'
        cur.execute(f'CREATE TABLE {bak} AS SELECT id, process_code FROM {tbl} WHERE 1=1')
        conn.commit()
        print(f'[B0] 备份 {tbl} → {bak} ({cur.rowcount} 行)')

    # 1. 回填 process_records.process_code
    cur.execute("SELECT id, process_name, process_code FROM process_records WHERE process_code IS NULL OR process_code = %s", ('',))
    empty_rows = cur.fetchall()
    print(f'\n[process_records] 待回填 {len(empty_rows)} 行:')

    cur.execute('SELECT name, process_code FROM process_code_registry')
    registry = {r[0]: r[1] for r in cur.fetchall()}
    print(f'[process_records] registry 自定义工序: {len(registry)} 条')

    filled = 0
    unfilled = []
    for row_id, pname, pcode in empty_rows:
        code = PROCESS_CODES.get(pname) or registry.get(pname)
        if code:
            cur.execute('UPDATE process_records SET process_code=%s WHERE id=%s', (code, row_id))
            filled += 1
        else:
            unfilled.append((row_id, pname))

    conn.commit()
    print(f'[process_records] 成功回填: {filled}/{len(empty_rows)} 行')

    if unfilled:
        print(f'[process_records] ❌ 无法回填 (工序名不在标准字典也不在 registry):')
        for rid, pname in unfilled:
            print(f'  id={rid}, process_name={pname!r}')
    else:
        print('[process_records] ✅ 全部回填完成')

    # 2. 回填 orders.salesperson (R13 新字段)
    cur.execute("SELECT id, created_by, updated_by, salesman FROM orders WHERE salesperson IS NULL OR salesperson = %s", ('',))
    empty_orders = cur.fetchall()
    print(f'\n[orders] 待回填 salesperson {len(empty_orders)} 行:')

    filled2 = 0
    for row_id, created_by, updated_by, salesman in empty_orders:
        src = updated_by or created_by or salesman
        if src:
            cur.execute('UPDATE orders SET salesperson=%s WHERE id=%s', (src, row_id))
            filled2 += 1
        else:
            cur.execute("UPDATE orders SET salesperson='未知' WHERE id=%s", (row_id,))
            print(f'  ⚠️ id={row_id} 无法确定 salesperson, 填"未知"')

    conn.commit()
    print(f'[orders] 成功回填: {filled2}/{len(empty_orders)} 行')

    # 3. 验证
    print()
    cur.execute('SELECT COUNT(*) FROM process_records WHERE process_code IS NULL OR process_code = %s', ('',))
    remain_pr = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM orders WHERE salesperson IS NULL OR salesperson = %s', ('',))
    remain_ord = cur.fetchone()[0]
    print(f'[验证] process_records.process_code 仍为空: {remain_pr} 行')
    print(f'[验证] orders.salesperson 仍为空: {remain_ord} 行')

    cur.close()
    conn.close()

    ok = (remain_pr == 0 and remain_ord == 0)
    print()
    print('========== 回填完成 ==========' if ok else f'========== 回填未完成: PR空={remain_pr}, ord空={remain_ord} ==========')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
