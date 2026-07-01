"""库存管理 Web 蓝图 — 入口"""
from flask import Blueprint
from .routes_core import register_routes_core
from .routes_data import register_routes_data
from .routes_system import register_routes_system
from .routes_api import register_routes_api

web_bp = Blueprint('inventory_web', __name__, template_folder='templates')

register_routes_core(web_bp)
register_routes_data(web_bp)
register_routes_system(web_bp)
register_routes_api(web_bp)

@web_bp.route('/inventory')
def index():
    from flask import redirect
    return redirect('/inventory/dashboard')
