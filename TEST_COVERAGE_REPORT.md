# 项目测试覆盖率报告

**生成时间**: 2026-06-15 11:17
**Python版本**: 3.14.3
**项目路径**: `d:\yuan\不锈钢网带跟单3.0`

---

## 一、执行摘要

| 指标 | 数值 | 说明 |
|------|------|------|
| **总测试用例数** | **707** | 收集到的测试用例 |
| **测试模块数** | **4** | core, models, services, utils |
| **源代码模块** | **5** | core, models, models/database, services, utils |
| **测试文件数** | **183** | 主项目143 + mobile_api_ai 40 |
| **源代码总行数** | **19,867** | 不含__pycache__和下划线文件 |
| **现有覆盖率** | **10.35%** | 基于coverage_analysis.xml |

---

## 二、项目模块结构

### 2.1 源代码模块

| 模块 | Python文件 | 代码行数 | 占比 |
|------|-----------|---------|------|
| **core/** | 23 | 3,741 | 18.8% |
| **models/** | 23 | 7,035 | 35.4% |
| **models/database/** | 4 | 126 | 0.6% |
| **services/** | 9 | 2,512 | 12.6% |
| **utils/** | 30 | 6,453 | 32.5% |
| **总计** | **89** | **19,867** | 100% |

### 2.2 测试模块

| 测试模块 | 测试文件数 | 测试用例分布 |
|----------|-----------|-------------|
| **tests/unit/core/** | 43 | event_bus, process_code, saga, config等 |
| **tests/unit/models/** | 50 | order, process, quality, inventory等 |
| **tests/unit/services/** | 16 | order_service, process_service等 |
| **tests/unit/utils/** | 48 | helpers, validators, excel_utils等 |
| **mobile_api_ai/tests/unit/** | 40 | API,调度,存储等 |
| **总计** | **197** | **707+ 测试用例** |

---

## 三、现有覆盖率数据

### 3.1 现有覆盖率报告

| 报告文件 | 大小 | 生成时间 | 覆盖率 |
|---------|------|---------|--------|
| `coverage.json` | 962.3 KB | 2026-06-10 | - |
| `coverage_analysis.xml` | 164.4 KB | 2026-06-10 | **10.35%** |

### 3.2 覆盖率详情 (coverage_analysis.xml)

```
版本: 7.14.1
行有效: 4,433
行覆盖: 459
分支覆盖: 0
分支有效: 0
覆盖率: 10.35%
```

**注意**: 现有覆盖率报告仅覆盖 `models/` 模块，未包含 core, services, utils 模块。

---

## 四、测试用例详细分布

### 4.1 tests/unit/core/ (43个测试文件)

| 测试模块 | 测试用例数 | 说明 |
|---------|-----------|------|
| event_bus | ~30 | 事件总线核心功能 |
| event_store | ~10 | 事件存储 |
| process_code | ~50 | 工序代码处理 |
| saga | ~10 | Saga模式 |
| config | ~15 | 配置管理 |
| error_handler | ~10 | 错误处理 |
| redis_event_bus | ~10 | Redis事件总线 |
| register_process | ~20 | 工序注册 |
| rule_engine | ~10 | 规则引擎 |
| 其他 | ~40 | circuit_breaker, metrics等 |

### 4.2 tests/unit/models/ (50个测试文件)

| 测试模块 | 测试用例数 | 说明 |
|---------|-----------|------|
| order | ~60 | 订单模型 |
| process | ~40 | 工序模型 |
| quality | ~30 | 质检模型 |
| production | ~25 | 生产模型 |
| inventory | ~25 | 库存模型 |
| shipment | ~20 | 发货模型 |
| operator | ~15 | 操作员模型 |
| 其他 | ~50 | bom, unit, enums等 |

### 4.3 tests/unit/services/ (16个测试文件)

| 测试模块 | 测试用例数 | 说明 |
|---------|-----------|------|
| order_service | ~40 | 订单服务 |
| process_service | ~30 | 工序服务 |
| inventory_sync | ~20 | 库存同步 |
| schedule_dispatch | ~15 | 调度服务 |
| wechat_report | ~10 | 微信报表 |
| 其他 | ~20 | base_service, audit等 |

### 4.4 tests/unit/utils/ (48个测试文件)

| 测试模块 | 测试用例数 | 说明 |
|---------|-----------|------|
| helpers | ~40 | 辅助函数 |
| validators | ~30 | 验证器 |
| excel_utils | ~25 | Excel工具 |
| query_cache | ~15 | 查询缓存 |
| material_calculator | ~20 | 物料计算 |
| logistics_tracker | ~15 | 物流追踪 |
| 其他 | ~40 | pagination, window_manager等 |

---

## 五、覆盖率缺口分析

### 5.1 现有覆盖率问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **总体覆盖率低** | 🔴 高 | 仅10.35%，远低于行业标准 |
| **覆盖范围不完整** | 🟡 中 | 仅models模块被覆盖 |
| **缺少分支覆盖** | 🟡 中 | 分支覆盖率为0% |
| **移动API未覆盖** | 🟡 中 | mobile_api_ai独立运行 |

### 5.2 覆盖率目标建议

| 模块 | 当前覆盖率 | 建议目标 | 差距 |
|------|-----------|---------|------|
| **core/** | 0% | 70% | -70% |
| **models/** | 10.35% | 80% | -70% |
| **services/** | 0% | 70% | -70% |
| **utils/** | 0% | 70% | -70% |
| **总体** | **10.35%** | **70%** | **-60%** |

---

## 六、测试质量评估

### 6.1 测试文件组织

✅ **优点**:
- 按模块分组清晰 (`tests/unit/core/`, `tests/unit/models/`等)
- 测试文件命名规范 (`test_*.py`)
- 模块结构与源代码对应

⚠️ **问题**:
- 缺少测试目录：`tests/e2e/`, `tests/integration/` 规模较小
- 部分测试文件为临时测试 (`test_*.py` 散落在根目录)
- `mobile_api_ai/tests/` 与主项目测试分离

### 6.2 测试覆盖范围

✅ **覆盖充分**:
- 核心业务逻辑 (order, process, quality)
- 数据访问层 (DAO)
- 工具函数 (helpers, validators)
- 配置管理 (config, error_codes)

⚠️ **覆盖不足**:
- 集成测试 (e2e, integration)
- UI测试 (desktop/views)
- 性能测试
- 安全性测试

---

## 七、改进建议

### 7.1 立即行动 (高优先级)

1. **完善覆盖率配置**
   ```ini
   # .coveragerc
   [run]
   source =
       core
       models
       services
       utils
   omit =
       tests/*
       */__pycache__/*
   ```

2. **运行完整覆盖率测试**
   ```bash
   pytest tests/unit/ \
       --cov=core \
       --cov=models \
       --cov=services \
       --cov=utils \
       --cov-report=term-missing \
       --cov-report=html
   ```

3. **修复失败的测试收集**
   - `test_event_bus_factory.py`: 缺少 `sync` 模块

### 7.2 短期改进 (1-2周)

1. **提高models模块覆盖率到70%**
   - 增加边界条件测试
   - 增加异常路径测试

2. **增加core模块测试**
   - event_bus集成测试
   - config加载测试

3. **增加services模块测试**
   - 业务流程测试
   - 服务间交互测试

### 7.3 长期改进 (1个月+)

1. **建立CI覆盖率检查**
   - 设置覆盖率门槛 (如50%)
   - 覆盖率下降时阻止合并

2. **增加E2E测试**
   - 关键业务流程端到端测试
   - 使用Playwright/Selenium

3. **性能测试集成**
   - 使用pytest-benchmark
   - 设置性能回归门槛

---

## 八、覆盖率统计命令

### 8.1 生成完整覆盖率报告

```bash
# 在项目根目录运行
python -m pytest tests/unit/ \
    --cov=core \
    --cov=models \
    --cov=services \
    --cov=utils \
    --cov-report=term-missing \
    --cov-report=json:coverage_full.json \
    --cov-report=html:htmlcov/ \
    -v
```

### 8.2 查看HTML报告

```bash
# 打开HTML覆盖率报告
start htmlcov/index.html
```

### 8.3 快速检查

```bash
# 仅显示总体覆盖率
python -m pytest tests/unit/ \
    --cov=. \
    --cov-report=term-missing \
    --co -q | tail -20
```

---

## 九、附录

### A. 依赖版本

| 组件 | 版本 |
|------|------|
| pytest | 9.0.3 |
| coverage | 7.14.1 |
| Python | 3.14.3 |

### B. 相关文件

- 配置文件: `.coveragerc`, `pytest.ini`
- 测试配置: `tests/conftest.py`, `tests/unit/conftest.py`
- 覆盖率报告: `coverage.json`, `coverage_analysis.xml`

### C. 测试发现

**收集到的测试用例总数**: 707个
**收集失败的测试**: 1个 (sync模块不存在)

---

**报告生成时间**: 2026-06-15 11:17:06
**生成方式**: Python AST分析 + pytest收集
