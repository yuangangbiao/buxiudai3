# SUPPLEMENT_全面模块化改造.md（补充方案）

> 文档版本：v1.0
> 日期：2026-06-13
> 用途：补充审计中发现的 5 大缺口 + 5 项实施保障

---

## 〇、灰度切换机制（T26）

> **重要前提**：5003 是**消息入口**，不是所有内部服务统一入口。  
> 本节中所有"通过 5003"指的是**消息类**调用。

### 0.0 5003 角色澄清

| 角色 | 5003 调度中心 |
|------|--------------|
| **消息入口** | ✅ 报工、状态变更、通知等 |
| **数据查询** | ❌ 不必走 5003（直连本地表） |
| **API Gateway** | ❌ 5003 不是 API Gateway |
| **库存管理** | ❌ 5010 独立，不走 5003 |

### 0.1 切换策略

采用**功能开关（Feature Flag）**方式实现灰度切换。

### 0.2 开关设计

```python
# mobile_api_ai/config/feature_flags.py（新建）
FEATURE_FLAGS = {
    # DAL 灰度切换（百分比）
    'DAL_ENABLED': {
        'enabled': False,           # 总开关
        'percentage': 0,            # 灰度比例 0-100
        'whitelist': [],            # 白名单 order_no
        'blacklist': [],            # 黑名单 order_no
    },

    # 各模块独立开关
    'ORDER_MODULE_DAL': False,      # 订单模块走 DAL
    'PROCESS_MODULE_DAL': False,   # 工序模块走 DAL
    'QUALITY_MODULE_DAL': False,   # 质检模块走 DAL
    'MATERIAL_MODULE_DAL': False,  # 物料模块走 DAL

    # 8008 桥接开关
    'SYNC_BRIDGE_VIA_8008': False,  # 走 8008 同步

    # 读取优化
    'READ_FROM_LOCAL_TABLES': True, # 读取走本地表
}
```

### 0.3 灰度阶段

| 阶段 | 比例 | 持续时间 | 验证内容 |
|------|------|----------|----------|
| **P0: 暗部署** | 0% | 1 天 | DAL 初始化、模块加载无异常 |
| **P1: 内测** | 1% | 3 天 | 单订单走 DAL，监控错误率 |
| **P2: 小流量** | 10% | 3 天 | 10% 订单走 DAL，对比数据一致性 |
| **P3: 大流量** | 50% | 3 天 | 50% 订单走 DAL，监控性能 |
| **P4: 全量** | 100% | 持续 | 全量走 DAL |

### 0.4 切换判断逻辑

```python
# mobile_api_ai/dal/base.py
def should_use_dal(self, order_no: str = None) -> bool:
    """判断是否走 DAL"""
    flag = FEATURE_FLAGS.get('DAL_ENABLED', {})

    if not flag.get('enabled'):
        return False

    # 白名单优先
    if order_no and order_no in flag.get('whitelist', []):
        return True

    # 黑名单跳过
    if order_no and order_no in flag.get('blacklist', []):
        return False

    # 百分比判断
    percentage = flag.get('percentage', 0)
    if percentage >= 100:
        return True
    if percentage <= 0:
        return False

    # 使用 hash 稳定分流
    if order_no:
        return (hash(order_no) % 100) < percentage
    return False
```

### 0.5 回滚机制

| 触发条件 | 操作 |
|----------|------|
| 错误率 > 5% | 自动回滚 |
| 性能下降 > 50% | 自动回滚 |
| 同步失败率 > 10% | 自动回滚 |
| 人工决策 | 一键回滚 |

```python
# mobile_api_ai/dal/rollback.py
def emergency_rollback():
    """紧急回滚"""
    FEATURE_FLAGS['DAL_ENABLED']['enabled'] = False
    FEATURE_FLAGS['DAL_ENABLED']['percentage'] = 0
    logger.critical('[DAL] 紧急回滚，所有请求走旧实现')

def gradual_rollback(target_percentage):
    """渐进回滚"""
    FEATURE_FLAGS['DAL_ENABLED']['percentage'] = target_percentage
    logger.warning(f'[DAL] 灰度回滚至 {target_percentage}%')
```

---

## 〇点一、8008 降级方案（T27）

### 1.1 降级策略

8008 不可达时，采用**降级模式**：

```
8008 可达 → 正常模式
8008 不可达 → 降级模式（仅写 container_center）
8008 恢复 → 自动恢复
```

### 1.2 降级状态机

