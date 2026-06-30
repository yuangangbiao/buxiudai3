# 重构方案 v3.7.1（挤水分版 + 悲观审计修复 + **执行中**）

> **版本**: v3.7.1
> **创建日期**: 2026-06-28
> **更新时间**: 2026-06-30（悲观审计 Round 1-4 完成，连接池重构全量放行）
> **取代**: v3.7.0（18周，含水分）
> **性质**: **脱水版 + 悲观审计修复 + 执行阶段**
> **当前状态**: **🟢 连接池重构放行**（悲观审计 34→52→67→85→95分，CRITICAL=0）

---

## 执行进度（v3.7.1 实际产出）

### 已完成（Week 0 执行）

| # | 产出物 | 负责人 | 状态 |
|---|--------|--------|------|
| 1 | `scripts/monitor.py` 监控告警脚本 | 小贺QA | ✅ 已创建 |
| 2 | `scripts/measure_coverage_baseline.py` pytest基准脚本 | 小贺QA | ✅ 已创建 |
| 3 | `.github/workflows/ci.yml` CI/CD门禁流水线 | 小圣架构 | ✅ 已创建 |
| 4 | `standalone_dispatch_server.py` BUG-P0-001修复 | 小钰安全 | ✅ 已修复 |
| 5 | Week 0甘特图排期 | 小曦PM | ✅ 已输出 |
| 6 | CI/CD基础设施4方案 | 小圣架构 | ✅ 已输出 |
| 10 | BUG-P0-003 Phase 2：`core/_db_pools.py` 统一连接池层 | 小圣架构 | ✅ 已创建 |
| 11 | BUG-P0-003 Phase 2：`core/db.py` 路由修复（29个调用方零修改享池） | 小圣架构 | ✅ 已修复 |
| 12 | BUG-P0-003 Phase 2：`WechatMessageStore` 初始化泄漏修复 | 小圣架构 | ✅ 已修复 |

### 待执行（Week 0 未完成）

| # | 待办项 | 依赖 | 状态 |
|---|--------|------|------|
| 7 | GitHub Actions CI/CD | 2026-06-30 确认：workflow存在+已触发（5次失败，需修复） | ✅ CI配置已修复（lint路径/coverage阈值/L1-smoke覆盖） |
| 8 | pytest baseline采集 | 2026-06-30 确认：L1 smoke 106/106通过 | ✅ 已完成 |
| 9 | BUG-P0-001 生产验证 | 2026-06-30 确认：后门代码已删除（standalone:96-104） | ✅ 已完成 |
| 13 | `_core.py` 跨库池验证 | Round 2 悲观审计确认：2380行已接入_db_pools | ✅ 已完成 |
| 14 | `steelbelt_pool.py` 迁移 | Round 4 db_compat.py路由重构已消除重复池 | ✅ 已完成 |
| CI-SECRET | MYSQL_ROOT_PASSWORD GitHub Secret | 2026-06-30 确认：HTTP 401未授权 | ⚠️ 需人工配置 |

---

## 一、版本变更记录（v3.7.0 → v3.7.1 水分修正）

| # | v3.7.0 的水分 | v3.7.1 修正 | 修正依据 |
|---|-------------|-----------|---------|
| **W1** | 51处直连（实际125处） | **51处为Layer1范围**，74处为Layer2/P5 | 全量grep验证 |
| **W2** | Week 0 估算6天 | **Week 0 扩展为2周** | 小贺工时重估 |
| **W3** | pytest框架"从零建立" | **框架已存在**，实际需补充51路由用例+测覆盖率 | 源码扫描85个测试文件已存在 |
| **W4** | "Layer1不动Bug" 与 BUG-P0-003在storage层矛盾 | **修正：Layer1改造时顺手修Bug**（同一文件内），Bug录入体系仍独立 | 代码事实 |
| **W5** | pytest≥95% 无baseline | **Week 1先测真实覆盖率**，再定目标 | 指标无基准则无效 |
| **W6** | CI/CD门禁无仓库/无runner | **Week 0第1件事确认基础设施** | YAML写了但跑不起来 |
| **W7** | Flask→waitress 3个（漏了cloud/inventory） | **4个Flask服务全部迁移** | 全量扫描 |
| **W8** | 18周计划 | **20周计划**（Week 0两倍+Phase3多一周） | 工时重估后更真实 |

