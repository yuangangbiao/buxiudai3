# -*- coding: utf-8 -*-
"""
订单确认弹窗
"""
import tkinter as tk
from tkinter import ttk
from config import COLORS, FONTS
from models.order import OrderDAO
from constants import OrderStatus
from desktop.views.dialogs import alert
from utils.helpers import format_spec
from utils.order_templates import DIM_FIELDS, MATERIAL_FIELDS, SURFACE_FIELD
from utils.copyable_widgets import ReadonlyEntry
import json


def show_order_confirm(parent, order: dict):
    """订单确认界面 - 用于进一步确认订单并下单"""
    # 检查parent窗口是否有效
    try:
        if not parent.winfo_exists():
            parent = None
    except Exception:
        parent = None
    top = tk.Toplevel(parent)
    top.title("订单确认")
    from utils.window_manager import setup_resizable_window
    setup_resizable_window(top, "order_confirm", "700x750")
    top.transient(parent)
    top.grab_set()

    # 解析 extra_params
    extra = order.get("extra_params") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}

    main_frame = tk.Frame(top, bg=COLORS["bg_main"])
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # 创建 Canvas + Scrollbar 支持滚动
    canvas = tk.Canvas(main_frame, bg=COLORS["bg_main"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_main"])

    def update_scrollregion(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    scrollable_frame.bind("<Configure>", update_scrollregion)
    canvas.bind("<Configure>", update_scrollregion)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 标题
    tk.Label(scrollable_frame, text="📋 订单确认", font=FONTS["large"],
             bg=COLORS["bg_main"], fg=COLORS["primary"]).pack(pady=(10, 5))

    tk.Label(scrollable_frame, text=f"订单号：{order.get('order_no', '')}",
             font=FONTS["subtitle"], bg=COLORS["bg_main"], fg=COLORS["primary"]).pack(pady=2)

    current_status = order.get("status", OrderStatus.PENDING.value)
    tk.Label(scrollable_frame, text=f"当前状态：{current_status}",
             font=FONTS["body"], bg=COLORS["bg_main"], fg="#E65100").pack(pady=2)

    # ===== 基本信息卡片 =====
    card1 = tk.LabelFrame(scrollable_frame, text="👤 基本信息", font=FONTS["subtitle"],
                         bg="white", padx=15, pady=10)
    card1.pack(fill=tk.X, pady=(10, 5), padx=5)

    info_rows = [
        ("客户名称", order.get("customer_name", "")),
        ("联系电话", order.get("customer_phone", "") or "-"),
        ("客户地址", order.get("customer_address", "") or "-"),
        ("交货日期", order.get("delivery_date", "") or "-"),
    ]

    for label, value in info_rows:
        row = tk.Frame(card1, bg="white")
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label + "：", font=FONTS["body"], bg="white",
                anchor="w", width=10).pack(side=tk.LEFT)
        ReadonlyEntry(row, text=value, font=FONTS["body"], bg="#F0F0F0",
                relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 产品信息卡片 =====
    card2 = tk.LabelFrame(scrollable_frame, text="📦 产品信息", font=FONTS["subtitle"],
                         bg="white", padx=15, pady=10)
    card2.pack(fill=tk.X, pady=5, padx=5)

    product_rows = [
        ("产品类型", order.get("product_type", "")),
        ("材　　质", order.get("material", "") or "-"),
        ("数　　量", f"{order.get('quantity', 0)} {order.get('unit', '米')}"),
        ("单　　价", f"¥{order.get('unit_price', 0)}"),
        ("总　　价", f"¥{order.get('total_amount', 0)}"),
    ]

    for label, value in product_rows:
        row = tk.Frame(card2, bg="white")
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label + "：", font=FONTS["body"], bg="white",
                anchor="w", width=10).pack(side=tk.LEFT)
        ReadonlyEntry(row, text=value, font=FONTS["body"], bg="#F0F0F0",
                relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 规格明细卡片 =====
    spec = format_spec(order)
    if spec:
        row = tk.Frame(card2, bg="white")
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text="规　　格：", font=FONTS["body"], bg="white",
                anchor="w", width=10).pack(side=tk.LEFT)
        ReadonlyEntry(row, text=spec, font=FONTS["body"], bg="#FFF9C4",
                relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 尺寸参数卡片 =====
    dim_unit_map = {fd["key"]: fd.get("unit", "") for fd in DIM_FIELDS}
    dim_keys = {fd["key"] for fd in DIM_FIELDS}
    dim_params = {k: v for k, v in extra.items() if k in dim_keys and v}

    if dim_params:
        card3 = tk.LabelFrame(scrollable_frame, text="📏 尺寸参数", font=FONTS["subtitle"],
                             bg="white", padx=15, pady=10)
        card3.pack(fill=tk.X, pady=5, padx=5)

        for key, value in dim_params.items():
            row = tk.Frame(card3, bg="white")
            row.pack(fill=tk.X, pady=2)
            label_text = key
            unit = dim_unit_map.get(key, "")
            if unit:
                label_text += f" ({unit})"
            tk.Label(row, text=label_text, font=FONTS["body"], bg="white",
                    anchor="w", width=14).pack(side=tk.LEFT)
            ReadonlyEntry(row, text=str(value), font=FONTS["body"], bg="#E3F2FD",
                    relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 材质参数卡片 =====
    mat_keys = {fd["key"] for fd in MATERIAL_FIELDS}
    mat_params = {k: v for k, v in extra.items() if k in mat_keys and v}

    if mat_params:
        card4 = tk.LabelFrame(scrollable_frame, text="🔩 材质参数", font=FONTS["subtitle"],
                             bg="white", padx=15, pady=10)
        card4.pack(fill=tk.X, pady=5, padx=5)

        for key, value in mat_params.items():
            row = tk.Frame(card4, bg="white")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=key, font=FONTS["body"], bg="white",
                    anchor="w", width=14).pack(side=tk.LEFT)
            ReadonlyEntry(row, text=str(value), font=FONTS["body"], bg="#E8F5E9",
                    relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 表面处理卡片 =====
    surface_keys = {fd["key"] for fd in SURFACE_FIELD}
    surface_val = order.get("surface_treatment", "")
    surface_params = {k: v for k, v in extra.items() if k in surface_keys and v}

    if surface_val or surface_params:
        card5 = tk.LabelFrame(scrollable_frame, text="✨ 表面处理", font=FONTS["subtitle"],
                             bg="white", padx=15, pady=10)
        card5.pack(fill=tk.X, pady=5, padx=5)

        if surface_val:
            row = tk.Frame(card5, bg="white")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text="处理方式", font=FONTS["body"], bg="white",
                    anchor="w", width=14).pack(side=tk.LEFT)
            ReadonlyEntry(row, text=surface_val, font=FONTS["body"], bg="#FCE4EC",
                    relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

        for key, value in surface_params.items():
            row = tk.Frame(card5, bg="white")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=key, font=FONTS["body"], bg="white",
                    anchor="w", width=14).pack(side=tk.LEFT)
            ReadonlyEntry(row, text=str(value), font=FONTS["body"], bg="#FCE4EC",
                    relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 特殊要求/备注卡片 =====
    special = order.get("special_requirements", "")
    remark = order.get("remark", "")

    if special or remark:
        card6 = tk.LabelFrame(scrollable_frame, text="📝 其他信息", font=FONTS["subtitle"],
                             bg="white", padx=15, pady=10)
        card6.pack(fill=tk.X, pady=5, padx=5)

        if special:
            tk.Label(card6, text="特殊要求：", font=FONTS["body"], bg="white",
                    anchor="w").pack(anchor="w")
            ReadonlyEntry(card6, text=special, font=FONTS["body"], bg="#FFF3E0",
                    relief=tk.SUNKEN, padx=8).pack(fill=tk.X, pady=(2, 5))

        if remark:
            tk.Label(card6, text="备　　注：", font=FONTS["body"], bg="white",
                    anchor="w").pack(anchor="w")
            ReadonlyEntry(card6, text=remark, font=FONTS["body"], bg="#F5F5F5",
                    relief=tk.SUNKEN, padx=8).pack(fill=tk.X, pady=2)

    # ===== 生产统计卡片 =====
    stats = OrderDAO.get_order_statistics(order.get("id"))
    process_details = stats.get("process_details", [])

    card7 = tk.LabelFrame(scrollable_frame, text="📊 生产统计", font=FONTS["subtitle"],
                         bg="white", padx=15, pady=10)
    card7.pack(fill=tk.X, pady=5, padx=5)

    stats_row = tk.Frame(card7, bg="white")
    stats_row.pack(fill=tk.X, pady=2)
    tk.Label(stats_row, text="订单用时：", font=FONTS["body"], bg="white",
            anchor="w", width=12).pack(side=tk.LEFT)
    order_days = f"{stats.get('order_total_days')} 天" if stats.get('order_total_days') is not None else "无"
    ReadonlyEntry(stats_row, text=order_days, font=FONTS["body"], bg="#E8F5E9",
            relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    stats_row2 = tk.Frame(card7, bg="white")
    stats_row2.pack(fill=tk.X, pady=2)
    tk.Label(stats_row2, text="生产用时：", font=FONTS["body"], bg="white",
            anchor="w", width=12).pack(side=tk.LEFT)
    prod_days = f"{stats.get('production_total_days')} 天" if stats.get('production_total_days') is not None else "无"
    ReadonlyEntry(stats_row2, text=prod_days, font=FONTS["body"], bg="#E8F5E9",
            relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    stats_row3 = tk.Frame(card7, bg="white")
    stats_row3.pack(fill=tk.X, pady=2)
    tk.Label(stats_row3, text="总损耗率：", font=FONTS["body"], bg="white",
            anchor="w", width=12).pack(side=tk.LEFT)
    loss_rate = f"{stats.get('loss_rate')}%" if stats.get('loss_rate') is not None else "无"
    ReadonlyEntry(stats_row3, text=loss_rate, font=FONTS["body"], bg="#FFF3E0",
            relief=tk.SUNKEN, padx=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ===== 工序详情卡片 =====
    if process_details:
        card8 = tk.LabelFrame(scrollable_frame, text="⚙️ 工序详情", font=FONTS["subtitle"],
                             bg="white", padx=15, pady=10)
        card8.pack(fill=tk.X, pady=5, padx=5)

        for p in process_details:
            p_frame = tk.Frame(card8, bg="#FAFAFA", relief=tk.GROOVE, bd=1)
            p_frame.pack(fill=tk.X, pady=3, padx=2)

            header = tk.Frame(p_frame, bg="#FAFAFA")
            header.pack(fill=tk.X, padx=5, pady=3)
            tk.Label(header, text=f"【{p.get('process_name', '未知工序')}】",
                    font=FONTS["normal_bold"], bg="#FAFAFA", fg=COLORS["primary"]).pack(side=tk.LEFT)
            status = p.get("status", "待开始")
            status_color = "#4CAF50" if status == "已完成" else ("#2196F3" if status == "进行中" else "#999999")
            tk.Label(header, text=status, font=FONTS["small"], bg="#FAFAFA",
                    fg=status_color).pack(side=tk.RIGHT)

            detail_row1 = tk.Frame(p_frame, bg="#FAFAFA")
            detail_row1.pack(fill=tk.X, padx=5, pady=1)
            tk.Label(detail_row1, text="用时：", font=FONTS["small"], bg="#FAFAFA",
                    width=8, anchor="w").pack(side=tk.LEFT)
            duration = f"{p.get('duration_days')} 天" if p.get('duration_days') is not None else "无"
            tk.Label(detail_row1, text=duration, font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT)

            tk.Label(detail_row1, text="｜合格率：", font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT, padx=(10, 0))
            pass_rate = f"{p.get('pass_rate')}%" if p.get('pass_rate') is not None else "无"
            pass_color = "#4CAF50" if p.get('pass_rate') and p.get('pass_rate') >= 90 else ("#FF9800" if p.get('pass_rate') and p.get('pass_rate') >= 70 else "#F44336")
            tk.Label(detail_row1, text=pass_rate, font=FONTS["small"], bg="#FAFAFA",
                    fg=pass_color if p.get('pass_rate') else "#666").pack(side=tk.LEFT)

            tk.Label(detail_row1, text="｜损耗率：", font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT, padx=(10, 0))
            loss = f"{p.get('loss_rate')}%" if p.get('loss_rate') is not None else "无"
            tk.Label(detail_row1, text=loss, font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT)

            detail_row2 = tk.Frame(p_frame, bg="#FAFAFA")
            detail_row2.pack(fill=tk.X, padx=5, pady=1)
            tk.Label(detail_row2, text="完成量：", font=FONTS["small"], bg="#FAFAFA",
                    width=8, anchor="w").pack(side=tk.LEFT)
            tk.Label(detail_row2, text=f"{p.get('completed_qty', 0)}", font=FONTS["small"],
                    bg="#FAFAFA").pack(side=tk.LEFT)

            tk.Label(detail_row2, text="｜合格量：", font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT, padx=(10, 0))
            tk.Label(detail_row2, text=f"{p.get('qualified_qty', 0)}", font=FONTS["small"],
                    bg="#FAFAFA").pack(side=tk.LEFT)

            tk.Label(detail_row2, text="｜用料：", font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT, padx=(10, 0))
            material = p.get('material_usage', 0) or 0
            tk.Label(detail_row2, text=f"{material} kg", font=FONTS["small"], bg="#FAFAFA").pack(side=tk.LEFT)

    # 鼠标滚轮支持
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<MouseWheel>", on_mousewheel)

    # 提示
    tip_frame = tk.Frame(scrollable_frame, bg="#E3F2FD", pady=8)
    tip_frame.pack(fill=tk.X, pady=10, padx=5)
    tk.Label(tip_frame, text="💡 请仔细核对订单信息，确认无误后点击「确认订单」安排生产",
             font=FONTS["small"], bg="#E3F2FD", fg="#1976D2").pack()

    # 按钮
    btn_frame = tk.Frame(scrollable_frame, bg=COLORS["bg_main"])
    btn_frame.pack(pady=10)

    def on_edit():
        """编辑订单"""
        top.destroy()
        # 关闭确认弹窗后打开编辑对话框
        from .new_order_dialog import NewOrderDialog
        def on_save(data):
            # 基本校验
            if not data.get("customer_name"):
                from desktop.views.dialogs import alert
                alert("请填写客户名称！", "必填项")
                return
            try:
                # 保存到数据库（OrderDAO.update 内部自动计算 total_amount）
                OrderDAO.update(order["id"], data)
            except Exception as e:
                from desktop.views.dialogs import alert
                alert(f"保存失败：{str(e)}", "错误")
                return

            # 刷新列表并重新打开确认界面
            if parent and hasattr(parent, 'load_orders'):
                parent.load_orders()
            updated_order = OrderDAO.get_by_id(order["id"])
            if updated_order:
                show_order_confirm(parent, updated_order)

        NewOrderDialog(parent, on_save, order)

    def _auto_publish_to_dispatch(order_data):
        """自动发布订单任务到调度中心"""
        import os
        import requests

        if os.getenv('AUTO_PUBLISH_ORDER', '0') != '1':
            return

        try:
            container_url = os.getenv('CONTAINER_URL', 'http://localhost:5002')
            api_key = os.getenv('CONTAINER_API_KEY', '')

            task_content = {
                "order_no": order_data.get("order_no", ""),
                "product_type": order_data.get("product_type", ""),
                "material": order_data.get("material", ""),
                "spec": order_data.get("spec", ""),
                "quantity": order_data.get("quantity", 0),
                "unit": order_data.get("unit", "米"),
                "delivery_date": order_data.get("delivery_date", ""),
                "surface_treatment": order_data.get("surface_treatment", ""),
                "extra_params": order_data.get("extra_params", {}),
                "special_requirements": order_data.get("special_requirements", ""),
            }

            url = f"{container_url.rstrip('/')}/api/internal/publish"
            headers = {"X-API-Key": api_key} if api_key else {}
            payload = {
                "data_type": "order_production",
                "title": f"订单排产：{order_data.get('order_no', '')}",
                "content": task_content,
                "priority": "normal",
                "source": "主软件_订单管理"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                print(f"✅ 订单 {order_data.get('order_no', '')} 已自动发布到调度中心")
            else:
                print(f"⚠️ 自动发布失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️ 自动发布异常: {str(e)}")

    def on_confirm():
        # 检查必填尺寸参数 - 只有已添加到订单中的才验证
        extra = json.loads(order.get("extra_params", "{}")) if isinstance(order.get("extra_params"), str) else order.get("extra_params", {})
        required_in_order = [fd for fd in DIM_FIELDS if fd.get("required") and fd["key"] in extra and not extra[fd["key"]]]
        missing = [f"「{fd['label']}」" for fd in required_in_order]
        if missing:
            alert(f"以下必填参数未填写：\n{', '.join(missing)}", "必填项")
            return
        try:
            result = OrderDAO.update_status(order["id"], OrderStatus.CONFIRMED.value)
            if result:
                top.destroy()
                if parent and hasattr(parent, 'load_orders'):
                    parent.load_orders()

                _auto_publish_to_dispatch(order)

                alert(f"✅ 订单已{OrderStatus.CONFIRMED.value}！可进入「生产排单」安排生产。", "确认成功")
            else:
                alert("确认失败，请重试。", "错误")
        except Exception as e:
            alert(f"确认失败：{str(e)}", "错误")

    def on_cancel():
        top.destroy()

    ttk.Button(btn_frame, text="✏️ 编辑订单", command=on_edit,
              width=12).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="✓ 确认订单", command=on_confirm,
              style="Success.TButton", width=15).pack(side=tk.LEFT, padx=10)
    
    def on_calculate_materials():
        """计算物料"""
        from utils.material_calculator import MaterialCalculator
        from tkinter import messagebox
        
        product_type = order.get("product_type", "")
        
        if not product_type:
            messagebox.showwarning("提示", "订单中没有产品类型信息")
            return
        
        order_params = {
            "product_type": product_type,
            "quantity": order.get("quantity", 0),
            "unit": order.get("unit", "米")
        }
        
        extra = order.get("extra_params") or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except Exception:
                extra = {}
        
        order_params.update(extra)
        
        calculator = MaterialCalculator(order_params)
        materials = calculator.calculate_material_types()
        
        if not materials:
            messagebox.showinfo("提示", f"产品类型「{product_type}」暂未配置物料计算规则\n\n请先在「材料备料」→「物料规则」中配置规则")
            return
        
        preview_text = f"根据订单参数，将添加以下物料：\n\n"
        preview_text += f"产品类型：{product_type}\n"
        preview_text += f"━━━━━━━━━━━━━━━\n"
        for m in materials:
            display = MaterialCalculator.format_material_display(m)
            preview_text += f"• {display}\n"
        preview_text += f"━━━━━━━━━━━━━━━\n"
        preview_text += f"共计：{len(materials)} 种物料"
        
        confirm = messagebox.askyesno("确认计算物料", preview_text)
        if not confirm:
            return
        
        from models.database import get_connection
        from datetime import datetime
        conn = get_connection()
        cursor = conn.cursor()
        added_count = 0

        for m in materials:
            material_name = m["material_name"]
            spec_value = m.get("spec_value")
            spec_unit = m.get("spec_unit", "")

            spec_text = ""
            if spec_value:
                spec_text = f"{spec_value}{spec_unit}"

            try:
                cursor.execute("""
                    INSERT INTO order_materials (order_id, material_name, spec, unit,
                        required_qty, prepared_qty, status, created_at)
                    VALUES (%s, %s, %s, %s, 0, 0, '待备料', %s)
                """, (order["id"], material_name, spec_text, "待定", datetime.now().isoformat()))
                added_count += 1
            except Exception:
                pass

        conn.commit()
        cursor.close()
        conn.close()
        
        if added_count > 0:
            messagebox.showinfo("成功", f"已添加 {added_count} 种物料到备料清单\n\n请在「材料备料」中查看并完善数量")
        else:
            messagebox.showwarning("提示", "未能添加物料，可能已存在相同的物料记录")
    
    ttk.Button(btn_frame, text="🔧 计算物料", command=on_calculate_materials,
              width=12).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="取消", command=on_cancel,
              width=10).pack(side=tk.LEFT, padx=10)
