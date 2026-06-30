# 51路由回归测试清单 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P1 文档，Week 0 建立框架，Week 3前完成全部用例
> **审计来源**: 4专家审计（小贺品控）→ H-3
> **维护人**: 开发+品控（小贺）

---

## 一、测试覆盖范围

### 1.1 蓝图优先级分级（高风险先测）

> 🔴 高风险：涉及写库/事务/外部微信调用，必须先测
> 🟡 中风险：涉及只读但影响老板/工人核心体验
> 🟢 低风险：内部管理接口，影响小

| 优先级 | 蓝图 | 路由数 | 涉及写库 | 涉及Bug | 对应文件 | 状态 |
|:------:|------|:------:|:--------:|:-------:|---------|:----:|
| 🔴 P0 | **process.bp** | 8 | ✅ | BUG-P0-003 | app.py | ⬜ |
| 🔴 P0 | **scan.bp** | 2 | ✅ | BUG-P0-002 | app.py | ⬜ |
| 🔴 P0 | **auth.bp** | 3 | ✅ | BUG-P0-001 | app.py | ⬜ |
| 🔴 P0 | **quality.bp** | 4 | ✅ | - | app.py | ⬜ |
| 🔴 P0 | **quality_inspection.bp** | 3 | ✅ | - | app.py | ⬜ |
| 🔴 P0 | **approval.bp** | 2 | ✅ | - | app.py | ⬜ |
| 🟡 P1 | **legacy_routes.bp** | ~5 | 混合 | BUG-P1/P2系列 | api/legacy_routes.py | ⬜ |
| 🟡 P1 | **message.bp** | 2 | ✅ | - | app.py | ⬜ |
| 🟡 P1 | **stats.bp** | 2 | ✅ | - | app.py | ⬜ |
| 🟡 P1 | **report_record_admin** | 20 | ✅ | - | report_record_admin.py | ⬜ |
| 🟢 P2 | **health.bp** | 1 | ❌ | - | app.py | ⬜ |
| 🟢 P2 | **ai.bp** | 6 | ❌ | - | api/ai.py | ⬜ |
| 🟢 P2 | **cost.bp** | 13 | ❌ | - | api/cost.py | ⬜ |
| 🟢 P2 | **reports.bp** | 22 | ❌ | - | api/reports.py | ⬜ |
| 🟢 P2 | **inventory_external.bp** | ~3 | ❌ | - | app.py | ⬜ |

**测试顺序**：先测🔴P0批次（6个蓝图）→ 再测🟡P1批次 → 最后测🟢P2批次
**注**：蓝图表态以Week 0 N15诊断结果为准。静默蓝图（ai/cost/reports）若降级/删除，对应测试用例同步移除。

---

## 二、测试用例模板

每个路由必须包含以下5类测试用例：

### 模板：路由回归测试

```python
# tests/test_regression/test_{module}_{route}.py

class Test{route_class_name}:
    """回归测试：{路由描述}"""

    @pytest.fixture
    def auth_headers(self):
        """认证头 fixture"""
        # 登录获取token
        resp = requests.post(f'{BASE_URL}/api/auth/login', json={
            'username': os.getenv('TEST_USERNAME', 'admin'),
            'password': os.getenv('TEST_PASSWORD', 'admin123'),
        })
        token = resp.json()['data']['token']
        return {'Authorization': f'Bearer {token}'}

    def test_{route_name}_正常情况(self, auth_headers):
        """技术验证：正常输入返回正确数据"""
        resp = requests.get(f'{BASE_URL}{ROUTE}', headers=auth_headers)
        assert resp.status_code == 200
        assert 'data' in resp.json()

    def test_{route_name}_无权限(self):
        """技术验证：无token被拒绝"""
        resp = requests.get(f'{BASE_URL}{ROUTE}')
        assert resp.status_code == 401

    def test_{route_name}_边界值(self, auth_headers):
        """异常验证：极端输入不崩溃"""
        resp = requests.get(f'{BASE_URL}{ROUTE}?page=-1', headers=auth_headers)
        # 应返回400或空数据，不应500
        assert resp.status_code in [200, 400]

    def test_{route_name}_并发安全(self, auth_headers):
        """并发验证：100并发请求无崩溃"""
        from concurrent.futures import ThreadPoolExecutor
        def call():
            r = requests.get(f'{BASE_URL}{ROUTE}', headers=auth_headers)
            return r.status_code
        with ThreadPoolExecutor(max_workers=100) as ex:
            results = list(ex.map(lambda _: call(), range(100)))
        assert all(s in [200, 401, 403] for s in results)  # 无500

    def test_{route_name}_性能基准(self, auth_headers):
        """性能验证：P99 ≤ 1000ms"""
        import time
        times = []
        for _ in range(100):
            start = time.time()
            requests.get(f'{BASE_URL}{ROUTE}', headers=auth_headers)
            times.append((time.time() - start) * 1000)
        p99 = sorted(times)[98]
        assert p99 <= 1000, f"P99={p99:.0f}ms > 1000ms"
```

---

## 三、51路由清单（app.py 26处直连对应路由）

> 以下为预计路由，实际以代码分析为准

