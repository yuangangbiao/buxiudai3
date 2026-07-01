# -*- coding: utf-8 -*-
"""
9 张统计表配置（中心化管理）
- 触发频率（cron 表达式）
- 字段映射（中文名 → 智能表格 field_id）
- 接收端点
"""
import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)


# 9 张表的中文显示名
TABLE_DISPLAY_NAMES = {
    'production_daily_report': '生产日报',
    'production_monthly_report': '生产月报',
    'workshop_capacity': '车间产能分析',
    'workorder_progress': '工单进度跟踪',
    'substep_report': '工序报工汇总',
    'inventory_weekly_report': '库存周报',
    'inventory_monthly_summary': '物料收发存汇总',
    'inventory_alert': '库存预警',
    'inventory_slow_moving': '呆滞料分析',
}


# 触发频率（cron 表达式）
SCHEDULE_CONFIG = {
    'production_daily_report':    {'cron': '0 18 * * *',    'enabled': True},
    'production_monthly_report':  {'cron': '0 9 1 * *',     'enabled': True},
    'workshop_capacity':          {'cron': '0 18 * * *',    'enabled': True},
    'workorder_progress':         {'cron': '0 */4 * * *',   'enabled': True},  # 每 4 小时
    'substep_report':             {'cron': '*/30 * * * *',  'enabled': True},  # 每 30 分钟
    'inventory_weekly_report':    {'cron': '0 9 * * 1',     'enabled': True},  # 每周一 9 点
    'inventory_monthly_summary':  {'cron': '0 9 1 * *',     'enabled': True},
    'inventory_alert':            {'cron': '0 9 * * *',     'enabled': True},
    'inventory_slow_moving':      {'cron': '0 9 * * 1',     'enabled': True},  # 每周一 9 点
}


# 推送配置
PUSH_CONFIG = {
    'local_5005_url': os.getenv('LOCAL_5005_URL', 'http://127.0.0.1:5005'),
    'push_endpoint': '/api/stats/push',
    'stats_api_key': os.getenv('STATS_API_KEY'),  # 无默认值，强制环境变量
    'max_retries': int(os.getenv('STATS_MAX_RETRIES', '3')),
    'retry_base_interval': int(os.getenv('STATS_RETRY_INTERVAL', '2')),  # 指数退避基数（秒）
    'request_timeout': int(os.getenv('STATS_REQUEST_TIMEOUT', '30')),
}


# 库存相关阈值
INVENTORY_CONFIG = {
    'safety_threshold': int(os.getenv('INVENTORY_SAFETY_THRESHOLD', '10')),
    'slow_moving_days': int(os.getenv('INVENTORY_SLOW_MOVING_DAYS', '90')),
}


# 9 张表的字段映射（中文显示名 → 智能表格 field_id）
# ⚠️ 实际 field_id 需在企业微信智能表格创建后填入
# 格式: table_type → {field_name: field_id}
FIELD_MAPPING = {
    'production_daily_report': {
        '记录ID': 'f0001', '日期': 'f0002', '班组': 'f0003', '产线': 'f0004',
        '计划数': 'f0005', '完成数': 'f0006', '差异率': 'f0007', '合格率': 'f0008',
        '操作员': 'f0009', '备注': 'f000A', '写入时间': 'f000B',
    },
    'production_monthly_report': {
        '记录ID': 'f1001', '月份': 'f1002', '产线': 'f1003',
        '计划数': 'f1004', '完成数': 'f1005', '产能利用率': 'f1006', '达成率': 'f1007',
        '订单数': 'f1008', '停机时长(h)': 'f1009', '备注': 'f100A', '写入时间': 'f100B',
    },
    'workshop_capacity': {
        '记录ID': 'f2001', '车间': 'f2002', '设备': 'f2003', '日期': 'f2004',
        '工时(h)': 'f2005', '有效工时(h)': 'f2006', '停机时长(h)': 'f2007',
        'OEE': 'f2008', '性能率': 'f2009', '合格率': 'f200A', '写入时间': 'f200B',
    },
    'workorder_progress': {
        '工单号': 'f3001', '客户': 'f3002', '产品': 'f3003',
        '计划开始': 'f3004', '计划完工': 'f3005', '实际开始': 'f3006', '实际完工': 'f3007',
        '当前工序': 'f3008', '完成工序': 'f3009', '总工序': 'f300A', '进度条': 'f300B',
        '状态': 'f300C', '写入时间': 'f300D',
    },
    'substep_report': {
        '记录ID': 'f4001', '工单号': 'f4002', '工序': 'f4003', '操作人': 'f4004',
        '批次号': 'f4005', '报工数': 'f4006', '合格数': 'f4007', '合格率': 'f4008',
        '报工时间': 'f4009', '备注': 'f400A', '写入时间': 'f400B',
    },
    'inventory_weekly_report': {
        '记录ID': 'f6001', '周次': 'f6002', '周起始日期': 'f6003', '周结束日期': 'f6004',
        '仓库': 'f6005', '入库数': 'f6006', '出库数': 'f6007',
        '库存余额': 'f6008', '库存金额': 'f6009', '异动笔数': 'f600A', '写入时间': 'f600B',
    },
    'inventory_monthly_summary': {
        '记录ID': 'f7001', '月份': 'f7002', '物料编码': 'f7003', '物料名称': 'f7004',
        '期初数量': 'f7005', '入库数量': 'f7006', '出库数量': 'f7007', '期末数量': 'f7008',
        '单价': 'f7009', '期末金额': 'f700A', '写入时间': 'f700B',
    },
    'inventory_alert': {
        '物料编码': 'f8001', '物料名称': 'f8002', '仓库': 'f8003', '当前库存': 'f8004',
        '安全库存': 'f8005', '预警状态': 'f8006', '建议补货量': 'f8007',
        '最近入库时间': 'f8008', '写入时间': 'f8009',
    },
    'inventory_slow_moving': {
        '物料编码': 'f9001', '物料名称': 'f9002', '仓库': 'f9003', '当前库存': 'f9004',
        '最后异动日期': 'f9005', '库龄(天)': 'f9006', '单价': 'f9007', '库存金额': 'f9008',
        '状态': 'f9009', '写入时间': 'f900A',
    },
}


# 9 张表对应的智能表格 docid/sheet_id（创建后填入）
# 留空表示待创建
SMART_SHEET_INDEX = {
    # 'production_daily_report': {
    #     'docid': 'xxx', 'sheet_id': 'xxx', 'url': 'xxx'
    # },
}
