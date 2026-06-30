# TODO v3.7.1 - 后续待办

> **创建日期**: 2026-06-25
> **关联版本**: v3.7.1
> **来源**: v3.7.0 遗留事项

---

## 一、立即待办（v3.7.1 启动前）

### 1.1 业务代码 Q-B（v3.6.4 决议 + v3.7.0 遗留）

| # | 任务 | 文件 | 工作量 | 操作指引 |
|---|------|------|:------:|----------|
| 1 | 真正删除 desktop_container_integration.py | 根目录 | 1天 | 迁移 7 个引用方到 dispatch_center.*_publisher |
| 2 | 清理剩余 40 处裸异常日志 | `dispatch_center/_core.py` | 2h | `sed` 或人工替换 `logger.error(f'...{e}')` → `logger.exception('...')` |
| 3 | 统一 `/sync/xxx` 路径风格 | 1.6 节文档 + 相关代码 | 2h | 路径改为 `/api/dispatch-center/sync/xxx` |
| 4 | 修复 R-001 违规（直连库） | `models/order.py` 跨库 JOIN | 1天 | 重构为 API 调用 + TODO 注释 |

### 1.2 DLQ retry worker 增强

| # | 任务 | 工作量 | 操作指引 |
|---|------|:------:|----------|
| 5 | DLQ retry 单元测试 | 2h | tests/unit/dispatch_center/test_dlq_retry.py |
| 6 | DLQ 监控指标 | 1h | 添加 metrics: queue_size, retry_rate, poison_count |
| 7 | DLQ 告警规则 | 1h | poison_count > 10 触发企业微信告警 |

---

## 二、v3.7.1 计划任务

### 2.1 完善 L 测试

| # | 任务 | 工作量 | 操作指引 |
|---|------|:------:|----------|
| 8 | L4 业务场景测试 | 5天 | test_emergency / test_multi_user / test_field_work |
| 9 | 已有 L2/L3 测试扩充 | 3天 | 5002/5003 视角的 L2 + L3 一致性测试 |
| 10 | L1 测试参数化 | 1天 | 同一测试支持多角色/多场景 |

### 2.2 性能与监控

| # | 任务 | 工作量 | 操作指引 |
|---|------|:------:|----------|
| 11 | 接入 Prometheus | 1周 | 安装 prometheus_client，5 个服务添加 metrics 端点 |
| 12 | Grafana 看板 | 3天 | dashboard.json + 订单/工序/质检核心指标 |
| 13 | 性能监控告警 | 2天 | CPU>80%、响应>2s、错误率>5% |

### 2.3 架构治理（高优先级）

| # | 任务 | 工作量 | 操作指引 |
|---|------|:------:|----------|
| 14 | 5 服务依赖图谱 | 2天 | mermaid 绘制，识别关键路径 |
| 15 | 测试优先级分级 | 1天 | critical/important/normal 标记 |
| 16 | 变更影响分析 | 1周 | PR 模板 + 自动识别受影响测试 |
| 17 | _core.py 拆分（高风险评估后决定） | 1月 | 9635 行 → 5 个文件 |

---

## 三、缺失配置

### 3.1 CI 环境变量（继承 v3.6.9）

| 变量名 | 状态 |
|--------|------|
| `MYSQL_TEST_PASSWORD` | 默认 123456，需接入密钥管理 |
| `WECHAT_CORP_ID` | 待申请 |
| `WECHAT_AGENT_ID` | 待申请 |
| `CLOUD_API_KEY` | 待申请 |

### 3.2 DLQ 表 schema 验证

| 项 | 状态 |
|----|------|
| `dlq` 表存在 | ✅ 已知存在 |
| `dlq.payload` 字段 | 需确认类型（VARCHAR/TEXT/JSON）|
| `dlq.retry_count` 字段 | 需确认存在 |
| `dlq.next_retry_at` 字段 | 需确认存在 |
| `dlq.status` 字段 | 需确认存在（含 'poisoned' 值）|
| `dlq.error_msg` 字段 | 需确认存在 |
| `dlq.updated_at` 字段 | 需确认存在 |

> ⚠️ 集成到 dispatch 中心前必须先核对 schema，不匹配需要 ALTER TABLE

### 3.3 浏览器（已就绪）

| 组件 | 状态 |
|------|------|
| Chromium | ✅ Playwright 自带 |
| Firefox | ⏳ 待安装 |
| WebKit | ⏳ 待安装 |

---

## 四、风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|:----:|----------|
| desktop_container_integration.py 删除引发崩溃 | 🔴 高 | 逐步迁移 7 引用方 + 保留 .bak 1 个月 |
| _core.py 拆分引入回归 | 🔴 高 | 评估后决定，本次不拆 |
| DLQ schema 不匹配 | 🟡 中 | 集成前先 DDL 验证 |
| 40 处裸异常日志遗漏 | 🟢 低 | 增量清理 |
| 5 服务全链路 e2e 缺失 | 🟡 中 | v3.7.2 计划 |

---

## 五、负责人分配

| 任务 | 负责人 |
|------|--------|
| 1.1.1-4 业务 Q-B | 小圣 + 小贺 |
| 1.2.5-7 DLQ 增强 | 小圣 + 小钰 |
| 2.1.8-10 L 测试 | 小贺 |
| 2.2.11-13 性能监控 | 小钰 + 小圣 |
| 2.3.14-17 架构治理 | 小圣 + 小曦 |

---

## 六、立即求助

如需技术支持：
- 测试框架 → @小贺（QA）
- 架构 → @小圣（架构）
- 业务理解 → @小曦（PM）
- 安全合规 → @小钰（安全）

---

**TODO 维护人**: AI 团队 | **更新周期**: 每周 | **最后更新**: 2026-06-25