| # | 蓝图 | 路由 | HTTP方法 | 测试用例数 | 状态 |
|---|------|------|:--------:|:---------:|:----:|
| 1 | auth.bp | /api/auth/login | POST | 5 | ⬜ |
| 2 | auth.bp | /api/auth/logout | POST | 2 | ⬜ |
| 3 | auth.bp | /api/auth/userinfo | GET | 3 | ⬜ |
| 4 | scan.bp | /api/scan/verify | POST | 4 | ⬜ |
| 5 | scan.bp | /api/scan/records | GET | 2 | ⬜ |
| 6 | process.bp | /api/process/list | GET | 4 | ⬜ |
| 7 | process.bp | /api/process/{id} | GET | 3 | ⬜ |
| 8 | process.bp | /api/process/{id} | PUT | 4 | ⬜ |
| 9 | process.bp | /api/process/{id}/publish | POST | 3 | ⬜ |
| 10 | process.bp | /api/process/{id}/complete | POST | 3 | ⬜ |
| 11 | process.bp | /api/process/substeps | GET | 3 | ⬜ |
| 12 | process.bp | /api/process/substeps | POST | 4 | ⬜ |
| 13 | process.bp | /api/process/{id}/sync | POST | 3 | ⬜ |
| 14 | process.bp | /api/process/idempotent | GET | 3 | ⬜ |
| 15 | quality.bp | /api/quality/list | GET | 3 | ⬜ |
| 16 | quality.bp | /api/quality/{id} | GET | 3 | ⬜ |
| 17 | quality.bp | /api/quality | POST | 4 | ⬜ |
| 18 | quality.bp | /api/quality/{id} | PUT | 4 | ⬜ |
| 19 | quality_inspection.bp | /api/quality-inspection/records | GET | 3 | ⬜ |
| 20 | quality_inspection.bp | /api/quality-inspection/{id} | GET | 3 | ⬜ |
| 21 | quality_inspection.bp | /api/quality-inspection | POST | 4 | ⬜ |
| 22 | message.bp | /api/message/list | GET | 2 | ⬜ |
| 23 | message.bp | /api/message/send | POST | 3 | ⬜ |
| 24 | approval.bp | /api/approval/list | GET | 3 | ⬜ |
| 25 | approval.bp | /api/approval/{id} | POST | 3 | ⬜ |
| 26 | health.bp | /api/health | GET | 2 | ⬜ |
| 27 | stats.bp | /api/stats/overview | GET | 3 | ⬜ |
| 28 | stats.bp | /api/stats/daily | GET | 3 | ⬜ |

---

## 四、pytest覆盖率真实目标（v3.7.1版）

> ⚠️ **脱水说明**：v3.7.0喊pytest≥95%是无根据的数字。
> 实际情况：已有85个测试文件，但从未测过覆盖率。
> Week 0必须先测出当前覆盖率，再定合理目标。

### 4.1 覆盖率测量（Week 0第1件事）

```bash
cd mobile_api_ai
pytest tests/ --cov=mobile_api_ai --cov-report=term --cov-report=xml -v
# 查看 coverage.xml 中的 covered_lines / valid_lines
```

### 4.2 合理目标（按范围比例）

| 阶段 | 时间 | 目标覆盖率 | 说明 |
|------|------|:---------:|------|
| Week 0（起点） | Week 0 | **测出当前值** | 填入下方空白 |
| G1放量前 | Week 4末 | **当前+X%** | Layer1第一批51路由用例补充 |
| G3放量前 | Week 10末 | **65%** | Layer1全部完成后 |
| 最终验收 | Week 19 | **80%** | 全量完成后 |

```
当前覆盖率: ____% ← Week 0实测后填写（不得留空）
G1目标: 当前覆盖率 + 15%
G3目标: 65%
最终目标: 80%
```

**为什么不喊95%**：
- v3.7.1明确范围：51处/Layer1
- 51路由覆盖 / 全部代码行数 = ~40%覆盖率上限
- 加上dispatch_center等核心模块，80%是天花板
- 95%是不考虑范围的虚高数字，喊了也达不到

### 4.3 测试执行节奏

| 阶段 | 时间 | 任务 | 通过率目标 |
|------|------|------|:---------:|
| 覆盖率测量 | Week 0 第1天 | 跑现有85个测试，测覆盖率 | 测出真实值 |
| 冒烟测试骨架 | Week 0 | 51个路由建立测试骨架 | 框架就绪即可 |
| 第一批🔴P0 | Week 2-4 | app.py 6个蓝图（写库+事务） | 优先通过 |
| 第二批🟡P1 | Week 5-7 | report_record 20路由 | 优先通过 |
| 第三批🟢P2 | Week 8-10 | 剩余路由 + legacy_routes | 补充完善 |
| G1放量前 | Week 4末 | 全部51路由全量通过 | 50% |
| G3放量前 | Week 10末 | 全量回归 | 65% |
| Week 19 | 验收前 | 全量回归 + 性能压测 | 80% |

---

## 五、测试数据管理

### 5.1 测试账号

```bash
# .env.test
TEST_USERNAME=admin
TEST_PASSWORD=admin123
TEST_WORKER_USERNAME=worker_test
TEST_WORKER_PASSWORD=Worker@123
BASE_URL=http://localhost:5008
```

### 5.2 测试数据隔离

- 每个测试用例使用独立的测试数据（test_前缀）
- 测试数据在teardown时清理
- 禁止在生产环境运行回归测试

---

## 六、签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | 编写测试用例 | ☐ |
| 品控（小贺） | 审核测试覆盖度 | ☐ |
| PM（小曦） | 确认工厂场景覆盖 | ☐ |

**截止**: Week 3 前完成全部测试用例编写
**最后更新**: 2026-06-28
