# FALLBACK.md（降级方案）

> 文档版本：v1.0（2026-06-13）

---

## 一、降级原则

模块化改造必须保证**降级可用**，即当新模块异常时，能自动回退到旧逻辑或安全模式。

---

## 二、降级场景

### 2.1 Sync Bridge 8008 不可用

**触发条件**：
- 8008 端口无响应
- 同步请求超时（> 5s）
- steel_belt 数据库连接失败

**降级策略**：

```
┌──────────────────────┐
│ 报工/同步请求        │
└──────────┬───────────┘
           ↓
      8008 桥接
           ↓ (失败)
      outbox 队列（落盘）
           ↓
      异步重试线程
           ↓ (恢复后)
      steel_belt 写入
```

**用户感知**：
- 报工提交成功（已落本地表）
- 同步状态显示"待同步"
- 后台自动重试直到成功

### 2.2 调度中心 5003 不可用

**触发条件**：
- 5003 端口无响应
- 微信 API 调用失败

**降级策略**：

```
微信通知请求
  ↓
 5003 调度中心
  ↓ (失败)
 通知队列（Redis 持久化）
  ↓
 后台重试 + 降级通知
```

**用户感知**：
- 报工不影响
- 微信通知延迟发送
- 控制台告警

### 2.3 本地表不可用

**触发条件**：
- container_center 数据库不可用
- 本地表读写失败

**降级策略**：

```
业务请求
  ↓
 本地表查询
  ↓ (失败)
 回退到 steel_belt 读（仅限非敏感数据）
  ↓ (也失败)
 返回错误 + 缓存上一次结果
```

**注意**：回退到 steel_belt 是**有损降级**，需要记录告警。

### 2.4 5003 消息总线被绕开

**触发条件**：
- notify.py 直连企业微信 API
- 不经过 5003

**修复**：见 H1 修复任务。

### 2.5 DAL 模块异常

**触发条件**：
- 新模块逻辑错误
- 数据模型不匹配

**降级策略**：

```
业务请求
  ↓
 DAL 模块
  ↓ (异常)
 回退到旧逻辑（直接调 storage）
  ↓ (也失败)
 错误码 1501/1502 + 日志告警
```

---

## 三、降级开关

### 3.1 全局降级

```python
# mobile_api_ai/config/feature_flags.py

FEATURE_FLAGS = {
    'DAL_FALLBACK_MODE': False,      # DAL 降级模式
    'SYNC_BRIDGE_FALLBACK': False,   # 8008 降级
    'LOCAL_TABLE_FALLBACK': False,   # 本地表降级
    'WECHAT_FALLBACK': False,        # 微信降级
}
```

### 3.2 触发条件

```python
def check_fallback_conditions():
    """检查是否需要降级"""
    if api_error_rate > 0.05:  # 5%
        FEATURE_FLAGS['DAL_FALLBACK_MODE'] = True
    
    if sync_failure_rate > 0.10:  # 10%
        FEATURE_FLAGS['SYNC_BRIDGE_FALLBACK'] = True
    
    if local_table_error_rate > 0.05:
        FEATURE_FLAGS['LOCAL_TABLE_FALLBACK'] = True
```

---

## 四、降级队列

### 4.1 Outbox 队列

**位置**：`/tmp/sync_outbox/`（或配置）

**格式**：
```json
{
  "id": "uuid",
  "created_at": "2026-06-13T10:00:00",
  "retry_count": 0,
  "action": "sub-step-report",
  "payload": { ... }
}
```

### 4.2 重试策略

| 重试次数 | 间隔 | 处理 |
|----------|------|------|
| 1 | 1s | 立即重试 |
| 2 | 5s | 退避 |
| 3 | 30s | 退避 |
| 4 | 5min | 退避 |
| 5+ | 1h | 持续重试 |

**最大重试次数**：无上限（持续重试）

### 4.3 告警

| 指标 | 阈值 | 告警 |
|------|------|------|
| 队列长度 | > 100 | WARNING |
| 队列长度 | > 1000 | ERROR |
| 单条重试次数 | > 10 | WARNING |
| 队列堆积时间 | > 1h | ERROR |

---

## 五、监控

### 5.1 降级状态端点

```python
@app.route('/api/fallback/status', methods=['GET'])
def fallback_status():
    return jsonify({
        'code': 0,
        'data': {
            'dal_fallback': FEATURE_FLAGS['DAL_FALLBACK_MODE'],
            'sync_fallback': FEATURE_FLAGS['SYNC_BRIDGE_FALLBACK'],
            'local_fallback': FEATURE_FLAGS['LOCAL_TABLE_FALLBACK'],
            'wechat_fallback': FEATURE_FLAGS['WECHAT_FALLBACK'],
            'outbox_size': get_outbox_size(),
        }
    })
```

### 5.2 告警规则

| 规则 | 严重度 |
|------|--------|
| 降级模式触发 | WARNING |
| 降级模式持续 1h+ | ERROR |
| Outbox 队列超过阈值 | WARNING/ERROR |
| 同步失败率超过 5% | ERROR |

---

## 六、恢复流程

### 6.1 自动恢复

```python
def auto_recover():
    """每 5 分钟检查一次"""
    if FEATURE_FLAGS['DAL_FALLBACK_MODE']:
        # 尝试重新启用 DAL
        if test_dal_health():
            FEATURE_FLAGS['DAL_FALLBACK_MODE'] = False
            logger.info('[FALLBACK] DAL 自动恢复')
```

### 6.2 手动恢复

```bash
# 1. 关闭降级开关
python -c "from config.feature_flags import FEATURE_FLAGS; FEATURE_FLAGS['DAL_FALLBACK_MODE'] = False"

# 2. 观察监控
curl http://localhost:5008/api/perf/stats

# 3. 必要时重启服务
```

---

## 七、测试

### 7.1 注入故障测试

```python
def test_sync_bridge_fallback():
    """模拟 8008 不可用"""
    # 1. 关闭 8008
    # 2. 发起报工请求
    # 3. 验证 outbox 队列有新增
    # 4. 重启 8008
    # 5. 验证队列被处理
```

### 7.2 降级切换测试

```python
def test_dal_fallback_switch():
    """测试 DAL 降级切换"""
    # 1. 启用 DAL
    # 2. 注入故障
    # 3. 验证自动降级
    # 4. 恢复故障
    # 5. 验证自动恢复
```

---

## 八、参考

- [GRAYSCALE.md](./GRAYSCALE.md)
- [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md)
- [DAL_DESIGN.md](./DAL_DESIGN.md)
