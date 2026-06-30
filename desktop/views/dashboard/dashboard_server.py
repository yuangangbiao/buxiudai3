#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stainless Steel Belt Production Tracking - Dashboard API Server
For dashboard.html data supply

Run: python dashboard_server.py
Open: http://localhost:5000
"""

import os
import sys
import socket
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request

LOG_FILE = os.path.join(os.environ.get('TEMP', '/tmp'), 'dashboard_server.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("[INIT] Dashboard server module loading...")

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, base_dir)
from constants import OrderStatus, ProcessStatus


def _get_user_dir():
    """获取用户可写目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _load_db_config_to_env():
    """从 db_config.json 加载配置到环境变量，供 models.database.get_connection() 使用"""
    user_dir = _get_user_dir()
    db_config_file = os.path.join(user_dir, "db_config.json")
    if os.path.exists(db_config_file):
        try:
            with open(db_config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            os.environ['MYSQL_HOST'] = config.get("host", "localhost")
            os.environ['MYSQL_PORT'] = str(config.get("port", 3306))
            os.environ['MYSQL_DATABASE'] = config.get("database", "steel_belt")
            os.environ['MYSQL_USER'] = config.get("user", "root")
            if config.get("password"):  # 非空才覆盖，避免覆盖.env中的正确密码
                os.environ['MYSQL_PASSWORD'] = config["password"]
            return config
        except Exception:
            pass
    return {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", 3306)),
        "database": os.environ.get("MYSQL_DATABASE", "steel_belt"),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", "")
    }


# 启动时加载配置到环境变量
_load_db_config_to_env()

# ─── DAO 层导入 ──────────────────────────────────────────
from models.database import get_connection
from models.inventory import InventoryDAO
from models.order import OrderDAO
from models.production import ProductionDAO
from models.shipment import ShipmentDAO
from models.process import ProcessDAO

DB_TYPE = "mysql"


def row_to_dict(row):
    """Convert row to dict"""
    if row is None:
        return None
    return dict(row)


def format_cn_date(dt):
    """将日期格式化为中文显示 2026年5月5日"""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d')
        except Exception:
            return dt
    if isinstance(dt, datetime):
        return f"{dt.year}年{dt.month}月{dt.day}日"
    return str(dt)


if getattr(sys, 'frozen', False):
    BASE_DIR = str(__import__('pathlib').Path(sys._MEIPASS))
    user_dir = str(__import__('pathlib').Path(sys.executable))
    template_path = str(__import__('pathlib').Path(user_dir) / 'views' / 'dashboard' / 'templates')
    if not os.path.exists(template_path):
        template_path = str(__import__('pathlib').Path(BASE_DIR) / 'views' / 'dashboard' / 'templates')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=template_path, static_folder=None)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ============================================
# Routes
# ============================================

@app.route('/')
def index():
    """Dashboard page - 默认打开最新版"""
    return render_template('dashboard_v3.html')

@app.route('/v1')
def index_v1():
    """方案1 - 深蓝经典版"""
    return render_template('dashboard_v1.html')

@app.route('/v2')
def index_v2():
    """方案2 - 进度卡片版"""
    return render_template('dashboard_v2.html')

@app.route('/v3')
def index_v3():
    """方案3 - 紧凑卡片版"""
    return render_template('dashboard_v3.html')

@app.route('/config')
def show_config():
    """配置页面"""
    return render_template('dashboard_config.html')