```
┌─────────────────────────────────────────────┐
│                                             │
│   正常模式                                    │
│   ┌─────────┐                               │
│   │ 写入     │ → 8008 → steel_belt         │
│   │ container│                              │
│   └─────────┘                               │
│        ↓ 8008 连续失败 3 次                  │
│   降级模式                                    │
│   ┌─────────┐                               │
│   │ 写入     │ → 仅 container_center       │
│   │ container│                              │
│   └─────────┘                               │
│        ↓ 8008 恢复（健康检查通过）           │
│   正常模式                                    │
│   ┌─────────┐                               │
│   │ 写入     │ → 8008 → steel_belt         │
│   │ container│                              │
│   └─────────┘                               │
│                                             │
└─────────────────────────────────────────────┘
```

### 1.3 降级实现

```python
# mobile_api_ai/sync/bridge_client.py（新建）
class BridgeClient:
    """8008 桥接客户端（带降级）"""

    def __init__(self):
        self.url = os.environ.get('SYNC_BRIDGE_URL', 'http://localhost:8008')
        self.failure_count = 0
        self.degraded = False
        self.MAX_FAILURES = 3
        self.RECOVER_INTERVAL = 60  # 秒
        self.last_check = 0

    def sync_to_steelbelt(self, data: dict) -> bool:
        """同步到 steel_belt（带降级）"""
        if self.degraded:
            if not self._try_recover():
                logger.warning('[8008] 降级模式，仅写 container_center')
                return False
        try:
            resp = requests.post(
                f'{self.url}/api/dal/sync-to-steelbelt',
                json=data,
                timeout=5
            )
            if resp.ok:
                self.failure_count = 0
                return True
            self._record_failure()
            return False
        except (requests.exceptions.Timeout, ConnectionError) as e:
            self._record_failure(e)
            return False

    def _record_failure(self, err=None):
        """记录失败"""
        self.failure_count += 1
        if self.failure_count >= self.MAX_FAILURES:
            self.degraded = True
            logger.error(f'[8008] 连续失败 {self.failure_count} 次，进入降级模式: {err}')
            self._send_alert('degraded')

    def _try_recover(self) -> bool:
        """尝试恢复"""
        now = time.time()
        if now - self.last_check < self.RECOVER_INTERVAL:
            return False
        self.last_check = now
        try:
            resp = requests.get(f'{self.url}/sync/queue/status', timeout=2)
            if resp.ok:
                self.degraded = False
                self.failure_count = 0
                logger.info('[8008] 恢复成功，退出降级模式')
                self._send_alert('recovered')
                return True
        except Exception:
            pass
        return False
```

### 1.4 降级时的数据处理

| 数据类型 | 降级处理 |
|----------|----------|
| 报工 | 写入 `process_sub_steps`（container_center），标记 `pending_sync=1` |
| 状态变更 | 写入 `process_records`（container_center），标记 `pending_sync=1` |
| 订单创建 | 写入 `orders_local`（container_center），标记 `pending_sync=1` |

### 1.5 降级时数据补偿

```python
# 定时任务：每 5 分钟扫描 pending_sync 记录
def sync_pending_records():
    """补偿降级期间未同步的数据"""
    records = storage.get_pending_sync_records()
    for rec in records:
        bridge_client.sync_to_steelbelt(rec)
        if not bridge_client.degraded:
            storage.mark_synced(rec['id'])
```

---

## 〇点二、监控告警点（T28）

### 2.1 监控指标

| 指标 | 采集点 | 告警阈值 |
|------|--------|----------|
| **DAL 调用成功率** | DAL 各模块 | < 95% |
| **8008 同步成功率** | BridgeClient | < 90% |
| **同步延迟** | sync_queue | > 10 秒 |
| **跨库直查次数** | 监控系统 | > 0（应为零） |
| **本地表同步延迟** | orders_local | > 60 秒 |
| **线程数** | thread_lifecycle | > 100 |
| **数据库连接池使用率** | PooledDB | > 80% |

### 2.2 告警点

| 告警 ID | 触发条件 | 通知方式 | 级别 |
|---------|----------|----------|------|
| `DAL_001` | DAL 模块错误率 > 5% | 企业微信 + 日志 | ERROR |
| `DAL_002` | 8008 不可达 | 企业微信 + 短信 | CRITICAL |
| `DAL_003` | 同步队列堆积 > 100 | 企业微信 | WARNING |
| `DAL_004` | 跨库直查检测到新点 | 日志 | WARNING |
| `DAL_005` | 降级模式触发 | 企业微信 + 短信 | CRITICAL |
| `DAL_006` | 字段白名单违规 | 日志 + 立即告警 | CRITICAL |
| `DAL_007` | 线程数异常 | 日志 | WARNING |
| `DAL_008` | 数据库连接池满 | 日志 + 告警 | ERROR |

