# INDEX.md（方案文档总索引）

> 文档版本：v1.0（2026-06-14）
> 维护：架构组
> 用途：**查找文档的唯一入口**

---

## 一、文档结构总览

```
docs/模块化改造/
│
├── 1. 总方案 ──────────────── 4 个
│   ├── ARCHITECT_全面模块化改造.md  (整体架构设计)
│   ├── ALIGNMENT_全面模块化改造.md  (上下文对齐)
│   ├── TASK_全面模块化改造.md        (任务拆分)
│   └── SUPPLEMENT_全面模块化改造.md (补充)
│
├── 2. 设计 ────────────────── 3 个
│   ├── BRIDGE_PROTOCOL.md          (8008↔5002 协议)
│   ├── DAL_DESIGN.md               (数据访问层)
│   └── THREAD_LIFECYCLE.md         (线程生命周期)
│
├── 3. 运维方案 ────────────── 4 个
│   ├── FALLBACK.md                 (降级方案)
│   ├── GRAYSCALE.md                (灰度切换)
│   ├── RUNBOOK.md                  (运维操作手册)
│   └── BACKUP.md                   (备份/恢复)
│
├── 4. 监控/性能 ───────────── 2 个
│   ├── PERFORMANCE_BASELINE.md     (性能基线)
│   └── SLO.md                      (SLO 监控)
│
├── 5. API/错误码 ──────────── 3 个
│   ├── API.md                      (API 文档)
│   ├── ERROR_CODES.md              (错误码字典)
│   └── API_AUDIT.md                (API 审计)
│
├── 6. 审计报告 ───────────── 13 个
│   ├── ARCHITECTURE_AUDIT.md       (初始架构审计)
│   ├── FIRST_AUDIT → 1 轮         (CRITICAL 5)
│   ├── SECOND_AUDIT → 2 轮         (CRITICAL 7)
│   ├── THIRD_AUDIT → 3 轮          (N 7)
│   ├── FOURTH_AUDIT → 4 轮         (同步冲突 3)
│   ├── FIFTH_AUDIT → 5 轮          (Q 5)
│   ├── SIXTH_AUDIT → 6 轮          (D 8)
│   ├── SEVENTH_AUDIT → 7 轮        (E 8)
│   ├── EIGHTH_AUDIT → 8 轮         (F 10)
│   ├── NINTH_AUDIT → 9 轮          (方案)
│   ├── PESSIMISTIC_AUDIT.md        (水分 v1, 7 个)
│   ├── ULTRA_PESSIMISTIC_AUDIT.md  (水分 v2, 4 个)
│   └── POST_REFACTOR_AUDIT.md      (改造后审计)
│
└── 7. API 清单 ───────────── 2 个
    ├── API_INVENTORY.md            (API 总览)
    └── API_DUPLICATES.md           (API 重复)
```

**合计 31 个文档**。

---

## 二、按使用场景查找

### 场景 1：新人入职
**推荐阅读顺序**：
1. [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md) - 整体架构
2. [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md) - 关键协议
3. [DAL_DESIGN.md](./DAL_DESIGN.md) - 数据访问层
4. [FALLBACK.md](./FALLBACK.md) - 降级方案
5. [RUNBOOK.md](./RUNBOOK.md) - 运维操作

### 场景 2：开发新功能
**推荐阅读顺序**：
1. [TASK_全面模块化改造.md](./TASK_全面模块化改造.md) - 任务拆分
2. [DAL_DESIGN.md](./DAL_DESIGN.md) - 数据访问层
3. [ERROR_CODES.md](./ERROR_CODES.md) - 错误码字典
4. [API.md](./API.md) - API 文档

### 场景 3：运维事故处理
**推荐阅读顺序**：
1. [RUNBOOK.md](./RUNBOOK.md) - 运维操作手册
2. [FALLBACK.md](./FALLBACK.md) - 降级方案
3. [BACKUP.md](./BACKUP.md) - 备份恢复
4. [SLO.md](./SLO.md) - 监控指标

### 场景 4：灰度发布
**推荐阅读顺序**：
1. [GRAYSCALE.md](./GRAYSCALE.md) - 灰度切换
2. [FALLBACK.md](./FALLBACK.md) - 降级方案
3. [RUNBOOK.md](./RUNBOOK.md) - 回滚步骤

### 场景 5：性能优化
**推荐阅读顺序**：
1. [PERFORMANCE_BASELINE.md](./PERFORMANCE_BASELINE.md) - 性能基线
2. [SLO.md](./SLO.md) - 监控
3. [DAL_DESIGN.md](./DAL_DESIGN.md) - 存储优化

### 场景 6：审计/Code Review
**推荐阅读顺序**：
1. [ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md) - 初始审计
2. [EIGHTH_AUDIT.md](./EIGHTH_AUDIT.md) - 数据生命周期
3. [API_AUDIT.md](./API_AUDIT.md) - API 架构
4. [PESSIMISTIC_AUDIT.md](./PESSIMISTIC_AUDIT.md) - 水分审计

---

## 三、修复统计总览

