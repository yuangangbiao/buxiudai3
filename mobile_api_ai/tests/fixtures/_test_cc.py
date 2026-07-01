import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from container_dashboard import get_container_center
cc = get_container_center()
print(f'ContainerCenter: {cc}')
print(f'Storage: {cc.storage if cc else None}')
if cc:
    pkgs = cc.storage.get_packages()
    print(f'Packages: {len(pkgs)}')