### 2.3 监控实现

```python
# mobile_api_ai/monitoring/dal_monitor.py（新建）
class DALMonitor:
    """DAL 监控器"""

    def __init__(self):
        self.metrics = {
            'dal_success': 0,
            'dal_failure': 0,
            'sync_success': 0,
            'sync_failure': 0,
            'cross_db_hits': 0,
            'queue_size': 0,
        }
        self.alerts = []

    def record_dal_call(self, module, success):
        """记录 DAL 调用"""
        if success:
            self.metrics['dal_success'] += 1
        else:
            self.metrics['dal_failure'] += 1
            self._check_alert('DAL_001')

    def record_sync(self, success):
        """记录同步"""
        if success:
            self.metrics['sync_success'] += 1
        else:
            self.metrics['sync_failure'] += 1
            self._check_alert('DAL_003')

    def record_cross_db_hit(self, file, line):
        """记录跨库直查"""
        self.metrics['cross_db_hits'] += 1
        logger.warning(f'[跨库直查] {file}:{line}')
        self._check_alert('DAL_004')

    def get_health(self) -> dict:
        """健康检查"""
        total = self.metrics['dal_success'] + self.metrics['dal_failure']
        success_rate = (self.metrics['dal_success'] / total * 100) if total > 0 else 100
        return {
            'dal_success_rate': success_rate,
            'cross_db_hits': self.metrics['cross_db_hits'],
            'queue_size': self.metrics['queue_size'],
            'degraded': bridge_client.degraded
        }
```

### 2.4 健康检查端点

```python
# 5003 端点
@app.route('/api/dal/health')
def dal_health():
    monitor = get_dal_monitor()
    return jsonify(monitor.get_health())

# 8008 端点
@app.route('/api/dal/bridge-health')
def bridge_health():
    return jsonify({
        'status': 'degraded' if bridge_client.degraded else 'ok',
        'failure_count': bridge_client.failure_count
    })
```

---

## 〇点三、性能基准（T29）

### 3.1 改造前基准

| 指标 | 当前值 | 测试方法 |
|------|--------|----------|
| 工序任务列表加载 | ~80ms | 实际生产日志 |
| 报工保存 | ~120ms | 实际生产日志 |
| 跨库直查（一次） | ~5-15ms | 实际生产日志 |
| 8008 同步延迟 | 1-3 秒 | 实际生产日志 |
| 调度中心并发 | 50 QPS | 压力测试 |

### 3.2 改造后目标

| 指标 | 目标值 | 提升 |
|------|--------|------|
| 工序任务列表加载 | < 50ms | **40% ↑** |
| 报工保存 | < 80ms | **33% ↑** |
| 本地表查询（替代跨库） | < 2ms | **70% ↑** |
| 8008 同步延迟 | < 1 秒 | **66% ↑** |
| 调度中心并发 | 100 QPS | **100% ↑** |

### 3.3 性能测试

```python
# mobile_api_ai/tests/performance/test_dal_perf.py（新建）
import time
import pytest

class TestDALPerformance:
    """DAL 性能测试"""

    def test_order_list_perf(self):
        """订单列表加载性能"""
        start = time.time()
        result = OrderModule().list()
        elapsed = time.time() - start
        assert elapsed < 0.05, f'订单列表耗时 {elapsed*1000:.2f}ms，超过 50ms'
        assert len(result) > 0

    def test_report_save_perf(self):
        """报工保存性能"""
        data = {
            'order_no': 'TEST-001',
            'step_name': '编织',
            'quantity': 10,
            'operator': 'test_user'
        }
        start = time.time()
        ProcessModule().report(data)
        elapsed = time.time() - start
        assert elapsed < 0.08, f'报工保存耗时 {elapsed*1000:.2f}ms，超过 80ms'

    def test_local_query_perf(self):
        """本地表查询性能"""
        start = time.time()
        for _ in range(100):
            result = storage.get_order_local('TEST-001')
        elapsed = time.time() - start
        assert elapsed < 0.2, f'100 次查询耗时 {elapsed*1000:.2f}ms'
```

### 3.4 性能监控

每次发布前运行 `pytest tests/performance/ -v`，对比基线：
- 性能提升 ≥ 20% → 通过
- 性能持平 → 通过
- 性能下降 → 不通过，需优化

