# ARCHITECTURE_AUDIT.md（整体架构功能流程审计）

> 文档版本：v1.0（2026-06-13）
> 审计范围：服务拓扑、数据流、控制流、关键路径、SPOF、降级
> 审计维度：6 大项

---

## 一、整体服务拓扑

### 1.1 服务清单

| 服务 | 端口 | 进程入口 | 用途 | 状态 |
|------|------|----------|------|------|
| 报工系统 | 5008 | `app.py` | 手机端主入口 | ✅ |
| 容器中心 | 5002 | `container_center_api.py` | 业务主库 | ✅ |
| 调度中心 | 5003 | `standalone_dispatch_server.py` | 微信消息、任务派发 | ✅ |
| 同步桥 | 8008 | `sync_bridge_server.py` | 内部同步到 steel_belt | ✅ |
| 人脸考勤 | 5009 | `face_server.py` | 独立 | ✅ |

### 1.2 服务依赖图

```
                                ┌─────────────────────┐
                                │  手机端浏览器        │
                                └──────────┬──────────┘
                                           │ HTTP
                                ┌──────────▼──────────┐
                                │  报工系统 5008      │
                                │  app.py             │
                                └──┬────┬────┬────┬───┘
                  ┌──────────────────┘    │    │    └────────────┐
                  │ 代理          ┌────────┘    │              │
                  ▼              ▼             ▼              ▼
        ┌──────────────────┐ ┌──────┐  ┌─────────────┐  ┌──────────┐
        │  容器中心 5002    │ │ 企业 │  │ 同步桥 8008  │  │ 调度中心 │
        │ container_center │ │ 微信 │  │ sync_bridge │  │   5003   │
        └────────┬─────────┘ └──────┘  └──────┬──────┘  └────┬─────┘
                 │                            │              │
                 ▼                            ▼              ▼
        ┌──────────────────┐         ┌─────────────┐ ┌──────────────┐
        │  container_      │         │  steel_belt │ │  企业微信 API │
        │  center 库       │         │  库         │ │              │
        └──────────────────┘         └─────────────┘ └──────────────┘
```

---

## 二、关键数据流

### 2.1 报工数据流（手机端 → steel_belt）

```
[1] 手机端 POST /api/process_sub_step
        ↓
[2] app.py:567 process_sub_step()
        ↓
[3] 校验订单在 steel_belt.orders 存在
        ↓
[4] 幂等检查（避免同人同批次重复）
        ↓
[5] MySQLStorage.save_process_sub_step_with_pkg_update()
        ↓ 写入 container_center.process_sub_steps
        ↓
[6] bridge.sync_client.send('sub-step-report') 
        ↓ HTTP POST http://127.0.0.1:8008/api/sync/sub-step-report
        ↓
[7] 8008 写入 steel_belt.process_sub_steps
        ↓
[8] invalidate_process_tasks_cache() 失效缓存
        ↓
[9] 返回 200 OK
```

**问题点**：
- ❌ **第 3 步跨库直查**（H2 修复未生效）
- ❌ **第 6 步失败时未入 outbox**（依赖业务层 enqueue_report）
- ❌ **第 4 步幂等检查**依赖 pymysql 直连（无连接池管理）

### 2.2 物料数据流（手机端 → container_center）

```
[1] 手机端 POST /api/material/confirm
        ↓
[2] app.py:1903 material_confirm() [v2.0 代理]
        ↓
[3] requests.post(f'{CONTAINER_CENTER_URL}/api/material/confirm', ...)
        ↓ HTTP POST http://127.0.0.1:5002/api/material/confirm
        ↓ 透传 Authorization + X-Forwarded-For
        ↓
[4] 5002 api_material_confirm() 实际实现
        ↓ 写 container_center.data_packages
        ↓
[5] 返回 200 OK 透传回 5008
        ↓
[6] 5008 透传回手机端
```

**问题点**：
- ✅ 已优化（v2.0 修复）
- ⚠️ 链路过长：手机端 → 5008 → 5002（2 次 HTTP 跳转）
- ⚠️ 5008 不可用时，5002 直连入口仍可用，但前端调用需要改 URL

### 2.3 微信通知流（业务 → 用户）

```
[1] 业务触发（报工/审批）
        ↓
[2] notify.send_notification(userid, message)
        ↓
[3] [v2.0 H1 修复后] requests.post(f'{DISPATCH_WE_CHAT_API}', ...)
        ↓ HTTP POST http://127.0.0.1:5003/api/wechat/send-notification
        ↓
[4] 5003 调度中心 messages/send
        ↓
[5] 企业微信 API
        ↓
[6] 推送到用户微信
```

**问题点**：
- ✅ v2.0 修复后走 5003
- ⚠️ 5003 不可用 → 降级到本地 sqlite 队列（无重发机制）

### 2.4 报告队列消费流

```
[1] report_queue worker 线程（每 10s）
        ↓
[2] dequeue_pending_reports(limit=5)
        ↓ 读 container_center.report_queue
        ↓
[3] 写入 process_sub_steps
        ↓
[4] 同步到 8008
        ↓
[5] mark_report_processed
```

**问题点**：
- ❌ **H2 修复未生效**：用 `threading.Thread` 而非 `create_daemon_thread`
- ❌ **无 `is_shutting_down()` 检查**：进程退出时无法优雅停止
- ❌ **无重试上限**：失败会无限重试

---

## 三、CRITICAL 问题（5 项）

