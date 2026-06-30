# 业务流程驱动 E2E 测试设计方案

**版本**：v1.0
**日期**：2026-06-26
**状态**：📝 设计阶段
**目标读者**：开发、测试、PM

---

## 一、背景与目标

### 1.1 当前痛点

现有 E2E 测试（`tests/e2e/test_01_auth.py` ~ `test_11_metrics.py`）**按 API 层组织**，存在以下问题：

| 问题 | 影响 |
|------|------|
| 单文件覆盖单 API，无法跨流程 | 真实业务是发布→生产→发货的串联，单元化测试无法覆盖 |
| 跨服务（5001↔5003↔5008）联动弱 | 数据一致性靠 mock，缺乏真实校验 |
| 异常路径覆盖不足 | DB 状态、缓存状态、微信消息状态未联合验证 |
| UI 验证缺失 | 仅验证后端 API，不验证浏览器页面交互 |
| 数据库中间态不可见 | 关键步骤后无法断言"数据应该长这样" |

### 1.2 设计目标

建立**业务流程驱动**的端到端测试套件，与现有 API 层测试**互补并存**：

1. **完整主链路**：工单发布 → 7 步生产流程 → 发货全链路验证
2. **跨端点联动**：5001/5003/5008 多服务真实协同
3. **移动端报工**：扫码报工 + 状态回写
4. **调度中心回归**：派工→报工→缓存失效回写
5. **数据库看门狗**：关键节点中间态断言
6. **浏览器补充验证**：扫码、点击等 UI 交互场景

---

## 二、关键决策（已与用户确认）

| 决策点 | 选择 | 备注 |
|--------|------|------|
| **覆盖范围** | 完整主链路 + 跨端点 + 手机报工 + 调度回归 + DB 检测 | 第一批全覆盖 |
| **测试账号** | 苑岗彪（独立工厂账号） | 隔离生产数据 |
| **执行环境** | 本地开发环境 | 5002/5003/5010/5008 本地服务 |
| **Playwright 定位** | 补充验证（关键节点） | 仅在扫码/微信点击使用 |
| **组织方式** | 新建 `tests/e2e/business_flows/` | 不动现有 test_01~11 |
| **隔离策略** | 独立账号 + E2E_ 前缀工单号 | 测试后清理 |

---

## 三、架构设计

### 3.1 整体架构

```
tests/e2e/
├── conftest.py                          ← 现有（不动）
├── test_01_auth.py ~ test_11_metrics.py ← 现有（不动）
├── test_flows.py                        ← 现有（不动）
│
└── business_flows/                      ← 【新增】业务流程驱动测试
    ├── __init__.py                      ← 空标记
    ├── conftest.py                      ← 业务流专用 fixture
    ├── _helpers.py                      ← 业务流工具（DB 看门狗、断言）
    ├── _playwright_helpers.py           ← Playwright UI 辅助
    │
    ├── test_bf_01_main_chain.py         ← 完整主链路（8 步串联）
    ├── test_bf_02_mobile_report.py      ← 手机报工（含 Playwright）
    ├── test_bf_03_dispatch_regress.py   ← 调度中心回归
    ├── test_bf_04_cross_service.py      ← 跨端点联动
    └── test_bf_05_db_watchdog.py        ← DB 看门狗独立验证
```

### 3.2 文件职责

| 文件 | 职责 | 测试函数数预估 |
|------|------|--------------|
| `conftest.py` | 提供 `main_chain_session`（贯穿主链路的工单上下文）、`mobile_session`、`dispatcher_session`、`clean_e2e_orders` | - |
| `_helpers.py` | `assert_order_state`、`assert_process_step`、`assert_redis_cache`、`query_order_progress`、`cleanup_e2e_orders` | - |
| `_playwright_helpers.py` | `mobile_page_qr_scan`、`wechat_message_click`、`screenshot_after_step` | - |
| `test_bf_01_main_chain.py` | 完整 8 步主链路：发布→排产→物料→生产→质检→入库→完工→发货 | 1 个长链路 + 5 个断点 |
| `test_bf_02_mobile_report.py` | 扫码报工 API + Playwright 扫码 UI + 状态回写 | 3 个 |
| `test_bf_03_dispatch_regress.py` | 派工接口、报工回写、缓存失效、状态机白名单 | 6 个 |
| `test_bf_04_cross_service.py` | 5001 创建订单 → 5003 同步 → 5008 报工 → 5001 状态查询 | 4 个 |
| `test_bf_05_db_watchdog.py` | DB 中间态断言：orders/process_steps/tasks 三表一致性 | 8 个 |

