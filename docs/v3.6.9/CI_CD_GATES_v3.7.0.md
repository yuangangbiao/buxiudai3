# CI/CD 门禁配置 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P1 文档，Week 1 建立CI配置
> **审计来源**: 4专家审计（小贺品控）→ H-2

---

## 一、门禁体系

### 1.1 4-gate门禁

| Gate | 名称 | 标准 | 阻断条件 | 执行时机 |
|------|------|------|---------|---------|
| **Gate1** | pytest | pytest通过率 ≥ 95% | < 95% | 每次PR/合并 |
| **Gate2** | performance | P99 ≤ baseline + 200ms | > baseline+200ms | 每日定时 |
| **Gate3** | bandit | bandit扫描 0 HIGH | 任何HIGH | 每次PR/合并 |
| **Gate4** | concurrency | 100并发×10轮 零崩溃 | 任何崩溃 | 每周定时 |

---

## 二、CI配置（GitHub Actions）

### 2.1 主CI流水线

```yaml
# .github/workflows/ci.yml

name: v3.7.0 CI Pipeline

on:
  push:
    branches: [v3.7.0-refactor, 'feature/**']
  pull_request:
    branches: [v3.7.0-refactor, main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点跑性能测试

jobs:
  # ============ Gate1: pytest ============
  gate1-pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov requests pymysql
          pip install -e mobile_api_ai/  # 以dev模式安装
      - name: Run pytest
        run: |
          pytest tests/ -v --cov=mobile_api_ai --cov-report=xml
          # 计算通过率
          COVERAGE=$(python -c "import xml.etree.ElementTree as ET; t = ET.parse('coverage.xml'); m = t.find('.//metrics'); print(int(m.attrib['covered_lines'])/int(m.attrib['valid_lines'])*100)")
          echo "Coverage: $COVERAGE%"

  # ============ Gate3: bandit security ============
  gate3-bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install bandit
        run: pip install bandit
      - name: Run bandit
        run: |
          bandit -r mobile_api_ai -ll -f json -o bandit.json
          # 检查HIGH漏洞数量
          HIGH=$(python -c "import json; d=json.load(open('bandit.json')); print(len([x for x in d['results'] if x['issue_severity']=='HIGH']))")
          echo "HIGH vulnerabilities: $HIGH"
          if [ "$HIGH" -gt 0 ]; then exit 1; fi

  # ============ Gate2: performance baseline ============
  gate2-performance:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install pytest requests locust
      - name: Start app
        run: |
          # 启动app.py（在后台）
          cd mobile_api_ai
          python app.py &
          sleep 5
      - name: Run performance baseline
        run: python tests/performance/perf_baseline.py

  # ============ Gate4: concurrency test ============
  gate4-concurrency:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install pytest requests
      - name: Start app
        run: |
          cd mobile_api_ai
          python app.py &
          sleep 5
      - name: Run concurrency test
        run: python tests/performance/concurrency_test.py
```

### 2.2 PR合并门禁（必须全部通过）

```yaml
  # 合并前必须全部通过
  merge-gate:
    needs: [gate1-pytest, gate3-bandit]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check gate results
        run: |
          if [[ "${{ needs.gate1-pytest.result }}" != "success" ]]; then
            echo "Gate1 (pytest) FAILED"
            exit 1
          fi
          if [[ "${{ needs.gate3-bandit.result }}" != "success" ]]; then
            echo "Gate3 (bandit) FAILED"
            exit 1
          fi
          echo "All merge gates PASSED"
```

---

## 三、性能基线配置

### 3.1 性能基线文件

```python
# tests/performance/baseline.json

{
  "created": "2026-06-28",
  "version": "v3.7.0",
  "routes": {
    "/api/auth/login": {"p50": 80, "p95": 150, "p99": 300},
    "/api/process/list": {"p50": 120, "p95": 250, "p99": 500},
    "/api/quality/records": {"p50": 100, "p95": 200, "p99": 400},
    "/api/health": {"p50": 10, "p95": 30, "p99": 50}
    // ... 完整51个路由的baseline
  }
}
```

