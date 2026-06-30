# FOURTH_AUDIT.md（第四轮悲观审计）

> 文档版本：v1.0（2026-06-13）
> 审计范围：22 个修复后端到端数据流 + 启动依赖 + 鉴权
> 审计方法：**假设每行新代码都是 bug**

---

## 一、第四轮新发现（5 个 Q）

### 🔴 Q1: 8008 → 5002 mirror 未透传 trace_id

**问题**：`sync_bridge.py:543-562` 用 `requests.post` 而非 `traced_request`

```python
_trace_id = __import__('utils.trace', fromlist=['get_trace_id']).get_trace_id()
_resp = _req.post(  # ← 普通 requests，不是 traced_request
    f'{CC}/api/process_sub_steps/mirror',
    json={..., 'trace_id': _trace_id},  # ← trace_id 在 body 不是 header
)
```

**影响**：
- 5002 mirror 路由收不到 X-Trace-Id
- mirror 失败时调试困难（看不到 8008 的 trace_id）
- 5 个代理（app.py）的 traced_request 已带 header，但这里漏了

**修复**：改用 `traced_request('POST', ...)`。

### 🔴 Q2: 5002 自己的 process_sub_steps 写路径无 mirror

**问题**：5002 业务代码写 `process_sub_steps`（非 `_local`），但**没有任何代码**同步到 `process_sub_steps_local`。

```python
# 5002 业务
INSERT INTO process_sub_steps (id, order_no, ...)  # ← 写原表

# 8008 业务
INSERT INTO steel_belt.process_sub_steps (...)  # ← 写 steel_belt
mirror → process_sub_steps_local              # ← 8008 写本地表

# 结果：
# - 5002 写原表的数据 永远不会 出现在 _local
# - 8008 写的数据 会 出现在 _local（通过 mirror）
# - 同一个 order_no 可能在 process_sub_steps（5002 原表） 和 process_sub_steps_local（mirror） 各一份
```

**影响**：
- 数据混乱
- ETL 同步 process_sub_steps_local 时，5002 原表数据永远漏掉
- 双源数据不一致

**修复**：把 5002 业务改为写 process_sub_steps_local。

### 🔴 Q3: mirror 路由无鉴权

**问题**：`/api/process_sub_steps/mirror` 是公开 POST 端点。

```python
@app.route('/api/process_sub_steps/mirror', methods=['POST'])  # ← 无 @auth
def api_process_sub_steps_mirror():
    # 任何人都能 POST 任意数据进 process_sub_steps_local
    # 攻击者可注入伪造的报工数据
```

**影响**：
- 任意人可写伪造报工
- 内部接口暴露在公网（如果 5002 在公网）

**修复**：
- 添加 IP 白名单（仅 127.0.0.1）
- 或添加内部共享密钥

### 🔴 Q4: ETL 与 mirror 双写同一表

**问题**：

```
T+0s: 8008 写 steel_belt
T+0s: 8008 mirror → process_sub_steps_local
T+30s: ETL 拉 steel_belt → 写 process_sub_steps_local  ← 可能覆盖
```

**影响**：
- 两者写同一张表
- 数据内容相同（都是 8008 的写入），所以不会**错误**
- 但有写放大、浪费资源

**修复**：
- 选项 A：ETL 排除 process_sub_steps（不同步）
- 选项 B：ETL 同步时优先 trust mirror（只同步 mirror 失败的行）
- 选项 C：接受双写（数据一致即可）

### 🔴 Q5: ETL 失败无重试无告警

**问题**：

```python
# etl_local_mirror.py
for src, tgt, sf in sync_configs:
    try:
        n = _sync_table_with_state(src, tgt, sf)
    except Exception as e:
        logger.warning(f'[ETL] {src} → {tgt} 失败: {e}')  # ← 只 warn
```

**影响**：
- ETL 失败悄无声息
- 镜像表可能长期数据缺失
- 业务读 _local 时读不到，业务挂掉也查不到原因

**修复**：
- 失败计数
- 连续失败 3 次触发告警
- 写 dead_letter 表

---

## 二、仍需关注的旧问题

| # | 问题 | 状态 |
|---|------|------|
| N7 | trace 头不覆盖 | ✅ 已修 |
| N4 | ETL 启动协调 | ✅ 已修 |
| N5 | 5003 trace 注册 | ✅ 已修 |

---

## 三、架构一致性评分

| 维度 | 第三轮 | 第四轮（悲观）|
|------|--------|--------------|
| 跨库直查读 | 18/20 | 18/20 |
| 跨库直查写 | 16/20 | **12/20**（Q2 双源数据）|
| 镜像表同步 | 18/20 | 14/20（Q4 双写） |
| trace 跨服务 | 18/20 | **16/20**（Q1 mirror 漏透传） |
| 鉴权安全 | 14/20 | **10/20**（Q3 mirror 公开）|
| 错误恢复 | 16/20 | **12/20**（Q5 ETL 失败无声）|
| 数据一致性 | 16/20 | **10/20**（Q2 双源）|
| **总分** | **131/160（82%）** | **92/160（57.5%）** |

---

## 四、第四轮真实状态

| 项 | 乐观 | 悲观 |
|----|------|------|
| 22 个修复 | ✅ | ✅ |
| **Q1 mirror 漏 trace** | ❌ | 🔴 |
| **Q2 5002 原表无 mirror** | ❌ | 🔴 |
| **Q3 mirror 公开** | ❌ | 🔴 |
| **Q4 ETL 双写** | ❌ | 🟡 |
| **Q5 ETL 失败无声** | ❌ | 🔴 |
| 架构真实评分 | 90% | **57.5%** |

---

## 五、累计修复统计

| 阶段 | 数量 | 累计 |
|------|------|------|
| 第一批 CRITICAL | 5 | 5 |
| 第二批 CRITICAL | 7 | 12 |
| 第三批 N 编号 | 7 | 19 |
| 第四批 同步冲突 | 3 | 22 |
| **第五批 Q 编号（待修）** | **5** | **27** |

---

## 六、修复优先级

| 优先级 | 项 | 工作量 |
|--------|-----|--------|
| **P0** | Q1 8008 mirror 用 traced_request | 5min |
| **P0** | Q3 mirror 鉴权（IP 白名单）| 30min |
| **P1** | Q2 5002 业务改写 _local | 2h |
| **P1** | Q4 ETL 排除 process_sub_steps | 10min |
| **P2** | Q5 ETL 失败告警 | 1h |

---

## 七、参考

- [ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md) - 第 1 轮
- [POST_REFACTOR_AUDIT.md](./POST_REFACTOR_AUDIT.md) - 第 2 轮
- [FINAL_AUDIT.md](./FINAL_AUDIT.md) - 第 3 轮
- 本文档 - 第 4 轮

---

## 八、关键教训

> **每修复一个 bug 都会引入新 bug**。22 个修复引入了 5 个新问题。
> 真实架构评分：57.5%（不是 90%）。
> 改造需要**多轮迭代 + 自动化测试**才能稳定。