**总计**：约 27 个测试函数 + 1 个主链路长测试

---

## 四、核心设计

### 4.1 工单上下文 fixture（步骤链模式）

主链路测试用**单工单贯穿**，每步推进后做断言：

```python
# business_flows/conftest.py

@pytest.fixture
def main_chain_session(db_session, login_as):
    """主链路测试上下文 - 单工单贯穿 8 步"""
    # 1. 准备：苑岗彪账号登录、生成 E2E_ 前缀工单号
    session = login_as('苑岗彪', role='dispatcher')
    order_no = generate_e2e_order_no()  # E2E-YYYYMMDD-NNNN

    yield {
        'order_no': order_no,
        'session': session,
        'db': db_session,
        'progress': {
            'published': False,
            'scheduled': False,
            'material_ready': False,
            'in_production': False,
            'qc_required': False,
            'warehoused': False,
            'completed': False,
            'shipped': False,
        },
    }

    # 2. 清理：测试后删除 E2E_ 前缀订单
    cleanup_e2e_orders(order_no)
```

### 4.2 主链路测试结构（步骤链模式）

```python
# business_flows/test_bf_01_main_chain.py

class TestMainChain:
    """完整主链路 - 8 步串联"""

    def test_01_publish(self, main_chain_session):
        """Step 1: 工单发布"""
        # POST /api/workorder/publish
        # DB 断言：orders 表状态=published, processes 表有 7 步骤
        # 缓存断言：dispatch_center 缓存有这条工单

    def test_02_schedule(self, main_chain_session):
        """Step 2: 排产确认（需确认步骤）"""
        # POST /api/process/advance + 微信确认回复模拟
        # DB 断言：scheduled_steps 有记录

    def test_03_material_ready(self, main_chain_session):
        """Step 3: 物料准备"""
        # POST /api/material/confirm
        # DB 断言：material_ready=true, material_records 有数据

    def test_04_production(self, main_chain_session):
        """Step 4: 生产加工"""
        # POST /api/production/start
        # DB 断言：in_production=true, tasks 有进度

    def test_05_qc(self, main_chain_session):
        """Step 5: 质量检验（含 Playwright 移动端报工）"""
        # POST /api/qc/submit
        # DB 断言：qc_required=true, qc_records 有数据

    def test_06_warehouse(self, main_chain_session):
        """Step 6: 成品入库"""
        # POST /api/inventory/warehousing
        # DB 断言：warehoused=true, inventory_quantity 增加

    def test_07_complete(self, main_chain_session):
        """Step 7: 完工确认"""
        # POST /api/order/complete
        # DB 断言：completed=true, dispatch_center 缓存清理

    def test_08_ship(self, main_chain_session):
        """Step 8: 发货"""
        # POST /api/shipment/create
        # DB 断言：shipped=true, 订单不可再修改
```

### 4.3 DB 看门狗（独立测试）

DB 看门狗提供**关键节点的中间态断言**，与主链路测试**互补**（即便主链路挂了，DB 看门狗还能给出更精细的失败定位）：

```python
# business_flows/_helpers.py

class DBWatchdog:
    """数据库看门狗 - 关键节点数据一致性验证"""

    def assert_order_consistency(self, order_no):
        """订单表 + 缓存 + 调度中心三方一致"""
        # orders 表 status
        # container_center 缓存
        # dispatch_center 缓存

    def assert_process_step_state(self, order_no, step_name, expected_status):
        """工序步骤状态机断言"""
        # process_steps 表 status_key

    def assert_material_records(self, order_no, min_count=1):
        """物料记录完整性"""
        # material_records 表 count

    def assert_qc_records(self, order_no, expected_result):
        """质检记录断言"""
        # qc_records 表 result

    def assert_inventory_delta(self, order_no, expected_delta):
        """库存变化断言"""
        # inventory_quantity 变化值
```