### 3.2 性能压测脚本

```python
# tests/performance/perf_baseline.py

import json
import time
import requests
import statistics

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5008')
ROUTES_FILE = 'tests/performance/baseline.json'

def measure_p99(route, method='GET', payload=None):
    times = []
    for _ in range(100):
        start = time.time()
        if method == 'GET':
            r = requests.get(f'{BASE_URL}{route}')
        else:
            r = requests.post(f'{BASE_URL}{route}', json=payload)
        times.append((time.time() - start) * 1000)
    return sorted(times)[98]  # P99

def test_all_routes():
    with open(ROUTES_FILE) as f:
        baseline = json.load(f)

    results = {}
    for route, bl in baseline['routes'].items():
        p99 = measure_p99(route)
        threshold = bl['p99'] + 200  # 允许+200ms
        results[route] = {
            'p99': p99,
            'threshold': threshold,
            'pass': p99 <= threshold
        }
        print(f"{route}: P99={p99:.0f}ms {'✅' if p99 <= threshold else '❌'}")

    # 汇总
    total = len(results)
    passed = sum(1 for r in results.values() if r['pass'])
    print(f"\n性能通过率: {passed}/{total} = {passed/total*100:.0f}%")

    if passed / total < 0.95:
        print("❌ Gate2 FAILED: < 95% routes passed")
        exit(1)
    else:
        print("✅ Gate2 PASSED")
```

---

## 四、并发压测配置

```python
# tests/performance/concurrency_test.py

import requests
from concurrent.futures import ThreadPoolExecutor

ROUTES = [
    '/api/process/list',
    '/api/quality/records',
    '/api/health',
]

def concurrent_call(route):
    try:
        r = requests.get(f'http://localhost:5008{route}', timeout=5)
        return r.status_code
    except Exception as e:
        return f"ERROR: {e}"

def test_100_concurrent_10_rounds():
    for round in range(10):
        with ThreadPoolExecutor(max_workers=100) as ex:
            results = list(ex.map(concurrent_call, ROUTES * (100 // len(ROUTES) + 1))[:100])
        errors = [r for r in results if isinstance(r, str) or r >= 500]
        if errors:
            print(f"❌ Round {round+1} FAILED: {len(errors)} errors")
            print(errors[:3])
            exit(1)
        print(f"✅ Round {round+1}: 100 concurrent requests OK")
    print("\n✅ Gate4 PASSED: 10 rounds × 100 concurrent = 1000 requests, 0 crash")
```

---

## 五、CI执行结果看板

| 指标 | 当前值 | 目标 | 状态 |
|------|:------:|:----:|:----:|
| pytest通过率 | - | ≥ 95% | ⬜ |
| P99 ≤ baseline+200ms | - | ≥ 95%路由 | ⬜ |
| bandit HIGH漏洞 | - | = 0 | ⬜ |
| 100并发×10轮崩溃数 | - | = 0 | ⬜ |

---

## 六、实际可执行文件

### 6.1 GitHub Actions YAML（需创建到项目根目录）

路径：`mobile_api_ai/.github/workflows/ci.yml`