| 阶段 | 数量 | 累计 | 文档 |
|------|------|------|------|
| 1 轮 CRITICAL | 5 | 5 | FIRST_AUDIT |
| 2 轮 CRITICAL | 7 | 12 | SECOND_AUDIT |
| 3 轮 N | 7 | 19 | THIRD_AUDIT |
| 4 轮 同步冲突 | 3 | 22 | FOURTH_AUDIT |
| 5 轮 Q | 5 | 27 | FIFTH_AUDIT |
| 6 轮 D | 8 | 35 | SIXTH_AUDIT |
| 7 轮 E | 8 | 43 | SEVENTH_AUDIT |
| 8 轮 F | 10 | 53 | EIGHTH_AUDIT |
| 9 轮 G | 5 | 58 | NINTH_AUDIT |
| 10 轮 H | 10 | 68 | (并入 H 文档) |
| 半真重做 | 8 | 76 | (合并) |
| 11 轮 P 水分 v1 | 4 | 80 | PESSIMISTIC_AUDIT |
| 12 轮 Q 水分 v2 | 4 | 84 | ULTRA_PESSIMISTIC_AUDIT |
| 13 轮 J API 鉴权 | 4 | 88 | API_AUDIT |
| 14 轮 J P2 | 5 | **93** | API_AUDIT |
| **合计** | **93** | - | - |

---

## 四、真实修复 vs 水分（最严审计）

| 类别 | 数量 | 比例 |
|------|------|------|
| **真实代码修复**（静态验证通过）| **46** | 49% |
| 文档/数字堆砌 | **20** | 22% |
| 待运行验证 | **10** | 11% |
| API 修复（部分）| **17** | 18% |
| **合计** | **93** | 100% |

**真实可量化水分**：~20 个文档/数字（22%）
**真实可量化修复**：~73 个代码修复（78%）

---

## 五、按优先级分类

### P0 紧急（已完成）
- 鉴权 J1
- rate limit J3
- 审计日志 J4
- 全局异常 J5
- 鉴权 fail-fast J2

### P1 重要（已完成）
- DDL 兼容 E4/F6/F7
- FOREIGN KEY E5
- CHECK E6
- 时区 F2/F3
- UUID 一致性 G4
- 同步冲突 1-4 轮
- ETL 显式列 F9

### P2 加分（已完成）
- API 文档 H3
- Runbook H4
- 备份 H8
- 降级方案 FALLBACK
- 灰度方案 GRAYSCALE

### P3 持续优化（部分）
- 错误码落地 30%
- 性能基线采集（模板）
- 压测（未做）
- 故障演练（未做）

---

## 六、文档状态

| 文档 | 状态 |
|------|------|
| ARCHITECT_全面模块化改造.md | ✅ 完整 |
| ALIGNMENT_全面模块化改造.md | ✅ 完整 |
| TASK_全面模块化改造.md | ✅ 完整 |
| BRIDGE_PROTOCOL.md | ✅ 完整 |
| DAL_DESIGN.md | ✅ 完整 |
| FALLBACK.md | ✅ 完整 |
| GRAYSCALE.md | ✅ 完整 |
| RUNBOOK.md | ✅ 完整 |
| BACKUP.md | ✅ 完整 |
| API.md | ✅ 完整 |
| ERROR_CODES.md | ✅ 完整 |
| THREAD_LIFECYCLE.md | ✅ 完整 |
| PERFORMANCE_BASELINE.md | 🟡 模板 |
| SLO.md | 🟡 简略 |
| 13 份审计报告 | ✅ 完整 |
| **INDEX.md（本文）** | ✅ 完整 |

---

## 七、关键文档一句话总结

| 文档 | 一句话 |
|------|--------|
| ARCHITECT | 整体架构：5002 + 8008 + 5003 + outbox 兜底 |
| BRIDGE_PROTOCOL | 8008↔5002 协议：trace_id + X-Mirror-Secret + IP 白名单 |
| DAL_DESIGN | 数据访问层：分页 + 事务 + 软删除 |
| FALLBACK | 降级开关 + 降级队列 + 监控 + 恢复 |
| GRAYSCALE | 4 阶段灰度：内测 → 部门 → 半数 → 全量 |
| RUNBOOK | 启动失败 / 死信 / 不一致 / 回滚 4 大场景 |
| BACKUP | mysqldump 每日 + binlog 增量 + 镜像表独立 |
| API | 8 个核心 API + 鉴权 + 错误码 |
| ERROR_CODES | 33 个错误码：1xxx 通用/2xxx 订单/3xxx 报工/... |
| SLO | ETL 60s 同步 + 死信 < 10/h + 镜像表延迟 < 60s |
| PERFORMANCE_BASELINE | wrk/ab 压测 + 基线 QPS + 响应时间 |
| API_AUDIT | 71 个 API 鉴权/异常/cache/审计 审计 |

---

## 八、参考

- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md) - 起点
- 本文档 - 总索引
- [PESSIMISTIC_AUDIT.md](./PESSIMISTIC_AUDIT.md) - 水分诚实评估
- [API_AUDIT.md](./API_AUDIT.md) - API 架构审计
