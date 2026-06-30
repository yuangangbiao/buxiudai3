# CONSENSUS v3.7.0 - 业务代码 P0 + L1 冒烟测试

> **版本**: v3.7.0
> **阶段**: 6A 阶段 1 收口 (Consensus)
> **日期**: 2026-06-25

---

## 1. 明确的需求描述

### 1.1 业务代码修复

| 任务 | 描述 | 验收标准 |
|------|------|----------|
| P0-2 | DLQ retry worker | 函数存在+单元测试+文档 |
| Q-B6 | 删除废弃文件 | 文件删除+引用清理 |
| Q-B7 | 修复裸异常日志 | 5+ 处修复+不破坏功能 |

### 1.2 L1 冒烟测试

5 个核心场景：
1. **test_login.py** - 5 角色登录测试
2. **test_order_create.py** - 订单创建流程
3. **test_process_publish.py** - 工序发布
4. **test_quality_check.py** - 质检流程
5. **test_shipment.py** - 发货流程

每个测试 ≤ 30s，整体 ≤ 5min。

## 2. 技术实现方案

### 2.1 P0-2 DLQ retry worker

**位置**: `mobile_api_ai/dispatch_center/_dlq_retry.py`（新文件）

**架构**:
```
独立线程 → 扫描 dlq 表 → 过滤 next_retry_at <= now
                  ↓
        调用原发送函数 → 成功: DELETE / 失败: UPDATE retry_count
                  ↓
        指数退避: next_retry_at = now + 2^retry_count 秒
```

**关键函数**:
```python
def start_dlq_retry_worker() -> bool: ...
def _dlq_retry_loop(): ...
def _dlq_retry_once() -> int: ...
def _should_retry(record: dict) -> bool: ...
```

### 2.2 Q-B6 删除废弃文件

**操作**:
1. 搜索 `desktop_container_integration.py` 所有引用
2. 删除文件
3. 清理 import
4. pytest 验证

### 2.3 Q-B7 修复裸异常日志

**修复模式**:
```python
# ❌ 修复前
except Exception as e:
    logger.error(f'操作失败: {e}')

# ✅ 修复后
except Exception:
    logger.exception('操作失败')  # 自动带堆栈
```

**优先级**: 5003 调度中心的写入路径（高风险）+ 报工/质检同步（高风险）

### 2.4 L1 冒烟测试

**目录**: `tests/L1_smoke/`

**测试方式**: 离线 + mock
- 不依赖真实服务启动
- 用 mock 替代 DB/HTTP 调用
- 验证核心业务逻辑

## 3. 任务边界限制

### 3.1 In Scope

- P0-2: DLQ retry worker 完整实现
- Q-B6: 删除 1 个废弃文件
- Q-B7: 5+ 处裸异常日志修复
- L1: 5 个冒烟测试用例
- 文档：ARCHITECTURE_v3.7.0.md

### 3.2 Out of Scope

- _core.py 完整拆分（9635 行风险过大）
- 5 服务全链路测试
- Prometheus 监控
- Grafana 看板

## 4. 验收标准汇总

| 任务 | 验收方式 | 完成定义 (DoD) |
|------|----------|---------------|
| P0-2 | pytest + 手动启动调度中心 | 函数可调用 + 重试生效 |
| Q-B6 | 编译通过 | 引用全部清理 |
| Q-B7 | pytest + 代码 review | 5+ 处修复 + 测试通过 |
| L1 | pytest | 5min 内跑完 + 0 错误 |

## 5. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| DLQ retry 引发重复消费 | 🟡 | 加唯一索引 + 状态机 |
| 删除废弃文件引发崩溃 | 🟡 | 全文搜索引用 |
| 异常日志修复改变格式 | 🟢 | 不影响下游消费 |
| L1 测试不稳定 | 🟡 | 全 mock 离线 |

---

**共识达成，进入下一阶段**: [DESIGN_v3.7.0.md](DESIGN_v3.7.0.md)
