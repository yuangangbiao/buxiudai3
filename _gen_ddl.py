# -*- coding: utf-8 -*-
"""从 mobile_api_ai/wechat_container.db 真实结构生成完整 MySQL DDL"""
import sqlite3, os

SRC_DB = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
OUT_FILE = r'D:\yuan\构想文件\wechat_container数据库MySQL迁移方案\ddl_29_tables.sql'

def infer_mysql_type(col_name, sqlite_type, default_val):
    cn = col_name.lower()
    st = sqlite_type.upper() if sqlite_type else 'TEXT'
    if cn == 'id' and st == 'INTEGER':
        return 'INT AUTO_INCREMENT PRIMARY KEY'
    if cn == 'id' and st == 'TEXT':
        return 'VARCHAR(36) PRIMARY KEY'
    if st == 'INTEGER':
        return 'INT'
    if st == 'REAL':
        if any(k in cn for k in ['price','amount','cost','quantity','qty']):
            return 'DECIMAL(12,2)'
        return 'DOUBLE'
    if any(cn.endswith(p) for p in ['_at','_date']):
        if default_val and 'datetime' in str(default_val).lower():
            return 'DATETIME(3)'
        return 'DATETIME(3)'
    if '_id' in cn or cn.endswith('_no') or cn.endswith('_code') or cn.endswith('_key') or cn.endswith('_type'):
        return 'VARCHAR(100)'
    if any(k in cn for k in ['config','content','steps','tags','params','json']):
        return 'JSON'
    if cn in ['remark','remarks','reason','description','detail','comments','message','error','error_msg','error_message','confirm_comments','reject_reason','raw_data','event_detail','event_data','return_data','write_back_cmd','command_data','schedule_data','analyzed_result']:
        return 'TEXT'
    if cn.endswith('_name') or cn.endswith('_by') or cn == 'status' or cn == 'priority' or cn == 'source' or cn == 'unit':
        return 'VARCHAR(100)'
    if cn == 'enabled':
        return 'TINYINT(1)'
    if cn.endswith('_count'):
        return 'INT'
    if cn in ['role','format','category','group','direction','action','event_type','action_type','cron_expression']:
        return 'VARCHAR(50)'
    return 'VARCHAR(200)'

def get_default(dval, col_name, mysql_type):
    if dval is None:
        return None
    s = str(dval)
    if s == 'None' or s.strip().upper() == 'NULL':
        return None
    # MySQL: TEXT/JSON 列不能有默认值
    if mysql_type in ('TEXT', 'JSON'):
        return None
    # MySQL: DATETIME(3) 不能用 CURRENT_TIMESTAMP 作为默认值（仅 TIMESTAMP 可用）
    if 'DATETIME' in mysql_type and 'CURRENT_TIMESTAMP' in s:
        return None
    if s.startswith('datetime('):
        return None
    if s == '0':
        if 'TINYINT' in mysql_type: return '0'
        if 'INT' in mysql_type: return '0'
        if 'DECIMAL' in mysql_type: return '0.00'
        if 'DOUBLE' in mysql_type: return '0.0'
    if s == '1' and 'TINYINT' in mysql_type:
        return '1'
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        inner = s[1:-1]
        if inner == '': return None  # MySQL 不允许 TEXT 默认空串
        return f"'{inner}'"
    return f"'{s}'"

comments_map = {
    'process_records':'容器中心-处理记录(含流程步骤/工单映射)',
    'process_sub_steps':'容器中心-工序报工明细(含数量/操作员/设备)',
    'schedule_records':'容器中心-排产记录(含发布/提交/确认/拒绝全流程)',
    'data_packages':'容器中心-数据包(核心调度单元,含分发/确认/完成)',
    'data_collection_records':'容器中心-数据采集记录(报工数据采集)',
    'data_flow_logs':'容器中心-数据流日志(全生命周期事件追踪)',
    'dispatch_commands':'容器中心-调度指令(操作员指派/设备分配)',
    'sync_retry_queue':'容器中心-同步重试队列(失败自动重试3次)',
    'sync_log':'容器中心-同步日志(方向/状态/错误)',
    'sync_logs':'容器中心-同步日志v旧版',
    'product_flow_map':'容器中心-产品类型→流程类型映射(生产/外协等)',
    'enterprise_structure':'容器中心-企业组织架构(部门/用户JSON)',
    'workers':'容器中心-工人信息(用户名/姓名/角色)',
    'attendance':'容器中心-考勤记录(签到/签退/状态)',
    'order_cost':'容器中心-订单成本汇总(收入/材料/人工/外协)',
    'order_cost_detail':'容器中心-订单成本明细(逐项成本分解)',
    'material_requirements':'容器中心-物料需求(缺料预警/备料追踪)',
    'material_usage_log':'容器中心-物料使用日志(工序用料记录)',
    'material_price':'容器中心-物料单价(材料名称/单价/单位)',
    'labor_price':'容器中心-工序工价(工序名称/单价/单位)',
    'return_records':'容器中心-回传记录(手机端回传/分析结果)',
    'pending_material_events':'容器中心-待处理物料事件(提醒/重试)',
    'schedule_flow_logs':'容器中心-排产流程日志(事件/操作员)',
    'sub_step_audit_log':'容器中心-报工审计日志(增删改查全记录)',
    'report_definition':'容器中心-报表定义(SQL模板/图表/列配置)',
    'report_output':'容器中心-报表输出(文件路径/行数/状态)',
    'report_schedule':'容器中心-报表调度(cron/参数/导出格式)',
    'export_profile':'容器中心-导出配置(格式/列/标题)',
}

