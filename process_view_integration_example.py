# -*- coding: utf-8 -*-
"""
工序视图容器集成示例

此文件展示如何在 views/process_view.py 中集成容器池功能
"""

# ──────────────────────────────────────────────────────────────
# 1. 在process_view.py的顶部添加导入
# ──────────────────────────────────────────────────────────────
"""
# 在现有的import之后添加：
try:
    from desktop_container_integration import get_integration
    CONTAINER_AVAILABLE = True
except ImportError as e:
    print(f'[容器集成] 模块不可用: {e}')
    CONTAINER_AVAILABLE = False
"""

# ──────────────────────────────────────────────────────────────
# 2. 在ProcessView类的__init__中初始化容器集成
# ──────────────────────────────────────────────────────────────
"""
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.current_order_id = None
        self.current_prod_id = None
        self.templates = None
        self._cached_order = None
        self._cached_records = None
        self._search_after_id = None
        
        # 初始化容器集成
        self.container_integration = None
        if CONTAINER_AVAILABLE:
            try:
                self.container_integration = get_integration()
                print('[工序视图] 容器集成已就绪')
            except Exception as e:
                print(f'[工序视图] 容器集成初始化失败: {e}')
        
        self.init_ui()
        self.load_orders()
"""

# ──────────────────────────────────────────────────────────────
# 3. 添加发布任务的方法到ProcessView类
# ──────────────────────────────────────────────────────────────
"""
    def _publish_task_to_container(self, process_data: dict) -> Optional[str]:
        """
        发布工序任务到容器池
        
        Args:
            process_data: 工序数据字典，包含：
                - work_order_no: 订单号
                - process_name: 工序名称
                - planned_qty: 计划数量
                - operator_id: 操作员ID
                - operator_name: 操作员名称
                - order_no: 订单号
                - customer_name: 客户名称
                - product_type: 产品类型
                - quantity: 订单数量
                - unit: 单位
        
        Returns:
            任务ID，失败返回None
        """
        if not self.container_integration or not self.container_integration.is_available:
            print('[工序视图] 容器集成不可用，跳过发布')
            return None
        
        try:
            task_id = self.container_integration.publish_report_task(
                order_no=process_data.get('order_no', ''),
                order_no=process_data.get('order_no', ''),
                process_name=process_data.get('process_name', ''),
                customer_name=process_data.get('customer_name', ''),
                product_type=process_data.get('product_type', ''),
                quantity=process_data.get('quantity', 0),
                unit=process_data.get('unit', ''),
                planned_qty=process_data.get('planned_qty', 0),
                process_status='待开始',
                operator_id=process_data.get('operator_id', 'OP001'),
                operator_name=process_data.get('operator_name', ''),
                priority='normal'
            )
            
            # 如果是编织或定型工序，也发布质检任务
            if process_data.get('process_name') in ['编织', '定型']:
                print('[工序视图] 工序需要质检，自动发布质检任务')
                self.container_integration.publish_quality_task(
                    order_no=process_data.get('order_no', ''),
                    order_no=process_data.get('order_no', ''),
                    customer_name=process_data.get('customer_name', ''),
                    product_type=process_data.get('product_type', ''),
                    inspection_type='终检',
                    operator_id='OP004',
                    operator_name='质检'
                )
            
            return task_id
            
        except Exception as e:
            print(f'[工序视图] 发布任务失败: {e}')
            return None
"""

# ──────────────────────────────────────────────────────────────
# 4. 修改_add_process方法，在添加工序后发布任务
# ──────────────────────────────────────────────────────────────
"""
    def _add_process(self):
        \"\"\"添加工序\"\"\"
        if not self.current_order_id:
            alert('请先选择订单！')
            return
        
        # ... 现有的表单创建代码 ...
        
        # 假设form_data是表单返回的工序数据
        # form_data = ...
        
        # 保存工序到数据库
        # process_id = ProcessDAO.create(form_data)
        
        # ====== 新增：发布任务到容器池 ======
        if self.container_integration and self.container_integration.is_available:
            # 获取订单信息
            order = self._cached_order or OrderDAO.get_by_id(self.current_order_id)
            prod = self._cached_prod or ProductionDAO.get_by_order_id(self.current_order_id)
            
            if order and prod:
                task_data = {
                    'order_no': order.get('order_no', ''),
                    'order_no': prod.get('order_no', ''),
                    'process_name': form_data.get('process_name', ''),
                    'customer_name': order.get('customer_name', ''),
                    'product_type': order.get('product_type', ''),
                    'quantity': order.get('quantity', 0),
                    'unit': order.get('unit', ''),
                    'planned_qty': form_data.get('planned_qty', 0),
                    'operator_id': form_data.get('operator_id', 'OP001'),
                    'operator_name': form_data.get('worker', ''),
                }
                
                task_id = self._publish_task_to_container(task_data)
                
                if task_id:
                    print(f'[工序视图] 任务已发布到容器池: {task_id}')
                else:
                    print(f'[工序视图] 任务发布失败')
        
        # 刷新列表
        self.load_processes()
        self._show_order_info()
"""

# ──────────────────────────────────────────────────────────────
# 5. 在header中添加容器池状态按钮（可选）
# ──────────────────────────────────────────────────────────────
"""
        # 在__init__的header按钮组中添加：
        if CONTAINER_AVAILABLE:
            tk.Button(btn_frame, text="📦 容器池", font=FONTS["body"], 
                    bg="#546E7A", fg=COLORS["text_white"], relief=tk.FLAT, padx=8, pady=3,
                    cursor="hand2", command=self._show_container_status).pack(side=tk.LEFT, padx=2)
    
    def _show_container_status(self):
        \"\"\"显示容器池状态\"\"\"
        if not self.container_integration or not self.container_integration.is_available:
            alert('容器集成不可用！')
            return
        
        self.container_integration.show_status()
        messagebox.showinfo('容器池状态', '状态已打印到控制台！')
"""

print('=' * 60)
print('工序视图集成示例')
print('=' * 60)
print('\n请查看此文件中的代码注释，了解如何集成容器池功能！\n')

