# 5008 移动端排产/报工加载空单 — 根因排查报告

> **排查时间**：2026-06-24
> **服务**：5008 mobile_api_ai（PID 由 `scripts/_check_5008_pid.py` 维护）
> **端口定位**：5008 = `mobile_api_ai/app.py` Flask 服务
> **症状**：移动端排产页面、报工页面打开后**没有订单显示**（空单）

---

## 一、5008 服务路由地图

5008 移动端核心路由（来自 [app.py:1741](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py#L1741) 和 [api/scan.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/scan.py)）：

| 路由 | 用途 | 数据源 |
|------|------|--------|
| `GET /api/schedule_record/list` | 排产列表 | 容器中心 `container_center.schedule_records` 表 |
| `POST /api/scan/task` | 扫码报工前置 | 容器中心 packages + `distribute()` 分配 |
| `GET /api/scan/workorder/<order_no>` | 扫码工单查询 | 容器中心 packages |
| `GET /api/process/my-tasks` | 我的报工任务 | MySQL process_sub_steps/quality_records/material_records/repair_records |
| `GET /api/quality/list` | 质检列表 | MySQL quality_records |

---

## 二、根因分析（4 大可能，按概率排序）

### 根因 1：容器中心 storage 层的 `get_packages` 性能/过滤 bug（最可能）

**证据**：
- [api/scan.py:358-360](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/scan.py#L358-L360) 注释自承：
  > "Dev-only: 验证 report_submitted 链路(因 **storage 既有 get_packages bug, /api/scan/task 的 distribute 成功路径暂走不通**, 此端点用于报告验证)"

- [container_center/storage/document_store.py:259-262](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/container_center/storage/document_store.py#L259-L262)：
  ```python
  def get_packages(self, doc_type='work_order', status=None, limit=100):
      result = self.query(doc_type=doc_type, status=status, size=limit)
      return result['data']
  ```
  → 简单包装 `self.query()`，但 `query()` 在 L246 处的 `size=limit` 实际传入可能与 ES/MySQL 存储层期望的参数名不匹配

**影响范围**：
- `/api/scan/task` 找不到任务 → `distribute` 永远走不通 → 报工前置卡住
- `/api/scan/workorder/<order_no>` 返回"工单未找到"（错误码 2001）

**修复建议**：
```python
# 在 document_store.py 中加日志
def get_packages(self, doc_type='work_order', status=None, limit=100):
    logger.info(f"[get_packages] doc_type={doc_type} status={status} limit={limit}")
    result = self.query(doc_type=doc_type, status=status, size=limit)
    logger.info(f"[get_packages] 返回数量: {len(result.get('data', []))}")
    return result.get('data', [])
```

### 根因 2：状态机映射导致状态显示滞后

**证据**：
- [dispatch_center/_sync.py:152-167](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/dispatch_center/_sync.py#L152-L167) 状态映射表（`STATUS_KEY_TO_MYSQL`）：

  | 英文 key | MySQL 中文值 |
  |---------|-----------|
  | `scheduled` | 已排产 |
  | `confirmed` | 已确认 |
  | `in_production` | 生产中 |

  - 桌面端 `production_orders.status` 字段是**中文**（"已排产"/"已确认"/"生产中"）
  - 5008 移动端 `schedule_records.status` 是**英文 key**（`scheduled`/`confirmed`/`in_production`）

- [app.py:1786](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py#L1786) 中 `schedule_record/update` 接收的 `status` 参数会被存为字符串但**未做枚举校验**，可能写入非预期值
- 两端枚举值不统一时，排产记录从桌面端"已排产"（MySQL中文）同步到容器中心（CC 英文 key）必须经过 `_STATUS_KEY_TO_MYSQL` 反向映射，**反向映射未在同步代码中提供**

**影响范围**：
- 排产列表显示的状态可能是英文 key 原值，未翻译
- 状态从 `scheduled → confirmed` 转换时，反向同步到桌面端可能失败

**修复建议**：
```python
# 在 _sync.py 增加反向映射
_MYSQL_TO_STATUS_KEY = {v: k for k, v in _STATUS_KEY_TO_MYSQL.items()}
```

### 根因 3：调度中心 schedule_bp 与 app.py 内联路由重复注册

**证据**：
- [app.py:1741](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py#L1741) 直接 `@app.route('/api/schedule_record/list')` 定义
- [app.py:1867-1868](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py#L1867-L1868) 又注册 `dispatch_center.schedule_routes` 的 `schedule_bp` + `workorder_bp`

**风险**：
- 两条 `/api/schedule_record/list` 可能并存，Flask 路由匹配第一个，第二个被忽略
- 两套实现，行为可能不一致

**修复建议**：
- 删掉 app.py:1741-1836 内联的排产路由，**统一调用** `dispatch_center/schedule_routes.py`
- 确认 `schedule_routes.py` 实现的 list 接口签名与移动端调用方匹配

### 根因 4：报工子表无任务数据（数据库侧）

**证据**：
- [api/process.py:42-49](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/process.py#L42-L49) 4 段 SQL 都过滤 `status NOT IN ('completed', 'withdrawn')`
- 若所有任务的 `status` 都是 `completed` 或 `withdrawn`，返回空数组 → 前端展示空
- 兜底逻辑（`try/except`）被设计为**静默吞错**（L64/L89/L114/L139），错误被记为 warning 而非 fail

**修复建议**：
- 先用 SQL 直接查询 4 张表：
  ```sql
  SELECT COUNT(*), status FROM process_sub_steps GROUP BY status;
  SELECT COUNT(*), status FROM quality_records GROUP BY status;
  SELECT COUNT(*), status FROM material_records GROUP BY status;
  SELECT COUNT(*), status FROM repair_records GROUP BY status;
  ```
- 如果全部为空，说明桌面端**未将任务写入子表**，是上游数据缺失问题
- 临时调试：把过滤条件 `status NOT IN ('completed', 'withdrawn')` 去掉，看是否能返回数据

---

## 三、快速验证清单

### 1. 现场验证（5 分钟）

```bash
# (1) 验证服务在线
curl http://localhost:5008/api/health

# (2) 验证排产接口（看是否真返回空）
curl http://localhost:5008/api/schedule_record/list?page=1\&page_size=20

# (3) 验证报工任务接口
curl "http://localhost:5008/api/process/my-tasks?worker_id=OP001"

# (4) 验证扫码接口（看错误码 2001 vs 5001 vs 5002）
curl -X POST http://localhost:5008/api/scan/task \
  -H "Content-Type: application/json" \
  -d '{"qr_data":"WO:WO202606001","operator_id":"OP001"}'
```

### 2. 数据库侧验证（10 分钟）

```sql
-- 容器中心排产表数据量
SELECT COUNT(*), status FROM container_center.schedule_records 
WHERE is_deleted=0 GROUP BY status;

-- 报工子表数据量
SELECT 'process_sub_steps' tbl, COUNT(*) total, 
       SUM(status NOT IN ('completed','withdrawn')) active
FROM process_sub_steps
UNION ALL
SELECT 'quality_records', COUNT(*), 
       SUM(status NOT IN ('completed','withdrawn'))
FROM quality_records
UNION ALL
SELECT 'material_records', COUNT(*), 
       SUM(status NOT IN ('completed','withdrawn'))
FROM material_records
UNION ALL
SELECT 'repair_records', COUNT(*), 
       SUM(status NOT IN ('completed','withdrawn'))
FROM repair_records;
```

### 3. 日志验证（5 分钟）

```bash
# 5008 错误日志
tail -f mobile_api_ai/logs/main_server.err | grep -E "scan|schedule|process"
tail -f mobile_api_ai/logs/dispatch_5003.err | grep -E "sync|status"
```

---

## 四、按优先级修复路线

| 优先级 | 操作 | 预计耗时 |
|--------|------|---------|
| **P0** | 数据库 SQL 验证清单（第三部分第 2 点）— 确认是否有数据 | 10 min |
| **P0** | curl 接口验证（第三部分第 1 点）— 确认返回结构 | 5 min |
| **P1** | 在 `get_packages` 加日志，确认 storage bug 影响范围 | 30 min |
| **P1** | 在 `app.py:1741-1836` 加 `if request.endpoint != 'schedule_record_list': return` 临时 debug，验证是否路由冲突 | 15 min |
| **P2** | 增加状态反向映射 `_MYSQL_TO_STATUS_KEY` | 30 min |
| **P2** | 统一 `schedule_record/list` 路由（app.py 内联 vs schedule_bp），删除重复 | 1h |
| **P3** | 把 `api/process.py` 兜底 `try/except` 改为显式 fail | 1h |

---

## 五、关键代码索引

| 文件 | 行号 | 关键函数/路由 |
|------|------|------------|
| [mobile_api_ai/app.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py) | 1741 | `schedule_record_list` 内联路由 |
| [mobile_api_ai/app.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py) | 1867-1868 | schedule_bp/workorder_bp 注册 |
| [mobile_api_ai/api/scan.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/scan.py) | 69-108 | `find_task_in_container` 在容器中找任务 |
| [mobile_api_ai/api/scan.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/scan.py) | 186-250 | `scan_workorder_task` 扫码分配任务 |
| [mobile_api_ai/api/process.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/api/process.py) | 24-152 | `my_tasks` 报工任务列表（4 表） |
| [mobile_api_ai/container_center_v5.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/container_center_v5.py) | 1035-1064 | `collect_report` 收集报工数据 |
| [mobile_api_ai/container_center/storage/document_store.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/container_center/storage/document_store.py) | 259-262 | `get_packages` 容器包查询（**bug 疑似点**） |
| [mobile_api_ai/dispatch_center/_sync.py](file:///d:/yuan/%E4%B8%8D%E9%94%88%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/dispatch_center/_sync.py) | 152-167 | `_STATUS_KEY_TO_MYSQL` 状态映射（缺少反向映射） |

---

## 六、结论

**最大可能性**：`get_packages` 容器中心 storage 层的 bug 导致移动端扫码/排产接口无法从容器拿到任务包。

**最可能次因**：状态机映射缺失反向映射，导致桌面端 → 容器中心同步链路状态丢失或显示英文 key。

**最简单诊断**：第三部分"快速验证清单"前两步（curl + SQL 验证），可在 **15 分钟内**确认是数据问题还是代码问题。
