# ALIGNMENT — 云端去除调度中心功能

> 阶段 1: Align（对齐阶段）· 需求边界确认 + 共识文档
> 任务：云端去除调度中心业务功能（/api/sync/*），迁移到本地 5003 调度中心
> 创建时间：2026-06-08

---

## 一、项目与任务特性规范

### 1.1 项目特性

| 维度 | 现状 |
|------|------|
| 项目名 | 不锈钢网带跟单系统 3.0 |
| 技术栈 | Python 3.13 + Flask + MySQL（steel_belt）+ 容器中心 5002 + 8008 同步桥 |
| 服务端口 | 5000 桌面端 / 5002 容器中心 / **5003 调度中心** / 5008 报工 / 5009 人脸 / **8008 同步桥** / 15003 云端 wechat_server |
| 架构模式 | 多进程多服务，desktop launcher 启动一组进程 |
| 数据流 | 业务层调容器中心 SDK 改文档 → 容器中心 watcher 异步通过 8008 桥写 MySQL steel_belt |
| 业务定位 | **云端仅保留企业微信回调，业务能力下沉本地** |

### 1.2 任务特性

| 维度 | 说明 |
|------|------|
| 任务名 | 云端去除调度中心功能（云端 wechat_server.py 中 22 个 /api/sync/* 端点迁移到本地 5003） |
| 任务范围 | 16 个端点新增 + 3 蓝图注册 + 1 端点 8008 新增 + 1 规则更新 |
| 任务边界 | **不动容器中心 5002 / 不动桌面端 5000 / 不动 8008 同步桥已有 4 端点** |
| 不在范围 | 桌面端硬编码改 3 个真重复端点 URL（云端不删，仅 5003 提供等价） |

---

## 二、原始需求

> 用户原话：
> 1. "云端不在承担调度中心功能，把云端的这个功能去除"
> 2. "查询本地是否已有这些功能，把没有的列出来经同意后在加入，重复功能不在添加"
> 3. "5003 的 report/confirm 走 8008 桥，8008 加 /api/sync/report-confirm 端点 OK"

### 2.1 需求拆解

| 编号 | 需求 | 来源 |
|------|------|------|
| REQ-1 | 云端 wechat_server.py 不再承担业务 API（/api/sync/*） | 用户原话 #1 |
| REQ-2 | 业务能力迁移到本地 5003（standalone_dispatch_server.py） | 用户原话 #1 |
| REQ-3 | 重复功能不在本地添加（3 个真重复不迁移） | 用户原话 #2 |
| REQ-4 | report/confirm 走 8008 桥（不直写 MySQL） | 用户原话 #3 |
| REQ-5 | 8008 同步桥加 /api/sync/report-confirm 端点 | 用户原话 #3 |
| REQ-6 | F1 修复（operation_logs.direction）由云端负责 | 用户选择 |
| REQ-7 | 完整 6A 工作流（Align → Architect → Atomize → Approve → Automate → Assess） | 用户选择 |

---

## 三、需求边界（明确任务范围）

### 3.1 任务范围内（In-Scope）

#### A. 新增到 5003 的 16 个端点（新建 sync_bp 蓝图）

| 端点 | 实现路径 | F1 依赖 |
|------|----------|---------|
| POST /api/sync/report | 调容器中心 SDK .update_document('work_order', ...) | ❌ |
| POST /api/sync/report/actual | 调容器中心 SDK .update_document() | ❌ |
| POST /api/sync/outsource/publish | 调容器中心 SDK .create_document('outsource', ...) | ❌ |
| POST /api/sync/delivery-date-change | 调容器中心 SDK .update_document() | ❌ |
| POST /api/sync/validate/input | 5003 内存正则 `^ORD-\d{8,}$` | ❌ |
| GET /api/sync/task/<order>/status | 5003 读容器中心 + 读 MySQL | ✅ |
| GET /api/sync/tasks/<id> | 5003 读容器中心 | ❌ |
| POST /api/sync/drift/check | 5003 内存比对 | ❌ |
| POST /api/sync/data/fingerprint | 5003 内存 SHA256 | ❌ |
| GET /api/sync/circuit/status | 5003 内存 _CircuitBreaker | ❌ |
| POST /api/sync/circuit/reset | 5003 内存 _CircuitBreaker.reset() | ❌ |
| GET /api/sync/queue/status | 5003 读内存队列 | ❌ |
| GET /api/sync/queue/stats | 5003 读内存队列 | ❌ |
| GET /api/sync/reports | 5003 走 sync_client.send 读 8008 队列 + 直读 MySQL | ✅ |
| GET /api/sync/logs | 5003 直读 MySQL operation_logs | ✅ |
| GET /api/sync/report/requests | 5003 直读 MySQL report_request | ✅ |
| POST /api/sync/report/confirm | **5003 调 8008 /api/sync/report-confirm**（走桥） | ✅ |

#### B. 补注册蓝图到 standalone_dispatch_server.py

| 蓝图 | url_prefix | 行数 |
|------|-----------|------|
| schedule_bp | /api/schedule/* | 9 端点 |
| workorder_bp | /api/workorder/* | 1 端点 |
| sync_bp（新建）| /api/sync/* | 16 端点 |

#### C. 8008 同步桥新增 1 端点

| 端点 | 用途 |
|------|------|
| POST /api/sync/report-confirm | 报工确认收口，入队后写 MySQL report_request 表 |

#### D. 规则更新

- 更新 [wechat_server_cloud_only.md](file:///D:/yuan/.trae/rules/wechat_server_cloud_only.md)：允许本地改动 wechat_server.py 做迁移（**不删，只拆分**）

### 3.2 任务范围外（Out-of-Scope）

| 不做项 | 原因 |
|--------|------|
| 删除 wechat_server.py 中 /api/sync/* 代码 | 用户未要求删除（云端继续跑 15003 兼容，只是新业务走 5003） |
| 改桌面端 5000 调 URL | 桌面端不调 15003 /api/sync/*（实测 0 调用方） |
| 改容器中心 5002 任何代码 | 业务规则不变（容器中心仍接收 5003 / 8008 的调用） |
| 改 8008 同步桥已有 4 端点 | 不动 sub-step-report / status-change / quality-report / sync-process |
| 修云端 F1（direction 列） | 用户选择"先建端点，F1 云端修" |
| 修云端 F2（订单号正则） | 用户选择"先建端点，本地按正确正则写，不动云端" |
| 修云端 F3（Content-Type） | 用户选择"先建端点，本地按正确 Content-Type 写" |
| 改云端 3 个真重复端点 | 保留云端兼容（15003 仍可访问），5003 提供等价 |

### 3.3 3 个真重复端点（按"重复不在添加"原则不迁移）

| 云端 15003 端点 | 本地 5003 等价 |
|----------------|---------------|
| GET /api/sync/tasks | GET /api/dispatch-center/tasks |
| GET /api/sync/status | GET /api/dispatch-center/status |
| GET /api/sync/health/detailed | GET /api/schedule/health（补注册后可用） |
| GET /api/sync/task/<order>/status | GET /api/schedule/status/<order_no>（补注册后可用） |

---

## 四、需求理解（对现有项目的理解）

### 4.1 现有架构（已实地验证）

```
┌─────────────────────────────────────────────────────────────┐
│  桌面端 5000  ─→  容器中心 5002  ─→  8008 同步桥  ─→  MySQL  │
│         │              │                  │              │
│         ↓              ↓                  ↓              │
│    (业务操作)     (文档+包存储)    (异步落库)         (steel_belt)│
│                                                              │
│  调度中心 5003  ─→  容器中心 5002 (复用 SDK 客户端)        │
│         │                                                    │
│         ↓                                                    │
│    (任务分发/排产/调度)                                        │
│                                                              │
│  云端 15003  ─→  容器中心 5002 (另一 SDK 客户端)            │
│         │                                                    │
│         ↓                                                    │
│    (企业微信回调 + 业务 /api/sync/*)                          │
│    ⚠️ 现状：业务下沉后云端只留回调                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 关键数据流（报工举例）

```
5003 /api/sync/report (新增)
    ↓ 调容器中心 SDK
容器中心 5002 .update_document('work_order', task_id, {...})
    ↓ 容器中心自身触发
容器中心 5002 /api/process_sub_step (报工审核端点)
    ↓ 异步 thread
8008 /api/sync/sub-step-report (8008 已有)
    ↓ _enqueue_sync() 入队
队列 worker 消费 → _sync_quality_to_mysql()
    ↓
MySQL steel_belt.process_sub_steps ✓
```

### 4.3 关键代码引用

| 模块 | 文件 | 行 |
|------|------|-----|
| 容器中心 watcher | [container_center_api.py:2250-2262](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/container_center_api.py#L2250-L2262) | 异步通知 8008 桥 |
| 8008 同步桥 | [sync_bridge.py:362-402](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/sync_bridge.py#L362-L402) | sub-step-report 实现 |
| 8008 入口 | [bridge/sync_client.py:1-19](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/bridge/sync_client.py) | 8008 桥统一调用 |
| 5003 入口 | [standalone_dispatch_server.py:1-170](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/standalone_dispatch_server.py) | 调度中心 Flask |
| 15003 入口 | [wechat_server.py:1-100](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/wechat_server.py) | 云端 Flask |

---

## 五、疑问澄清

### 5.1 已澄清（已解决）

| 问题 | 答案 |
|------|------|
| 云端去除哪些功能？ | 22 个 /api/sync/* 业务 API（云端保留兼容，5003 提供新入口） |
| 承接方？ | standalone_dispatch_server.py (5003) |
| 规则冲突？ | 用户授权更新 wechat_server_cloud_only.md |
| 重复功能处理？ | 3 个真重复不迁移，让调用方改打 5003 等价端点 |
| 16 个端点是否冲突？ | HTTP 0 冲突 / 业务逻辑 0 冲突 / 类命名 0 冲突 |
| 桌面端影响？ | 0 影响（实测 0 调用方） |
| 走 8008 桥 vs 直写 MySQL？ | 业务操作类（report/publish/...）调容器中心 SDK；数据落库类（report/confirm）走 8008 桥；读类（reports/logs）直读 MySQL |
| F1 修复时机？ | 云端负责，本地先建端点 |
| 开发模式？ | 完整 6A 流程 |
| 不加哪些？ | POST /api/sync/report/wechat（云端微信回调专用） |

### 5.2 不确定（待云端修复后确认）

| 问题 | 缓解措施 |
|------|----------|
| 云端 F1 修复时机 | 本地端点先建，跑通时标 500，告知云端修 |
| 云端 F2 修复时机 | 本地按正确正则 `^ORD-\d{8,}$` 写，15003 旧正则保留兼容 |
| 云端 F3 修复时机 | 本地按正确 Content-Type 写（先 try JSON，再 try form） |

---

## 六、验收标准（测试用例可执行）

### 6.1 功能验收

| ID | 验收项 | 通过条件 |
|----|--------|---------|
| AC-1 | 16 端点全部注册到 5003 | `conflict_check.py` 改写为 `register_check.py`，逐个 GET/POST，**全部 200/400/405**（非 404） |
| AC-2 | 补注册 schedule_bp / workorder_bp | scan_5003.py 扫到 9 + 1 个新端点，**全部 200/400/405** |
| AC-3 | sync_bp 注册 | scan_5003.py 扫到 16 个 /api/sync/* 端点 |
| AC-4 | 8008 /api/sync/report-confirm 可用 | 8008 进程里 POST 返 200 |
| AC-5 | report/confirm 走 8008 桥 | 5003 report/confirm 内部不直写 MySQL，调 sync_client.send() |
| AC-6 | report/actual/outsource/delivery-date 调容器中心 SDK | 函数体含 `_get_container_center()` 或 SDK 客户端调用 |
| AC-7 | validate/input 正确性 | 输入 `ORD-202605020001` 返 200，`invalid_xxx` 返 400 |
| AC-8 | circuit/queue 内存单例 | 多次请求返回同一 status（id 一致） |
| AC-9 | drift/fingerprint 计算正确 | 同输入同输出（SHA256 一致） |
| AC-10 | F1 依赖的 6 端点（标 ✅）正确报 500 | F1 修复前返 `{code: 500, message: 'Unknown column direction'}`，**不返 404** |

### 6.2 文档验收

| ID | 验收项 | 通过条件 |
|----|--------|---------|
| AC-11 | 4 文档齐备 | ALIGNMENT + CONSENSUS + DESIGN + TASK 全部存在且非空 |
| AC-12 | 规则更新 | wechat_server_cloud_only.md 含"允许本地改动做迁移"段落 |
| AC-13 | 函数级注释 | sync_bp.py 中 16 个端点函数全部含 docstring + 参数说明 + 返回值说明 |
| AC-14 | 同步到构想文件 | d:\yuan\构想文件\云端去除调度中心功能\ 下有 4 份文档副本 |

### 6.3 架构验收

| ID | 验收项 | 通过条件 |
|----|--------|---------|
| AC-15 | 桌面端 0 改动 | desktop_container_integration.py 文件不变（diff 为空） |
| AC-16 | 容器中心 0 改动 | container_center_api.py 文件不变（diff 为空） |
| AC-17 | 8008 已有 4 端点不变 | sync_bridge.py 中 sub-step-report / status-change / quality-report / sync-process 函数不变 |
| AC-18 | 重复 3 端点不在 5003 注册 | 5003 无 /api/sync/tasks（无 status）/api/sync/status/api/sync/health/detailed |

---

## 七、风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| F1 修复前 6 端点报 500 | 中 | 端点骨架先建，错误信息明确指向 F1，云端修后自动恢复 |
| 业务操作类（report/actual）调容器中心 SDK 失败 | 中 | 容器中心 5002 仍是单点，需保证 5002 启动 |
| 8008 同步桥队列积压 | 低 | 8008 已有队列 worker，无需新加 |
| 容器中心 5002 watcher 时延 | 低 | 容器中心 2250-2262 已有异步 thread，无新增压力 |
| 16 端点代码量较大 | 中 | 拆分到 16 个独立函数 + 完整注释 |
| 规则更新影响其他模块 | 低 | 仅 1 文件改动（wechat_server_cloud_only.md） |

---

## 八、达成共识

本对齐文档需经用户确认后，进入阶段 2 (Architect) 生成 DESIGN 文档。