### 3.5 性能报告

每次实施后输出性能报告：

```markdown
## T2 实施性能报告
- 实施前: 80ms
- 实施后: 35ms
- 提升: 56%
- 状态: ✅ 通过
```

---

## 〇点四、文档同步清单（T30）

### 4.1 改造后需更新的文档

| 文档 | 路径 | 更新内容 |
|------|------|----------|
| 架构总结 | `docs/不锈钢网带跟单系统3.0_架构总结_2026.md` | 添加 DAL、统一入口章节 |
| 排产流程规范 | `docs/排产流程规范_2026.md` | 添加灰度切换说明 |
| 数据分层架构 | `docs/数据分层架构说明.md` | 添加 SSOT 本地表说明 |
| 扫码报工接口 | `docs/扫码报工系统接口说明.md` | 添加 DAL 接口说明 |
| 全局架构细分 | `docs/全局架构细分.md` | 添加 5003 统一路径 |
| README | 项目根 `README.md` | 添加新模块说明 |

### 4.2 新增的文档

| 文档 | 路径 | 用途 |
|------|------|------|
| DAL 架构设计 | `docs/模块化改造/DAL_DESIGN.md` | DAL 详细设计 |
| 8008 桥接规范 | `docs/模块化改造/BRIDGE_PROTOCOL.md` | API 协议 |
| 错误码定义 | `docs/模块化改造/ERROR_CODES.md` | 错误码字典 |
| 线程管理规范 | `docs/模块化改造/THREAD_LIFECYCLE.md` | 线程管理 |
| 灰度切换手册 | `docs/模块化改造/GRAYSCALE.md` | 灰度操作手册 |
| 降级方案 | `docs/模块化改造/FALLBACK.md` | 降级操作手册 |

### 4.3 代码注释规范

| 类型 | 规范 |
|------|------|
| 模块顶部 | 简要描述 + 作者 + 日期 |
| 类 | 用途 + 设计思路 |
| 函数 | 参数 + 返回 + 异常 + 示例 |
| 关键算法 | 注释说明 |
| TODO | `# TODO(优先级): 描述` |

### 4.4 CHANGELOG 维护

```markdown
# CHANGELOG.md（新建）

## [Unreleased]

### Added
- T1: 存储层基类
- T2: ContainerStorage
- T5: OrderModule

### Changed
- T13: 调度中心走 5003 统一入口

### Fixed
- 跨库直查问题

### Deprecated
- 旧的 `get_steelbelt_cursor()` 内部直连

### Security
- steel_belt 字段白名单
```

### 4.5 文档检查清单

- [ ] 架构总结已更新
- [ ] README 已更新
- [ ] 新增 6 份文档
- [ ] CHANGELOG 已维护
- [ ] 代码注释规范
- [ ] 错误码字典已发布

---

## 一、完整跨库直查清单（7 处 - v2.0 修订）

### 1.1 跨库直查位置（精确行号）

| 序号 | 文件 | 实际行号 | 用途 | 改造方案 |
|------|------|----------|------|----------|
| 1 | `dispatch_center/_core.py` | L1048-1075 | `_sync_to_mysql()` 写入 `production_orders` | 内部重写为走 8008 |
| 2 | `dispatch_center/_core.py` | L211 | 查询 `customer_group` | 改为读 `orders_local` |
| 3 | `dispatch_center/_core.py` | **L1790-1796** | `_get_violation_conn()` 连接 steel_belt | 改为读 `violations_local` |
| 4 | `dispatch_center/_core.py` | L5947 | 校验订单存在 | 改为读 `orders_local` |
| 5 | `dispatch_center/_core.py` | L7265-7270 | 检查 MySQL 连通性 | **保留（健康检查）** |
| 6 | `app.py` | L575-586 | 手机端校验订单存在 | 改为读 `orders_local` |
| 7 | `dispatch_center/schedule_routes.py` | L1154-1170 | 查询 `customer_group` | 改为读 `orders_local` |

**v2.0 修订说明**：
- 1 号位：原方案 L1048-1101 实际是 L1048-1075（精确审计）
- 3 号位：原方案 L1770 实际是 **L1790-1796**（`_get_violation_conn` 函数，连接 steel_belt 库的 `violation_log` 表）
- 5 号位：健康检查保留（不属于"直查业务数据"）
- 6 号位：原方案 L362-372 实际是 L575-586（精确审计）

### 1.2 改造策略