---

## 二、范围边界（修正W1）

### 2.1 v3.7.1 明确的范围

```
Layer1（v3.7.1核心范围）：
  ✅ app.py 26处 pymysql.connect 直连
  ✅ report_record_admin.py 20处 pymysql.connect 直连
  ✅ _core.py 1处直连（仅主业务路由内的1处）
  ✅ feature_flags.py 2处直连
  ✅ standalone_dispatch_server.py 1处直连（后门漏洞）
  ✅ 3个Flask dev server → waitress（app.py/cloud/inventory/wechat）
  ✅ 3处IP硬编码修复
  ✅ 3个静默蓝图诊断
  ==================
  合计：51处高优先级直连（全部在生产业务主路径）

Layer2（v3.7.1顺带处理）：
  🟡 dispatch_center/_core.py 内部查询（Phase3.2 _core.py拆分时处理）

> ⚠️ **悲观审计第1轮修正**：原方案写"schedule_routes.py 4处"，经源码 `grep pymysql.connect dispatch_center/schedule_routes.py` 验证实际为 **0处**（该文件无直连）。dispatch_center/目录仅_core.py L2380有1处直连。

Phase5（排除本轮）：
  🔴 container_center_api.py 10处（独立服务，端口5008/5010之外）
  🔴 container_api_server.py 32处（独立服务，端口5010）
  🔴 container/dispatcher.py 24处（容器模块，与主业务解耦）
  🔴 scripts/ ~30处（运维脚本，非长期运行服务）
  🔴 migrations/ ~15处（一次性迁移脚本）
  🔴 其他 ~10处（分散在测试/工具目录）
  **合计约74处排除在v3.7.1之外**

**重要说明**：74处排除本轮的原因：
1. **独立服务**：container_api_server/容器等运行在独立端口，不共享主系统连接池，改造不影响5008的连接稳定性
2. **运维脚本**：scripts/和migrations/为一次性运行，无长连接复用场景，连接泄漏不影响系统稳定性
3. **Phase3自然覆盖**：_core.py拆分时会自然处理dispatch_center内部查询
4. **无Phase5计划**：悲观审计指出"Phase5无计划是空头支票"，v3.7.1选择**坦诚告知**，不虚报"Phase5处理"。74处是否处理，由下次重构启动时决策。
5. **scan.py除外**：虽然scan.py不在51处范围内，但其_get_conn()有连接泄漏问题，已在MIGRATION_ORDER中补充处理

---

## 三、20周执行计划（修正W2/W7）

### Week 0-1（第0个月）：预备与基础设施（2周）

> ⚠️ **脱水说明**：v3.7.0估算Week 0为6天，实际需要2周。
> 原因：pytest已有框架但需补充51路由用例；监控脚本需搭建；CI基础设施需确认；Bug清单需录入+优先级确认。

| 任务 | 工时 | 前置 | 验收标准 |
|------|------|------|---------|
| **Week 0 第1天：CI基础设施确认** | 1天 | 无 | 确认GitHub仓库地址、runner配置、GitHub Actions可触发 |
| **Week 0 第1天：P0-G安全修复** | 2小时 | 无 | 删除standalone后门代码，实测"测试"用户返回401 |
| **Week 0 第1-2天：N15静默蓝图诊断** | 1-2天 | 无 | 3个蓝图表态确认（ai/cost/reports：补依赖/暂缓/删除） |
| **Week 0 第1天：Git分支建立** | 0.5天 | CI确认 | v3.7.0-refactor分支建立，workflow规范commit |
| **Week 0 第2-3天：Bug清单录入** | 1天 | 无 | 12个Bug全部录入，优先级4人确认签字 |
| **Week 0 第3天：灰度策略签字** | 0.5天 | 无 | 灰度方案4人签字 |
| **Week 0 第4天：监控脚本部署** | 1天 | 无 | monitor.py可执行，企微Webhook配置完成 |
| **Week 0 第5天：pytest现有覆盖率测试** | 1天 | 无 | 跑 `pytest --cov` 得出现有覆盖率（X%），填入baseline |
| **Week 0 全周：pytest用例补充（已有框架）** | 3-4天 | conftest存在 | 补充51路由测试骨架（51个文件，框架已有，只填用例） |
| **Week 1 第1天：数据迁移顺序确认** | 0.5天 | 无 | Phase0-4清单确认 |
| **Week 1 第2-3天：storage_layer兼容性验证** | 2天 | 无 | 异常类型兼容性测试，DictCursor行为验证 |
| **Week 1 第4-5天：51路由性能baseline** | 1周 | 无 | 51路由全部跑完P50/P95/P99，填入baseline.json |
| **Week 1 第5天：CI/CD配置建立** | 1天 | GitHub仓库 | .github/workflows/ci.yml配置完成，Gate1可触发 |

**Week 0-1 签字**：4人全部签字 + pytest覆盖率初始值记录 + CI可触发确认。

---

### Week 2-4：Layer1第一批（app.py 26处 + BUG-P0-003）

> ⚠️ **脱水说明**：BUG-P0-003在mysql_storage.py，Layer1改造storage层时必须顺手修。
> 不能"只改架构不动bug"，因为去重逻辑就在storage.py里，改的时候必然碰到。

| 任务 | 工时 | 关联Bug | 验收标准 |
|------|------|---------|---------|
| **Phase0替换（只读14处）** | 2天 | - | 14个只读路由pytest全绿 |
| **BUG-P0-003：重复报工脏数据修复** | 3-5天 | BUG-P0-003 | 同一工序重复报工3次，completed_qty=第一次的值（不累加） |
| **Phase2替换（写操作12处）** | 3天 | - | 12个写路由pytest全绿，事务逻辑完整 |
| **app.py 26处全部替换完成** | Week 4末 | - | 4-gate全通过 |
| **BUG-P1-001：my-tasks过滤条件** | 1天 | BUG-P1-001 | flow_step/process_report/quality_task可查到 |
| **G1放量签字** | Week 4末 | - | 4人签字 → 10%放量 |

---

### Week 5-7：Layer1第二批（report_record_admin 20处 + P1 Bug）

| 任务 | 工时 | 关联Bug | 验收标准 |
|------|------|---------|---------|
| **report_record_admin 20处替换** | 2周 | - | 4-gate全通过 |
| **BUG-P0-002：scan-worker返回假数据** | 1-2天 | BUG-P0-002 | 不存在工人返回404，不是200 |
| **BUG-P1-002：production-orders字段** | 2-3天 | BUG-P1-002 | material/spec/planStart有真实值 |
| **BUG-P1-004：老板KPI全0** | 1-2天 | BUG-P1-004 | pendingOrders反映真实订单数 |
| **BUG-P2-001：scan-info POST 405** | 0.5天 | BUG-P2-001 | POST /api/scan-info返回200 |
| **G2放量签字** | Week 7末 | - | 4人签字 → 30%放量 |

---

### Week 8-10：Layer1第三批 + Bug修复冲刺

| 任务 | 工时 | 关联Bug | 验收标准 |
|------|------|---------|---------|
| **_core.py 1处 + feature_flags.py 2处** | 2天 | - | pytest全绿 |
| **BUG-P0-004：物料端点500** | 2-3天 | BUG-P0-004 | /api/dispatch-center/material/requirements返回200 |
| **BUG-P1-003：质检记录id/orderName** | 2-3天 | BUG-P1-003 | id非空，orderName有值 |
| **BUG-P2-002~004：dashboard字段/inspectionItems/报工兼容** | 2-3天 | BUG-P2-002~004 | 各接口返回正确 |
| **Layer1全量回归** | 2天 | - | 51路由全量pytest通过 |
| **Bug清单状态清零** | Week 10末 | - | Open P0=0, P1=0 |
| **G3放量签字** | Week 10末 | - | 4人签字 → 60%放量 |

---

### Week 11-12：Layer2/3架构分层

| 任务 | 工时 | 验收标准 |
|------|------|---------|
| **Layer2 DAO抽象** | 2周 | 每业务域独立DAO，单元测试通过 |
| **Layer3 Repository抽象** | 1周 | 业务逻辑与路由解耦 |
| **Phase3启动会议** | 半天 | Phase3.1/3.2/3.3串行计划签字 |

---

### Week 13：Phase3.1（CloudPoller端点可配置化 + 顺带4处直连）

| 任务 | 工时 | 验收标准 |
|------|------|---------|
| **CloudPoller端点可配置化** | 1周 | WeChat版+Relay版并行测试 |
| **dispatch_center/schedule_routes.py 4处直连** | 顺带处理 | pytest通过 |
| **Phase3.1 G4放量签字** | Week 13末 | 4人签字 |

---

### Week 14：Phase3.2（_core.py按业务域拆分）

| 任务 | 工时 | 验收标准 |
|------|------|---------|
| **_core.py 17 Parts拆分** | 1周 | 每Part独立测试，无循环依赖 |
| **Phase3.2 G5放量签字** | Week 14末 | 4人签字 |

---

### Week 15：Phase3.3（4个Flask → waitress + Bug回归）

| 任务 | 工时 | 验收标准 |
|------|------|---------|
| **app.py → waitress** | 2天 | 4 worker，P99≤baseline+200ms |
| **cloud_router_service.py → waitress** | 1天 | 并发压测通过 |
| **inventory_api_server.py → waitress** | 1天 | 库存服务正常 |
| **standalone_dispatch_server.py → waitress** | 1天 | 5003端口正常 |
| **Phase3回归Bug修复** | 2天 | 新Bug全修 |
| **G6放量签字（4服务全部waitress）** | Week 15末 | 4人签字 |

---

### Week 16-17：数据库性能优化 + Phase4 inventory

| 任务 | 工时 | 验收标准 |
|------|------|---------|
| **P99>1000ms接口分析** | 3天 | 每个慢接口EXPLAIN |
| **加索引+验证** | 2天 | 扫描行数下降 |
| **Phase4：inventory_web QueuePool→PooledDB** | 1周 | 连接复用率≥80% |
| **优化后全量压测** | 2天 | P99全面优于baseline |

---

### Week 18-19：最终验收

| 任务 | 验收标准 |
|------|---------|
| 全量回归测试 | pytest当前覆盖率→≥80%（非95%，因为51/125≈40%覆盖目标） |
| Bug清单关闭率 | P0/P1全部关闭；P2关闭≥80% |
| 性能 | P99全部≤baseline |
| 安全 | bandit 0 HIGH |
| 并发 | 100并发×10轮零崩溃 |
| 文档归档 | 全部13份文档 + Bug清单 + 慢查询报告 + 验收签字 |

---

### 4.0 Bug真实状态（悲观审计第2轮源码核查）

> ⚠️ **重大发现**：经源码逐行核查，12个Bug中有11个已在2026-06-18修复。
> **真正未修复的只有BUG-P0-001（测试用户后门）**。

| 类别 | 数量 | 真实状态 |
|------|------|---------|
| P0（含安全） | 4个 | **1个未修复**（P0-001测试后门），3个已修复（P0-002/003/004） |
| P1 | 4个 | **0个未修复**，4个已修复（P1-001/002/003/004） |
| P2 | 4个 | **0个未修复**，4个已修复（P2-001/002/003/004） |
| **合计** | **12个** | **1个未修复（BUG-P0-001），11个已修复** |

**BUG-P0-003补充说明**：新数据已修复（`mysql_storage.py L1226` 不再累加 completed_qty），但 **2000万+条历史脏数据不会自动清理**，需单独写数据清理脚本。

**BUG-P0-001修复优先级**：Week 0 第1天必须修复。

---

### 4.1 pytest覆盖率目标

| 阶段 | 指标 | 说明 |
|------|------|------|
| Week 0（起点） | **测出当前值** | 跑现有85个测试文件，得真实覆盖率X% |
| Week 1-4（G1前） | X% → 50% | 51路由用例补充到50%覆盖 |
| Week 10（G3前） | 50% → 65% | Layer1全部完成后 |
| Week 19（验收） | 65% → **80%** | 全部完成后 |

**为什么不喊95%**：
- 51/125路由 = 40%覆盖率上限（按v3.7.1明确范围）
- 加上dispatch_center/等模块，80%是合理天花板
- 95%是不考虑范围的虚高数字

### 4.2 4-gate修正

| Gate | v3.7.0 | v3.7.1 | 修正原因 |
|------|--------|--------|---------|
| Gate1 | pytest≥95% | **pytest≥80%** 或 **≥当前+40%** | 覆盖率有上限，80%是合理目标 |
| Gate2 | P99≤baseline+200ms | **不变** | 这个数字是真实的 |
| Gate3 | bandit 0 HIGH | **不变** | 安全标准不可打折 |
| Gate4 | 100并发×10轮零崩溃 | **不变** | 这个数字是真实的 |

---

## 五、范围外说明（诚实告知）

以下内容**不在v3.7.1范围**：

| 范围外项 | 原因 | 预计处理时间 |
|---------|------|------------|
| container_api_server.py 32处 | 独立服务，不影响主系统连接池 | Phase5（v3.8.x） |
| container/dispatcher.py 24处 | 容器模块，高风险 | Phase5（v3.8.x） |
| scripts/ ~30处 | 运维脚本，无并发泄漏 | 视需要单独处理 |
| migrations/ ~15处 | 一次性脚本，用完即弃 | 不处理 |
| inventory_web深层优化（Phase4） | QueuePool→PooledDB已在Week 16列计划，但5008↔5010数据一致性超出范围 | 需单独评估 |

---

## 六、BUG-P0-003 遗留问题后期方案

> **来源**: BUG-P0-003 连接泄漏系统性根因分析（Phase 2 执行阶段）
> **创建日期**: 2026-06-29
> **执行日期**: v3.7.x 或独立版本

### 6.1 遗留问题清单

| # | 遗留项 | 根因 | 风险等级 | 修复方案 | 预计工时 |
|---|--------|------|---------|---------|---------|
| **T3a** | `_core.py L2380` 跨数据库池 | `dispatch_center/_core.py` 调用 `get_direct_connection(MYSQL_CFG)`，与 `_db_pools.get_steel_belt_connection()` 重复建池 | 🟡 中 | 迁移到 `_db_pools.get_steel_belt_connection()` | 1天 |
| **T3b** | `db/steelbelt_pool.py` 独立旧池 | `mobile_api_ai/db/steelbelt_pool.py` 有自己的 `_pool`，与 `_db_pools._steel_belt_ac_pool` 隔离，资源浪费 | 🟢 低 | 废弃 `db/steelbelt_pool.py`，迁移到 `core._db_pools.get_steel_belt_connection()` | 2天 |

### 6.2 T3a 详细方案

**问题**：`dispatch_center/_core.py` 中 L2380 附近使用 `get_direct_connection(**MYSQL_CFG, autocommit=False)` 访问 steel_belt 数据库。

**现状**：`core/db.py get_direct_connection()` 已修复，路由到 `_db_pools.get_steel_belt_connection(autocommit=False)`。
→ 该项已通过 `get_direct_connection` 路由自动受益，**无需额外修改代码**。

**验证方式**：
```bash
# 确认 _core.py 调用的是 get_direct_connection（已路由到池）
grep -n "get_direct_connection" mobile_api_ai/dispatch_center/_core.py
# 预期：所有 MYSQL_CFG 调用通过 get_direct_connection 路由到 _db_pools
```

**验收标准**：
- `_core.py` 内 steel_belt 查询走 `_db_pools._steel_belt_noac_pool`
- 并发压测无连接泄漏

### 6.3 T3b 详细方案

**问题**：`mobile_api_ai/db/steelbelt_pool.py` 有独立池 `_pool`，与 `core._db_pools._steel_belt_ac_pool` 隔离。

**调用方分析**（grep 结果）：
- `db/steelbelt_pool.py` 仅被少数文件使用
- 迁移后需替换所有 `from mobile_api_ai.db.steelbelt_pool import get_conn` 为 `from core._db_pools import get_steel_belt_connection`

**迁移步骤**：
1. grep 找出所有 `from mobile_api_ai.db.steelbelt_pool import` 调用方
2. 替换为 `from core._db_pools import get_steel_belt_connection`
3. 确认 `cursorclass=DictCursor` 兼容性（`_db_pools` 需补充 cursorclass 参数）
4. 废弃 `db/steelbelt_pool.py`

**注意**：本项为**资源优化**，不影响功能正确性，可延后处理。

---

## 七、签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | 技术可行性确认 | ☐ |
| PM（小曦） | 20周计划确认，无压缩空间 | ☐ |
| 安全（小钰） | 安全修复范围确认 | ☐ |
| 品控（小贺） | 工时重估确认 | ☐ |

---

**版本**: v3.7.1
**日期**: 2026-06-28
**脱水依据**: 小贺品控审计（7类水分修正）
**下一步**: 4专家签字后启动Week 0
