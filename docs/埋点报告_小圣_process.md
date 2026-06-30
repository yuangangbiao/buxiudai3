# 埋点报告 - process 蓝图(小圣)

> 任务人:小圣(架构师)
> 执行日期:2026-06-23 17:01
> 待埋点文件:`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api\process.py`
> 不变更文件:`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\metrics.py`(只读消费)
> 涉及端口:5008(mobile_api_ai)

---

## 1. 端点清单

| # | 方法 | 路径 | 业务含义 | 埋点类型 |
|---|------|------|---------|---------|
| 1 | GET | `/api/process/my-tasks` | 操作员任务列表(生产/质检/物料/维修合并查询) | api_request + record_error |

> 共 1 个端点。`grep -n "@bp.route" process.py` 结果:`@bp.route('/my-tasks', methods=['GET'])` 唯一命中。
> 不存在 POST 端点,任务要求"不只改 GET 不改 POST"已天然满足(整个蓝图就只有 1 个 GET)。

---

## 2. 埋点代码 diff

### 2.1 import 改动(文件顶部)

```python
# 新增
import time
from metrics import metrics
```

> 路径选择依据:`metrics.py` 位于 `mobile_api_ai/` 包根目录,与 `metrics_api.py` 同款用法一致(`grep "from metrics" mobile_api_ai/api/*.py` 唯一命中 `metrics_api.py:7`)。

### 2.2 `my_tasks` 函数改造

| 改造点 | 改造前 | 改造后 |
|--------|--------|--------|
| 进入计时 | 无 | `start = time.time(); status_code = 200` |
| 参数校验失败 | 直接 `return fail(400)`,无埋点 | 显式 `status_code = 400` 后 finally 埋点 |
| 成功返回 | `return success(...)` | 不变 |
| 异常捕获 | 仅 `return fail(500)` | 增加 `metrics.record_error('process_error', str(e), endpoint)` |
| 退出埋点 | 无 | `finally: metrics.api_request(endpoint, duration, status_code)` |

关键 diff(节选,完整 diff 见 git):

```python
@bp.route('/my-tasks', methods=['GET'])
def my_tasks():
    """获取操作员的任务列表(生产/质检/物料/维修)"""
    endpoint = '/api/process/my-tasks'
    start = time.time()
    status_code = 200
    try:
        worker_id = request.args.get('worker_id', '')
        if not worker_id.strip():
            status_code = 400
            return fail(message="缺少 worker_id 参数", code=400)
        # ... 4 个 SELECT 子查询(原业务代码未改动) ...
        return success(data={'tasks': task_list[:50], 'total': len(task_list)})
    except Exception as e:
        status_code = 500
        metrics.record_error('process_error', str(e), endpoint)   # ← 新增
        logger.exception("my_tasks error")
        return fail(500, message=str(e))
    finally:
        duration = time.time() - start
        metrics.api_request(endpoint, duration, status_code)     # ← 新增
```

### 2.3 报工类端点额外埋点

> process 蓝图**没有**报工类端点(`/api/process/report` 不在本蓝图)。任务要求"报工类端点额外调用 `metrics.report_submitted`" — N/A(本蓝图无此场景)。
> 报工端点位于其他蓝图(待后续分配)。

---

## 3. 验证截图(实跑数据)

### 3.1 200 路径(正常查询)

**命令**:`& "C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe" -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:5008/api/process/my-tasks?worker_id=test_001', timeout=8); print(r.status, r.read().decode()[:120])"`
**时间**:2026-06-23 17:01:50
**文件路径**:`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api\process.py:24-29`

```
status=200
{"code":0,"data":{"tasks":[],"total":0},"message":"操作成功"}
```

✅ 业务响应正常,埋点不破坏业务。

### 3.2 400 路径(缺 worker_id)

**命令**:同 3.1,去掉 `?worker_id=...`
**时间**:2026-06-23 17:01:51
**文件路径**:`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api\process.py:32-34`

```
HTTP 200 (Flask 默认包装), body={"code":400,"message":"缺少 worker_id 参数"}
```

✅ 业务校验失败路径走通,埋点记 status_code=400。

### 3.3 500 路径(数据库异常) + record_error 验证

**触发方法**:在 `_get_conn` 临时加文件开关 `if os.path.exists('.tmp_simulate_500'): raise RuntimeError(...)`,调一次,跑完恢复并删文件。
**命令**:`python scripts/_trigger_500.py`
**时间**:2026-06-23 17:01:30
**文件路径**:`d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api\process.py:21-23` (已恢复)

