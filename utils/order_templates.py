# -*- coding: utf-8 -*-
"""
订单模板和自定义参数管理 - 数据库版
"""
import json


DIM_FIELDS = [
    {"key": "总宽",        "label": "总宽",        "unit": "mm", "type": "number", "group": "宽度类", "required": True},
    {"key": "网带宽度",     "label": "网带宽度",    "unit": "mm", "type": "number", "group": "宽度类", "required": True},
    {"key": "钢丝直径",     "label": "钢丝直径",    "unit": "mm", "type": "number", "group": "厚度/直径", "required": True},
    {"key": "加强链片厚度", "label": "加强链片厚度", "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "链条厚度",     "label": "链条厚度",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "链板板厚",     "label": "链板板厚",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "链板网孔直径", "label": "链板网孔直径", "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "螺距",         "label": "螺距",        "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "曲轴直径",     "label": "曲轴直径",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "穿杆直径",     "label": "穿杆直径",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "主轴直径",     "label": "主轴直径",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "主齿轮直径",   "label": "主齿轮直径",  "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "辅助轮直径",   "label": "辅助轮直径",  "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "加强筋直径",   "label": "加强筋直径",  "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "网带节距",     "label": "网带节距",    "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "加强筋间距",   "label": "加强筋间距",  "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "链条距",       "label": "链条距",      "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "穿杆距",       "label": "穿杆距",      "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "中心距",       "label": "中心距",      "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "加强垫片布置", "label": "加强垫片布置", "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "扣间隙",       "label": "扣间隙",      "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "链条直径",     "label": "链条直径",    "unit": "mm", "type": "number", "group": "厚度/直径"},
    {"key": "节距",         "label": "节距",        "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "目数",         "label": "目数",        "unit": "目", "type": "number", "group": "间距类"},
    {"key": "网孔尺寸",     "label": "网孔尺寸",    "unit": "mm", "type": "number", "group": "间距类"},
    {"key": "总长度",       "label": "总长度",      "unit": "mm", "type": "number", "group": "长度类", "required": True},
    {"key": "折边长度",     "label": "折边长度",    "unit": "mm", "type": "number", "group": "长度类"},
    {"key": "单段长度",     "label": "单段长度",     "unit": "m", "type": "number", "group": "长度类"},
    {"key": "网带段数",     "label": "网带段数",     "unit": "段", "type": "number", "group": "数量类"},
    {"key": "网带排数",     "label": "网带排数",    "unit": "条", "type": "number", "group": "数量类"},
    {"key": "加强筋数量",   "label": "加强筋数量",  "unit": "条", "type": "number", "group": "数量类"},
    {"key": "主齿轮齿数",   "label": "主齿轮齿数",  "unit": "齿", "type": "number", "group": "数量类"},
    {"key": "主齿轮数量",   "label": "主齿轮数量",  "unit": "套", "type": "number", "group": "数量类"},
    {"key": "辅助齿轮齿数", "label": "辅助齿轮齿数", "unit": "齿", "type": "number", "group": "数量类"},
    {"key": "辅助轮数量",   "label": "辅助轮数量",  "unit": "个", "type": "number", "group": "数量类"},
    {"key": "横杆数量",     "label": "横杆数量",    "unit": "根", "type": "number", "group": "数量类"},
    {"key": "挡板高度",     "label": "挡板高度",    "unit": "mm", "type": "number", "group": "挡板类"},
    {"key": "挡板厚度",     "label": "挡板厚度",    "unit": "mm", "type": "number", "group": "挡板类"},
    {"key": "链板网孔规格", "label": "链板网孔规格", "unit": "mm", "type": "number", "group": "链板类"},
    {"key": "裙边高度",     "label": "裙边高度",    "unit": "mm", "type": "number", "group": "裙边类"},
    {"key": "裙边厚度",     "label": "裙边厚度",    "unit": "mm", "type": "number", "group": "裙边类"},
    {"key": "裙边宽度",     "label": "裙边宽度",    "unit": "mm", "type": "number", "group": "裙边类"},
]

MATERIAL_FIELDS = [
    {"key": "曲轴材质",     "label": "曲轴材质",     "type": "dropdown", "group": "材质类"},
    {"key": "网丝材质",     "label": "网丝材质",     "type": "dropdown", "group": "材质类"},
    {"key": "穿杆材质",     "label": "穿杆材质",     "type": "dropdown", "group": "材质类"},
    {"key": "链条材质",     "label": "链条材质",     "type": "dropdown", "group": "材质类"},
    {"key": "主齿轮材质",   "label": "主齿轮材质",   "type": "dropdown", "group": "材质类"},
    {"key": "挡板材质",     "label": "挡板材质",     "type": "dropdown", "group": "材质类"},
    {"key": "辅助轮材质",   "label": "辅助轮材质",   "type": "dropdown", "group": "材质类"},
    {"key": "加强筋材质",   "label": "加强筋材质",   "type": "dropdown", "group": "材质类"},
    {"key": "链板材质",     "label": "链板材质",     "type": "dropdown", "group": "材质类"},
    {"key": "裙边材质",     "label": "裙边材质",     "type": "dropdown", "group": "材质类"},
]

SURFACE_FIELD = [
    {"key": "表面处理", "label": "表面处理", "type": "dropdown"},
]

def get_surface_field():
    """获取表面处理字段配置（动态从数据库加载选项）"""
    from utils.custom_types import get_surface_treatment_options
    options = get_surface_treatment_options()
    return [{"key": "表面处理", "label": "表面处理", "type": "combo_editable", "options": options}]


SURFACE_OPTS = [
    "无处理", "镀锌", "抛光", "钝化", "喷漆", "电泳", "磷化", "其他"
]

MATERIAL_OPTS = [
    "304不锈钢", "316不锈钢", "316L不锈钢", "310S不锈钢",
    "201不锈钢", "碳钢镀锌", "铝合金", "铜合金", "钛合金", "其他"
]


def get_common_fields():
    return [
        {"key": "customer_name",    "label": "客户名称 *",  "type": "entry",    "required": True,  "placeholder": "如：振华机械"},
        {"key": "customer_phone",  "label": "联系电话",    "type": "entry",    "placeholder": "如：13800138000"},
        {"key": "customer_address", "label": "客户地址",    "type": "entry",    "placeholder": "如：广东省深圳市"},
        {"key": "customer_group",   "label": "客户分组",    "type": "entry"},
        {"key": "quantity",         "label": "数　　量 *", "type": "number",   "required": True,  "placeholder": "如：100"},
        {"key": "unit_price",       "label": "单价(元)",    "type": "number"},
        {"key": "material",         "label": "材　　质",    "type": "combo_editable", "options": MATERIAL_OPTS},
        {"key": "delivery_date",    "label": "交货日期",    "type": "date"},
    ]


def get_remark_fields():
    return [
        {"key": "remark",           "label": "订单备注",   "type": "textarea"},
        {"key": "product_remark",   "label": "产品备注",   "type": "textarea", "placeholder": "详细描述产品规格、特殊要求等（产品专属备注，与订单备注区分）"},
    ]


# ══════════════════════════════════════════════════════════════
# 数据库操作函数
# ══════════════════════════════════════════════════════════════

def _get_db():
    from models.database import get_connection
    return get_connection()


# ══════════════════════════════════════════════════════════════
# 模板管理（保存/加载/管理 预设参数组合）
# ══════════════════════════════════════════════════════════════

def get_template_names(product_type: str) -> list:
    """获取指定产品类型的模板名称列表"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT template_name FROM order_templates WHERE product_type = %s ORDER BY template_name",
        (product_type,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if rows:
        if isinstance(rows[0], dict):
            return [row['template_name'] for row in rows]
        return [row[0] for row in rows]
    return []


def get_template(product_type: str, name: str) -> dict:
    """获取模板数据"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT values_json, order_json FROM order_templates WHERE product_type = %s AND template_name = %s",
        (product_type, name)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return {}
    values = json.loads(row['values_json']) if row['values_json'] else {}
    order = json.loads(row['order_json']) if row['order_json'] else {}
    return {"values": values, "order": order}


def save_template(product_type: str, name: str, values: dict, order: dict = None) -> tuple:
    """保存模板"""
    if not name.strip():
        return False, "模板名称不能为空"
    conn = _get_db()
    values_json = json.dumps(values or {}, ensure_ascii=False)
    order_json = json.dumps(order or {}, ensure_ascii=False)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO order_templates (product_type, template_name, values_json, order_json)
            VALUES (%s, %s, %s, %s)
        """, (product_type, name.strip(), values_json, order_json))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"模板「{name}」已保存"
    except Exception as e:
        conn.close()
        return False, f"模板「{name}」已存在，请使用其他名称"


def rename_template(product_type: str, old_name: str, new_name: str) -> tuple:
    """重命名模板"""
    if not new_name.strip():
        return False, "新名称不能为空"
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE order_templates SET template_name = %s WHERE product_type = %s AND template_name = %s",
                   (new_name.strip(), product_type, old_name))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "重命名成功"


def delete_template(product_type: str, name: str) -> tuple:
    """删除模板"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM order_templates WHERE product_type = %s AND template_name = %s",
                   (product_type, name))
    conn.commit()
    cursor.close()
    conn.close()
    return True, f"模板「{name}」已删除"


# ══════════════════════════════════════════════════════════════
# 自定义参数管理（尺寸参数 + 材质参数）
# ══════════════════════════════════════════════════════════════

def get_custom_params() -> list:
    """获取所有自定义参数列表"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT params_json FROM custom_params ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        if isinstance(row, dict):
            raw = row.get("params_json", "")
        else:
            raw = row[0] if row else ""
        if raw:
            return json.loads(raw)
    return []


def get_custom_material_params() -> list:
    """获取所有自定义材质参数列表（返回key列表）"""
    custom_params = get_custom_params()
    result = []
    for p in custom_params:
        if isinstance(p, dict):
            key = p.get("key", "")
        elif isinstance(p, str):
            key = p
        else:
            continue
        if key:
            result.append(key)
    return result


def get_custom_all_params() -> list:
    """获取所有自定义参数列表（包括尺寸和材质）"""
    return get_custom_params()


def get_custom_dim_params() -> list:
    """获取所有自定义尺寸参数列表"""
    return get_custom_params()


def save_custom_params(params: list) -> tuple:
    """保存自定义参数列表"""
    conn = _get_db()
    params_json = json.dumps(params, ensure_ascii=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM custom_params ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE custom_params SET params_json = %s WHERE id = %s",
                       (params_json, row[0]))
    else:
        cursor.execute("INSERT INTO custom_params (params_json) VALUES (%s)", (params_json,))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "已保存"


# ══════════════════════════════════════════════════════════════
# 预设模板数据（用于初始化和产品类型选择）
# ══════════════════════════════════════════════════════════════

def get_all_product_types() -> list:
    """获取所有产品类型列表"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM product_types ORDER BY name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if rows:
        if isinstance(rows[0], dict):
            return [row['name'] for row in rows]
        return [row[0] for row in rows]
    return []


def get_preset_fields(product_type: str) -> dict:
    """获取指定产品类型的预设字段"""
    return {
        "眼镜网带": {
            "dim_fields": [f for f in DIM_FIELDS if f["key"] in ["总宽", "钢丝直径", "加强筋数量", "节距"]],
            "mat_fields": [f for f in MATERIAL_FIELDS if f["key"] in ["材料名称", "材质"]],
            "surface_field": SURFACE_FIELD
        },
        "人字形网带": {
            "dim_fields": [f for f in DIM_FIELDS if f["key"] in ["总宽", "净宽", "钢丝直径", "目数", "总长度"]],
            "mat_fields": [f for f in MATERIAL_FIELDS if f["key"] in ["材料名称", "材质"]],
            "surface_field": SURFACE_FIELD
        }
    }.get(product_type, {
        "dim_fields": DIM_FIELDS[:5],
        "mat_fields": MATERIAL_FIELDS,
        "surface_field": SURFACE_FIELD
    })


def init_preset_data():
    """初始化预设数据到数据库"""
    from models.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()

    # 插入预设产品类型
    cursor.execute("SELECT COUNT(*) FROM product_types")
    if cursor.fetchone()[0] == 0:
        preset_types = ["眼镜网带", "人字形网带", "乙字形网带", "平板型网带", "链板式网带", "冷冻螺旋网"]
        for name in preset_types:
            cursor.execute("INSERT INTO product_types (name, is_preset) VALUES (%s, 1)", (name,))
        conn.commit()

    cursor.close()
    conn.close()