# 索引候选列
index_cols = {
    'order_no': 'idx', 'status': 'idx', 'data_type': 'idx',
    'operator': 'idx', 'process_id': 'idx', 'created_at': 'idx',
    'schedule_id': 'uk', 'worker': 'idx', 'related_order': 'idx',
    'product_type_id': 'idx', 'flow_id': 'idx', 'command_id': 'idx',
    'flow_type': 'idx', 'order_id': 'idx'
}

def generate():
    conn = sqlite3.connect(SRC_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]

    lines = []
    lines.append('-- ============================================================')
    lines.append('-- wechat_container SQLite → MySQL 完整 DDL')
    lines.append('-- 目标数据库: steel_belt (与主系统共享)')
    lines.append('-- 表名前缀: cc_ (避免与主系统表名冲突)')
    lines.append('-- 源文件: mobile_api_ai/wechat_container.db (496KB)')
    lines.append('-- 表总数: 29 张')
    lines.append('-- 生成时间: 2026-05-29')
    lines.append('-- 引擎: InnoDB, 字符集: utf8mb4, 排序: utf8mb4_unicode_ci')
    lines.append('-- ============================================================')
    
    total_cols = 0
    
    for i, tname in enumerate(tables, 1):
        prefix = tname if tname.startswith('_') else f'cc_{tname}'
        cursor.execute(f'PRAGMA table_info({tname})')
        cols = cursor.fetchall()
        total_cols += len(cols)
        comment = comments_map.get(tname, f'容器中心-{tname}')
        
        lines.append('')
        lines.append(f'-- ═══════════════════════════════════════════')
        lines.append(f'-- 表 [{i}/29] {tname} ({len(cols)}列)')
        lines.append(f'-- MySQL表名: {prefix}')
        lines.append(f'-- ═══════════════════════════════════════════')
        lines.append(f'DROP TABLE IF EXISTS `{prefix}`;')
        lines.append(f'CREATE TABLE `{prefix}` (')
        
        col_lines = []
        indexes = []
        has_col_pk = False
        
        for c in cols:
            cid, cname, ctype, cnotnull, cdefault, cpk = c
            mysql_type = infer_mysql_type(cname, ctype, cdefault)
            default_val = get_default(cdefault, cname, mysql_type)
            
            # 检查主键是否已包含在类型中
            if 'PRIMARY KEY' in mysql_type:
                has_col_pk = True
            
            col_comment = {
                'id':'主键','order_no':'订单号','process_type':'记录类型',
                'work_order_no':'工单号','product_name':'产品名称',
                'quantity':'数量','unit':'单位','customer_name':'客户名称',
                'delivery_date':'交货日期','priority':'优先级','status':'状态',
                'source':'来源/数据来源','created_at':'创建时间','updated_at':'更新时间',
                'completed_at':'完成时间','operator':'操作员','step_name':'工序名称',
                'batch_no':'批次号','qualified_qty':'合格数量','equipment_name':'设备名称',
                'remark':'备注','data_type':'数据类型','enabled':'是否启用',
                'retry_count':'重试次数','overtime_hours':'加班小时','overtime_minutes':'加班分钟',
                'customer_group':'客户分组','template_id':'模板ID','flow_type':'流程类型',
                'schedule_days':'排产天数','plan_start':'计划开始','plan_end':'计划结束',
            }.get(cname, '')
            
            parts = [f'    `{cname}` {mysql_type}']
            if cnotnull and 'PRIMARY KEY' not in mysql_type:
                parts.append('NOT NULL')
            if default_val:
                parts.append(f'DEFAULT {default_val}')
            if col_comment:
                parts.append(f"COMMENT '{col_comment}'")
            
            col_lines.append(' '.join(parts))
            
            if cname in index_cols and cname != 'id':
                indexes.append((cname, prefix, index_cols[cname]))
        
        # 如果不是内联主键，加 PRIMARY KEY
        if not has_col_pk:
            pk_def = None
            for c in cols:
                if c[5] == 1:  # cpk
                    pk_def = f'    PRIMARY KEY (`{c[1]}`)'
                    break
            if pk_def:
                col_lines.append(pk_def)
        
        # 构建索引
        idx_defs = []
        for ciname, pre, ixtype in indexes:
            # 短索引名
            short = pre.replace('cc_', '')
            if len(short) > 12: short = short[:12]
            idx_name = f'{ixtype}_{short}_{ciname}'[:64]
            if ixtype == 'uk':
                idx_defs.append(f'    UNIQUE KEY `{idx_name}` (`{ciname}`)')
            else:
                idx_defs.append(f'    INDEX `{idx_name}` (`{ciname}`)')
        
        lines.append(',\n'.join(col_lines))
        if idx_defs:
            lines.append(',')
            lines.append(',\n'.join(idx_defs))
        lines.append(f') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci')
        lines.append(f"  COMMENT='{comment}';")
    
    lines.append('')
    lines.append('-- ============================================================')
    lines.append(f'-- 总计: {len(tables)} 张表, {total_cols} 个列')
    lines.append('-- 执行方式: mysql -u root -p steel_belt < ddl_29_tables.sql')
    lines.append('-- ============================================================')
    
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f'✅ 生成完成: {OUT_FILE}')
    print(f'   表: {len(tables)} 张, 列: {total_cols} 个')
    conn.close()

if __name__ == '__main__':
    generate()