**响应**:
```
status=200 (Flask 包装), body={"code":500,"message":"SIMULATED_DB_ERROR_for_500_path_verification"}
```

**`/api/metrics/stats` 数据**:
```
api.total_requests = 3
api.status_codes   = {'200': 1, '404': 1, '500': 1}
errors.total       = 2
errors.by_type     = {api_errors_total: 2, api_requests_total: 3, errors_process_error: 1, errors_total: 2, errors_worker_scan_miss: 1}
recent errors:
  - worker_scan_miss      | 工人不存在: nonexistent_999       | endpoint=/api/scan/worker/<worker_id>
  - process_error         | SIMULATED_DB_ERROR_for_500_path_… | endpoint=/api/process/my-tasks  ← 本次埋点
```

✅ **record_error 路径确认生效**:`errors_process_error: 1` 命中,`endpoint=/api/process/my-tasks` 正确。
> 附:`404 + worker_scan_miss` 是 scan 蓝图正常业务触发,非本次任务范围。

### 3.4 metrics 终态数据(恢复后真实业务跑通)

**命令**:`python scripts/_verify_process_metrics.py`(3 次 GET my-tasks + 1 次 reset)
**时间**:2026-06-23 17:02:30
**文件路径**:`d:\yuan\不锈钢网带跟单3.0\scripts\_verify_process_metrics.py`

```
api.total_requests      = 3
api.status_codes        = {'200': 2, '400': 1}
api.top_endpoints       = {'/api/process/my-tasks': 3}
api.avg_duration_ms     = 36.4
api.error_rate          = 0.0
reports.total           = 0   (本蓝图无报工端点,符合预期)
errors.total            = 0
```

✅ **所有验收标准 1~5 全部满足**。

---

## 4. 完成度报告

| 字段 | 要求 |
|------|------|
| **完成度** | 5 / 5 (100%) |
| **主线目标** | ✅ 完成 — 1 个端点全路径埋点,200/400/500 三态均通过 metrics 实测验证 |

### 已验证项

| # | 验证项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | `metrics.api_request` 进入/退出调用 | ✅ | `api.top_endpoints: {'/api/process/my-tasks': 3}`(实跑命令 + 时间 + 文件路径见 3.4) |
| 2 | 异常路径走 `metrics.record_error` | ✅ | `errors_process_error: 1, endpoint=/api/process/my-tasks`(实跑命令见 3.3) |
| 3 | 报工类端点额外 `metrics.report_submitted` | N/A | process 蓝图无报工端点(grep `@bp.route` 仅 1 个 GET 命中) |
| 4 | 重启 5008 不报错 | ✅ | `restart_5008_metrics.py` 输出 "5008 READY at 1s, status=200" + `/api/metrics/health` 返回 200(命令见重启日志 17:00:27 / 17:01:55) |
| 5 | `/api/metrics/stats` 数据增长 | ✅ | `api.total_requests: 0 → 3`,`api.status_codes: {200:2, 400:1}`(命令 `_verify_process_metrics.py`) |

### 阻塞项

无。

### 下一刀

- [ ] 报工类端点(若其他蓝图存在)按同样模板补埋点 — 等待任务分配
- [ ] `metrics.py` 增加按 `endpoint` 维度的 P95 延迟直方图(可选优化)

---

## 5. 业务影响报告

### 5.1 用户场景对比

| # | 用户角色 | 改善前(痛点) | 改善后(价值) |
|---|---------|---------------|---------------|
| 1 | 运维/架构师(我) | 5008 异常时只能翻 Flask 日志,无法第一时间定位"process 端点到底慢不慢、错不错" | `/api/metrics/stats` 实时显示 `top_endpoints: /api/process/my-tasks: 3`、`avg_duration_ms: 36.4`,1 秒内定位 |
| 2 | 报工 App 前端 | 后端偶发 500 时无任何上报,只能依赖用户反馈"页面空白" | `errors_process_error` 自动累计,带 endpoint 标签,运维主动告警 |
| 3 | 产品/PM | 不知道 process 模块真实 QPS 与错误率,排期靠"听说" | `api.status_codes: {200: 2, 400: 1}` 直接反映线上业务码分布 |

### 5.2 业务能力新增(按业务流分类)

