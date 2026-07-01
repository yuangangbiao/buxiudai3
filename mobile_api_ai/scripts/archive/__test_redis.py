import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('REDIS_HOST', '127.0.0.1')

print("Importing cache...", flush=True)
try:
    from cache import cache
    print(f"cache OK: {type(cache).__name__}", flush=True)
except Exception as e:
    print(f"cache FAIL: {e}", flush=True)
