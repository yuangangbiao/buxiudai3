import re

app_file = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'

with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# 找到所有 "conn = MySQLStorage.get_connection()" 后紧跟 "FOR UPDATE" 的行
# 插入 conn.begin()
# 模式: conn = MySQLStorage.get_connection()\n...FOR UPDATE
pattern = r'(conn = MySQLStorage\.get_connection\(\))\n(.*?FOR UPDATE)'
count = 0

def fix_match(m):
    global count
    conn_line = m.group(1)
    rest = m.group(2)
    count += 1
    return f'{conn_line}\n            conn.begin()\n{rest}'

content = re.sub(pattern, fix_match, content, flags=re.DOTALL)
print(f'添加 conn.begin() 的 FOR UPDATE 查询: {count} 处')

if content != original:
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print('文件已更新')
else:
    print('无变化')
