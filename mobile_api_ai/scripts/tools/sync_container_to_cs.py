# -*- coding: utf-8 -*-
"""
容器中心 → 晨圣报工 数据同步脚本
把 wechat_container.db 中的真实数据推送到 chengsheng.db
并检查 chengsheng.db 是否有字段缺失
"""
import sqlite3
import os
import sys
import json
import uuid
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_CC = os.environ.get('WECHAT_CONTAINER_DB_PATH', os.path.join(BASE, 'wechat_container.db'))
DB_CS = os.environ.get('CHENGSHENG_DB_PATH', os.path.join(BASE, 'chengsheng.db'))

# =============================================
# 工具函数
# =============================================
def db_connect(path, label):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    print(f'已连接 {label}: {path} ({os.path.getsize(path)} bytes)')
    return conn

def get_table_info(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {}
    for r in cur.fetchall():
        tname = r['name']
        cur.execute('PRAGMA table_info("%s")' % tname)
        cols = [(c['name'], c['type']) for c in cur.fetchall()]
        cur.execute('SELECT COUNT(*) FROM "%s"' % tname)
        cnt = cur.fetchone()[0]
        tables[tname] = {'columns': cols, 'count': cnt}
    return tables

def print_table_info(tables, label):
    print(f'\n{"="*60}')
    print(f'{label}')
    print(f'{"="*60}')
    for tname, info in tables.items():
        print(f'  {tname} ({info["count"]} 行)')
        for col in info['columns']:
            print(f'    {col[0]} ({col[1]})')

def fetch_all(cur, table):
    cur.execute('SELECT * FROM "%s"' % table)
    return [dict(r) for r in cur.fetchall()]

# =============================================
# 推送函数
# =============================================
def push_workers(conn_cc, conn_cs):
    print('\n--- [推送] 员工名单: enterprise_structure → workers ---')
    cur_cc = conn_cc.cursor()
    cur_cs = conn_cs.cursor()

    rows = fetch_all(cur_cc, 'enterprise_structure')
    seen = set()
    employees = []
    for r in rows:
        users_json = r.get('users', '[]')
        if isinstance(users_json, str):
            try:
                users = json.loads(users_json)
            except Exception as e:
                print(f"[sync_container_to_cs] 解析users JSON失败: {e}")
                users = []
        else:
            users = users_json
        for u in users:
            name = u.get('name', '').strip()
            userid = u.get('userid', '').strip()
            if not name:
                continue
            key = userid if userid else name
            if key in seen:
                continue
            seen.add(key)
            employees.append({'name': name, 'userid': userid})

    print(f'从容器中心找到 {len(employees)} 名员工')
    for e in employees:
        print(f'  员工: {e["name"]} (userid: {e["userid"]})')

    inserted = 0
    for emp in employees:
        username = emp['userid'] if emp['userid'] else 'user_' + str(uuid.uuid4())[:8]
        cur_cs.execute('SELECT COUNT(*) as cnt FROM workers WHERE username=?', (username,))
        if cur_cs.fetchone()['cnt'] > 0:
            print(f'  跳过(已存在): {emp["name"]} ({username})')
            continue
        cur_cs.execute(
            'INSERT INTO workers (username, password, name, role, created_at, source) VALUES (?,?,?,?,?,?)',
            (username, 'cs123456', emp['name'], 'worker', datetime.now().isoformat(), 'container_sync')
        )
        inserted += 1
        print(f'  已插入: {emp["name"]} ({username})')
    conn_cs.commit()
    print(f'员工推送完成: 新增 {inserted} 人')

def push_workorders(conn_cc, conn_cs):
    print('\n--- [推送] 工单数据: process_records → orders + container_sync_records ---')

    cur_cc = conn_cc.cursor()
    cur_cs = conn_cs.cursor()

    rows = fetch_all(cur_cc, 'process_records')
    print(f'从容器中心找到 {len(rows)} 条工单记录')

    for r in rows:
        order_no = r.get('order_no', '') or ''
        order_no = r.get('order_no', '') or ''

        # 跳过测试数据
        if order_no.startswith('ORD-SCAN-') or order_no.startswith('ATTEND_'):
            print('  跳过(测试数据): %s' % order_no)
            continue

        product_name = r.get('product_name', '') or ''
        quantity = r.get('quantity', 0) or 0
        unit = r.get('unit', '') or ''
        customer_name = r.get('customer_name', '') or ''
        delivery_date = r.get('delivery_date', '') or ''
        priority = r.get('priority', 'normal') or 'normal'
        status = r.get('status', 'pending') or 'pending'
        steps_json = r.get('steps', '[]') or '[]'
        created_at = r.get('created_at', datetime.now().isoformat()) or datetime.now().isoformat()
        updated_at = r.get('updated_at', '') or ''
        completed_at = r.get('completed_at', '') or ''
        completed_by = r.get('completed_by', '') or ''
        flow_type = r.get('flow_type', '') or ''
        template_id = r.get('template_id', '') or ''
        task_count = r.get('task_count', 0) or 0
        completed_task_count = r.get('completed_task_count', 0) or 0
        current_step = r.get('current_step', '') or ''
        source = r.get('source', 'container') or 'container'
        process_type = r.get('process_type', '') or ''

        # --- 1. 推送到 orders 表 ---
        cur_cs.execute('SELECT COUNT(*) as cnt FROM orders WHERE order_id=?', (order_no,))
        exists = cur_cs.fetchone()['cnt'] > 0

        if not exists:
            cur_cs.execute(
                '''INSERT INTO orders
                   (order_id, name, material, spec, length, status, priority, delivery_date, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (order_no, product_name, '', '', quantity, status, priority, delivery_date, created_at)
            )
            print(f'  订单已插入: {order_no} → {product_name} ({quantity}{unit})')
        else:
            cur_cs.execute(
                '''UPDATE orders SET
                   name=?, status=?, priority=?, delivery_date=?
                   WHERE order_id=?''',
                (product_name, status, priority, delivery_date, order_no)
            )
            print(f'  订单已更新: {order_no} → {product_name}')

        # --- 2. 推送到 container_sync_records 表 ---
        cur_cs.execute('SELECT COUNT(*) as cnt FROM container_sync_records WHERE order_no=?', (order_no,))
        exists_sync = cur_cs.fetchone()['cnt'] > 0

        # 解析 steps
        if isinstance(steps_json, str):
            try:
                steps = json.loads(steps_json)
            except Exception as e:
                print(f"[sync_container_to_cs] 解析steps JSON失败: {e}")
                steps = []
        else:
            steps = steps_json

        steps_str = json.dumps(steps, ensure_ascii=False) if steps else '[]'

        record_id = r.get('id', '') or order_no

        sync_data = {
            'record_id': record_id,
            'process_type': process_type,
            'order_no': order_no,
            'order_no': order_no,
            'product_name': product_name,
            'quantity': quantity,
            'unit': unit,
            'customer_name': customer_name,
            'delivery_date': delivery_date,
            'priority': priority,
            'status': status,
            'current_step': current_step,
            'steps': steps_str,
            'task_count': task_count,
            'completed_task_count': completed_task_count,
            'source': source,
            'flow_type': flow_type,
            'template_id': template_id,
            'created_at': created_at,
            'updated_at': updated_at,
            'completed_at': completed_at,
            'completed_by': completed_by,
            'sync_status': 'synced',
            'last_synced_at': datetime.now().isoformat(),
        }

        if exists_sync:
            set_clause = ', '.join([f'"{k}"=?' for k in sync_data.keys()])
            values = list(sync_data.values()) + [order_no]
            cur_cs.execute(
                'UPDATE container_sync_records SET %s WHERE order_no=?' % set_clause,
                values
            )
        else:
            cols = ', '.join(['"%s"' % k for k in sync_data.keys()])
            placeholders = ', '.join(['?'] * len(sync_data))
            cur_cs.execute(
                'INSERT INTO container_sync_records (%s) VALUES (%s)' % (cols, placeholders),
                list(sync_data.values())
            )

        # --- 3. 解析 steps 推送到 order_processes ---
        if steps:
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    step_name = step.get('name', '') or step.get('step_name', '') or ''
                    process_key = step.get('process_key', '') or step_name
                else:
                    step_name = str(step)
                    process_key = str(step)

                # 检查是否已有
                cur_cs.execute(
                    'SELECT COUNT(*) as cnt FROM order_processes WHERE order_id=? AND process_key=?',
                    (order_no, process_key)
                )
                if cur_cs.fetchone()['cnt'] == 0:
                    cur_cs.execute(
                        'INSERT INTO order_processes (order_id, process_key, sequence) VALUES (?,?,?)',
                        (order_no, process_key, i)
                    )

        conn_cs.commit()

    print(f'工单推送完成: {len(rows)} 条工单已同步')

def push_sub_steps(conn_cc, conn_cs):
    print('\n--- [推送] 报工记录: process_sub_steps → sub_steps ---')

    cur_cc = conn_cc.cursor()
    cur_cs = conn_cs.cursor()

    # 兼容迁移：确保目标表有 qualified_qty 和 overtime_minutes 字段
    try:
        cur_cs.execute('ALTER TABLE sub_steps ADD COLUMN qualified_qty REAL DEFAULT 0')
    except Exception:
        pass
    try:
        cur_cs.execute('ALTER TABLE sub_steps ADD COLUMN overtime_minutes INTEGER DEFAULT 0')
    except Exception:
        pass

    rows = fetch_all(cur_cc, 'process_sub_steps')
    print(f'从容器中心找到 {len(rows)} 条报工记录')

    inserted = 0
    for r in rows:
        step_id = r.get('id', '') or r.get('step_id', '') or str(uuid.uuid4())
        process_id_param = r.get('process_id', '') or ''
        order_no = r.get('order_no', '') or ''
        step_name = r.get('step_name', '') or ''
        batch_no = r.get('batch_no', '') or ''
        quantity = r.get('quantity', 0) or 0
        qualified_qty = r.get('qualified_qty', quantity) or 0
        overtime_minutes = r.get('overtime_minutes', 0) or 0
        operator = r.get('operator', '') or ''
        remark = r.get('remark', '') or ''
        equipment_name = r.get('equipment_name', '') or ''
        created_at = r.get('created_at', datetime.now().isoformat()) or datetime.now().isoformat()

        # 检查是否已存在（用 step_id 或组合条件）
        cur_cs.execute('SELECT COUNT(*) as cnt FROM sub_steps WHERE step_id=?', (step_id,))
        if cur_cs.fetchone()['cnt'] > 0:
            continue

        cur_cs.execute(
            '''INSERT INTO sub_steps
               (step_id, process_id, order_no, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_minutes, created_at, synced)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)''',
            (step_id, process_id_param, order_no, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_minutes, created_at)
        )
        inserted += 1
        print(f'  报工记录已插入: {step_name} (数量={quantity}, 合格={qualified_qty}, 工时={overtime_minutes}分钟) 操作人: {operator}')

    conn_cs.commit()
    print(f'报工记录推送完成: 新增 {inserted} 条')

# =============================================
# 字段完整性检查
# =============================================
def check_field_completeness(tables_cc, tables_cs):
    print('\n' + '=' * 60)
    print('字段完整性检查')
    print('=' * 60)

    # 前端 API 需要的字段
    api_requirements = {
        'orders': {
            'order_id': '订单编号',
            'name': '订单名称',
            'material': '材质',
            'spec': '规格',
            'length': '数量',
            'status': '状态',
            'priority': '优先级',
            'delivery_date': '交货日期',
            'current_process_index': '当前工序索引',
            'created_at': '创建时间',
        },
        'workers': {
            'username': '用户名',
            'password': '密码',
            'name': '姓名',
            'role': '角色',
            'created_at': '创建时间',
            'source': '来源',
        },
        'sub_steps': {
            'step_id': '步骤ID',
            'process_id': '流程ID',
            'order_no': '订单号',
            'step_name': '步骤名',
            'batch_no': '批次号',
            'quantity': '数量',
            'operator': '操作人',
            'remark': '备注',
            'created_at': '创建时间',
            'synced': '同步状态',
        },
        'order_processes': {
            'order_id': '订单ID',
            'process_key': '工序KEY',
            'sequence': '顺序',
        },
    }

    all_ok = True
    for table, required_fields in api_requirements.items():
        if table not in tables_cs:
            print(f'  ❌ 缺少表: {table}')
            all_ok = False
            continue

        existing_cols = {c[0] for c in tables_cs[table]['columns']}
        missing = []
        for field, desc in required_fields.items():
            if field not in existing_cols:
                missing.append((field, desc))

        if missing:
            all_ok = False
            print(f'  [FAIL] {table} 表缺少字段:')
            for field, desc in missing:
                print(f'    - {field} ({desc})')
        else:
            print(f'  [OK] {table} 表字段完整 ({len(required_fields)} 个字段)')

    # 检查 container_sync_records 是否与 process_records 兼容
    print('\n--- 同步记录表兼容性检查 ---')
    if 'container_sync_records' in tables_cs and 'process_records' in tables_cc:
        cc_cols = {c[0] for c in tables_cc['process_records']['columns']}
        cs_cols = {c[0] for c in tables_cs['container_sync_records']['columns']}
        extra_in_cs = cs_cols - cc_cols - {'record_id', 'sync_status', 'last_synced_at'}
        if extra_in_cs:
            print(f'  [INFO] container_sync_records 比 process_records 多出的字段: {extra_in_cs}')
        missing_in_cs = cc_cols - cs_cols
        missing_in_cs = missing_in_cs - {'id'}
        if missing_in_cs:
            all_ok = False
            print(f'  [FAIL] container_sync_records 缺少 process_records 的字段: {missing_in_cs}')
        else:
            print(f'  [OK] container_sync_records 与 process_records 字段兼容')

    if all_ok:
        print('\n[OK] 所有表字段完整性检查通过')
    else:
        print('\n[WARN] 存在字段缺失，建议人工修正')

    return all_ok


# =============================================
# 主流程
# =============================================
def main():
    print('=' * 60)
    print('容器中心 → 晨圣报工 数据同步工具')
    print(f'启动时间: {datetime.now().isoformat()}')
    print('=' * 60)

    # 连接数据库
    conn_cc = db_connect(DB_CC, '容器中心')
    conn_cs = db_connect(DB_CS, '晨圣报工')

    # 获取表结构
    print('\n读取数据库结构...')
    tables_cc = get_table_info(conn_cc.cursor())
    tables_cs = get_table_info(conn_cs.cursor())

    print_table_info(tables_cc, '容器中心表结构')
    print_table_info(tables_cs, '晨圣报工表结构')

    # ---- 数据推送 ----
    print('\n\n' + '=' * 60)
    print('开始数据推送')
    print('=' * 60)

    # 1. 推送员工名单
    if 'enterprise_structure' in tables_cc and 'workers' in tables_cs:
        push_workers(conn_cc, conn_cs)
    else:
        print('⚠️ 跳过员工推送: 缺少 enterprise_structure 或 workers 表')

    # 2. 推送工单数据
    if 'process_records' in tables_cc and ('orders' in tables_cs or 'container_sync_records' in tables_cs):
        push_workorders(conn_cc, conn_cs)
    else:
        print('⚠️ 跳过工单推送: 缺少 process_records 或目标表')

    # 3. 推送报工记录
    if 'process_sub_steps' in tables_cc and 'sub_steps' in tables_cs:
        push_sub_steps(conn_cc, conn_cs)
    else:
        print('⚠️ 跳过报工记录推送: 缺少 process_sub_steps 或 sub_steps 表')

    # ---- 字段完整性检查 ----
    check_field_completeness(tables_cc, tables_cs)

    # ---- 最终报告 ----
    print('\n\n' + '=' * 60)
    print('同步完成报告')
    print('=' * 60)
    tables_cs_final = get_table_info(conn_cs.cursor())
    for tname, info in tables_cs_final.items():
        print(f'  {tname}: {info["count"]} 行')

    conn_cc.close()
    conn_cs.close()
    print('\n=== 同步脚本执行完成 ===')


if __name__ == '__main__':
    main()
