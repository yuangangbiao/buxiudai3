"""清空 auto_ensure_schema 缓存"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
try:
    from utils.auto_schema import clear_schema_cache
    clear_schema_cache()
    print("schema cache cleared successfully")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