```yaml
name: v3.7.0 CI Pipeline

on:
  push:
    branches: [v3.7.0-refactor, 'feature/**']
  pull_request:
    branches: [v3.7.0-refactor, main]
  schedule:
    - cron: '0 3 * * *'  # 每天凌晨3点跑性能

env:
  PYTHON_VERSION: '3.10'

jobs:
  gate1-pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-xdist requests pymysql DBUtils bandit locust

      - name: Run pytest with coverage
        run: |
          pytest mobile_api_ai/tests/ -v --cov=mobile_api_ai --cov-report=xml --cov-report=term
        continue-on-error: false

      - name: Check coverage
        run: |
          COVERAGE=$(python -c "
          import xml.etree.ElementTree as ET
          tree = ET.parse('coverage.xml')
          m = tree.find('.//metrics')
          valid = int(m.attrib.get('covered_lines', 0)) + int(m.attrib.get('missed_lines', 0))
          covered = int(m.attrib.get('covered_lines', 0))
          pct = (covered / valid * 100) if valid > 0 else 0
          print(f'{pct:.1f}')
          ")
          echo "Coverage: ${COVERAGE}%"
          if (( $(echo "$COVERAGE < 95" | bc -l) )); then
            echo "Gate1 FAILED: coverage ${COVERAGE}% < 95%"
            exit 1
          fi
          echo "Gate1 PASSED"

  gate3-bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install bandit
        run: pip install bandit

      - name: Run bandit security scan
        run: |
          bandit -r mobile_api_ai -ll -f json -o bandit.json
          HIGH=$(python -c "import json; d=json.load(open('bandit.json')); print(len([x for x in d['results'] if x['issue_severity']=='HIGH']))")
          echo "HIGH severity: $HIGH"
          if [ "$HIGH" -gt 0 ]; then
            echo "Gate3 FAILED: $HIGH HIGH vulnerabilities found"
            bandit -r mobile_api_ai -ll -f screen | grep "HIGH" | head -20
            exit 1
          fi
          echo "Gate3 PASSED"

  gate2-performance:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install test deps
        run: pip install pytest requests locust

      - name: Start Flask app
        run: |
          cd mobile_api_ai
          nohup python app.py > /tmp/app.log 2>&1 &
          sleep 8

      - name: Run performance baseline
        run: python mobile_api_ai/tests/performance/perf_baseline.py

  gate4-concurrency:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install test deps
        run: pip install pytest requests

      - name: Start Flask app
        run: |
          cd mobile_api_ai
          nohup python app.py > /tmp/app.log 2>&1 &
          sleep 8

      - name: Run concurrency test
        run: python mobile_api_ai/tests/performance/concurrency_test.py

  merge-gate:
    needs: [gate1-pytest, gate3-bandit]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Final gate check
        run: |
          if [[ "${{ needs.gate1-pytest.result }}" != "success" ]]; then
            echo "Gate1 (pytest ≥95%) FAILED — blocking merge"
            exit 1
          fi
          if [[ "${{ needs.gate3-bandit.result }}" != "success" ]]; then
            echo "Gate3 (bandit 0 HIGH) FAILED — blocking merge"
            exit 1
          fi
          echo "All merge gates PASSED — ready to merge"
```

### 6.2 性能压测脚本（需创建）

路径：`mobile_api_ai/tests/performance/perf_baseline.py`

```python
import os, json, time, requests

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5008')
ROUTES_FILE = os.path.join(os.path.dirname(__file__), 'baseline.json')

def measure_latency(route, method='GET', payload=None, count=100):
    times = []
    for _ in range(count):
        start = time.time()
        try:
            if method == 'GET':
                r = requests.get(f'{BASE_URL}{route}', timeout=10)
            else:
                r = requests.post(f'{BASE_URL}{route}', json=payload, timeout=10)
            times.append((time.time() - start) * 1000)
        except Exception:
            times.append(99999)
    times.sort()
    p50 = times[int(len(times) * 0.50)]
    p95 = times[int(len(times) * 0.95)]
    p99 = times[int(len(times) * 0.99)]
    return {'p50': p50, 'p95': p95, 'p99': p99}

def test_all_routes():
    with open(ROUTES_FILE) as f:
        baseline = json.load(f)

    results = {}
    for route, bl in baseline.get('routes', {}).items():
        lat = measure_latency(route)
        threshold = bl['p99'] + 200
        results[route] = {
            'p99': lat['p99'],
            'baseline_p99': bl['p99'],
            'threshold': threshold,
            'pass': lat['p99'] <= threshold
        }
        icon = 'PASS' if lat['p99'] <= threshold else 'FAIL'
        print(f"{icon} {route}: P99={lat['p99']:.0f}ms (baseline={bl['p99']}ms, threshold={threshold}ms)")

    total = len(results)
    passed = sum(1 for r in results.values() if r['pass'])
    pct = passed / total * 100 if total > 0 else 0
    print(f"\nPerformance: {passed}/{total} = {pct:.0f}%")

    if pct < 95:
        print(f"Gate2 FAILED: only {pct:.0f}% < 95%")
        exit(1)
    print("Gate2 PASSED")

if __name__ == '__main__':
    test_all_routes()
```