```python
# 改造前：直接连接 steel_belt
from db.steelbelt_pool import cursor as sb_cursor
conn, c = sb_cursor()
c.execute("SELECT customer_group FROM orders WHERE order_no=%s", (order_no,))
result = c.fetchone()

# 改造后：使用 SSOT 本地表
from storage.container_storage import ContainerStorage
storage = ContainerStorage()
order = storage.get_order_local(order_no)
result = {'customer_group': order['customer_group']} if order else None
```

### 1.3 字段白名单（修订 v2.0）

**审计发现**：原方案白名单 5 字段与实际 `sync_bridge.py:469-494` 写入 22 字段冲突。

**修订决策**：扩白名单为 22 字段（与 `sync_bridge.py` 实际写入一致），按"核心 + 业务"分类管理。

#### 1.3.1 核心字段（5 个，必须同步）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `order_no` | VARCHAR(50) | ✅ | 订单号 |
| `status` | VARCHAR(20) | ✅ | 状态 |
| `plan_start` | DATETIME | - | 计划开始 |
| `plan_end` | DATETIME | - | 计划结束 |
| `updated_at` | DATETIME | ✅ | 更新时间 |

#### 1.3.2 业务字段（17 个，按需同步）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `uuid` | VARCHAR(36) | - | UUID |
| `process_id` | INT | - | 工序 ID |
| `process_record_id` | INT | - | 流程记录 ID |
| `step_name` | VARCHAR(64) | - | 工序名 |
| `batch_no` | VARCHAR(64) | - | 批次号 |
| `quantity` | DECIMAL(12,2) | - | 数量 |
| `qualified_qty` | DECIMAL(12,2) | - | 合格数 |
| `operator` | VARCHAR(64) | - | 操作员 |
| `operator_id` | INT | - | 操作员 ID |
| `wechat_userid` | VARCHAR(100) | - | 微信 userid |
| `equipment_name` | VARCHAR(128) | - | 设备名 |
| `remark` | TEXT | - | 备注 |
| `record_date` | DATE | - | 报工日期 |
| `source` | VARCHAR(32) | - | 数据来源 |
| `overtime_hours` | DECIMAL(8,2) | - | 加班工时 |
| `synced` | TINYINT(1) | - | 同步标记 |
| `synced_at` | DATETIME | - | 同步时间 |
| `created_at` | DATETIME | - | 创建时间 |
| `created_by` | VARCHAR(64) | - | 创建人 |
| `updated_by` | VARCHAR(64) | - | 更新人 |

**注意**：`process_sub_steps` 表实际包含 22 字段，方案扩白名单以匹配实际写入。

**禁止写入**：
- ❌ `content`（大字段，仍禁止）
- ❌ `metadata`（大字段，仍禁止）
- ❌ `defect_description`（缺陷描述，仍禁止）
- ❌ `inspection_items`（JSON 字段，仍禁止）

---

## 二、后台线程管理策略

### 2.1 现状

| 位置 | 线程类型 | 风险 |
|------|---------|------|
| `dispatch_center/_core.py:828` | 持久化线程 | 中（每次都创建） |
| `dispatch_center/_core.py:4158-4159` | 同步状态线程 | 中 |
| `dispatch_center/_core.py:4480` | 异步确认线程 | 中 |
| `dispatch_center/_core.py:7032` | outbox 消费线程 | 中 |
| `sync_bridge.py:613` | 状态变更线程 | 中 |
| `container_center_api.py:367, 705, 2385` | 清理/推送/校对线程 | 中 |
| `app.py:2276` | report-queue 消费线程 | 中 |
| `cloud_poller.py:516` | 云端轮询线程 | 中 |
| `retry_queue.py:115` | retry worker | 中 |
| `alert_engine.py:702` | 告警引擎 | 中 |

**共 90+ 处 daemon 线程**（已在 `docs/容器中心稳定性诊断报告.md` 记录问题）

### 2.2 统一线程管理

#### 2.2.1 现有资源

| 工具 | 位置 | 用途 |
|------|------|------|
| `ResilientThread` | `container_center_api.py:123` | 弹性线程 |
| `thread_lifecycle.py` | `thread_lifecycle.py:38` | 线程生命周期管理 |
| `_ResilientLogCleaner` | `standalone_dispatch_server.py:771` | 日志清理线程 |

#### 2.2.2 改造方案

**所有后台线程必须通过 `thread_lifecycle.py` 注册**：

```python
# mobile_api_ai/thread_lifecycle.py（已有）
from thread_lifecycle import ThreadRegistry, register_thread

# 改造前
def _async_post_confirm():
    # ...
threading.Thread(target=_async_post_confirm, daemon=True).start()

# 改造后
def _async_post_confirm():
    # ...
register_thread(target=_async_post_confirm, name='post-confirm')
```