@app.route('/api/health')
def api_health():
    """统一健康检查端点"""
    from datetime import datetime
    return jsonify({
        'status': 'ok',
        'service': 'dashboard',
        'version': '3.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/dashboard_data')
def get_dashboard_data():
    """Get all dashboard data"""
    try:
        data = {}

        # ─── 1. 订单统计（通过 OrderDAO） ──────────────────
        stats = OrderDAO.get_dashboard_order_stats()
        data['totalOrders'] = stats['totalOrders']
        data['monthlyNew'] = stats['monthlyNew']
        data['statusDistribution'] = stats['statusDistribution']
        data['completionRate'] = stats['completionRate']
        data['producingOrders'] = stats['producingOrders']
        data['readyToShip'] = stats['readyToShip']
        data['overdueOrders'] = stats['overdueOrders']

        # ─── 2. 生产列表（通过 ProductionDAO + ProcessDAO） ──
        production_rows = ProductionDAO.get_dashboard_production_list(limit=20)
        production_list = []
        for row in production_rows:
            d = dict(row)

            # Build specs string
            specs_parts = []
            if d.get('mesh_size'): specs_parts.append(f"网孔{d['mesh_size']}mm")
            if d.get('wire_diameter'): specs_parts.append(f"丝径{d['wire_diameter']}mm")
            if d.get('width'): specs_parts.append(f"宽{d['width']}mm")
            if d.get('length'): specs_parts.append(f"长{d['length']}m")
            if d.get('surface_treatment'): specs_parts.append(d['surface_treatment'])
            d['specs'] = ' / '.join(specs_parts) if specs_parts else '-'
            # Remove individual spec fields
            for k in ['mesh_size', 'wire_diameter', 'width', 'length', 'surface_treatment']:
                d.pop(k, None)

            # 添加优先级显示
            priority_map = {1: "🔴高", 5: "🟡中", 9: "🟢低", 10: "🟢低"}
            priority_val = d.pop('priority', 5)
            d['priority_text'] = priority_map.get(priority_val, "🟡中")

            # 计算生产进度（通过 ProcessDAO）
            prod_id = d.pop('prod_id', None)
            d['process_details'] = []
            if prod_id:
                process_records = ProcessDAO.get_by_production(prod_id)
                total_proc = len(process_records)
                done_proc = sum(
                    1 for pr in process_records
                    if pr['status'] in (ProcessStatus.COMPLETED.value, "合格")
                )
                d['progress'] = round(done_proc / total_proc * 100, 1) if total_proc > 0 else 0
                d['progress_text'] = f"{done_proc}/{total_proc} 工序"

                # 构建工序详情列表
                process_list = []
                for pr in process_records:
                    planned = pr.get('planned_qty') or 0
                    completed = pr.get('completed_qty') or 0
                    if planned > 0:
                        prog = round(min(completed, planned) / planned * 100, 1)
                    elif pr['status'] in (ProcessStatus.COMPLETED.value, '合格'):
                        prog = 100.0
                    elif pr['status'] in ('进行中', ProcessStatus.IN_PROGRESS.value):
                        prog = 50.0
                    else:
                        prog = 0.0
                    process_list.append({
                        'name': pr['process_name'],
                        'seq': pr['process_seq'],
                        'status': pr['status'],
                        'completed': completed,
                        'qualified': pr.get('qualified_qty') or 0,
                        'worker': pr.get('worker') or '',
                        'planned': planned,
                        'progress': prog
                    })
                d['process_details'] = process_list
            else:
                d['progress'] = 0
                d['progress_text'] = '0/0 工序'

            # 交期倒计时
            if d.get('delivery_date'):
                try:
                    delivery_val = d['delivery_date']
                    if isinstance(delivery_val, datetime):
                        dd = delivery_val
                    else:
                        dd = datetime.strptime(str(delivery_val), '%Y-%m-%d')
                    delta = (dd - datetime.now()).days
                    if delta < 0:
                        d['countdown'] = delta
                        d['countdown_text'] = f"逾期{-delta}天"
                        d['countdown_level'] = 'overdue'
                    elif delta == 0:
                        d['countdown'] = 0
                        d['countdown_text'] = "今天到期"
                        d['countdown_level'] = 'urgent'
                    elif delta <= 3:
                        d['countdown'] = delta
                        d['countdown_text'] = f"还剩{delta}天"
                        d['countdown_level'] = 'warning'
                    else:
                        d['countdown'] = delta
                        d['countdown_text'] = f"还剩{delta}天"
                        d['countdown_level'] = 'normal'
                except Exception:
                    d['countdown'] = None
                    d['countdown_text'] = '-'
                    d['countdown_level'] = 'normal'
            else:
                d['countdown'] = None
                d['countdown_text'] = '-'
                d['countdown_level'] = 'normal'

            # 格式化交货日期为中文
            d['delivery_date'] = format_cn_date(d.get('delivery_date'))

            production_list.append(d)
        data['productionList'] = production_list

        # ─── 3. 订单列表（v1版，通过 OrderDAO） ──────────────
        data['orderList'] = OrderDAO.get_dashboard_order_list(limit=20)

        # ─── 4. 物料缺料（跨表 JOIN，保留在 server 但使用统一连接） ──
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    po.order_no,
                    om.material_name,
                    om.unit,
                    SUM(om.required_qty - om.prepared_qty) as shortage_qty
                FROM order_materials om
                LEFT JOIN production_orders po ON om.order_id = po.order_id
                WHERE om.prep_status = '缺料' OR (om.required_qty > om.prepared_qty AND om.prepared_qty < om.required_qty)
                GROUP BY po.order_no, om.material_name, om.unit
                HAVING SUM(om.required_qty - om.prepared_qty) > 0
                ORDER BY po.order_no, om.material_name
            """)
            shortage_list = []
            for row in cursor.fetchall():
                d = row_to_dict(row)
                d['shortage_display'] = f"{d['shortage_qty']}{d['unit']}"
                shortage_list.append(d)
            data['shortageList'] = shortage_list
        finally:
            conn.close()

        # ─── 5. 告警（通过 OrderDAO + HTTP 库存查询） ─────────
        alerts = []

        # 交期告警
        alert_orders = OrderDAO.get_delivery_alert_orders(days_ahead=7)
        processed_orders = set()
        for row in alert_orders:
            order_no = row['order_no']
            if order_no in processed_orders:
                continue
            processed_orders.add(order_no)

            try:
                delivery_date_val = row['delivery_date']
                if isinstance(delivery_date_val, datetime):
                    delivery_date = delivery_date_val
                else:
                    delivery_date = datetime.strptime(str(delivery_date_val), '%Y-%m-%d')
                days = (delivery_date - datetime.now()).days

                if days < 0:
                    overdue_days = abs(days)
                    alerts.append({
                        'level': 'critical',
                        'title': '🚨 订单逾期',
                        'description': f"订单 {order_no}（{row['customer_name']}）已逾期 {overdue_days} 天",
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                elif days <= 3:
                    alerts.append({
                        'level': 'critical',
                        'title': '🚨 即将到期',
                        'description': f"订单 {order_no}（{row['customer_name']}）距到期仅剩 {days} 天",
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                elif days <= 7:
                    alerts.append({
                        'level': 'warning',
                        'title': '⚠️ 即将到期',
                        'description': f"订单 {order_no}（{row['customer_name']}）距到期仅剩 {days} 天",
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
            except Exception as e:
                print(f"解析日期失败: {row['delivery_date']}, 错误: {e}")
                continue

        # 库存告警
        low_items = InventoryDAO.get_low_inventory_alerts(limit=3)
        for row in low_items:
            alerts.append({
                'level': 'info',
                'title': '📦 库存不足',
                'description': f"{row['material_name']} 当前库存 {row['quantity']}{row['unit']}",
                'time': datetime.now().strftime('%Y-%m-%d %H:%M')
            })

        data['alerts'] = alerts

        # ─── 6. 最近发货（通过 ShipmentDAO） ──────────────────
        shipments = ShipmentDAO.get_recent_for_dashboard(limit=10)
        for r in shipments:
            r['ship_date'] = format_cn_date(r.get('ship_date'))
        data['recentShipments'] = shipments

        # ─── 7. 库存概览（通过 InventoryDAO） ────────────────
        data['inventory'] = InventoryDAO.get_dashboard_overview()

        # ─── 8. 库存预警（跨表，保留在 server 但使用统一连接） ──
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    material_name, 
                    unit, 
                    SUM(required_qty) as total_required, 
                    SUM(prepared_qty) as total_prepared,
                    SUM(required_qty - prepared_qty) as shortage_qty
                FROM order_materials
                WHERE prep_status = '缺料' OR (required_qty > prepared_qty AND prepared_qty < required_qty)
                GROUP BY material_name, unit
                HAVING SUM(required_qty - prepared_qty) > 0
                ORDER BY shortage_qty DESC
            """)
            inventory_warnings = []
            for row in cursor.fetchall():
                shortage_qty = row['shortage_qty']
                if row['total_required'] > 0:
                    stock_rate = round((row['total_prepared'] / row['total_required']) * 100, 1)
                else:
                    stock_rate = 0
                inventory_warnings.append({
                    'material_name': row['material_name'],
                    'quantity': shortage_qty,
                    'unit': row['unit'],
                    'stock_rate': stock_rate
                })
            data['inventoryWarnings'] = inventory_warnings
        finally:
            conn.close()

        return jsonify(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'totalOrders': 0, 'monthlyNew': 0, 'producingOrders': 0, 'readyToShip': 0,
            'overdueOrders': 0, 'completionRate': 0,
            'statusDistribution': {}, 'productionList': [], 'alerts': [],
            'recentShipments': [], 'inventory': [], 'inventoryWarnings': []
        }), 500