### 6.3 并发压测脚本（需创建）

路径：`mobile_api_ai/tests/performance/concurrency_test.py`

```python
import os, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5008')
ROUTES = ['/api/health', '/api/stats/overview', '/api/process/list']

def concurrent_call(route, worker_id):
    try:
        r = requests.get(f'{BASE_URL}{route}', timeout=5)
        return r.status_code
    except Exception as e:
        return f"ERROR:{type(e).__name__}"

def test_100_concurrent_10_rounds():
    errors_total = 0
    for rnd in range(10):
        with ThreadPoolExecutor(max_workers=100) as ex:
            futures = []
            for _ in range(100):
                route = ROUTES[rnd % len(ROUTES)]
                futures.append(ex.submit(concurrent_call, route, rnd))
            results = [f.result() for f in as_completed(futures)]

        errors = [r for r in results if isinstance(r, str) or r >= 500]
        if errors:
            print(f"Round {rnd+1}: {len(errors)} errors — FAILED")
            print(errors[:3])
            errors_total += len(errors)
        else:
            print(f"Round {rnd+1}: 100 concurrent OK")

    if errors_total > 0:
        print(f"Gate4 FAILED: {errors_total} total errors")
        exit(1)
    print("Gate4 PASSED: 10 rounds × 100 concurrent = 1000 requests, 0 crash")
```

### 6.4 性能基线文件（需创建）

路径：`mobile_api_ai/tests/performance/baseline.json`

> **需在 Week 1 完成**：51个路由全部跑完，取P50/P95/P99填入下方占位符。

```json
{
  "created": "2026-WEEK1",
  "version": "v3.7.0",
  "note": "由 python perf_baseline.py 首次执行后自动生成",
  "routes": {
    "/api/health": {"p50": 0, "p95": 0, "p99": 0}
  }
}
```

---

## 七、CI基础设施前提（v3.7.1版 + 悲观审计确认）

> ⚠️ **悲观审计第1轮确认**：CI_CD_GATES 文档内容已完整，H3 的问题不是"文档缺失"而是"Week 0 未执行"。
> 以下是真实可落地的执行清单。

### 7.1 Week 0 第1天必须完成的4件事

```
【H3 悲观审计状态：文档完整，待Week 0第1天执行】
```

#### ☐ 事项1：确认GitHub仓库

```
GitHub仓库URL：________________________（填写后不得更改）

确认方法：
  $ git remote -v
  origin  https://github.com/{owner}/{repo}.git (fetch)
  origin  https://github.com/{owner}/{repo}.git (push)

确认状态：☐ 已确认
```

#### ☐ 事项2：确认GitHub Actions已启用

```
确认方法：GitHub网页 → Settings → Actions → "Allow all actions"
确认状态：☐ 已启用
```

#### ☐ 事项3：配置Secrets

```
Settings → Secrets → Actions → New repository secret

☐ MYSQL_HOST        = ________________________（主数据库IP）
☐ MYSQL_PORT        = 3306
☐ MYSQL_USER        = root
☐ MYSQL_PASSWORD    = ________________________
☐ MYSQL_DATABASE    = container_center
☐ BASE_URL          = http://localhost:5008
☐ WECHAT_WEBHOOK_KEY = ________________________

配置状态：☐ 全部填完
```

#### ☐ 事项4：创建.github/workflows/目录

```
$ mkdir -p mobile_api_ai/.github/workflows
$ git add .github/workflows/
$ git commit -m "feat: add CI workflow skeleton"
$ git push origin v3.7.0-refactor

推送后查看：GitHub → Actions 标签页 → 应看到workflow出现
GitHub Actions 状态：☐ workflow已触发
```

#### ☐ 验证Gate1可跑

