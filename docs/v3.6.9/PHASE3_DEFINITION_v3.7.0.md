# Phase3 明确定义 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P1 文档，Week 0 必须明确
> **审计来源**: 4专家审计（小曦PM）→ H-3

---

## 一、问题

v3.2方案中"Phase3"定义模糊：
- 是"第三阶段"的意思？
- 还是"第三层"（Layer3）的意思？
- 跟Layer2/3是什么关系？

导致：无法明确里程碑，无法分配资源，无法确定验收标准。

---

## 二、Phase3 定义

### 2.1 正式名称

> **Phase3 = 第三里程碑 = CloudPoller重构 + _core.py拆分 + Flask服务容器化**

### 2.2 与其他层的关系

```
Layer1（Week 3-8）    → 存储层归一（pymysql.connect → storage_layer）
Layer2（Week 11-12） → DAO抽象层
Layer3（Week 11-12） → Repository抽象层
    ↓
Phase3（Week 13-16） → 架构层收尾（CloudPoller + _core.py + waitress）
```

**结论**：
- Phase3 **不是** Layer3
- Phase3 **是** Layer1/2/3 完成后的架构收尾任务
- Phase3 **包含** 3个独立子任务（必须串行）

---

## 三、Phase3 三阶段串行计划

### 3.1 Phase3.1：CloudPoller端点可配置化（Week 13）

**任务**：将 `cloud_poller.py` 中的 `/api/poll` 端点hardcode改为可配置参数

**验收标准**：
- WeChat版和Relay版并行测试通过
- 切换不同端点不影响现有逻辑
- pytest覆盖CloudPoller相关用例 ≥ 90%

**回滚单元**：Phase3.1 可独立回滚，不影响Phase3.2/3.3

### 3.2 Phase3.2：_core.py按业务域拆分（Week 14）

**任务**：将 ~9053行的 `_core.py` 按20个Parts拆分为独立模块

**源码已有完整Part注释**（`dispatch_center/_core.py` 源码L16-L37）：

| Part | 名称 | 行号范围 | 拆分目标模块 |
|:----:|------|---------|------------|
| 1 | 导入与初始化 | L164-181 | `parts/part1_init/` |
| 2 | 核心类与上下文 | L182-219 | `parts/part2_core/` |
| 3 | 服务层函数 | L220-1227 | `parts/part3_services/` |
| 4 | 通知与消息路由 | L1228-1389 | `parts/part4_notifications/` |
| 5 | 流程任务路由 | L1390-1557 | `parts/part5_flow_tasks/` |
| 6 | 模板管理路由 | L1558-1832 | `parts/part6_templates/` |
| 7 | 违规与配置路由 | L1833-2224 | `parts/part7_violations/` |
| 8 | 任务管理路由 | L2225-2607 | `parts/part8_tasks/` |
| 9 | 操作员管理路由 | L2608-3440 | `parts/part9_operators/` |
| 10 | 消息模板路由 | L3441-3542 | `parts/part10_msg_templates/` |
| 11 | 流程管理路由 | L3543-4776 | `parts/part11_flow_mgmt/` |
| 11.5 | 统一订单全流程状态接口 | L4777-5417 | `parts/part11_5_unified_orders/` |
| 12 | 回归测试 API | L5418-5664 | `parts/part12_regression/` |
| 13 | 业务统计路由 | L5665-5887 | `parts/part13_stats/` |
| 14 | 定时任务控制器 | L5888-6151 | `parts/part14_schedules/` |
| 15 | 同步接口 | L6152-6238 | `parts/part15_sync/` |
| 16 | 质检与工单同步 | L6239-7110 | `parts/part16_quality_sync/` |
| 17 | 统一任务查询接口 | L7111-7980 | `parts/part17_unified_tasks/` |
| 18 | 质检与成本同步 | L7981-8270 | `parts/part18_quality_cost/` |
| 19 | 报工与同步接口 | L8271-8653 | `parts/part19_report_sync/` |
| 20 | 同步接口 | L8654-8731 | `parts/part20_sync/` |
| 20b | 配置接口 | L8732-8784 | `parts/part20b_config/` |

