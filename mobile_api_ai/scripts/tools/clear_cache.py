import os
os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

# 清除缓存文件，让新代码从数据库加载
cache_file = 'mobile_api_ai/dispatch_center_data.json'
if os.path.exists(cache_file):
    os.remove(cache_file)
    print(f"已删除缓存: {cache_file}")
else:
    print(f"缓存文件不存在: {cache_file}")

# 确认删除
print(f"缓存存在: {os.path.exists(cache_file)}")
