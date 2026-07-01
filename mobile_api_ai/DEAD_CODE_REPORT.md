# 死代码扫描报告 (F6 P9 2026-06-10)

> **扫描工具**: vulture 2.x + 自写 AST 扫描 + 自写 import 图分析
> **扫描范围**: `mobile_api_ai/` 顶级目录, 排除 `tests/`, `__pre_tests__/`, `scripts/`, `logs/`, `docs/`, `.sandbox_pkgs/`, `__pycache__/`, `_migration_backups/`
> **扫描时间**: 2026-06-10
> **全量文件**: 235 个 .py (排除 sandbox/deploy/tests)
> **总代码量**: 估计 ~150000 行

---

## ⚠️ 重要说明

本报告**仅基于静态分析**——所有标记项**需人工确认**。原因：
1. vulture 80% confidence 仍可能有误报（动态调用、字符串 import）
2. 死文件检测只看 `import` 引用，**不包含** `setup.py entry_points` / `pytest conftest` / `Flask 注册` 等动态加载
3. 死路由 308 个**几乎全是误报**（被前端/小程序/外部系统调用，不走 Python 内部 requests）

---

## 1. 死文件（22 个 / 92.1 KB / 9.4% 占比）

按文件大小排序，前 10：

| 文件 | 大小 | 估算行数 | 可能原因 |
|------|------|---------|---------|
| [api/swagger.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/swagger.py) | 16.4 KB | 327 | Swagger 文档生成, v3.5 引入未启用 |
| [api_validators.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api_validators.py) | 10.5 KB | 209 | API 验证器, v3.5 引入未启用 |
| [api/process_v2.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/process_v2.py) | 8.5 KB | 169 | 工艺 V2 重构未启用 |
| [db_transaction.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/db_transaction.py) | 8.1 KB | 161 | 事务装饰器, 已被 v4.0 替代 |
| [dispatch_center/_core_types.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core_types.py) | 7.6 KB | 152 | 类型定义, 已移至 _core.py |
| [dispatch_center/_constants.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_constants.py) | 7.2 KB | 143 | 常量, 可能被 .env 替代 |
| [migrations/0610_data_packages_flow_type.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/migrations/0610_data_packages_flow_type.py) | 6.2 KB | 123 | 一次性迁移脚本, 未集成到迁移框架 |
| [services/flow_type_alert.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/services/flow_type_alert.py) | 5.8 KB | 116 | flow_type 告警服务, 已被 v4.0 替代 |
| [services/speech_recognition.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/services/speech_recognition.py) | 4.8 KB | 95 | 语音识别, 缺 API key 未启用 |
| [migrations/0609_work_order_history.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/migrations/0609_work_order_history.py) | 4.5 KB | 90 | 同上 |

**合计**: 22 个文件 / **92.1 KB** / 约 **1900 行代码**

完整 22 个文件清单见扫描器输出 [._scan_1b_dead_files.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/_scan_1b_dead_files.py)

---

## 2. 死 import / 死变量 / 死代码块 (vulture 检测, ~20 项)

### 2.1 unused import（10 个）

