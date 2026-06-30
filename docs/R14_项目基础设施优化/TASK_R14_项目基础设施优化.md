# R14 项目基础设施优化 — TASK(v6)

> 配套 [`FINAL_R14_项目基础设施优化.md`](./FINAL_R14_项目基础设施优化.md) (v6)
> v6 状态:**未开工**,待第 6 轮悲观审计 0 CRITICAL 通过
> v6 工期重估:必做 **25-37h**(F 阶段 18-25h + G 阶段 6-9h + H 阶段 1-3h)
> 修订日期:2026-06-11(架构师视角 + 元审计精简 + 第 5 轮审计修补)

---

## v5 关键变化(v4 → v5 摘要,精简 28%)

| 关键变化 | v4 | **v5** |
|---------|----|----|
| operation_logs 表 | 8 字段 + 3 index | **5 字段 + 1 index**(过度设计精简) |
| F5 推广范围 | 450 处"全量" | **225 处关键**(50%,高频关键路径) |
| F1 子任务 | F1.1/1.2/1.3 三层 + G1 字节级兼容 | **F1 单任务 + G1 行为兼容(1 断言)** |
| 风险表 | 10 项(含 4 项理论风险) | **5 项(只列已观察风险)** |
| F6 判定标准 | 3 条 | **2 条(目录名 + mtime)** |
| R14 vs R13 | 极端回退方案 | **删除(只保留优先原则,留到遇到时再说)** |
| "架构师视角"标签 | 8+ 处 | **0 处(自吹自擂删除)** |
| 工期(必做) | 25-35h | **25-37h**(-10h 精简实施风险) |
| 总行数 | 531 | **328** |

---

## v6 关键变化(v5 → v6 摘要)

| 关键变化 | v5 | **v6** |
|---------|----|----|
| 事实偏差修补 | 7 处已知错误(op_logger 假死代码、auto_schema 路径、表冲突等) | **0 处已知事实偏差** |
| 工时(必做) | 25-37h | **25-37h**(不变) |
| F2 装饰器实现 | 仅描述"加 @with_lock" | **补充 _LOCK_REGISTRY 全局注册表伪代码** |
| F4 范围 | "36 处"无范围说明 | **明确限定 mobile_api_ai 3 文件 + 其他留 R15+** |
| 总行数 | 105 | **约 130** |

---

## 阶段 F:基础设施

| 任务 ID | 任务 | 文件 | v5 工期 | 验证 | 风险 |
|--------|------|------|:----:|------|:----:|
| F1 | 扩展 `utils/query_cache.py` 加 `cached()` 装饰器 | `utils/query_cache.py` (扩展) | **2-3h** | 单元测试 + G1 行为兼容 | 中 |
| F2 | 新建 `utils/decorators.py` 加 `with_lock(name)`(业务锁专用) | `utils/decorators.py` (新建) | **2-3h** | 单元测试 + 死锁 dogfood | 中 |
| F3 | 合并到 F2 加 `retry(max_attempts, backoff)` | `utils/decorators.py` (新建) | **1-2h** | 单元测试 | 低 |
| F4 | 替换 36 处 `pymysql.connect` 为 `from core.db import get_connection`(限定 mobile_api_ai/app.py + standalone_dispatch_server.py + storage/mysql_storage.py) | 多文件(**每文件单 commit**) | **6-8h** | grep 验证 0 命中(范围限定内) | **高** |
| F5 | 新建 `utils/violation_logger.py` + H2 schema 注册 + 推广 5 核心文件 **225 处关键 except** | 1 新建 + 1 扩展 + 5 改 + 1 schema | **6-8h** | grep + 单元测试 | **高** |
| F6 | 扫描 `dist/` 下可疑目录,2 条判定标准 → 移 `_archive/` | 文件系统 | **1-2h** | 文件系统检查 | 低 |

**F 阶段 v5 总计: 必做 18-25h**

---

## 阶段 G:测试 + 文档

| 任务 ID | 任务 | v5 工期 |
|--------|------|:----:|
| G1 | `utils/query_cache.py` cached 单元测试(行为兼容) | 1-2h |
| G2 | `utils/decorators.py` with_lock 单元测试 + 死锁 dogfood | 1-2h |
| G3 | `utils/decorators.py` retry 单元测试 | 1h |
| G4 | R13 单测不回归 | 1h |
| G5 | R6/R7 Playwright 不回归 | 1h |
| G6 | 文档:实施报告 + 运维手册 | 1-2h |

**G 阶段 v5 总计: 6-9h**

---

## 阶段 H:悲观审计 + 修订

| 任务 ID | 任务 | v5 工期 |
|--------|------|:----:|
| H1 | 每完成 F1/F2/F4/F5 一个原子任务,跑一次冒烟测试 | 嵌入 F1-F5 |
| H2 | F5 实施前先在 `utils/auto_schema.py` 注册 `operation_logs` 表(v6 schema) | 1h |
| H3 | F1-F6 全部完成后,做悲观审计第 5 轮(全量重审) | 1-2h |
| H4 | 修补 v5 审计发现的问题 | 视问题数 |

**H 阶段 v5 总计: 1-3h**

---

## 总工期汇总

| 范围 | v1 | v4 | **v5** | v5 精简 |
|------|:----:|:----:|:----:|------|
| **必做 (F1-F6) + G + H** | 7.4h | 25-35h | **25-37h** | -10h 实施风险 |
| **含可选 (F1-F12)** | 13.4h | 39-55h | **39-57h** | -14h 实施风险 |

---

## 与 R13 关系

R14 是 R13 的"基础设施补充"。R14 装饰器签名**优先确定**,R13 端点改造**对齐** R14(对齐原则)。

R13 实施时会用到 R14 的:`@retry` 装饰器 / `@with_lock` 装饰器 / `violation_logger` / `get_connection`。

---

## 待用户决策

**Q1**:R14 范围?
- **A** (推荐)只做 F1-F6 必做6 项 — v5 工期 **25-37h**
- **B** F1-F12 必做6 + 可选6 — v5 工期 **39-57h**
- **C** 只做 F1/F2/F3 三个装饰器(最小化)— v5 工期 **5-8h**

**Q2**:F4 `pymysql.connect` 替换策略?
- **A** (推荐)全量替换 36 处为 `from core.db import get_connection` — 工期 6-8h
- **B** 只改新代码 + 加 lint 规则禁止直接 pymysql.connect(渐进式)— 工期 2-3h + 持续监控

**Q3**:F5 异常日志替换策略?
- **A** (推荐)新建 violation_logger + 推广到 5 个核心文件 **225 处关键 except** — 工期 6-8h
- **B** 只在 5 个核心文件直接调用 operation_logs 表(跳过 violation_logger 抽象)— 工期 4-5h
- **C** 不替换,只加 lint 警告(不强制)— 工期 1h

我建议 **A + A + C**（v6 修订：F4 推荐 C 选项限定范围）。

---

## 修补状态(v5 → v6)

- [x] #1 op_logger 假死代码已修正
- [x] #2 core/auto_schema.py 路径已修正为 utils/auto_schema.py
- [x] #3 operation_logs 表兼容迁移 + DROP 回滚已补全
- [x] #4 pymysql.connect 范围明确(限定 mobile_api_ai 3 文件)
- [x] #5 @with_lock _LOCK_REGISTRY 注册表已补充
- [x] #6 get_direct_connection 描述已修正
- [x] #7 DDL DROP TABLE 回滚已补全
- [x] 版本号 v5 → v6 + 修订记录已同步

**确认 Q1+Q2+Q3 + 第 6 轮悲观审计 0 CRITICAL 通过后,方可开工。**