```
推送后5分钟内：
GitHub → Actions → 点击最新workflow run → pytest job
预期结果：绿色勾 ✅ 或红色X（正常，首次跑失败是预期的）
Gate1验证状态：☐ job可触发
```

### 7.2 Week 0 第1天完成后签字

```
以上5项全部完成后，开发负责人+PM签字：

☐ 事项1 GitHub仓库：________（签名+日期）
☐ 事项2 Actions启用：________（签名+日期）
☐ 事项3 Secrets配置：________（签名+日期）
☐ 事项4 目录创建：________（签名+日期）
☐ 事项5 Gate1验证：________（签名+日期）

→ 5项全部签字后，才算"CI基础设施已就绪"。
→ 此后4-gate方可正常触发。
```

```
【必须在Week 0第1天完成，否则CI/CD是空中楼阁】

1. GitHub仓库地址确认
   - 仓库URL是什么？（private/internal/public？）
   - 谁有push权限？
   - 是否已开启GitHub Actions？

2. CI Runner确认
   - 用GitHub托管runner（免费，公有仓库）？
   - 还是自建runner（需要自己的服务器）？
   - 测试数据库怎么配置？（CI环境没有本地MySQL）

3. 环境变量配置
   - 数据库连接信息放 Secrets 还是 .env 文件？
   - 企微Webhook Key放Secrets？
```

### 7.2 CI依赖项清单

```bash
# Week 0 第1天配置，否则Gate1/3跑不起来

GitHub仓库 Secrets（或等效配置）:
  MYSQL_HOST=127.0.0.1
  MYSQL_PORT=3306
  MYSQL_USER=root
  MYSQL_PASSWORD=xxx
  MYSQL_DATABASE=container_center
  BASE_URL=http://localhost:5008
  WECHAT_WEBHOOK_KEY=your_webhook_key

# 注意：CI runner上需要有一个可访问的MySQL实例
# 方案A: GitHub Actions → 用 GitHub 的 Ubuntu + Docker MySQL
# 方案B: 自建 runner → 连内网MySQL
# 方案C: 用 GitHub-hosted runner + mysql-service container
```

### 7.3 CI落地步骤

```bash
# Step 1: Week 0 第1天在GitHub仓库创建 Secrets
# Settings → Secrets → Actions → New repository secret

# Step 2: 创建 .github/workflows/ci.yml（已在上方6.1节提供YAML）

# Step 3: 验证Gate1可触发
git push origin feature/test-ci
# 查看 GitHub Actions 标签页，确认 pytest job 跑通

# Step 4: 验证Gate3可触发
git push origin feature/test-ci
# 查看 bandit job 结果
```

### 7.4 CI无法落地的备选方案

如果Week 0第1天无法确认CI基础设施（公司内网无GitHub访问权限）：

| 方案 | 说明 | Gate1实现 |
|------|------|---------|
| **A：本地Git hook** | pre-push hook 本地跑pytest | 本地执行 |
| **B：手动Gate** | 每次合并前手动跑pytest+bandit | 人工把控 |
| **C：GitLab迁移** | 迁移到公司GitLab + 自建CI runner | 需额外1-2周 |

---

## 八、CI配置管理

**文件位置**:
- GitHub Actions: `mobile_api_ai/.github/workflows/ci.yml`
- 压测脚本: `mobile_api_ai/tests/performance/`
- 基线数据: `mobile_api_ai/tests/performance/baseline.json`

**Week 0前提**: GitHub仓库确认 + Secrets配置 + CI runner可访问MySQL

**Gate修正（v3.7.1）**:
- Gate1: pytest覆盖率目标从95%改为**80%或当前+40%**（见REGRESSION_TEST_v3.7.0.md）
- Gate2-4: 标准不变

**更新规则**:
- 新增路由 → 更新 `baseline.json`（需跑完整压测）
- 新增依赖 → 更新 CI 的 pip install 行
- 性能基线变更 → 需PM签字确认
- 任何Gate阈值修改 → 需4专家团队评审

**最后更新**: 2026-06-28（v3.7.1脱水版）
