"""调试容器仪表板 - 测试 get_container_center"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from container_dashboard import get_container_center, get_container_stats

cc = get_container_center()
print(f"container_center = {cc}")
print(f"type = {type(cc)}")

if cc:
    print(f"storage = {cc.storage}")
    print(f"storage type = {type(cc.storage)}")
    try:
        pkgs = cc.storage.get_packages()
        print(f"get_packages() returned {len(pkgs)} packages")
    except Exception as e:
        print(f"get_packages() FAILED: {type(e).__name__}: {e}")
else:
    print("container_center is None!")

print("\n--- get_container_stats() ---")
stats = get_container_stats()
print(f"stats = {stats}")