#### 2.2.3 线程分类

| 类别 | 启动方式 | 关闭方式 |
|------|----------|----------|
| **关键线程** | 服务启动时启动 | 优雅关闭（wait） |
| **任务线程** | 动态创建 | 任务完成自动结束 |
| **周期线程** | 定时器调度 | 优雅关闭 |
| **守护线程** | daemon=True | 主进程退出时强制终止 |

#### 2.2.4 关闭顺序

```
SIGTERM 信号
  ↓
1. 停止接收新请求
  ↓
2. 关闭 HTTP 服务（Flask）
  ↓
3. 通知所有注册线程退出
  ↓
4. 等待关键线程完成（最多 30s）
  ↓
5. 强制终止残留线程
```

---

## 三、迁移脚本统一管理

### 3.1 现状

| 位置 | 数量 | 用途 |
|------|------|------|
| `migrations/` | 多个文件 | 数据库迁移 |
| `scripts/` | 多个子目录 | 工具脚本 |
| `__pre_tests__/` | 多个文件 | 迁移前测试 |
| `docs/` | 多个方案 | 迁移方案文档 |

**共 66 个文件包含 `ALTER TABLE`**。

### 3.2 统一迁移策略

#### 3.2.1 目录结构

```
mobile_api_ai/
├── migrations/
│   ├── v1.0.0_init/              # 初始化迁移
│   │   ├── 001_create_process_records.sql
│   │   ├── 002_create_data_packages.sql
│   │   └── 003_seed_local_tables.sql
│   │
│   ├── v1.1.0_module/            # 模块化迁移
│   │   ├── 001_add_orders_local.sql
│   │   ├── 002_add_production_orders_local.sql
│   │   ├── 003_add_operators_local.sql
│   │   └── 004_backfill_from_steelbelt.sql
│   │
│   ├── v1.2.0_dal/               # DAL 迁移
│   │   ├── 001_rename_tables.sql
│   │   └── 002_add_indexes.sql
│   │
│   └── run_migration.py          # 统一迁移执行器
```

#### 3.2.2 命名规范

| 类型 | 命名 | 示例 |
|------|------|------|
| 新增表 | `001_create_<table>.sql` | `001_create_orders_local.sql` |
| 删表 | `002_drop_<table>.sql` | `002_drop_schedule_records.sql` |
| 加字段 | `003_add_<col>_to_<table>.sql` | `003_add_synced_at_to_orders_local.sql` |
| 改字段 | `004_modify_<col>_in_<table>.sql` | `004_modify_status_in_process_records.sql` |
| 数据迁移 | `005_backfill_<from>_to_<to>.sql` | `005_backfill_steelbelt_to_local.sql` |
| 索引 | `006_add_index_<table>_<col>.sql` | `006_add_index_orders_local_order_no.sql` |

#### 3.2.3 迁移执行器

```python
# mobile_api_ai/migrations/run_migration.py
class MigrationRunner:
    """统一迁移执行器"""

    def __init__(self, db_name):
        self.db_name = db_name
        self.applied = self._get_applied_migrations()

    def run_all(self):
        """执行所有未应用的迁移"""
        pending = self._get_pending_migrations()
        for migration in pending:
            self._apply(migration)
            self._mark_applied(migration)

    def _apply(self, migration):
        """应用单个迁移（带事务）"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as c:
                    for sql in migration.statements:
                        c.execute(sql)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise MigrationError(f'迁移失败: {migration.name}') from e

    def rollback(self, target_version):
        """回滚到指定版本"""
        # ...
```

#### 3.2.4 迁移记录表

```sql
CREATE TABLE migration_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    version VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,
    checksum VARCHAR(64),
    INDEX idx_version (version)
);
```

---

## 四、错误码与日志统一

### 4.1 错误码体系

#### 4.1.1 错误码分类

| 范围 | 类别 | 示例 |
|------|------|------|
| 0 | 成功 | `{"code": 0, "message": "success"}` |
| 1000-1099 | 参数错误 | `{"code": 1001, "message": "参数不完整"}` |
| 1100-1199 | 鉴权错误 | `{"code": 1101, "message": "未授权"}` |
| 1200-1299 | 请求错误 | `{"code": 1201, "message": "JSON 解析失败"}` |
| 1300-1399 | 资源错误 | `{"code": 1301, "message": "订单不存在"}` |
| 1400-1499 | 路由错误 | `{"code": 1404, "message": "接口不存在"}` |
| 1500-1599 | 业务错误 | `{"code": 1501, "message": "报工失败"}` |
| 1600-1699 | 同步错误 | `{"code": 1601, "message": "同步到 steel_belt 失败"}` |
| **9000-9999** | **服务器错误（v2.0 修订）** | `{"code": 9000, "message": "内部错误"}` |

