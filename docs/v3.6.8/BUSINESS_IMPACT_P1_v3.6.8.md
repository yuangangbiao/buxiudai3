# 业务影响报告 - v3.6.8 P1 修复（11 项全）

## 1. 用户场景对比

> 改善前（痛点） → 改善后（价值）表格

| # | 用户角色 | 改善前（痛点） | 改善后（价值）|
|---|---------|---------------|---------------|
| 1 | **车间班组长**（桌面端物料编辑） | 系统自动计算的物料 `locked=1`，无法编辑补全，依赖管理员解锁 | 新物料自动 `locked=0`，班组长可直接编辑（解锁按钮仍保留作应急用）|
| 2 | **车间班组长**（报工纠错 reset） | 报工误操作后 reset 只清状态，**completed_qty 残留**导致下次累计错误 | reset 同时清零 completed_qty/qualified_qty/work_hours，状态干净 |
| 3 | **操作员**（误删物料/质检/发货）| DELETE 物理删除，找不回来，**审计追溯链断裂** | 软删除（`is_deleted=1`），可恢复，审计完整（R-113 合规）|
| 4 | **车间班组长**（并发编辑物料）| SELECT-then-UPDATE 间被另一事务锁死，**TOCTOU 越权编辑** | `SELECT ... FOR UPDATE` 行级锁，并发安全 |
| 5 | **SRE 运维**（健康检查）| `/health` 返回静态 `success`，**DB 挂掉也显示正常** | `/health` 真连 DB 验证，DB 故障时返回 503 + 错误信息 |
| 6 | **API 调用方**（报工超大数据）| 报工 `quantity: 1e100` 静默失败或异常崩溃 | 报工数量上限 1e6，超限返回 400 + 中文错误 |
| 7 | **生产操作员**（输入客户名）| 输入 `'  ABC  '`（前后空格）入库，查询匹配不到 | 字符串自动去前后空格 + 截断 200 字符 |
| 8 | **CI 工程师**（PR 质量门禁）| `cov-fail-under=10` 几乎所有 PR 都能通过，**覆盖率倒退无人察觉** | `cov-fail-under=80`，回归即阻断 |
| 9 | **CI 工程师**（5008 报工测试）| CI 只跑主项目，**mobile_api_ai 改完没有 CI 验证** | CI 加 mobile_api_ai 子目录测试，5003/5008 改动有质量保障 |
| 10 | **安全审计**（bandit 扫描）| `continue-on-error: true`，**安全漏洞被忽略** | 取消兜底，漏洞阻断 PR + 报告归档 30 天 |
| 11 | **生产工人**（outbox 监控）| outbox 积压无人知晓，**队列堵了才发现** | `get_outbox_stats()` 提供积压/死信统计，可纳入监控告警 |

## 2. 业务能力新增

> 按业务流分类

| 业务流 | 新增/优化功能 | 影响范围 |
|--------|--------------|---------|
| **物料管理** | 自动计算物料不再自动锁定（用户友好）| 系统计算生成的所有物料 |
| **物料管理** | 物料编辑并发安全（FOR UPDATE）| 物料编辑/补全 |
| **物料管理** | 物料软删除（is_deleted=1）| 物料删除 |
| **报工** | reset 清零 3 个累计字段 | 工序报工纠错 |
| **质检** | 软删除（is_deleted=1）| 质检记录删除 |
| **发货** | 软删除（is_deleted=1）| 发货记录删除 |
| **健康检查** | 5008 `/health` 真连 DB | 监控告警 |
| **输入校验** | 字符串长度 + 数值范围 + 去空格 | 订单/工序/报工 |
| **CI/CD** | 覆盖率门槛 80% + mobile_api_ai 子目录 + security 阻断 | 所有 PR |
| **跨库同步** | outbox 积压/死信监控统计 | outbox 表 |

## 3. 不变更部分

> 防回归保护清单

| # | 模块/功能 | 保护措施 | 验证方式 |
|---|----------|---------|---------|
| 1 | 5003 service token（X-API-Key + X-Dispatch-Token）| v3.6.5 已实现，本轮无变更 | 既有 _dispatch_auth_check 中间件测试 |
| 2 | 5001 CSRF 保护（60/60 变路由全覆盖）| 上一轮 P0 修复已完成 | `tests/scan_csrf.py` 已确认 |
| 3 | 5001 8 个高危接口的 admin 权限校验 | 上一轮 P0-C 修复已完成 | 既有装饰器测试 |
| 4 | 5008 outbox 兜底（P0-K）| 上一轮已完成 | `bridge/dispatch_center_sync.py:78-90` |
| 5 | 5003 死信告警（P0-M）| 上一轮已完成 | `notify.py: notify_sync_failed()` |
| 6 | package_exists 14 个 key（P1-5）| 6-23 已修复 | 既有单测覆盖 |
| 7 | 工序状态机白名单（P0-E）| 上一轮已完成 | `models/order.py: ALLOWED_ORDER_TRANSITIONS` |
| 8 | 工序 rowcount 检查（P0-D）| 上一轮已完成 | 既有单测覆盖 |
| 9 | 业务事务原子性 | save_process_sub_step_with_pkg_update 事务边界不变 | 既有单测覆盖 |
| 10 | 5003 调度中心协议 | `/api/dispatch-center/*` 接口契约不变 | 既有 5003 单测覆盖 |

## 4. 一句话总结

> 本次改动让不锈钢网带跟单系统的**物料/报工/软删除/输入校验/健康检查/CI 门禁**从"用户被锁定 / 累计错误 / 物理删除 / 异常崩溃 / 假健康 / 宽松 CI"变为"用户可编辑 / reset 干净 / 软删可恢复 / 边界防护 / 真连 DB / 80% 覆盖 + 阻断"，**11 项 P1 风险全部堵住**。

---

## 附：变更影响范围

### 文件变更清单
1. `desktop_web/server.py` — P1-1, P1-2, P1-3(3处), P1-4 共 6 处代码修改
2. `mobile_api_ai/app.py` — P1-6 health 接口加 DB ping
3. `mobile_api_ai/outbox_writer.py` — P1-10 新增 `get_outbox_stats()` 函数
4. `utils/validators.py` — P1-8 OrderValidator + ProcessValidator 补全
5. `.github/workflows/ci.yml` — P1-11 升级 + mobile_api_ai 测试 + security 阻断

### 调用方影响
- 前端无需改动（透明修复）
- 5008 health 调用方：DB 故障时 200 → 503，需监控方对接
- CI 工程师：下次 push 触发新版 CI（Python 3.11/3.12）

### 部署注意
- 无需数据库迁移（is_deleted 字段已存在，软删除自动回退硬删除）
- CI 升级到 Python 3.11/3.12，需要 GitHub Actions runner 默认支持
- `cov-fail-under=80` 会**首次**暴露低覆盖率模块，建议提前在本地跑一次 pytest 看报告
