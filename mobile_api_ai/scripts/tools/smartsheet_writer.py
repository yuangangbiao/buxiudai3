# -*- coding: utf-8 -*-
"""企业微信智能表格写入工具
通过 Webhook API 向智能表格写入工单数据

用法:
    python smartsheet_writer.py                          # 写入演示数据
    python smartsheet_writer.py --wo WO-202605006        # 指定订单号
    python smartsheet_writer.py --batch                   # 批量写入
"""
"""
[C-1 修复] 2026-06-04: Webhook Key 改为环境变量读取（符合 jgs7 安全规范）
旧代码（已废弃）:
    WEBHOOK_URL = (
        'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook'
        '?key=64eA1txLc3fAZMt2NCyxs2xltBZgmaEiPhv66IBMzJEplpfHEESIc4yWhdNa7uJ4Ynt6SF3bm2QhM8uq6VtIRtvyuCU0IpupRK6LVjFmEhoj'
    )
"""
import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)

# 强制环境变量，无硬编码默认值
WEBHOOK_KEY = os.getenv('WECHAT_SMARTSHEET_KEY', '')
if not WEBHOOK_KEY:
    raise RuntimeError(
        "[C-1 修复] 环境变量 WECHAT_SMARTSHEET_KEY 必须设置，"
        "不能使用硬编码值。请在 .env 中配置 WECHAT_SMARTSHEET_KEY=your_key"
    )
WEBHOOK_URL = (
    f'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook'
    f'?key={WEBHOOK_KEY}'
)

FIELD_SCHEMA = {
    'fabcde': '分类',
    'f3TVj5': '订单号',
    'f4lY4B': '客户名称',
    'fexnsG': '产品类型',
    'flrEhY': '材质',
    'fbAHzS': '状态',
    'fALAF6': '创建日期',
    'fj7LI3': '订单数量',
    'f7jOiq': '单位',
    'f0kcf1': '订单号',
    'fvy2Zd': '当前工序',
    'fS7rCo': '数据来源',
    'fIjGmz': '工序总数',
    'fceF0M': '备注'
}


def build_payload(records):
    """构建 Webhook 请求体"""
    return {
        'schema': FIELD_SCHEMA,
        'add_records': [{'values': r} for r in records]
    }


def send(payload):
    """发送数据到智能表格"""
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    result = resp.json()
    return result


def write_order(work_order_no, order_no, customer, product, material, status,
                date, qty, unit, current_step, source, total_steps, remark):
    """写入一条工单数据"""
    record = {
        'fabcde': '生产工单',
        'f3TVj5': order_no,
        'f4lY4B': customer,
        'fexnsG': product,
        'flrEhY': material,
        'fbAHzS': status,
        'fALAF6': date,
        'fj7LI3': qty,
        'f7jOiq': unit,
        'f0kcf1': order_no,
        'fvy2Zd': current_step,
        'fS7rCo': source,
        'fIjGmz': total_steps,
        'fceF0M': remark
    }
    payload = build_payload([record])
    result = send(payload)
    return result


def write_demo():
    """写入演示工单 WO-202605006"""
    return write_order(
        order_no='ORD-202604290001',
        customer='山东济南食品',
        product='平板型网带',
        material='304不锈钢',
        status='已创建',
        date='2026-05-17',
        qty='50',
        unit='件',
        current_step='原材料准备',
        source='跟单系统',
        total_steps='11',
        remark='跟单系统自动写入'
    )


def query_order_from_db(order_no):
    """从 SQLite 查询工单数据"""
    db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
    if not os.path.exists(db_path):
        return None
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    cur.execute('SELECT * FROM process_records WHERE order_no=?', (order_no,))
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    db.close()
    if not rows:
        return None
    return dict(zip(cols, rows[0]))


def write_from_db(order_no):
    """从数据库读取并写入智能表格"""
    row = query_order_from_db(order_no)
    if not row:
        print(f'未找到订单: {order_no}')
        return
    return write_order(
        work_order_no=row.get('order_no', ''),
        order_no=row.get('order_no', ''),
        customer=row.get('customer_name', '') or '',
        product=row.get('product_name', '') or '',
        material='',
        status=row.get('status', ''),
        date=str(row.get('created_at', ''))[:10],
        qty=str(row.get('quantity', '')),
        unit=row.get('unit', '') or '件',
        current_step='',
        source=row.get('source', '跟单系统'),
        total_steps='',
        remark=''
    )


def print_result(result):
    """打印写入结果"""
    if result.get('errcode') == 0:
        rid = result.get('add_records', [{}])[0].get('record_id', '')
        print(f'写入成功，record_id: {rid}')
    else:
        print(f'写入失败: {result.get("errmsg", "")}')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='写入工单数据到智能表格')
    parser.add_argument('--wo', help='指定订单号，从数据库读取')
    parser.add_argument('--demo', action='store_true', default=True, help='写入演示数据')
    args = parser.parse_args()

    if args.wo:
        result = write_from_db(args.wo)
    else:
        result = write_demo()

    print_result(result)


if __name__ == '__main__':
    main()