### 4.4 Playwright 补充验证

```python
# business_flows/_playwright_helpers.py

@pytest.fixture(scope="session")
def mobile_browser():
    """移动端浏览器 session"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        yield browser
        browser.close()


def mobile_qr_scan(page, order_no, process_name, qty):
    """模拟扫码报工 UI 操作"""
    # 1. 打开 5008 移动端页面
    # 2. 输入工单号
    # 3. 选择工序
    # 4. 输入数量
    # 5. 提交
    # 6. 截图保存
    pass


def wechat_message_click(card_id):
    """模拟点击微信通知卡片"""
    pass
```

### 4.5 跨端点测试设计

```python
# business_flows/test_bf_04_cross_service.py

class TestCrossService:
    """跨端点联动测试 - 真实协同"""

    def test_order_5001_to_5003_sync(self, db_session):
        """5001 创建订单 → 5003 自动同步（≤5秒）"""
        # 1. POST 5001 /api/orders
        # 2. 轮询 5003 /api/dispatch-center/orders 检查是否同步
        # 3. DB 断言：两库数据一致

    def test_dispatch_5003_to_mobile_5008(self, db_session):
        """5003 派工 → 5008 操作员看到任务"""
        # 1. POST 5003 /api/dispatch-center/distribute
        # 2. GET 5008 /api/mobile/tasks 查询
        # 3. 断言任务出现

    def test_mobile_5008_report_back_to_5001(self, db_session):
        """5008 报工 → 5001 订单进度更新"""
        # 1. POST 5008 /api/mobile/report
        # 2. GET 5001 /api/orders/{id}/progress
        # 3. 断言进度已更新
```

---

## 五、关键依赖与基础设施

### 5.1 复用现有基础设施

| 组件 | 路径 | 用途 |
|------|------|------|
| `tests/conftest.py` | 全局 fixture | `db_session`、`login_as`、`screenshot_on_failure` |
| `tests/e2e/conftest.py` | e2e fixture | `e2e_client`、`e2e_dispatcher_client`、`e2e_mobile_client` |
| `tests/core/api_client.py` | API 客户端 | APIClient 类（desktop_web/dispatch/mobile） |

### 5.2 新增依赖

| 依赖 | 用途 | 来源 |
|------|------|------|
| `playwright` | 浏览器自动化 | requirements.txt 已包含 |
| `pymysql` | DB 直接查询 | 已有 |
| `redis` | 缓存验证 | 已有 |

### 5.3 数据隔离机制

```python
# 工单号前缀：E2E-YYYYMMDD-NNNN
# 操作员：苑岗彪
# 客户：E2E_TEST_CUSTOMER
# 物料：E2E_TEST_MATERIAL
# 测试后清理策略：
#   1. 软删除（is_deleted=1）核心业务表
#   2. 物理删除 E2E_ 前缀临时表记录
#   3. 清理 dispatch_center 缓存
```

---

## 六、执行策略

### 6.1 测试命令

```bash
# 全部业务流程测试
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/ -v

# 单个流程
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/test_bf_01_main_chain.py -v

# 调试模式（带截图）
& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" -m pytest tests/e2e/business_flows/ -v --headed --screenshot=on
```

### 6.2 服务启动前置

| 服务 | 端口 | 启动命令 |
|------|------|---------|
| 5002 移动端 | 5002 | `python mobile_api_ai/app.py` |
| 5003 调度中心 | 5003 | `python standalone_dispatch_server.py` |
| 5001 Web 端 | 5001 | `python desktop_api_server.py` |
| 5010 库存 | 5010 | `python inventory_api_server.py` |
| MySQL | 3306 | 服务中 |

### 6.3 CI 集成

