import sqlite3
import json

conn = sqlite3.connect('wechat_container.db')

# 分析数据流动日志
cursor = conn.execute("SELECT event_type, COUNT(*) as count FROM data_flow_logs GROUP BY event_type ORDER BY count DESC")
flow_events = cursor.fetchall()
print('数据流动事件统计:')
for event_type, count in flow_events:
    print(f"  {event_type}: {count} 次")

# 分析调度命令
cursor = conn.execute("SELECT status, COUNT(*) as count FROM dispatch_commands GROUP BY status")
cmd_status = cursor.fetchall()
print('\n调度命令状态统计:')
for status, count in cmd_status:
    print(f"  {status}: {count} 条")

# 分析数据收集记录
cursor = conn.execute("SELECT data_type, COUNT(*) as count FROM data_collection_records GROUP BY data_type")
data_types = cursor.fetchall()
print('\n数据收集类型统计:')
for data_type, count in data_types:
    print(f"  {data_type}: {count} 条")

# 分析同步日志
cursor = conn.execute("SELECT action, COUNT(*) as count FROM sync_logs GROUP BY action")
sync_actions = cursor.fetchall()
print('\n同步操作统计:')
for action, count in sync_actions:
    print(f"  {action}: {count} 次")

conn.close()