**⚠️ v2.0 修订**：原方案 5000-5099 段位与 5003 端口冲突，改为 9000-9999。详见 `ERROR_CODES.md`。

#### 4.1.2 统一错误响应格式

```python
# mobile_api_ai/exceptions.py（新建）
class APIError(Exception):
    """统一 API 错误"""

    def __init__(self, code: int, message: str, data=None):
        self.code = code
        self.message = message
        self.data = data or {}

    def to_dict(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data
        }

# 使用示例
@bp.errorhandler(APIError)
def handle_api_error(e):
    return jsonify(e.to_dict()), e.http_status
```

### 4.2 日志统一

#### 4.2.1 日志格式

```python
# mobile_api_ai/logging_config.py（新建）
LOG_FORMAT = (
    '%(asctime)s | %(levelname)-8s | %(name)-30s | '
    '%(filename)s:%(lineno)-4d | %(message)s'
)

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': LOG_FORMAT,
            'datefmt': DATE_FORMAT
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'standard',
            'level': 'INFO'
        }
    },
    'loggers': {
        'mobile_api_ai': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

#### 4.2.2 日志分类

| Logger | 输出 | 用途 |
|--------|------|------|
| `mobile_api_ai.app` | `logs/app.log` | 报工系统 |
| `mobile_api_ai.dispatch` | `logs/dispatch.log` | 调度中心 |
| `mobile_api_ai.container` | `logs/container.log` | 容器中心 |
| `mobile_api_ai.sync` | `logs/sync.log` | 同步桥 |
| `mobile_api_ai.dal` | `logs/dal.log` | DAL 统一日志 |

#### 4.2.3 关键日志点

| 位置 | 日志级别 | 内容 |
|------|---------|------|
| 报工保存 | INFO | `order_no`, `step_name`, `quantity` |
| 状态变更 | INFO | `order_no`, `old_status`, `new_status` |
| 同步 steel_belt | INFO | `target`, `order_no`, `success/fail` |
| 同步失败 | WARNING | `error`, `retry_count` |
| 跨库直查 | WARNING | 提醒走本地表 |
| 模块异常 | ERROR | 异常堆栈 |

---

## 五、测试迁移

### 5.1 现状

| 测试文件 | 数量 | 覆盖范围 |
|---------|------|----------|
| `tests/unit/test_*.py` | 41 个 | 单元测试 |
| `__pre_tests__/test_*.py` | 多个 | 迁移前测试 |

### 5.2 测试分类

| 类别 | 命名 | 范围 |
|------|------|------|
| 存储层 | `test_*_storage*.py` | ContainerStorage, SteelbeltStorage |
| 模块 | `test_*_module*.py` | OrderModule, ProcessModule |
| 跨库 | `test_cross_db*.py` | 跨库直查转本地表 |
| 集成 | `test_*_integration*.py` | 多模块协作 |
| 回归 | `test_regression*.py` | 既有功能不退化 |
| 并发 | `test_concurrency*.py` | 并发安全 |
| 健康 | `test_health*.py` | 健康检查 |

### 5.3 新增测试清单

#### 5.3.1 必须新增的测试

| 测试名 | 用途 |
|--------|------|
| `test_dal_base.py` | BaseModule 基类 |
| `test_order_module.py` | OrderModule |
| `test_process_module.py` | ProcessModule |
| `test_quality_module.py` | QualityModule |
| `test_material_module.py` | MaterialModule |
| `test_operator_module.py` | OperatorModule |
| `test_container_storage.py` | ContainerStorage |
| `test_steelbelt_storage.py` | SteelbeltStorage |
| `test_field_whitelist.py` | steel_belt 字段白名单验证 |
| `test_call_path_audit.py` | 调用路径审计（5003 统一） |

#### 5.3.2 测试运行命令

```bash
# 运行所有测试
cd mobile_api_ai && pytest tests/unit/ -v

# 运行新模块测试
pytest tests/unit/test_dal_base.py tests/unit/test_order_module.py -v

# 运行跨库测试（确认无新跨库）
pytest tests/unit/test_cross_db.py -v