| 业务流 | 新增/优化功能 | 影响范围 |
|--------|--------------|---------|
| 监控 | process 蓝图全端点纳入 `/api/metrics/stats` 统计 | 5008 全局可观测性 +1 端点 |
| 监控 | process 端点异常自动入 `errors_process_error` 分类计数器 | 5008 错误告警源 +1 |
| 生产(报工查询) | 无业务逻辑变更,仅加埋点 | 0 行为变更 |
| 质检 / 物料 / 维修 | 无业务逻辑变更,仅加埋点 | 0 行为变更 |

### 5.3 不变更部分(防回归保护清单)

| # | 模块/功能 | 保护措施 | 验证方式 |
|---|----------|---------|---------|
| 1 | 4 个 SELECT 子查询(process_sub_steps / quality_records / material_records / repair_records) | 源码逐行对比 — 业务 SQL 字符未改 | 见 3.1,响应 `tasks=[]` 与改造前一致 |
| 2 | `success/fail` 返回结构(`{code, message, data?}`) | 未改 | 3.1 响应 `{"code":0,"data":{...}}` 结构一致 |
| 3 | 报工业务逻辑 | 本蓝图无报工端点,不涉及 | grep `@bp.route` 仅 1 个 GET 命中 |
| 4 | `metrics.py` 指标收集器实现 | 只读消费,未改 | `git diff mobile_api_ai/metrics.py` 为空 |
| 5 | `ai.py` AI 接口 | 任务明确"不要碰",未读未改 | 未访问该文件 |
| 6 | 数据库表结构 | 未执行 DDL | 无 `.sql` 改动 |

### 5.4 一句话总结

> 本次改动让 `process` 蓝图从"日志翻不到/无指标"变为"`/api/metrics/stats` 实时显示 200/400/500 三态分布 + endpoint 维度错误自动归类"。

---

## 6. 数字三要素(反虚高)

| 数字 | 命令 | 时间 | 文件 |
|------|------|------|------|
| 1 端点 | `grep -n "@bp.route" mobile_api_ai/api/process.py` | 2026-06-23 17:00:10 | `process.py:24` |
| 200/400/500 三态 | `python scripts/_verify_process_metrics.py` + `python scripts/_trigger_500.py` | 2026-06-23 17:01:30~17:02:30 | `scripts/_verify_process_metrics.py`, `scripts/_trigger_500.py` |
| 3 次 API 调用入统计 | `api.top_endpoints: {'/api/process/my-tasks': 3}` | 2026-06-23 17:02:30 | `/api/metrics/stats` 响应 |
| errors_process_error=1 | `errors.by_type: {errors_process_error: 1}` | 2026-06-23 17:01:30 | `/api/metrics/stats` 响应 |
| 36.4ms 平均延迟 | `api.avg_duration_ms: 36.4` | 2026-06-23 17:02:30 | `/api/metrics/stats` 响应 |

> **未测过的数字**:无。所有数字均附命令 + 时间 + 文件路径。

---

## 7. 已知风险/未闭环

1. **500 路径验证使用了文件开关(`.tmp_simulate_500`)**:为避免改业务代码破坏生产,临时在 `_get_conn` 加 `os.path.exists` 开关,验证后已删除并清理 `__pycache__/process.cpython*.pyc` 缓存。恢复后 `process.py:19-21` 与改造前一致。**已闭环**。
2. **process 蓝图无报工类端点**:`report_submitted` 调用 N/A。如后续发现遗漏(如 POST `/api/process/submit`),需按本报告 §2 模板补埋点。
3. **跨进程埋点一致性**:`metrics` 是进程内 deque(maxlen=1000),5008 多 worker 部署时各进程独立计数。本次单进程部署不受影响,但若引入 gunicorn 多 worker 需评估。

---

## 8. 文件清单(本任务)

| 类型 | 路径 | 状态 |
|------|------|------|
| 修改 | `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api\process.py` | ✅ 已埋点 |
| 验证脚本 | `d:\yuan\不锈钢网带跟单3.0\scripts\_verify_process_metrics.py` | ✅ 新建 |
| 验证脚本 | `d:\yuan\不锈钢网带跟单3.0\scripts\_verify_500_path.py` | ✅ 新建(辅助) |
| 验证脚本 | `d:\yuan\不锈钢网带跟单3.0\scripts\_trigger_500.py` | ✅ 新建(辅助) |
| 报告 | `d:\yuan\不锈钢网带跟单3.0\docs\埋点报告_小圣_process.md` | ✅ 本文件 |
