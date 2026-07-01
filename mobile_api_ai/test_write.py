import json, os
p = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\enterprise_structure.json'
print(f'目标路径: {p}')
print(f'文件存在: {os.path.exists(p)}')
print(f'目录存在: {os.path.exists(os.path.dirname(p))}')

# 尝试手动写入
d = {'test': True}
with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f)
print(f'手动写入后存在: {os.path.exists(p)}')

# 读回确认
d2 = json.load(open(p, encoding='utf-8'))
print(f'读回内容: {d2}')