# 运行回归测试
pytest tests/unit/test_regression_*.py -v
```

#### 5.3.3 测试覆盖率目标

| 类别 | 目标 |
|------|------|
| 整体覆盖率 | > 60% |
| 关键模块 | > 80% |
| DAL 基类 | > 90% |
| 字段白名单 | 100% |

---

## 六、补充任务清单

### 6.1 任务补充

| 阶段 | 任务 | 说明 | 优先级 |
|------|------|------|--------|
| Phase 1 | T19 | 线程生命周期统一管理 | HIGH |
| Phase 1 | T20 | 迁移脚本统一规范 | HIGH |
| Phase 1 | T21 | 错误码/日志统一 | HIGH |
| Phase 6 | T22 | 测试用例新增（10+ 个） | HIGH |
| Phase 6 | T23 | 调用路径审计脚本 | HIGH |
| Phase 6 | T24 | 字段白名单验证测试 | HIGH |
| Phase 6 | T25 | 回归测试套件 | MEDIUM |

### 6.2 Phase 1 任务扩展

| 任务 | 状态 | 依赖 |
|------|------|------|
| T1: 存储层基类 | 待开始 | - |
| T2: ContainerStorage | 待开始 | T1 |
| T3: SteelbeltStorage | 待开始 | T1 |
| T4: 模块基类 BaseModule | 待开始 | T1 |
| **T19: 线程生命周期管理** | **待开始** | - |
| **T20: 迁移脚本统一** | **待开始** | - |
| **T21: 错误码/日志统一** | **待开始** | - |

### 6.3 Phase 6 任务（新增）

| 任务 | 说明 | 依赖 |
|------|------|------|
| **T22: 测试用例新增** | 10+ 个测试覆盖 DAL | T1-T18 |
| **T23: 调用路径审计** | 自动化检查 5003 统一 | T11-T18 |
| **T24: 字段白名单验证** | 验证 steel_belt 不写大字段 | T11 |
| **T25: 回归测试** | 41 个既有测试全过 | T1-T18 |

---

## 七、改造实施顺序（最终版）

```
Phase 1: 基础层（7 个任务）
  ├── T1: 存储层基类
  ├── T2: ContainerStorage
  ├── T3: SteelbeltStorage
  ├── T4: 模块基类
  ├── T19: 线程生命周期
  ├── T20: 迁移脚本统一
  └── T21: 错误码/日志

Phase 2: 核心模块（4 个任务）
  ├── T5: OrderModule
  ├── T6: ProcessModule
  ├── T7: QualityModule
  └── T8: MaterialModule

Phase 3: 支撑模块（2 个任务）
  ├── T9: OperatorModule
  └── T10: MessageModule

Phase 4: 统一入口（2 个任务）
  ├── T11: 8008 统一入口
  └── T12: 同步队列优化

Phase 5: 服务改造（5 个任务）
  ├── T13: 调度中心改造（5003 统一入口）
  ├── T14: 报工系统改造
  ├── T15: 容器中心改造
  ├── T16: 库存管理改造
  └── T17: 云端服务改造（不调用 8008）

Phase 6: 测试与审计（4 个任务）
  ├── T18: 调用路径审计
  ├── T22: 测试用例新增
  ├── T23: 调用路径审计脚本
  ├── T24: 字段白名单验证
  └── T25: 回归测试

共 25 个任务
```

---

## 八、风险与缓解（更新）

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 90+ 后台线程未管理 | HIGH | T19 统一注册 |
| 跨库直查 7 处遗漏 | HIGH | T13-T17 服务改造覆盖 |
| 66 个迁移脚本分散 | MEDIUM | T20 统一规范 |
| 错误码不统一 | MEDIUM | T21 错误码规范 |
| 测试覆盖不足 | MEDIUM | T22-T25 测试套件 |
| steel_belt 字段膨胀 | MEDIUM | T24 字段白名单验证 |

---

## 九、文档清单（最终版）

```
docs/模块化改造/
├── ALIGNMENT_全面模块化改造.md   # 需求对齐（已含约束）
├── ARCHITECT_全面模块化改造.md   # 架构设计（已含统一路径）
├── TASK_全面模块化改造.md       # 任务拆分（已含 18 个任务）
└── SUPPLEMENT_全面模块化改造.md # 补充方案（本文档）
```

---

## 十、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-06-13 | 补充 5 大缺口：跨库清单、线程、迁移、错误码、测试 |
| v1.1 | 2026-06-13 | 补充 5 项实施保障：灰度切换、降级方案、监控告警、性能基准、文档同步 |
