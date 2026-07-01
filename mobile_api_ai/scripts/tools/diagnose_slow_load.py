"""
诊断脚本：检查排产/任务列表加载慢的原因

检查项：
1. data_packages 表数据量
2. process_records 表数据量
3. 本地 MySQL vs HTTP 回退的触发条件
4. 缓存状态
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

def check_table_stats():
    """检查表数据量"""
    print("\n" + "="*60)
    print("📊 表数据量统计")
    print("="*60)

    try:
        from db.steelbelt_pool import get_conn
        conn = get_conn()
        c = conn.cursor()

        # 检查 data_packages
        c.execute("SELECT COUNT(*) FROM container_center.data_packages")
        pkg_count = c.fetchone()[0]
        print(f"\n📦 data_packages 表: {pkg_count} 条")

        # 检查 process_records
        c.execute("SELECT COUNT(*) FROM container_center.process_records")
        rec_count = c.fetchone()[0]
        print(f"📋 process_records 表: {rec_count} 条")

        # 检查按 status 分布
        c.execute("""
            SELECT status, COUNT(*) as cnt
            FROM container_center.data_packages
            GROUP BY status
            ORDER BY cnt DESC
            LIMIT 10
        """)
        print(f"\n📈 data_packages 按状态分布:")
        for row in c.fetchall():
            print(f"   {row[0] or '(empty)'}: {row[1]} 条")

        # 检查按 data_type 分布
        c.execute("""
            SELECT data_type, COUNT(*) as cnt
            FROM container_center.data_packages
            GROUP BY data_type
            ORDER BY cnt DESC
            LIMIT 10
        """)
        print(f"\n📈 data_packages 按类型分布:")
        for row in c.fetchall():
            print(f"   {row[0]}: {row[1]} 条")

        conn.close()

        return pkg_count, rec_count

    except Exception as e:
        print(f"\n❌ 数据库查询失败: {e}")
        return None, None


def check_http_fallback_condition():
    """检查 HTTP 回退的触发条件"""
    print("\n" + "="*60)
    print("🔍 HTTP 回退触发条件分析")
    print("="*60)

    try:
        from container_center.v5_compatible_client import V5CompatibleClient
        from container_center.client.container_client import ContainerCenterClient

        # 模拟 V5CompatibleClient 的初始化
        cc = None
        try:
            from core.config import DB_PATHS
            from container_center_v5 import ContainerCenter
            cc = ContainerCenter()
            print("✅ ContainerCenter 初始化成功")
        except Exception as e:
            print(f"❌ ContainerCenter 初始化失败: {e}")

        # 检查 HTTP 客户端
        http_client = None
        try:
            url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
            secret = os.environ.get('CONTAINER_CENTER_SECRET', '')
            http_client = ContainerCenterClient(base_url=url, secret=secret)
            print(f"✅ HTTP 客户端初始化成功: {url}")
        except Exception as e:
            print(f"❌ HTTP 客户端初始化失败: {e}")

        # 模拟 query_documents 的逻辑
        print("\n📋 query_documents 调用链分析:")

        if cc is None:
            print("   ⚠️  cc=None → 会触发 HTTP 回退!")
        else:
            print("   ✅ cc 正常 → 走本地 MySQL")

        if http_client is None:
            print("   ⚠️  http_client=None → HTTP 回退会失败!")
        else:
            print("   ✅ http_client 正常 → HTTP 回退可用")

        # 测试本地查询
        if cc:
            try:
                start = time.time()
                packages = cc.storage.get_packages(limit=100)
                elapsed = (time.time() - start) * 1000
                print(f"\n⏱️  本地 MySQL 查询 (100条): {elapsed:.1f}ms, 获取 {len(packages)} 条")
            except Exception as e:
                print(f"\n❌ 本地 MySQL 查询失败: {e}")

        # 测试 HTTP 查询
        if http_client:
            try:
                start = time.time()
                result = http_client._request('GET', '/api/v4/work_order?page=1&size=100')
                elapsed = (time.time() - start) * 1000
                items = result.get('items', result.get('data', []))
                print(f"⏱️  HTTP 查询 (100条): {elapsed:.1f}ms, 获取 {len(items)} 条")
            except Exception as e:
                print(f"\n⚠️  HTTP 查询失败: {e}")

    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")


def check_cache_status():
    """检查缓存状态"""
    print("\n" + "="*60)
    print("💾 缓存状态")
    print("="*60)

    try:
        from dispatch_center._core import DispatchContext

        ctx = DispatchContext.get_instance()
        cache = ctx.work_order_cache

        print(f"\n📦 work_order_cache 状态:")
        print(f"   data: {'已缓存' if cache['data'] is not None else '空'}")
        print(f"   time: {cache['time']}")
        print(f"   ttl: {cache['ttl']} 秒")

        if cache['data'] is not None:
            import time
            age = time.time() - cache['time']
            print(f"   缓存年龄: {age:.0f} 秒")
            print(f"   缓存条目: {len(cache['data'])} 条")

            if age > cache['ttl']:
                print(f"   ⚠️  缓存已过期!")
            else:
                print(f"   ✅ 缓存有效")
        else:
            print(f"   ⚠️  缓存为空，下一次请求会触发加载")

    except Exception as e:
        print(f"\n❌ 缓存检查失败: {e}")


def main():
    print("="*60)
    print("🔍 排产/任务列表加载慢 - 诊断工具")
    print("="*60)

    check_table_stats()
    check_http_fallback_condition()
    check_cache_status()

    print("\n" + "="*60)
    print("📝 诊断结论")
    print("="*60)
    print("""
根据诊断结果判断:

1. 如果 data_packages 表 > 10000 条:
   → 数据量大，需要分页/虚拟滚动

2. 如果 "ContainerCenter 初始化失败":
   → HTTP 回退会触发，每次请求去调 5002 端口
   → 这是最可能的原因！

3. 如果 "HTTP 查询失败":
   → 即使触发回退也拿不到数据
   → 本地 MySQL 又没数据 → 返回空

4. 如果缓存为空:
   → 每次请求都要重新加载
   → 缓存预热可以改善
""")


if __name__ == '__main__':
    main()