| # | 问题 | 严重度 | 证据 |
|---|------|--------|------|
| C1 | `core/config.py` 目录不存在 | 🔴 | `Test-Path` 返回 False |
| C2 | `_start_report_queue_worker` 死循环 | 🔴 | `app.py:2395` `while True` 无 `is_shutting_down()` |
| C3 | H2 修复未生效 | 🔴 | `app.py:2469` 用 `threading.Thread` 而非 `create_daemon_thread` |
| C4 | 注释引用不存在的文件 | 🔴 | `app.py:1849` "sync_bridge 已迁移到 main.py"，`main.py` 不存在 |
| C5 | 报工数据流跨库直查未修复 | 🔴 | `app.py:582-589` `get_steelbelt_cursor` |

## 四、HIGH 问题（5 项）

| # | 问题 | 严重度 | 证据 |
|---|------|--------|------|
| H1 | 5008 不可用时，5002 直连入口未文档化 | 🟡 | 客户端可能仅知 5008 URL |
| H2 | 微信降级队列无重发 | 🟡 | `notify._fallback()` 仅落 sqlite |
| H3 | report_queue 失败无重试上限 | 🟡 | `mark_report_failed` 仅增计数 |
| H4 | 8008 启动失败时 app.py 仍启动 | 🟡 | `start_servers.bat` 无依赖顺序 |
| H5 | 配置分散在多个文件 | 🟡 | `core/config.py` + `app.py` 环境变量 + 5003 数据库配置 |

## 五、MEDIUM 问题（5 项）

| # | 问题 | 严重度 | 证据 |
|---|------|--------|------|
| M1 | 服务间调用超时分散（2s/3s/5s/10s/15s/30s） | 🟢 | 各处 timeout 不统一 |
| M2 | 无统一的服务注册/发现 | 🟢 | 硬编码 URL |
| M3 | 无统一的请求 ID（trace_id） | 🟢 | 难追踪跨服务调用 |
| M4 | 无统一的服务健康检查聚合 | 🟢 | 各服务 `/health` 独立 |
| M5 | `start_servers.bat` 无失败重试 | 🟢 | 任一服务启动失败不会感知 |

---

## 六、关键路径分析

### 6.1 主路径：手机报工

| 步骤 | 服务 | 风险 | SPOF |
|------|------|------|------|
| 1. 手机端 | - | - | - |
| 2. 5008 app.py | 5008 | 中 | 5008 |
| 3. container_center 5002 | 5002 | 中 | 5002 |
| 4. 8008 sync_bridge | 8008 | 中 | 8008 |
| 5. steel_belt DB | DB | 高 | DB |

**SPOF 数**：5 个
**平均延迟**：~80ms（合理）
**可用性**：4 个 9（5 个 9 × 99% 单点）

### 6.2 主路径：物料确认

| 步骤 | 服务 | 风险 |
|------|------|------|
| 1. 手机端 | - | - |
| 2. 5008 (代理) | 5008 | 中 |
| 3. 5002 (实现) | 5002 | 中 |
| 4. container_center DB | DB | 高 |

**链长**：2 次 HTTP 跳转
**延迟**：~40-60ms（2x 50ms）

---

## 七、风险评估

### 7.1 业务流程完整性

| 流程 | 完整性 | 缺失环节 |
|------|--------|----------|
| 报工提交 | 95% | 8008 失败补偿 |
| 物料确认 | 90% | 5008 不可用时降级 |
| 状态变更 | 85% | 失败重试 |
| 微信通知 | 80% | 5003 失败重发 |
| 数据同步 | 70% | outbox 队列 |

### 7.2 降级能力

| 服务 | 降级方式 | 完备度 |
|------|----------|--------|
| 5008 | 502/503 + 前端降级 UI | 🟡 部分 |
| 5002 | 5008 代理，5002 直连 | 🟢 OK |
| 8008 | outbox 队列 | 🔴 未实施 |
| 5003 | 降级到本地队列 | 🟡 无重发 |

---

## 八、审计评分

| 维度 | 评分 | 评语 |
|------|------|------|
| 1. 整体架构 | 16/20 | 服务划分清晰，依赖关系明确 |
| 2. 数据流 | 12/20 | 报工流 OK，物料/微信有优化空间 |
| 3. 控制流 | 14/20 | 业务流程闭环，但有循环依赖风险 |
| 4. 关键路径 | 18/20 | 主路径清晰 |
| 5. SPOF 识别 | 8/20 | **5 个 SPOF 仍存在** |
| 6. 错误恢复 | 10/20 | 降级不完整 |
| 7. 性能瓶颈 | 14/20 | 同步 HTTP 2x 开销 |
| 8. 一致性 | 12/20 | 跨库直查未完全解决 |
| **总分** | **104/160（65%）** | **未通过** |

---

## 九、修复优先级

| 优先级 | 项 | 工作量 | 风险 |
|--------|-----|--------|------|
| **P0** | 修复 `core/config.py` 缺失 | 1h | 高 |
| **P0** | 修复 `_start_report_queue_worker` 死循环 | 30min | 中 |
| **P0** | H2 修复在 app.py 中的 worker 线程 | 15min | 低 |
| **P0** | 修正 `main.py` 注释 | 5min | 低 |
| **P0** | 报工数据流去除跨库直查 | 1h | 中 |
| P1 | 8008 启动依赖检查 | 30min | 低 |
| P1 | 微信降级重发机制 | 2h | 中 |
| P1 | outbox 队列实施 | 4h | 高 |
| P2 | 服务注册/发现 | 8h | 中 |
| P2 | 统一 trace_id | 4h | 低 |
| P2 | 统一超时 | 2h | 低 |

---

## 十、参考

- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md)
- [DAL_DESIGN.md](./DAL_DESIGN.md)
- [FALLBACK.md](./FALLBACK.md)
- [THREAD_LIFECYCLE.md](./THREAD_LIFECYCLE.md)
- [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md)
- [API_DUPLICATES.md](./API_DUPLICATES.md)
