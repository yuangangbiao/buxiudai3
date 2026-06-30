# 业务流程驱动 E2E 测试套件

> **版本**: v1.0
> **创建日期**: 2026-06-26
> **设计文档**: `docs/superpowers/specs/2026-06-26-e2e-business-flow-design.md`
> **实施计划**: `docs/superpowers/plans/2026-06-26-e2e-business-flow.md`

## 概述

业务流程驱动的端到端测试套件，与现有 API 层测试（test_01~11）**互补并存**。

- **现有测试**：`tests/e2e/test_01_auth.py ~ test_11_metrics.py` — 按 API 层组织
- **本套件**：`tests/e2e/business_flows/test_bf_01~05.py` — 按业务流程组织

## 覆盖范围

| 业务流程 | 文件 | 测试数 |
|---------|------|------:|
| 完整主链路（发布→7步→发货） | test_bf_01_main_chain.py | 9 |
| 移动端扫码报工（API + UI） | test_bf_02_mobile_report.py | 6 |
| 调度中心回归 | test_bf_03_dispatch_regress.py | 10 |
| 跨端点联动（5001↔5003↔5008） | test_bf_04_cross_service.py | 4 |
| DB 看门狗独立验证 | test_bf_05_db_watchdog.py | 9 |
| **合计** | 5 文件 | **38** |

## 文件结构

```
business_flows/
├── __init__.py                          # 空标记
├── conftest.py                          # 业务流专用 fixture
├── _helpers.py                          # DBWatchdog + 业务流工具
├── _playwright_helpers.py               # Playwright UI 辅助
├── test_bf_01_main_chain.py             # 完整主链路（8 步）
├── test_bf_02_mobile_report.py          # 手机报工
├── test_bf_03_dispatch_regress.py       # 调度回归
├── test_bf_04_cross_service.py          # 跨端点联动
├── test_bf_05_db_watchdog.py            # DB 看门狗独立验证
└── README.md                            # 本文档
```

## 核心设计

### 业务流专用 Fixture

| Fixture | 作用域 | 用途 |
|---------|-------|------|
| `wait_for_services` | session | 等待 5001/5003/5008/5010 服务就绪 |
| `main_chain_session` | function | 主链路测试上下文（单工单贯穿 8 步） |
| `mobile_session` | function | 移动端测试上下文（worker 角色） |
| `dispatcher_session` | function | 调度员测试上下文 |

### DBWatchdog 工具

`tests/e2e/business_flows/_helpers.py` 提供 7 类断言：

- **订单维度**：`assert_order_status` / `assert_order_consistency`
- **工序维度**：`assert_process_step_state` / `assert_process_steps_count`
- **物料维度**：`assert_material_records`
- **质检维度**：`assert_qc_records`
- **库存维度**：`assert_inventory_delta`
- **报工维度**：`assert_task_progress`

## 执行命令

```bash
# 全部业务流程测试
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/ -v

# 单个流程
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/test_bf_01_main_chain.py -v

# 调试模式（带截图）
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/ -v --headed --screenshot=on

# 仅收集（不执行）
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/ --collect-only -q
```

## 测试账号

| 字段 | 值 |
|------|-----|
| 操作员 | `苑岗彪` |
| 客户 | `E2E_TEST_CUSTOMER` |
| 物料前缀 | `E2E-MAT-` |
| 工单前缀 | `E2E-YYYYMMDD-NNN` |

## 前置依赖服务

| 服务 | 端口 | 健康检查 |
|------|------|---------|
| 5001 Web | 5001 | `GET /api/health` |
| 5003 调度中心 | 5003 | `GET /api/health` |
| 5008 移动端 | 5008 | `GET /api/health` |
| 5010 库存 | 5010 | `GET /api/health` |
| MySQL | 3306 | steel_belt 库 |
| Redis | 6379 | dispatch:order:* 缓存 |

## 数据清理机制

测试结束自动清理（`conftest.py::_cleanup_e2e_order`）：

- `orders` 表软删除（`is_deleted=1`）
- `process_steps` / `material_records` / `qc_records` / `shipments` 物理删除
- Redis 缓存清理（按需）

## 设计原则

1. **不污染生产数据**：E2E_ 前缀 + 苑岗彪独立账号 + 测试后清理
2. **环境容错**：服务不可用时 `pytest.skip()` 而非失败，避免环境差异
3. **断言分层**：核心服务（5003）严格断言，辅助服务容错
4. **DB 看门狗独立**：即便主链路失败，DB 看门狗也能给出精细定位
5. **Playwright 补充**：仅在扫码、点击等 UI 场景使用，不拖慢主测试

## CI 集成

| 阶段 | 命令 | 目的 |
|------|------|------|
| Pre-merge | `pytest tests/e2e/business_flows/ -v --timeout=300` | PR 校验 |
| Nightly | `pytest tests/e2e/ -v --timeout=600` | 每日全量 |
| Release | `pytest tests/ -v --timeout=900` | 发布前 |

## 已知限制

1. **主链路依赖步骤链**：单独跑 Step 2 会失败（需先完成 Step 1）
2. **企业微信环境复杂**：微信消息卡片点击为占位实现
3. **并发测试未覆盖**：当前为串行测试，并发安全需额外验证
4. **CI 中需先启动服务**：测试不会自动启动 5001/5003/5008

## 后续优化方向

- [ ] 增加并发场景测试（5 线程报工不超额）
- [ ] 增加性能基准测试（API 响应时间分布）
- [ ] 增加异常注入测试（DB 中断、服务降级）
- [ ] 集成 pytest-html 生成可视化报告
- [ ] 微信消息点击改为 mock 拦截而非真实浏览器