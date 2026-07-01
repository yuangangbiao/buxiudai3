import sys, os, time, threading

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_DIR)
os.chdir(_PROJECT_DIR)

os.environ.setdefault('FACE_ATTENDANCE_ENABLED', 'false')
os.environ.setdefault('WECHAT_APP_ENV', 'development')
os.environ.setdefault('CONTAINER_CENTER_API_URL', 'http://localhost:5002')

results = {}
done_event = threading.Event()

def timed_import(module_name):
    result = []
    def target():
        try:
            start = time.time()
            if module_name == 'dispatch_center':
                from dispatch_center import dispatch_center_bp, _dispatch_cache
            elif module_name == 'wechat_server':
                import wechat_server
            result.append(('ok', time.time() - start))
        except Exception as e:
            result.append(('fail', str(e)))
        done_event.set()
    
    t = threading.Thread(target=target, daemon=True)
    t.start()
    if not done_event.wait(timeout=15):
        return 'timeout', '>15s'
    return result[0]

print("Testing container_center_client import...", flush=True)
start = time.time()
try:
    from container_center_client import ContainerCenterClient
    print(f"  OK ({time.time()-start:.1f}s)", flush=True)
except Exception as e:
    print(f"  FAIL: {e}", flush=True)

print("Testing dispatch_center import...", flush=True)
done_event.clear()
status, detail = timed_import('dispatch_center')
print(f"  {status}: {detail}", flush=True)

print("Testing wechat_server import...", flush=True)
done_event.clear()
status, detail = timed_import('wechat_server')
print(f"  {status}: {detail}", flush=True)

print("DONE", flush=True)
sys.stdout.flush()
