# -*- coding: utf-8 -*-
"""
五金行业库存管理系统 - 完整版 (优化版)
MySQL数据库 + 完善打印功能 + 跟单系统对接
"""
import re
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from datetime import datetime, date
import os
import threading
import json
from pathlib import Path

# 加载 .env 环境变量
env_file = Path(__file__).resolve().parent / '.env'
print(f"[DEBUG] Checking .env file at: {env_file}")
print(f"[DEBUG] .env exists: {env_file.exists()}")
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)
    print(f"[DEBUG] .env loaded. MYSQL_PASSWORD from env: '{os.getenv('MYSQL_PASSWORD', 'NOT_SET')}'")


def load_db_config():
    """从配置文件加载数据库配置"""
    import sys
    if hasattr(sys, '_MEIPASS'):
        # 运行在PyInstaller打包的EXE中
        app_dir = os.path.dirname(sys.executable)
    else:
        # 正常Python运行
        app_dir = os.path.dirname(__file__)
    
    config_file = os.path.join(app_dir, "inventory_config.json")
    
    # 默认配置 - 所有参数都在这里定义，便于统一管理
    default_config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": "inventory_db",
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_config = config.get("database", {})
                # 从配置文件覆盖默认值
                if db_config:
                    if "host" in db_config:
                        default_config["host"] = db_config["host"]
                    if "port" in db_config:
                        default_config["port"] = int(db_config["port"])
                    if "user" in db_config:
                        default_config["user"] = db_config["user"]
                    if "password" in db_config:
                        default_config["password"] = db_config["password"]
                    if "database" in db_config:
                        default_config["database"] = db_config["database"]
                    # 可选配置
                    if "connect_timeout" in db_config:
                        default_config["connect_timeout"] = int(db_config["connect_timeout"])
                    if "read_timeout" in db_config:
                        default_config["read_timeout"] = int(db_config["read_timeout"])
                    if "write_timeout" in db_config:
                        default_config["write_timeout"] = int(db_config["write_timeout"])
        except Exception as e:
            # 配置文件读取失败，使用默认配置
            import traceback
            with open('db_config_error.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now()} - 配置文件读取失败: {str(e)}\n{traceback.format_exc()}\n\n")
    
    return default_config


INVENTORY_DB_CONFIG = load_db_config()


_local = threading.local()

class InventoryDB:
    """库存管理系统MySQL数据访问层 - 优化版"""

    @contextmanager
    def get_connection(self):
        if not hasattr(_local, 'conn') or _local.conn is None:
            _local.conn = pymysql.connect(**INVENTORY_DB_CONFIG)
        conn = _local.conn
        try:
            yield conn
            conn.commit()
        except Exception:
            if _local.conn:
                _local.conn.rollback()
            _local.conn = None
            raise

    @contextmanager
    def get_cursor(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    def init_database(self):
        config = INVENTORY_DB_CONFIG.copy()
        db_name = config.pop("database")
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', db_name):
            raise ValueError(f"无效的数据库名: {db_name}")
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE `{db_name}`")
            self._create_tables(cursor)
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    def _create_tables(self, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warehouses (
                id INT PRIMARY KEY AUTO_INCREMENT,
                code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                location VARCHAR(100),
                remark VARCHAR(200),
                status TINYINT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                parent_name VARCHAR(50),
                remark VARCHAR(200),
                status TINYINT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INT PRIMARY KEY AUTO_INCREMENT,
                code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                contact VARCHAR(50),
                phone VARCHAR(20),
                address VARCHAR(200),
                main_products VARCHAR(200),
                payment_days INT DEFAULT 30,
                grade VARCHAR(10),
                remark VARCHAR(200),
                status TINYINT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT PRIMARY KEY AUTO_INCREMENT,
                sku VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                spec VARCHAR(100),
                unit VARCHAR(20) DEFAULT '个',
                category_id INT,
                price DECIMAL(12,2) DEFAULT 0,
                remark VARCHAR(200),
                status TINYINT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_id INT NOT NULL,
                warehouse_id INT NOT NULL,
                initial_qty DECIMAL(12,2) DEFAULT 0,
                inbound_qty DECIMAL(12,2) DEFAULT 0,
                outbound_qty DECIMAL(12,2) DEFAULT 0,
                current_qty DECIMAL(12,2) DEFAULT 0,
                safety_stock DECIMAL(12,2) DEFAULT 0,
                max_stock DECIMAL(12,2) DEFAULT 0,
                unit_price DECIMAL(12,2) DEFAULT 0,
                last_inbound_at DATETIME,
                last_outbound_at DATETIME,
                remark VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
                UNIQUE KEY uk_product_warehouse (product_id, warehouse_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                trans_no VARCHAR(50) UNIQUE NOT NULL,
                trans_type ENUM('inbound', 'outbound', 'adjust', 'transfer') NOT NULL,
                product_id INT NOT NULL,
                warehouse_id INT NOT NULL,
                from_warehouse_id INT,
                to_warehouse_id INT,
                qty DECIMAL(12,2) NOT NULL,
                unit_price DECIMAL(12,2) DEFAULT 0,
                total_amount DECIMAL(14,2) DEFAULT 0,
                supplier_id INT,
                order_no VARCHAR(50),
                trans_date DATE NOT NULL,
                operator VARCHAR(50),
                remark VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
                INDEX idx_trans_date (trans_date),
                INDEX idx_product_id (product_id),
                INDEX idx_order_no (order_no)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS print_templates (
                id INT PRIMARY KEY AUTO_INCREMENT,
                template_type VARCHAR(20) NOT NULL,
                template_name VARCHAR(50) NOT NULL,
                content TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id INT PRIMARY KEY AUTO_INCREMENT,
                error_code VARCHAR(20) NOT NULL,
                error_message TEXT NOT NULL,
                traceback TEXT,
                context TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                resolution TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE INDEX idx_error_logs_code ON error_logs(error_code)
        """)

        cursor.execute("""
            CREATE INDEX idx_error_logs_created ON error_logs(created_at)
        """)

    def insert_initial_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            warehouses = [
                ("WH-001", "1号仓", "主仓库A区", ""),
                ("WH-002", "2号仓", "主仓库B区", ""),
                ("WH-003", "3号仓", "原材料仓库", ""),
                ("WH-004", "4号仓", "成品仓库", ""),
            ]
            cursor.executemany(
                "INSERT IGNORE INTO warehouses (code, name, location, remark) VALUES (%s, %s, %s, %s)",
                warehouses
            )

            categories = [
                ("CAT-001", "螺栓螺母", "紧固件"), ("CAT-002", "螺钉", "紧固件"),
                ("CAT-003", "垫片", "紧固件"), ("CAT-004", "铆钉", "紧固件"),
                ("CAT-005", "合页铰链", "五金配件"), ("CAT-006", "门锁门吸", "五金配件"),
                ("CAT-007", "拉手把手", "五金配件"), ("CAT-008", "导轨滑道", "五金配件"),
                ("CAT-009", "电线电缆", "电气五金"), ("CAT-010", "开关插座", "电气五金"),
                ("CAT-011", "水管管件", "水暖五金"), ("CAT-012", "阀门", "水暖五金"),
                ("CAT-013", "钻头刀具", "工具刀具"), ("CAT-014", "手动工具", "工具刀具"),
                ("CAT-015", "砂轮砂纸", "磨具"), ("CAT-016", "焊接材料", "焊接"),
                ("CAT-017", "密封胶", "密封防水"), ("CAT-018", "油漆涂料", "表面处理"),
                ("CAT-019", "钢材型材", "金属材料"), ("CAT-020", "铝材", "金属材料"),
                ("CAT-021", "气动工具", "工具刀具"), ("CAT-022", "电动工具", "工具刀具"),
                ("CAT-023", "安全防护", "劳保用品"), ("CAT-024", "搬运工具", "工具刀具"),
                ("CAT-025", "照明器材", "电气五金"), ("CAT-026", "仪表量具", "测量工具"),
            ]
            cursor.executemany(
                "INSERT IGNORE INTO categories (code, name, parent_name) VALUES (%s, %s, %s)",
                categories
            )

            suppliers = [
                ("SUP-001", "华南五金制品有限公司", "张经理", "13800138001", "广东省佛山市南海区", "螺栓螺母、垫片", 30, "A"),
                ("SUP-002", "北京精诚五金批发", "李总", "13900139002", "北京市丰台区", "工具刀具、电气", 15, "B"),
                ("SUP-003", "上海泰达管件有限公司", "王工", "13700137003", "上海市闵行区", "水管管件、阀门", 30, "A"),
                ("SUP-004", "浙江新兴紧固件", "陈老板", "13600136004", "浙江省温州市", "螺钉铆钉", 45, "A+"),
                ("SUP-005", "广州市百利钢材行", "刘总", "13500135005", "广州市越秀区", "钢材型材铝材", 60, "B"),
            ]
            cursor.executemany(
                "INSERT IGNORE INTO suppliers (code, name, contact, phone, address, main_products, payment_days, grade) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                suppliers
            )

            products = [
                ("SKU-0001", "M8×50镀锌六角螺栓", "M8×50", "包(100个)", 25.00, "CAT-001", 100, 10, 200),
                ("SKU-0002", "M10×60不锈钢螺栓", "M10×60", "包(50个)", 42.00, "CAT-001", 50, 10, 100),
                ("SKU-0003", "M6平垫片镀锌", "M6", "袋(200个)", 12.00, "CAT-003", 200, 20, 500),
                ("SKU-0004", "304不锈钢弹垫M8", "M8", "袋(100个)", 18.50, "CAT-003", 80, 15, 300),
                ("SKU-0005", "M5×20十字沉头螺钉", "M5×20", "袋(200个)", 8.50, "CAT-002", 150, 20, 400),
                ("SKU-0006", "4×20自攻螺钉镀锌", "4×20", "盒(500个)", 15.00, "CAT-002", 100, 10, 300),
                ("SKU-0007", "M6×16内六角螺栓", "M6×16", "包(100个)", 22.00, "CAT-001", 60, 10, 150),
                ("SKU-0008", "4.8×19拉铆钉铝制", "4.8×19", "盒(500个)", 18.00, "CAT-004", 120, 15, 350),
            ]

            for sku, name, spec, unit, price, cat_code, init_qty, safety, max_qty in products:
                cursor.execute("""
                    INSERT INTO products (sku, name, spec, unit, price, category_id)
                    SELECT %s, %s, %s, %s, %s, id FROM categories WHERE code = %s
                """, (sku, name, spec, unit, price, cat_code))

                cursor.execute("SELECT id FROM products WHERE sku = %s", (sku,))
                row = cursor.fetchone()
                if row:
                    product_id = row['id']
                    cursor.execute("SELECT id FROM warehouses LIMIT 1")
                    wh_row = cursor.fetchone()
                    if wh_row:
                        warehouse_id = wh_row['id']
                        cursor.execute("""
                            INSERT INTO inventory
                            (product_id, warehouse_id, initial_qty, current_qty, safety_stock, max_stock, unit_price)
                            SELECT %s, %s, %s, %s, %s, %s, %s
                            WHERE NOT EXISTS (SELECT 1 FROM inventory WHERE product_id = %s AND warehouse_id = %s)
                        """, (product_id, warehouse_id, init_qty, init_qty, safety, max_qty, price, product_id, warehouse_id))

            conn.commit()

    def check_connection(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"[InventoryDB] 数据库连接检查失败: {e}")
            return False

    def get_warehouses(self):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM warehouses WHERE status = 1 ORDER BY code")
            return cursor.fetchall()

    def get_categories(self):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM categories WHERE status = 1 ORDER BY code")
            return cursor.fetchall()

    def get_suppliers(self):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM suppliers WHERE status = 1 ORDER BY code")
            return cursor.fetchall()

    def get_all_products(self):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.status = 1 ORDER BY p.sku
            """)
            return cursor.fetchall()

    def get_product_by_sku(self, sku):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.sku = %s AND p.status = 1
            """, (sku,))
            return cursor.fetchone()

    def get_all_inventory(self):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT i.*, p.name as product_name, p.sku, p.spec, p.unit, p.price as product_price,
                       w.name as warehouse_name, w.code as warehouse_code
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                ORDER BY w.code, p.sku
            """)
            return cursor.fetchall()

    def get_inventory_by_product(self, product_id):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT i.*, w.name as warehouse_name
                FROM inventory i
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.product_id = %s
            """, (product_id,))
            return cursor.fetchall()

    def get_product_stock(self, product_id):
        """获取产品总库存（所有仓库）"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(SUM(current_qty), 0) as total_stock
                FROM inventory
                WHERE product_id = %s
            """, (product_id,))
            row = cursor.fetchone()
            return float(row['total_stock']) if row else 0.0

    def get_statistics(self):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE status = 1")
            product_count = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(DISTINCT warehouse_id) as cnt FROM inventory")
            warehouse_count = cursor.fetchone()['cnt']

            cursor.execute("""
                SELECT
                    COALESCE(SUM(current_qty), 0) as total_qty,
                    COALESCE(SUM(current_qty * unit_price), 0) as total_value,
                    COALESCE(SUM(CASE WHEN current_qty <= safety_stock AND current_qty > 0 THEN 1 ELSE 0 END), 0) as low_stock_count,
                    COALESCE(SUM(CASE WHEN current_qty <= 0 THEN 1 ELSE 0 END), 0) as out_stock_count,
                    COALESCE(SUM(CASE WHEN current_qty > max_stock THEN 1 ELSE 0 END), 0) as over_stock_count
                FROM inventory
            """)
            row = cursor.fetchone()
            return {
                'product_count': product_count,
                'warehouse_count': warehouse_count,
                'total_qty': row['total_qty'],
                'total_value': row['total_value'],
                'low_stock_count': row['low_stock_count'],
                'out_stock_count': row['out_stock_count'],
                'over_stock_count': row['over_stock_count']
            }

    def get_low_stock_alerts(self):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT i.*, p.name as product_name, p.sku, p.spec, p.unit,
                       w.name as warehouse_name
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.current_qty <= i.safety_stock AND i.current_qty > 0
                ORDER BY (i.current_qty / NULLIF(i.safety_stock, 0)) ASC
            """)
            result = cursor.fetchall()
            return list(result) if result else []

    def get_stagnant_items(self, months=3):
        from datetime import timedelta
        cutoff = date.today() - timedelta(days=months * 30)
        all_inv = self.get_all_inventory()
        result = []
        for inv in all_inv:
            last_in = inv.get('last_inbound_at')
            last_out = inv.get('last_outbound_at')
            last_date = None
            if last_in: last_date = last_in
            elif last_out: last_date = last_out
            if last_date:
                if isinstance(last_date, str):
                    last_date = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
                if last_date < cutoff and float(inv.get('current_qty', 0) or 0) > 0:
                    result.append([
                        inv.get('sku', ''),
                        inv.get('product_name', ''),
                        int(float(inv.get('current_qty', 0) or 0)),
                        inv.get('category_name', '-') if inv.get('category_name') else '-',
                        inv.get('warehouse_name', '-') if inv.get('warehouse_name') else '-',
                        f"近{months}个月无出入库"
                    ])
            elif float(inv.get('current_qty', 0) or 0) > 0:
                result.append([
                    inv.get('sku', ''),
                    inv.get('product_name', ''),
                    int(float(inv.get('current_qty', 0) or 0)),
                    inv.get('category_name', '-') if inv.get('category_name') else '-',
                    inv.get('warehouse_name', '-') if inv.get('warehouse_name') else '-',
                    f"近{months}个月无出入库"
                ])
        return result

    def add_product(self, sku, name, spec, unit, price, category_id, warehouse_id, initial_qty=0, safety_stock=0, max_stock=0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO products (sku, name, spec, unit, price, category_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (sku, name, spec, unit, price, category_id))
                product_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO inventory (product_id, warehouse_id, initial_qty, current_qty, safety_stock, max_stock, unit_price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (product_id, warehouse_id, initial_qty, initial_qty, safety_stock, max_stock, price))

                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add product failed: {e}")
                return False

    def update_inventory_qty(self, product_id, warehouse_id, qty_change, trans_type='adjust'):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if trans_type == 'inbound':
                    sql = """
                        UPDATE inventory
                        SET current_qty = current_qty + %s,
                            inbound_qty = inbound_qty + %s,
                            last_inbound_at = NOW()
                        WHERE product_id = %s AND warehouse_id = %s
                    """
                    cursor.execute(sql, (qty_change, qty_change, product_id, warehouse_id))
                    if cursor.rowcount == 0:
                        cursor.execute("""
                            INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty, last_inbound_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (product_id, warehouse_id, qty_change, qty_change))
                elif trans_type == 'outbound':
                    sql = """
                        UPDATE inventory
                        SET current_qty = current_qty - %s,
                            outbound_qty = outbound_qty + %s,
                            last_outbound_at = NOW()
                        WHERE product_id = %s AND warehouse_id = %s AND current_qty >= %s
                    """
                    cursor.execute(sql, (qty_change, qty_change, product_id, warehouse_id, qty_change))
                    if cursor.rowcount == 0:
                        return False
                else:
                    sql = """
                        UPDATE inventory SET current_qty = current_qty + %s
                        WHERE product_id = %s AND warehouse_id = %s
                    """
                    cursor.execute(sql, (qty_change, product_id, warehouse_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Update inventory failed: {e}")
                return False

    def add_transaction(self, trans_type, product_id, warehouse_id, qty, unit_price=0, supplier_id=None, order_no=None, operator=None, remark=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                trans_no = f"{trans_type.upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                    INSERT INTO inventory_transactions
                    (trans_no, trans_type, product_id, warehouse_id, qty, unit_price, total_amount, supplier_id, order_no, trans_date, operator, remark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), %s, %s)
                """, (trans_no, trans_type, product_id, warehouse_id, qty, unit_price, float(qty) * float(unit_price), supplier_id, order_no, operator, remark))
                conn.commit()
                return trans_no
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add transaction failed: {e}")
                return None

    def get_transactions(self, product_id=None, start_date=None, end_date=None, limit=100):
        with self.get_cursor() as cursor:
            sql = """
                SELECT t.*, p.name as product_name, p.sku as product_sku,
                       w.name as warehouse_name,
                       s.name as supplier_name
                FROM inventory_transactions t
                JOIN products p ON t.product_id = p.id
                JOIN warehouses w ON t.warehouse_id = w.id
                LEFT JOIN suppliers s ON t.supplier_id = s.id
                WHERE 1=1
            """
            params = []
            if product_id:
                sql += " AND t.product_id = %s"
                params.append(product_id)
            if start_date:
                sql += " AND t.trans_date >= %s"
                params.append(start_date)
            if end_date:
                sql += " AND t.trans_date <= %s"
                params.append(end_date)
            sql += " ORDER BY t.created_at DESC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            return cursor.fetchall()

    def add_warehouse(self, code, name, location="", remark=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO warehouses (code, name, location, remark)
                    VALUES (%s, %s, %s, %s)
                """, (code, name, location, remark))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add warehouse failed: {e}")
                return False

    def add_category(self, code, name, parent_name="", remark=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO categories (code, name, parent_name, remark)
                    VALUES (%s, %s, %s, %s)
                """, (code, name, parent_name, remark))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add category failed: {e}")
                return False

    def add_supplier(self, code, name, contact="", phone="", address="", main_products="", payment_days=30, grade="C"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO suppliers (code, name, contact, phone, address, main_products, payment_days, grade)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (code, name, contact, phone, address, main_products, payment_days, grade))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add supplier failed: {e}")
                return False

    def search_inventory(self, keyword):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT i.*, p.name as product_name, p.sku, p.spec, p.unit, p.price as product_price,
                       w.name as warehouse_name, w.code as warehouse_code
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE p.sku LIKE %s OR p.name LIKE %s OR p.spec LIKE %s
                ORDER BY p.sku
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
            return cursor.fetchall()

    def search_by_material(self, material_name, spec=None, unit=None):
        """
        按物料名称精准匹配库存
        @param material_name: 物料名称（模糊匹配）
        @param spec: 规格（可选，精准匹配）
        @param unit: 单位（可选，精准匹配）
        @return: 匹配的库存列表
        """
        with self.get_cursor() as cursor:
            sql = """
                SELECT i.*, p.name as product_name, p.sku, p.spec, p.unit, p.price as product_price,
                       w.name as warehouse_name, w.code as warehouse_code
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE p.name LIKE %s
            """
            params = [f"%{material_name}%"]
            
            if spec:
                sql += " AND p.spec = %s"
                params.append(spec)
            if unit:
                sql += " AND p.unit = %s"
                params.append(unit)
            
            sql += " ORDER BY p.name, p.spec"
            
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_total_stock_by_material(self, material_name, spec=None):
        """
        获取物料总库存（所有仓库汇总）
        @param material_name: 物料名称
        @param spec: 规格（可选）
        @return: 总库存数量
        """
        with self.get_cursor() as cursor:
            sql = """
                SELECT COALESCE(SUM(i.current_qty), 0) as total_stock
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                WHERE p.name LIKE %s
            """
            params = [f"%{material_name}%"]
            
            if spec:
                sql += " AND p.spec = %s"
                params.append(spec)
            
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return float(row['total_stock']) if row else 0.0

    def add_inbound(self, product_id, warehouse_id, qty, remark="", operator=""):
        from datetime import datetime
        trans_no = f"IN{datetime.now().strftime('%Y%m%d%H%M%S')}"
        today = datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE inventory
                    SET inbound_qty = inbound_qty + %s,
                        current_qty = current_qty + %s,
                        last_inbound_at = NOW()
                    WHERE product_id = %s AND warehouse_id = %s
                """, (qty, qty, product_id, warehouse_id))
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO inventory (product_id, warehouse_id, initial_qty, current_qty, inbound_qty)
                        VALUES (%s, %s, 0, %s, %s)
                    """, (product_id, warehouse_id, qty, qty))

                cursor.execute("""
                    INSERT INTO inventory_transactions
                    (trans_no, trans_type, product_id, warehouse_id, qty, trans_date, operator, remark)
                    VALUES (%s, 'inbound', %s, %s, %s, %s, %s, %s)
                """, (trans_no, product_id, warehouse_id, qty, today, operator, remark))
                conn.commit()
                return trans_no
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add inbound failed: {e}")
                return None

    def add_outbound(self, product_id, warehouse_id, qty, remark="", operator=""):
        from datetime import datetime
        trans_no = f"OUT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        today = datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE inventory
                    SET outbound_qty = outbound_qty + %s,
                        current_qty = current_qty - %s,
                        last_outbound_at = NOW()
                    WHERE product_id = %s AND warehouse_id = %s AND current_qty >= %s
                """, (qty, qty, product_id, warehouse_id, qty))
                if cursor.rowcount == 0:
                    cursor.execute("SELECT current_qty FROM inventory WHERE product_id = %s AND warehouse_id = %s", (product_id, warehouse_id))
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    return None

                cursor.execute("""
                    INSERT INTO inventory_transactions
                    (trans_no, trans_type, product_id, warehouse_id, qty, trans_date, operator, remark)
                    VALUES (%s, 'outbound', %s, %s, %s, %s, %s, %s)
                """, (trans_no, product_id, warehouse_id, qty, today, operator, remark))
                conn.commit()
                return trans_no
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Add outbound failed: {e}")
                return None

    def get_inventory_transactions(self, trans_type=None, limit=100):
        if trans_type:
            trans_type = trans_type.upper() if trans_type.upper() in ('INBOUND', 'OUTBOUND') else None
        return self.get_transactions(limit=limit)

    def get_inventory_count_by_warehouse(self, warehouse_id):
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM inventory WHERE warehouse_id = %s", (warehouse_id,))
            return cursor.fetchone()['cnt']


inv_db = InventoryDB()
