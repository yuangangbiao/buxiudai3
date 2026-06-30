# EIGHTH_AUDIT.md（数据库严谨性第八轮审计）

> 文档版本：v1.0（2026-06-13）
> 审计范围：5 个 G 编号 - 数据血缘/软删除/保留期/事务顺序/outbox 重试
> 审计原则：**数据全生命周期严谨**

---

## 一、5 个 G 编号问题

### 🔴 G1: 镜像表无 source 字段（数据血缘缺失）

**问题**：
- ETL 同步到镜像表时，`source` 字段未标记为 `'etl'`
- 5002 业务层写时，source = 'mobile'
- 8008 mirror 写时，source = 'sync_bridge'
- 业务层读镜像表时，**无法知道数据来自哪里**

**修复**：
- 镜像表加 `_source VARCHAR(32)` 字段
- ETL 同步时 `UPDATE _local SET _source='etl' WHERE order_no=?`
- 业务层读时能看到数据血缘

### 🔴 G2: ETL 软删除不彻底

**问题**：
- ETL 用 `REPLACE INTO` 拉取 `WHERE updated_at >= ?`
- 源表 `is_deleted=1` 的行 → 镜像表更新为 is_deleted=1 ✅
- **但源表完全删除的行 → 镜像表不删除**（脏数据残留）

**修复方案 A**：
- ETL 增加"硬删除同步"通道
- 定期比对源表 vs 镜像表，删除镜像表中"源表已无"的行

**修复方案 B**：
- 源表用软删除，物理删除由人工审计
- 镜像表用软删除

**当前**：两种都没做 → 镜像表脏数据累积。

### 🔴 G3: 镜像表无清理策略

**问题**：
- `violations_local`、`process_sub_steps_local` 等只增不减
- 1 年后：百万级数据
- 性能下降，磁盘爆满

**修复**：
- 加 TTL 策略
- 例如：`process_sub_steps_local` 保留 90 天
- 定时任务：`DELETE FROM process_sub_steps_local WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)`

### 🔴 G4: 8008 写 process_sub_steps + process_records 无事务

**位置**：`sync_bridge.py:532-537`

**问题**：
```python
# 写 process_sub_steps (已 commit)
conn.commit()
# ↓
# 写 process_records (同一事务内)
c.execute("UPDATE process_records SET ...")
# ↓
conn.commit()  # ← 这是 process_records 的 commit
```

**风险**：
- 第一次 commit (process_sub_steps) 成功
- 第二次 commit (process_records) 失败
- 工序数据不一致

**修复**：
- 两步操作包一个事务
- 用 savepoint 或显式 BEGIN/COMMIT

### 🔴 G5: outbox 重试与已写数据冲突

**位置**：`outbox_worker.py` 消费逻辑

**问题**：
- 8008 写 steel_belt
- 8008 调 5002 /mirror（部分成功：HTTP 500 但实际已写）
- 8008 失败写 outbox
- 5002 outbox worker 重试
- REPLACE INTO 用 uuid 作为主键
- **新 payload 覆盖旧 payload（数据可能丢失）**

**修复**：
- 镜像表 REPLACE INTO 时，对比 `updated_at` 字段
- 旧 updated_at 不覆盖新数据
- 或者用 `INSERT ... ON DUPLICATE KEY UPDATE` 显式控制

---

## 二、数据生命周期矩阵

| 阶段 | 关键问题 | 当前 |
|------|----------|------|
| 创建 | 必填/类型/值域 | F 修复后 ✅ |
| 同步 | ETL/mirror/outbox | ✅ |
| 删除 | 软删除同步 | 🟡 部分 |
| 硬删除 | 镜像表清理 | 🔴 无 |
| 保留期 | TTL 策略 | 🔴 无 |
| 归档 | 旧数据归档 | 🔴 无 |
| 审计 | 数据血缘 | 🔴 无 |

---

## 三、并发竞争场景

| 场景 | 描述 | 风险 |
|------|------|------|
| 8008 写 + 5002 写同 order_no | 双写者 | 🔴 重复数据 |
| 8008 写 + ETL 拉同 order_no | 拉时未写 | 🟢 OK |
| 5002 写 + ETL 拉同 order_no | 拉时未写 | 🟢 OK |
| outbox 重试 + 5002 业务写 | 写时间差 | 🟡 数据漂移 |
| 多 5002 实例 | 实例 A 写 + B 写 | 🔴 race condition |

---

## 四、累计修复统计

| 阶段 | 数量 |
|------|------|
| 之前累计 | 61 |
| **第九批 G 编号** | **5** |
| **总计** | **66** |

---

## 五、真实架构评分

| 维度 | 上一轮 | **本轮** |
|------|--------|----------|
| 跨库直查 | 18/20 | 18/20 |
| 字段对齐 | 18/20 | 18/20 |
| 事务完整性 | 16/20 | **12/20**（G4 8008 无事务）|
| 数据约束 | 20/20 | 20/20 |
| 业务校验 | 18/20 | 18/20 |
| 时区一致性 | 16/20 | 16/20 |
| 死信告警 | 18/20 | 18/20 |
| **数据生命周期** | 10/20 | **6/20**（G1/G2/G3 缺失）|
| **总分** | **134/180（74%）** | **126/180（70%）** |

---

## 六、参考

- [SEVENTH_AUDIT.md](./SEVENTH_AUDIT.md) - 第七轮
- 本文档 - 第八轮

---

## 七、关键洞察

> **数据库严谨性不只是写入正确**：
>
> - 创建：✅（F 修复）
> - 同步：✅（E 修复）
> - **删除：🟡 部分**（G2 软删除不同步）
> - **保留：🔴 无策略**（G3）
> - **血缘：🔴 无标记**（G1）
> - **重试：🟡 数据漂移**（G5）
>
> **全生命周期严谨**才能说"零容忍脏数据"。
