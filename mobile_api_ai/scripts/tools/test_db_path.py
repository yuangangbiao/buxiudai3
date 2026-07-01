"""测试数据库路径是否正确配置"""
import os
import sys

print("=" * 60)
print("测试数据库路径配置")
print("=" * 60)

print(f"\n当前工作目录: {os.getcwd()}")
print(f"Python 路径:")
for p in sys.path:
    print(f"  - {p}")

print(f"\n环境变量 CONTAINER_DB_PATH:")
db_path = os.getenv('CONTAINER_DB_PATH', '未设置')
print(f"  {db_path}")

api_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api'
project_root = os.path.dirname(api_dir)

print(f"\n路径计算:")
print(f"  api_dir: {api_dir}")
print(f"  project_root: {project_root}")

if db_path and db_path.strip():
    final_path = db_path if os.path.isabs(db_path) else os.path.join(project_root, db_path)
else:
    final_path = os.path.join(project_root, 'mobile_api_ai', 'wechat_container.db')

print(f"  最终数据库路径: {final_path}")
print(f"  路径是否存在: {os.path.exists(final_path)}")

if os.path.exists(final_path):
    size = os.path.getsize(final_path)
    print(f"  文件大小: {size} 字节")
else:
    print(f"  ❌ 数据库文件不存在！")
    print(f"  可能的原因:")
    print(f"  1. 数据库文件在其他位置")
    print(f"  2. 服务器使用环境变量设置了不同的路径")

print("\n" + "=" * 60)
