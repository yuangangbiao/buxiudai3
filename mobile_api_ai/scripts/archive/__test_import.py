import sys, os, time
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('FACE_ATTENDANCE_ENABLED', 'false')
os.environ.setdefault('WECHAT_APP_ENV', 'development')
os.environ.setdefault('CONTAINER_CENTER_API_URL', 'http://localhost:5002')

print("Importing container_center_client...", flush=True)
t0 = time.time()
from container_center_client import ContainerCenterClient
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

print("Importing dispatch_center...", flush=True)
t0 = time.time()
from dispatch_center import dispatch_center_bp, _dispatch_cache
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

print("Importing container_center SDK...", flush=True)
t0 = time.time()
from container_center.v5_compatible_client import V5CompatibleClient
from container_center.client import ContainerCenterClient as ContainerCenterSDK
print(f"  OK ({time.time()-t0:.1f}s)", flush=True)

print("ALL IMPORTS PASSED", flush=True)
