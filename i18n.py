# -*- coding: utf-8 -*-
"""
国际化模块 - 简体中文
"""

# 翻译字典
_translations = {
    # 订单表单
    'order.form.order_no': '订单编号',
    'order.form.customer_name': '客户名称',
    'order.form.customer_name_placeholder': '请输入客户名称',
    'order.form.customer_phone': '联系电话',
    'order.form.customer_phone_placeholder': '请输入联系电话',
    'order.form.customer_address': '客户地址',
    'order.form.customer_address_placeholder': '请输入客户地址',
    'order.form.product_type': '产品类型',
    'order.form.material': '材质',
    
    # 订单列表表头
    'order.columns.order_no': '订单编号',
    'order.columns.customer': '客户名称',
    'order.columns.product': '产品类型',
    'order.columns.material': '材质',
    'order.columns.spec': '规格参数',
    'order.columns.qty': '数量',
    'order.columns.amount': '金额',
    'order.columns.delivery': '交货日期',
    'order.columns.status': '状态',
    
    # 订单列表标题和操作
    'order.title': '订单管理',
    'order.status': '状态',
    'order.status_all': '全部',
    'order.search': '搜索',
    'order.reset': '重置',
    
    # 生产排产表头
    'production.columns.wo_no': '订单号',
    'production.columns.order_no': '订单编号',
    'production.columns.customer': '客户',
    'production.columns.product': '产品',
    'production.columns.qty': '数量',
    'production.columns.priority': '优先级',
    'production.columns.plan_start': '计划开始',
    'production.columns.plan_end': '计划完成',
    'production.columns.actual_start': '实际开始时间',
    'production.columns.status': '状态',
    
    # 生产选择表头
    'production.select_columns.no': '订单号',
    'production.select_columns.customer': '客户',
    'production.select_columns.product': '产品',
    'production.select_columns.material': '材质',
    'production.select_columns.qty': '数量',
    'production.select_columns.amount': '金额',
    'production.select_columns.delivery': '交货日期',
    'production.select_columns.status': '状态',
    
    # 生产排产标题和操作
    'production.title': '生产排产',
    'production.status': '状态',
    'production.keyword': '关键词',
    'production.select_title': '选择订单并排产',
    'production.detail_title': '订单详情',
    
    # 生产排产详情字段
    'production.detail_fields.order_no': '订单编号',
    'production.detail_fields.customer_name': '客户名称',
    'production.detail_fields.product_type': '产品类型',
    'production.detail_fields.material': '材质',
    'production.detail_fields.mesh_size': '网孔尺寸',
    'production.detail_fields.wire_diameter': '丝径',
    'production.detail_fields.dimensions': '尺寸规格',
    'production.detail_fields.quantity': '数量',
    'production.detail_fields.unit_price': '单价',
    'production.detail_fields.total_amount': '总金额',
    'production.detail_fields.delivery_date': '交货日期',
    'production.detail_fields.status': '订单状态',
    'production.detail_fields.created_at': '创建时间',
    
    # 工序视图表头
    'process.columns.seq': '序号',
    'process.columns.name': '工序名称',
    'process.columns.worker': '执行人',
    'process.columns.total': '计划',
    'process.columns.unit': '单位',
    'process.columns.completed': '完成',
    'process.columns.today': '今日',
    'process.columns.percent': '进度',
    'process.columns.qualified': '合格',
    'process.columns.hours': '工时',
    'process.columns.outsource': '外协',

    # 工序视图标题和标签
    'process.title': '工序追踪',
    'process.labels.total': '计划',
    'process.labels.completed': '完成',
    'process.labels.qualified': '合格',
    'process.labels.process': '工序',
    'process.labels.qty': '报工数量',
    'process.labels.qualified_qty': '合格数量',
    'process.labels.hours': '工时',
    'process.labels.worker': '执行人',
    'process.labels.remark': '备注',
    'process.submit': '提交报工',
    'process.no_work_order': '无生产工单',
    'process.no_match_work_order': '未找到匹配的工单',
    'process.search_work_order': '🔍 查询工单',
    'process.overall_progress': '整体生产进度：{percent}',
    'process.record_count': '共 {count} 条',
    'process.not_scheduled': '该订单尚未排产',

    # 操作员视图表头
    'operator.columns.operator_id': '工号',
    'operator.columns.name': '姓名',
    'operator.columns.role': '角色',
    'operator.columns.last_login': '最后登录',
    'operator.columns.created_at': '创建时间',
    'operator.columns.action': '操作',
    'operator.columns.target_type': '目标类型',
    'operator.columns.details': '详情',
    
    # 物料准备视图表头
    'material.columns.material_name': '物料名称',
    'material.columns.spec': '规格',
    'material.columns.unit': '单位',
    'material.columns.required_qty': '需求数量',
    'material.columns.prepared_qty': '已备数量',
    'material.columns.status': '状态',
    'material.columns.updated_at': '更新时间',
    
    # 通用按钮和标签
    'btn.new': '新建',
    'btn.edit': '编辑',
    'btn.delete': '删除',
    'btn.save': '保存',
    'btn.cancel': '取消',
    'btn.ok': '确定',
    'btn.search': '搜索',
    'btn.reset': '重置',
    'btn.confirm': '确认',
    'btn.select': '选择',
    'btn.add': '添加',
    'btn.remove': '移除',
    
    # 状态标签
    'status.pending': '待确认',
    'status.confirmed': '待排产',
    'status.producing': '生产中',
    'status.completed': '已完成',
    'status.archived': '已归档',
    'status.cancelled': '已取消',
    
    # 生产状态标签
    'production.status.pending': '待生产',
    'production.status.in_progress': '生产中',
    'production.status.completed': '已完成',
    
    # 优先级标签
    'priority.high': '高',
    'priority.medium': '中',
    'priority.low': '低',
    
    # 提示信息
    'msg.select_item': '请选择一项',
    'msg.confirm_delete': '确定要删除吗？',
    'msg.save_success': '保存成功',
    'msg.delete_success': '删除成功',
    'msg.error': '发生错误',
}

def t(key, **kwargs):
    """获取翻译字符串"""
    translation = _translations.get(key, key)
    if kwargs:
        return translation.format(**kwargs)
    return translation

def set_locale(locale):
    """设置语言环境"""
    pass

def get_locale():
    """获取当前语言环境"""
    return 'zh_CN'