@app.route('/api/status')
def get_status():
    """Health check"""
    return jsonify({'status': 'running', 'timestamp': datetime.now().isoformat()})


# ─── 省份订单分布 API ───────────────────────────────────────
@app.route('/api/province_distribution')
def get_province_distribution():
    """各省份订单分布（从 customer_address/customer_name 提取省份）"""
    try:
        rows = OrderDAO.get_province_data()

        # 省份关键词映射（按长度降序排列，避免"东北"被"东"匹配）
        PROVINCE_KEYWORDS = [
            ('内蒙古', '内蒙古'), ('黑龙江', '黑龙江'), ('新疆维吾尔', '新疆'), ('广西壮族', '广西'),
            ('西藏自治', '西藏'), ('宁夏回族', '宁夏'), ('香港特别行政', '香港'), ('澳门特别行政', '澳门'),
            ('北京', '北京'), ('天津', '天津'), ('上海', '上海'), ('重庆', '重庆'),
            ('河北', '河北'), ('山西', '山西'), ('辽宁', '辽宁'), ('吉林', '吉林'),
            ('江苏', '江苏'), ('浙江', '浙江'), ('安徽', '安徽'), ('福建', '福建'),
            ('江西', '江西'), ('山东', '山东'), ('河南', '河南'), ('湖北', '湖北'),
            ('湖南', '湖南'), ('广东', '广东'), ('海南', '海南'), ('四川', '四川'),
            ('贵州', '贵州'), ('云南', '云南'), ('陕西', '陕西'), ('甘肃', '甘肃'),
            ('青海', '青海'), ('台湾', '台湾'),
            # 城市→省份
            ('深圳', '广东'), ('广州', '广东'), ('东莞', '广东'), ('佛山', '广东'),
            ('珠海', '广东'), ('中山', '广东'), ('惠州', '广东'), ('汕头', '广东'),
            ('宁津', '山东'), ('德州', '山东'), ('济南', '山东'), ('青岛', '山东'),
            ('郑州', '河南'), ('洛阳', '河南'), ('武汉', '湖北'), ('长沙', '湖南'),
            ('杭州', '浙江'), ('宁波', '浙江'), ('温州', '浙江'), ('成都', '四川'),
            ('南京', '江苏'), ('苏州', '江苏'), ('无锡', '江苏'),
        ]

        def extract_province(customer_name, address):
            text = (address or '') + (customer_name or '')
            for kw, prov in PROVINCE_KEYWORDS:
                if kw in text:
                    return prov
            return '未知'

        dist = {}
        for row in rows:
            p = extract_province(row.get('customer_name', ''), row.get('customer_address', ''))
            dist[p] = dist.get(p, 0) + 1

        # 移除"未知"（如果为0）
        if '未知' in dist and dist['未知'] == 0:
            del dist['未知']

        return jsonify({'success': True, 'data': dist})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Start
# ============================================

if __name__ == '__main__':
    # 获取本机局域网IP地址
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    local_ip = get_local_ip()

    config = _load_db_config_to_env()
    print("=" * 50)
    print("[Dashboard] Stainless Steel Belt Tracking")
    print("=" * 50)
    print(f"Database: MySQL ({config.get('host')}:{config.get('port')}/{config.get('database')})")
    print(f"Local:  http://localhost:5005")
    if local_ip != "127.0.0.1":
        print(f"LAN:    http://{local_ip}:5005  (局域网设备可访问)")
    else:
        print("LAN:    未检测到网络连接，仅限本机访问")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    port = int(os.getenv('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