| CI 阶段 | 命令 | 目的 |
|---------|------|------|
| Pre-merge | `pytest tests/e2e/business_flows/ -v --timeout=300` | PR 校验 |
| Nightly | `pytest tests/e2e/ -v --timeout=600` | 每日全量 |
| Release | `pytest tests/ -v --timeout=900` | 发布前 |

---

## 七、风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 数据库中间态被前序测试污染 | 🔴 高 | 独立账号 + E2E_ 前缀 + 清理 fixture |
| 跨服务启动顺序依赖 | 🟡 中 | conftest 提供 `wait_for_services` fixture |
| 微信消息 mock 不真实 | 🟡 中 | Playwright 直接操作企业微信页面（5008 移动端） |
| 长链路测试失败定位难 | 🟡 中 | DB 看门狗独立测试 + 步骤级断言 |
| 苑岗彪账号数据冲突 | 🔴 高 | 单独建表隔离 OR 测试前清空该账号数据 |

---

## 八、验收标准

### 8.1 功能验收

- [ ] 5 个测试文件创建完成
- [ ] 27+ 测试函数全部可执行
- [ ] 主链路 8 步串联测试通过
- [ ] DB 看门狗独立测试通过
- [ ] Playwright 扫码报工 UI 验证通过
- [ ] 跨端点联动测试通过

### 8.2 质量验收

- [ ] 测试后清理生效（DB 无残留）
- [ ] 失败有清晰错误信息 + 截图
- [ ] 测试时间 < 5 分钟（不含 Playwright 启动）
- [ ] 与现有 test_01~11 互不干扰

### 8.3 文档验收

- [ ] 每个测试函数有 docstring 说明业务含义
- [ ] 测试报告自动生成（pytest-html）
- [ ] 测试用例覆盖矩阵更新

---

## 九、实施计划

| 阶段 | 任务 | 产出 |
|------|------|------|
| Phase 1 | 创建 conftest.py + _helpers.py + _playwright_helpers.py | 基础设施 |
| Phase 2 | 实现 test_bf_01_main_chain.py（8 步） | 主链路 |
| Phase 3 | 实现 test_bf_02_mobile_report.py（含 Playwright） | 移动端 |
| Phase 4 | 实现 test_bf_03_dispatch_regress.py | 调度回归 |
| Phase 5 | 实现 test_bf_04_cross_service.py | 跨端点 |
| Phase 6 | 实现 test_bf_05_db_watchdog.py | DB 看门狗 |
| Phase 7 | 集成测试 + CI 集成 + 文档 | 交付 |

---

## 十、参考资料

| 文档 | 路径 |
|------|------|
| 业务流程图 | `docs/系统业务流程图.md` |
| 现有 E2E 测试计划 | `docs/E2E测试计划_20260623.md` |
| 测试污染审计 | `docs/TEST_POLLUTION_AUDIT_v3.8.1.md` |
| 项目架构约束 | `.trae/rules/project_rules.md` |
| 6A 工作流规则 | `.trae/rules/6A工作流项目规则.md` |
| Flask 开发规范 | `.trae/rules/Flask开发规范.md` |

---

## 附录 A：测试用例覆盖矩阵

| 业务流程 | API 端点 | DB 表 | 缓存 | 微信 | UI |
|---------|---------|-------|------|------|-----|
| 主链路发布 | /api/workorder/publish | orders, processes | dispatch_cache | ✅ | - |
| 排产确认 | /api/process/advance | process_steps | - | ✅ | - |
| 物料准备 | /api/material/confirm | material_records | - | ✅ | - |
| 生产加工 | /api/production/start | tasks, task_progress | - | - | - |
| 质量检验 | /api/qc/submit | qc_records | - | - | - |
| 成品入库 | /api/inventory/warehousing | inventory | - | - | - |
| 完工确认 | /api/order/complete | orders | dispatch_cache | ✅ | - |
| 发货 | /api/shipment/create | shipments, orders | - | - | - |
| 移动报工 | /api/mobile/report | tasks, task_progress | - | - | ✅ |
| 跨端点 | /api/orders, /api/dispatch-center/*, /api/mobile/* | 跨库 | - | - | - |

---

**文档结束**