| 文件:行 | 内容 |
|---------|------|
| [api/legacy_routes.py:16](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L16) | `SHORT_TIMEOUT` 未用 |
| [api/quality_inspection.py:10](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/quality_inspection.py#L10) | `QualityRuleDAO` 未用 |
| [dispatch_center/_core.py:23](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L23) | `CARD_GROUPS` 未用 |
| [dispatch_center/_core.py:23](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L23) | `classify_payloads` 未用 |
| [dispatch_center/_core.py:23](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L23) | `LEGACY_TO_NEW` 未用 |
| [dispatch_center/_core.py:23](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L23) | `NEW_DATA_TYPES` 未用 |
| [inventory_api_server.py:67](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_api_server.py#L67) | `_secrets` 未用 |
| [inventory_web/db_utils.py:19](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/db_utils.py#L19) | `InvalidOperation` 未用 |
| [log_rotation.py:22](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/log_rotation.py#L22) | `TimedRotatingFileHandler` 未用 |
| [models/database.py:5](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/models/database.py#L5) | `PooledConnection` 未用 |

**清理收益**: 删 10 行 import, **0 风险**（unused = 删了不影响）

### 2.2 unused variable（8 个）

| 文件:行 | 内容 |
|---------|------|
| [cache.py:217](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/cache.py#L217) | `exc_tb` except 捕获后未用 |
| [container_center_api.py:2566](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py#L2566) | `product_type_id` 局部变量未用 |
| [container_center_client.py:140](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_client.py#L140) | `queue_max_size` |
| [container_center_client.py:905](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_client.py#L905) | `exc_tb` |
| [db_transaction.py:67](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/db_transaction.py#L67) | `exc_tb` |
| [db_transaction.py:245](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/db_transaction.py#L245) | `exc_tb` |
| [log_rotation.py:32](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/log_rotation.py#L32) | `date_format` |
| [metrics.py:169](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/metrics.py#L169) | `exc_tb` |

### 2.3 unreachable code（2 个）

| 文件:行 | 内容 |
|---------|------|
| [container_center_client.py:191](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_client.py#L191) | `else` 永远不可达 |
| [dispatch_center/schedule_routes.py:1073](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/schedule_routes.py#L1073) | `return` 后还有代码 |

### 2.4 unsatisfiable ternary（1 个）

| 文件:行 | 内容 |
|---------|------|
| [scripts/diag_500_traceback.py:45](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/scripts/diag_500_traceback.py#L45) | 三元判断永远为假 |

---

## 3. 死路由（308 个）—— ⚠️ 误报率高

| 扫到路由总数 | 481 个 |
|------|------|
| "未在 Python 内部调用" | 308 个 |
| **真实死路由（可能）** | **< 30 个** |

**为什么 308 个几乎全是误报**：
- 这些 API 路由被**前端 H5 / 小程序 / 外部企微**调用，不走 Python `requests.get`
- 扫描器只查 Python 内部 `requests.get('URL')` 模式

**真死的可疑路由**（需人工确认）：
- `data_collector_api.py` 的 `/collect/*` 路径（共 6 个）—— 容器中心 collect 接口可能没对接
- `sync_bp.py:469 /task/<order_no>/status` —— 同步桥接状态查询
- `wechat_work_bot_bp.py:549/568 /app/hook` —— 企微回调，可能有但用得少

**建议**：与前端/小程序开发对账，**不要轻易删路由**

---

## 4. 业务功能级死代码（粗估）

| 类型 | 估计数 | 备注 |
|------|------|------|
| 整个未启用的功能模块 | 3-5 个 | Swagger、SpeechRecognition、auto_advance、process_v2 |
| 旧版本的兼容实现 | 5-10 个 | v3.5 合并的 v4.0 兼容代码 |
| 一次性脚本（已在 _migration_backups）| 10+ | 已备份，不算"死" |
| F16 阶段的临时修补 | 5-8 个 | F15/F16/T16.1 注释里提到 |

**估计死代码总量**:
- 死文件: 92.1 KB / 1900 行
- 死函数/类/变量: ~30 项 / ~100 行
- 业务模块级: 5-10 个 / 1000-3000 行
- **总计**: 3000-5000 行 / 占项目 2-3%

---

## 5. 建议清理优先级

| 优先级 | 行动 | 风险 | 收益 |
|:----:|------|:---:|:---:|
| 🟢 1 | 删 10 个 unused import | 极低 | 小 |
| 🟢 2 | 删 8 个 unused variable | 低 | 小 |
| 🟢 3 | 修 2 个 unreachable code | 低 | 中（可读性）|
| 🟡 4 | 确认 22 个死文件 | 中 | 大（92 KB）|
| 🔴 5 | 确认 308 个死路由 | 高 | 不明（前端可能用）|
| 🔴 6 | 删"业务模块级"死代码 | 高 | 需 DBA/产品/前端确认 |

---

## 6. 工具/脚本（可复用）

| 脚本 | 用途 |
|------|------|
| [._scan_1b_dead_files.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/_scan_1b_dead_files.py) | 死文件检测 (grep-based) |
| [._scan_3_dead_routes.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/_scan_3_dead_routes.py) | 死路由检测 (Python 内部调用对照) |
| `vulture` CLI | 死 import/变量/unreachable |

---

## 7. 总结

| 指标 | 数据 | 置信度 |
|------|------|:----:|
| 全量 .py 文件 | 235 个 | 🟢 100% |
| **死文件** | **22 个** / 92.1 KB / 9.4% | 🟢 高 |
| 死 import/variable/代码块 | ~20 项 | 🟡 中（vulture 80%）|
| 死路由 | 308 个（**误报多**）| 🔴 低 |
| **真实业务死代码** | **3000-5000 行** | 🟡 估计 |
| **建议立即清理** | ~20 项小修 + 22 个文件确认 | — |

**下一步建议**：
1. 立即清理：~20 项 unused import/variable（风险极低）
2. 排期清理：22 个死文件确认（建议逐个 review）
3. 不建议：308 个"死路由"——可能被前端调用
