# MySQL 直写迁移方案 v6.1 — 最终审计

**审计对象**: `docs/system_design.md` v6.1（737行）  
**审计人**: 齐活林（交付总监）  
**审计基准**: API数据读写审计（33/F）+ 连接审计（73/C+）+ 方案审计 v1→v5

---

## 最终评分: 94/100 (A)

| 维度 | 得分 | 评语 |
|------|------|------|
| 架构正确性 | 95 | 分库+8008桥接，两层解耦 |
| 问题覆盖率 | 100 | **P0×11 全部覆盖** |
| 实施细节 | 95 | 逐行替换方案，精确到L号 |
| 源码准确性 | 90 | 行号基本正确，少量缺标注 |
| 依赖正确性 | 95 | T02→T03→T05 链正确 |
| 风险评估 | 85 | 主风险已覆盖，DDL细节可补充 |
| 文档可读性 | 95 | 清晰分节，模板化替换方案 |

---

## 审计历史

| 审计轮次 | 对象 | 发现 | 评分 |
|---------|------|------|------|
| 第1轮 | v1 方案 | P0×4: Router不可行、合库、Scheduler、回退 | 54/D+ |
| 第2轮 | v2 方案 | Router废弃+合库修正 | 87/B+ |
| 第3轮 | v3 方案 | 漏2文件、process_v2损坏、timeout不统一 | 85/B |
| 第4轮 | v4 方案 | container_center_api漏8行 | 93/A- |
| 第5轮 | v5 方案 | _v4_doc_store SQLite硬编码、2 NameError | 91/A- |
| **第6轮** | **v6.1 方案** | **全部修正，可直接执行** | **94/A** |

---

## P0 覆盖矩阵: 11/11 ✅

| # | 来源 | 问题 | v6.1 位置 |
|---|------|------|----------|
| 1 | app.py | WHERE rowid=%s? | §3.1 L159 |
| 2 | app.py | cc_data_packages | §3.3 L865 |
| 3 | app.py | cc_process_records | §3.1 L198 |
| 4 | app.py | 双写无事务 | §3.1 L158-210 |
| 5 | process_v2 | %s? | §3.5 L113 |
| 6 | process_v2 | SQL损坏 | §3.5 L138 |
| 7 | process_v2 | None.commit() | §3.5 L144 |
| 8 | container_center_api | _v4_doc_store硬编码SQLite | §3.7 L124-136 |
| 9 | container_center_api | process_id NameError | §3.8 L1970 |
| 10 | container_center_api | mysql_error NameError | §3.9 L2310 |
| 11 | dispatch_center | 硬编码密码88888888 | §3.4 L67 |

---

## 文件覆盖: 46/46 ✅

| 任务 | 文件数 | 状态 |
|------|--------|------|
| T01 配置层 | 5 | ✅ |
| T02 Router废弃 | 12 | ✅ (含_v4_doc_store) |
| T03 核心改造 | 7 | ✅ (含P0-9/10) |
| T04 同步处理器 | 12 | ✅ |
| T05 清理验证 | 8 | ✅ |
| **总计** | **46** | |

---

## 数据流验证

```
报工写入: ✅  app.py/process_v2 → CONTAINER_MYSQL_CFG → COMMIT
8008桥接: ✅  sync_bridge → 读CONTAINER → 写MYSQL → COMMIT
调度查询: ✅  dispatch_center → MYSQL_CFG / CONTAINER_MYSQL_CFG
容器查询: ✅  container_center_api → CONTAINER_MYSQL_CFG
SQLite:   ✅  SchedulerManager 保留（非业务）
```

---

## 结论

v6.1 方案经过 6 轮迭代、3 次架构变更、5 次审计，已覆盖原始审计 52→33 分的全部缺陷。方案包含：

- 分库架构 + 8008 解耦桥接
- 46 文件、5 任务、逐行替换方案
- 11 P0 + 13 P1 + 6 P2 全部覆盖
- SQL 语法修正清单
- 连接模板和事务规范

**可执行。建议启动 T01→T02→T03→T04→T05 顺序实施。**
