"""[v3.7.8 起点] commit 4 人会议产出"""
import subprocess
import os

files = [
    'docs/LESSONS_LEARNED.md',
    'scripts/manual_e2e_check.py',
    'tests/integration/test_publisher_e2e.py',
    'docs/STORAGE_INVENTORY.md',
]

for f in files:
    if not os.path.exists(f):
        print(f'  SKIP: {f}')
        continue
    r = subprocess.run(['git', 'add', f], capture_output=True, text=True)
    print(f'  add {f}: {r.returncode}')

msg = '''docs(v3.7.8): 4 人会议产出（教训 + e2e + 存储盘点）

[v3.7.8 起点] 4 人会议决议产出 4 份文档

1. docs/LESSONS_LEARNED.md
   - 5 件错事（mock 陷阱、单文件视角、API 不匹配、文档虚报、commit scope）
   - 5 步学习法（看全、跑测试、真实点击、多人审、文档对比）
   - 3 条铁律（测试绿不等于系统工作、读全链路、审计必须唱反调）
   - 7 条具体教训 + 责任分配

2. scripts/manual_e2e_check.py
   - 不用 docker，今天能跑
   - 验证 publisher.py 运行时行为
   - 检测：API 兼容、内存存储、数据流向缺失
   - 真实发现：publisher.py 不调 HTTP/DB（已知问题）

3. tests/integration/test_publisher_e2e.py
   - 7 个集成测试用例
   - 3 passed（API + 业务流）
   - 4 skipped（依赖未就绪：5003、MySQL）
   - 等 docker-compose 准备好后启用 skip 的测试

4. docs/STORAGE_INVENTORY.md
   - 4 套存储介质：SQLite、MySQL、内存 Dict、HTTP 转发
   - 13 张表的写入位置、修复建议、优先级
   - 核心问题：publisher.py 只写内存 Dict（重启丢）
   - 修复路径：DDL + pymysql 接入 CONTAINER_MYSQL_CFG

测试结果:
- manual_e2e_check.py: 4 项通过 + 数据流向缺失（已记录）
- test_publisher_e2e.py: 3 passed, 4 skipped (依赖未就绪)
- 现有 124 个单元测试保持通过

下一步（v3.7.8 实施）:
- 创建 dispatch_center_tasks 表（DDL）
- publisher.py 改 pymysql 直连
- docker-compose 启动 5003 + MySQL
- 启用 4 个 skipped 的集成测试'''

r = subprocess.run(['git', 'commit', '-F', '-'], input=msg, capture_output=True, text=True)
print('commit return:', r.returncode)
if r.returncode == 0:
    print(r.stdout[:300])
else:
    print('stderr:', r.stderr[:500])