# -*- coding: utf-8 -*-
"""
订单表单定义
"""
from config import PRODUCT_TYPES, MATERIALS, ORDER_STATUS, SURFACE_TREATMENTS, UNITS
from constants import OrderStatus
from i18n import t
from models.database import generate_order_no
from utils.custom_types import get_product_types, get_materials


def get_new_order_fields():
    """新建订单表单字段"""
    return [
        (t('order.form.order_no'), "order_no", generate_order_no(), "readonly"),
        (t('order.form.customer_name') + " *", "customer_name", "", "entry", [], t('order.form.customer_name_placeholder')),
        (t('order.form.customer_phone'), "customer_phone", "", "entry", [], t('order.form.customer_phone_placeholder')),
        (t('order.form.customer_address'), "customer_address", "", "entry", [], t('order.form.customer_address_placeholder')),
        (t('order.form.product_type') + " *", "product_type", get_product_types()[0], "combo_editable", get_product_types()),
        (t('order.form.material') + " *", "material", get_materials()[0], "combo_editable", get_materials()),
        (t('order.form.width'), "width", "", "number", [], t('order.form.width_placeholder')),
        (t('order.form.length'), "length", "", "number", [], t('order.form.length_placeholder')),
        (t('order.form.wire_diameter'), "wire_diameter", "", "number", [], t('order.form.wire_diameter_placeholder')),
        (t('order.form.mesh_size'), "mesh_size", "", "number", [], t('order.form.mesh_size_placeholder')),
        (t('order.form.quantity') + " *", "quantity", "1", "number", [], t('order.form.quantity_placeholder')),
        (t('order.form.unit_price'), "unit_price", "0", "number", [], t('order.form.unit_price_placeholder')),
        (t('order.form.unit'), "unit", "米", "combo", UNITS),
        (t('order.form.surface_treatment'), "surface_treatment", SURFACE_TREATMENTS[0], "combo", SURFACE_TREATMENTS),
        (t('order.form.delivery_date'), "delivery_date", "", "date", [], t('order.form.delivery_date_placeholder')),
        (t('order.form.special_requirements'), "special_requirements", "", "textarea", [], t('order.form.special_requirements_placeholder')),
        (t('order.form.remark'), "remark", "", "textarea", [], t('order.form.remark_placeholder')),
    ]


def get_edit_order_fields(order: dict):
    """编辑订单表单字段"""
    return [
        (t('order.form.order_no'), "order_no", order.get("order_no", ""), "readonly"),
        (t('order.form.customer_name') + " *", "customer_name", order.get("customer_name", ""), "entry", [], t('order.form.customer_name_placeholder')),
        (t('order.form.customer_phone'), "customer_phone", order.get("customer_phone", ""), "entry", [], t('order.form.customer_phone_placeholder')),
        (t('order.form.customer_address'), "customer_address", order.get("customer_address", ""), "entry", [], t('order.form.customer_address_placeholder')),
        (t('order.form.product_type') + " *", "product_type", order.get("product_type", ""), "combo_editable", get_product_types()),
        (t('order.form.material') + " *", "material", order.get("material", ""), "combo_editable", get_materials()),
        (t('order.form.width'), "width", str(order.get("width") or ""), "number", [], t('order.form.width_placeholder')),
        (t('order.form.length'), "length", str(order.get("length") or ""), "number", [], t('order.form.length_placeholder')),
        (t('order.form.wire_diameter'), "wire_diameter", str(order.get("wire_diameter") or ""), "number", [], t('order.form.wire_diameter_placeholder')),
        (t('order.form.mesh_size'), "mesh_size", str(order.get("mesh_size") or ""), "number", [], t('order.form.mesh_size_placeholder')),
        (t('order.form.quantity') + " *", "quantity", str(order.get("quantity", 1)), "number", [], t('order.form.quantity_placeholder')),
        (t('order.form.unit_price'), "unit_price", str(order.get("unit_price", 0)), "number", [], t('order.form.unit_price_placeholder')),
        (t('order.form.unit'), "unit", order.get("unit", "米"), "combo", UNITS),
        (t('order.form.surface_treatment'), "surface_treatment", order.get("surface_treatment", ""), "combo", SURFACE_TREATMENTS),
        (t('order.form.delivery_date'), "delivery_date", order.get("delivery_date", ""), "date", [], t('order.form.delivery_date_placeholder')),
        (t('order.form.status'), "status", order.get("status", OrderStatus.PENDING.value), "combo", list(ORDER_STATUS.keys())),
        (t('order.form.special_requirements'), "special_requirements", order.get("special_requirements", ""), "textarea", [], t('order.form.special_requirements_placeholder')),
        (t('order.form.remark'), "remark", order.get("remark", ""), "textarea", [], t('order.form.remark_placeholder')),
    ]
