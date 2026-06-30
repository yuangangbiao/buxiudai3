# GRAYSCALE.md（灰度切换手册）

> 文档版本：v1.0（2026-06-13）

---

## 一、灰度目标

DAL 模块化改造的灰度上线，从 0% 到 100% 逐步切换，确保不影响生产。

---

## 二、灰度开关

### 2.1 配置文件

**位置**：`mobile_api_ai/config/feature_flags.py`

```python
FEATURE_FLAGS = {
    'DAL_ENABLED': {
        'enabled': False,           # 总开关
        'percentage': 0,            # 灰度比例 0-100
        'whitelist': [],            # 白名单 order_no
        'blacklist': [],            # 黑名单 order_no
    },
    'ORDER_MODULE_DAL': False,
    'PROCESS_MODULE_DAL': False,
    'QUALITY_MODULE_DAL': False,
    'MATERIAL_MODULE_DAL': False,
    'SYNC_BRIDGE_VIA_8008': False,
    'READ_FROM_LOCAL_TABLES': True,
}
```

### 2.2 灰度决策函数

```python
def is_dal_enabled(order_no: str = None) -> bool:
    """判断是否启用 DAL"""
    flag = FEATURE_FLAGS['DAL_ENABLED']
    if not flag['enabled']:
        return False
    if order_no in flag['whitelist']:
        return True
    if order_no in flag['blacklist']:
        return False
    # 按比例灰度
    if flag['percentage'] >= 100:
        return True
    if flag['percentage'] <= 0:
        return False
    # 简单 hash 取模
    import hashlib
    h = int(hashlib.md5(order_no.encode()).hexdigest(), 16)
    return (h % 100) < flag['percentage']
```

---

## 三、灰度阶段

### 3.1 阶段 0: 准备（1 周）

| 任务 | 状态 |
|------|------|
| 部署新代码（开关全部 False） | ✅ |
| 数据迁移（双写准备） | ✅ |
| 监控埋点 | ✅ |
| 应急回滚脚本 | ✅ |

### 3.2 阶段 1: 白名单（3 天）

```python
FEATURE_FLAGS['DAL_ENABLED'] = {
    'enabled': True,
    'percentage': 0,
    'whitelist': ['WO-001', 'WO-002', 'WO-003', 'WO-004', 'WO-005'],
}
```

| 验证项 | 频率 | 标准 |
|--------|------|------|
| 功能正确性 | 实时 | 100% 一致 |
| 性能 | 每小时 | < 100ms |
| 错误率 | 每小时 | < 0.1% |
| 跨库直查 | 实时 | 0 次 |

**通过标准**：3 天内无 P0/P1 故障。

### 3.3 阶段 2: 10% 灰度（1 周）

```python
FEATURE_FLAGS['DAL_ENABLED']['percentage'] = 10
```

| 验证项 | 频率 | 标准 |
|--------|------|------|
| API 响应时间 | 实时 | < 200ms |
| 同步成功率 | 每小时 | > 99% |
| 降级队列长度 | 每小时 | < 100 |
| 慢 SQL 数 | 每小时 | < 10 |

### 3.4 阶段 3: 50% 灰度（1 周）

```python
FEATURE_FLAGS['DAL_ENABLED']['percentage'] = 50
```

| 验证项 | 频率 | 标准 |
|--------|------|------|
| QPS 峰值 | 实时 | 50% 流量通过 |
| 数据库连接数 | 实时 | < 80% 上限 |
| 内存使用 | 每小时 | < 80% 上限 |

### 3.5 阶段 4: 100% 全量

```python
FEATURE_FLAGS['DAL_ENABLED']['percentage'] = 100
FEATURE_FLAGS['DAL_ENABLED']['enabled'] = True
```

**观察 1 周后**，清理开关代码。

---

## 四、监控

### 4.1 关键指标

| 指标 | 采集 | 告警阈值 |
|------|------|----------|
| DAL API 响应时间 | `/api/perf/stats` | > 200ms |
| 慢 SQL 次数 | 日志 | > 10/小时 |
| 同步失败率 | outbox 队列 | > 1% |
| 跨库直查 | 日志 | > 0 |
| 降级队列长度 | 队列 | > 100 |

### 4.2 监控端点

- `/api/perf/stats` - 性能统计
- `/api/perf/threads` - 线程状态
- `/health` - 健康检查

---

## 五、回滚

### 5.1 一键回滚

```python
# 关闭所有开关
FEATURE_FLAGS['DAL_ENABLED']['enabled'] = False
FEATURE_FLAGS['DAL_ENABLED']['percentage'] = 0
FEATURE_FLAGS['ORDER_MODULE_DAL'] = False
FEATURE_FLAGS['PROCESS_MODULE_DAL'] = False
FEATURE_FLAGS['SYNC_BRIDGE_VIA_8008'] = False
```

### 5.2 紧急回滚（5 分钟内）

1. 关闭总开关：`DAL_ENABLED = False`
2. 等待 30 秒（让正在处理的请求完成）
3. 观察监控：API 响应时间、错误率
4. 必要时重启服务

### 5.3 数据一致性

回滚不会丢失数据（因为是双写或读本地表）。但需要检查：

- 降级队列中是否有未处理项
- 是否有部分同步失败
- 监控数据是否有异常

---

## 六、应急联系方式

| 角色 | 联系人 | 联系方式 |
|------|--------|----------|
| 项目负责人 | - | - |
| 后端负责人 | - | - |
| DBA | - | - |
| 运维 | - | - |

---

## 七、参考

- [DAL_DESIGN.md](./DAL_DESIGN.md)
- [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md)
- [FALLBACK.md](./FALLBACK.md)