**拆分原则**：
- Part 1-2（初始化+核心类）→ 被所有其他Part依赖，**最后拆**
- Part 3（服务层）→ Part 11-12依赖它，**先拆但谨慎**
- Part 19.5/20（统一查询接口）→ Part 11的子功能，先拆
- Part 12（回归测试API）→ **不参与拆分**，独立保留或移到tests/

**验收标准**：
- 每个Part独立导入无循环依赖
- 每个Part独立pytest测试通过
- 原有的 `_core.py` 文件删除或仅保留顶层入口

**回滚单元**：Phase3.2 可独立回滚，不影响Phase3.3

### 3.3 Phase3.3：Flask→waitress（Week 16）

**任务**：将 `wechat_server.py` / `cloud_router_service.py` / `inventory_api_server.py` 三个服务的 Flask 内置服务器替换为 waitress

**改造清单**：

| 文件 | 行号 | 当前启动方式 | 改造后 |
|------|------|------------|--------|
| `app.py` | L2306 | `app.run(debug=False)` | `waitress serve(app, threads=4)` |
| `standalone_dispatch_server.py` | L1280 | `app.run(debug=False)` | `waitress serve(app, threads=4)` |
| `cloud_router_service.py` | L287 | `app.run(debug=False)` | `waitress serve(app, threads=4)` |
| `inventory_api_server.py` | L430 | `app.run(debug=False)` | `waitress serve(app, threads=8)` |
| `wechat_cloud.py` | L1194 | `make_server(threaded=True)` | `waitress serve(app, threads=8)` ✅ |
| `cloud_relay.py` | L339 | `waitress serve` | **已是waitress，无需改造** ✅ |

**验收标准**：
- 100并发×10轮零崩溃
- P99响应时间 ≤ baseline + 200ms
- 日志输出位置正确（stdout → 日志文件）
- 监控指标正常（进程数、CPU、内存）

**回滚单元**：Phase3.3 可独立回滚

---

## 四、Phase3 与 G4/G5 放量的关系

| 放量批次 | 对应Phase3子任务 | 放量条件 |
|---------|-----------------|---------|
| **G4** | Phase3.1 CloudPoller完成 | 4-gate门禁通过 |
| **G5** | Phase3.2 _core.py拆分完成 + Phase3.3 waitress完成 | 4-gate门禁通过 |

**注**：Phase3.1 和 Phase3.2 可合并为 G4（如果间隔<1周），Phase3.3 单独为 G5。

---

## 五、Phase3 签字里程碑

| 里程碑 | 签字人 | 允许时间 |
|--------|--------|---------|
| Phase3.1 启动 | 开发+架构（小圣） | Week 13第1天 |
| Phase3.1 G4放量签字 | 开发+PM+安全+品控 | Week 13末 |
| Phase3.2 启动 | 开发+架构（小圣） | Week 14第1天 |
| Phase3.2 放量签字 | 开发+PM+安全+品控 | Week 14末 |
| Phase3.3 启动 | 开发+架构（小圣） | Week 16第1天 |
| Phase3.3 G5放量签字 | 开发+PM+安全+品控 | Week 16末 |

---

## 六、与其他任务的依赖关系

```
Phase3.1（CloudPoller）
  前置: Layer1全部完成（Week 8末）
  后置: Phase3.2可开始

Phase3.2（_core.py拆分）
  前置: Phase3.1完成 + Layer2/3完成（Week 12末）
  后置: Phase3.3可开始

Phase3.3（waitress）
  前置: Phase3.2完成
  后置: Week 16末完成 → Week 17数据库优化可开始
```

---

**签字确认**: PM（小曦）☐ / 架构（小圣）☐ / 开发负责人☐
**最后更新**: 2026-06-28
