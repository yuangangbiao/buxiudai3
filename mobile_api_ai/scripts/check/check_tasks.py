import os
import sys
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _project_root)
from container_center_v5 import ContainerCenter
db_path = os.path.join(_project_root, 'wechat_container.db')
cc = ContainerCenter({'type': 'sqlite', 'db_path': db_path})

pkg = cc.storage.get_package('77A5D62F')
if pkg:
    print(f"任务 77A5D62F 详情:")
    print(f"  ID: {pkg.get('id')}")
    print(f"  状态: {pkg.get('status')}")
    print(f"  操作员: {pkg.get('target_operator')}")
    print(f"  标题: {pkg.get('title')}")
    print(f"  content: {pkg.get('content')}")