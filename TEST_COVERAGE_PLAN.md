# 测试覆盖率提升计划

**目标**: 将测试覆盖率从 **10-15%** 提升到 **70%**

**生成时间**: 2026-06-15

---

## 一、当前覆盖率现状

### 1.1 模块级统计

| 模块 | 可测试项数 | 现有测试用例 | 覆盖率估算 | 目标覆盖率 |
|------|-----------|-------------|-----------|-----------|
| **core** | 194 | ~300 | ~15% | 70% |
| **models** | 416 | ~500 | ~12% | 70% |
| **services** | 105 | ~150 | ~14% | 70% |
| **utils** | 354 | ~400 | ~11% | 70% |
| **总计** | **1069** | **~1350** | **~12%** | **70%** |

### 1.2 需要补充的测试量

| 指标 | 数值 |
|------|------|
| 总可测试项 | 1069 |
| 目标覆盖(70%) | 749 |
| 现有覆盖 | ~135 |
| **需要补充覆盖** | **~614** |

---

## 二、模块级详细计划

### 2.1 CORE 模块 (目标: +20%)

**当前状态**: ~15%
**目标**: +20% → 总计35%

#### 优先级1: 高频使用的核心函数

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `db.py` | `get_connection()` | 单元测试 | P0 |
| `db.py` | `get_connection_context()` | 单元测试 | P0 |
| `db.py` | `reload_db_config()` | 单元测试 | P1 |
| `event_bus.py` | `publish()` | 单元测试 | P0 |
| `event_bus.py` | `subscribe()` | 单元测试 | P0 |
| `event_bus.py` | `EventBus.__init__()` | 单元测试 | P1 |
| `config.py` | `get_config()` | 单元测试 | P1 |
| `config.py` | `reload()` | 单元测试 | P2 |

#### 优先级2: 错误处理和边界情况

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `error_handler.py` | `handle_error()` | 单元测试 | P0 |
| `error_handler.py` | `log_error()` | 单元测试 | P1 |
| `exceptions.py` | `自定义异常类` | 单元测试 | P1 |
| `circuit_breaker.py` | `call()` | 单元测试 | P1 |

#### 优先级3: 工具函数

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `logger.py` | `get_logger()` | 单元测试 | P1 |
| `logger.py` | `StructuredLogger` | 单元测试 | P2 |
| `metrics.py` | `record_metric()` | 单元测试 | P2 |

**CORE模块补充目标**: +40项测试用例

---

### 2.2 MODELS 模块 (目标: +25%)

**当前状态**: ~12%
**目标**: +25% → 总计37%

#### 优先级1: 核心DAO

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `order.py` | `create()` | 单元测试 | P0 |
| `order.py` | `update()` | 单元测试 | P0 |
| `order.py` | `get_by_id()` | 单元测试 | P0 |
| `process.py` | `create()` | 单元测试 | P0 |
| `process.py` | `update_record()` | 单元测试 | P0 |
| `quality.py` | `create()` | 单元测试 | P0 |
| `quality.py` | `confirm_order_completion()` | 单元测试 | P0 |

#### 优先级2: 业务逻辑

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `production.py` | `create()` | 单元测试 | P1 |
| `production.py` | `update_status()` | 单元测试 | P1 |
| `production.py` | `confirm_schedule()` | 单元测试 | P1 |
| `shipment.py` | `create()` | 单元测试 | P1 |
| `shipment.py` | `confirm_ship()` | 单元测试 | P1 |
| `inventory.py` | `adjust_stock()` | 单元测试 | P1 |

#### 优先级3: 辅助功能

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `material_rules.py` | `get_rules()` | 单元测试 | P2 |
| `quality_rule.py` | `get_all()` | 单元测试 | P2 |
| `process_calc_rule.py` | `calculate_planned_qty()` | 单元测试 | P2 |
| `operation_log.py` | `create()` | 单元测试 | P2 |

**MODELS模块补充目标**: +100项测试用例

---

### 2.3 SERVICES 模块 (目标: +25%)

**当前状态**: ~14%
**目标**: +25% → 总计39%

#### 优先级1: 核心服务

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `order_service.py` | `create_order()` | 单元测试 | P0 |
| `order_service.py` | `update_order()` | 单元测试 | P0 |
| `order_service.py` | `change_status()` | 单元测试 | P0 |
| `process_service.py` | `report_progress()` | 单元测试 | P0 |
| `process_service.py` | `update_record()` | 单元测试 | P0 |

#### 优先级2: 调度和通知

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `schedule_dispatch_service.py` | `publish_schedule()` | 单元测试 | P1 |
| `inventory_notifier.py` | `notify_material_prepared()` | 单元测试 | P1 |
| `wechat_report_service.py` | `publish_task_to_operator()` | 单元测试 | P1 |

#### 优先级3: 审计和日志

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `audit_service.py` | `log()` | 单元测试 | P2 |
| `audit_service.py` | `get_logs()` | 单元测试 | P2 |

**SERVICES模块补充目标**: +50项测试用例

---

### 2.4 UTILS 模块 (目标: +20%)

**当前状态**: ~11%
**目标**: +20% → 总计31%

#### 优先级1: 核心工具

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `validators.py` | `validate_*()` | 单元测试 | P0 |
| `helpers.py` | `validate_*()` | 单元测试 | P0 |
| `helpers.py` | `format_*()` | 单元测试 | P0 |

#### 优先级2: 业务工具

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `material_calculator.py` | `calculate_material_types()` | 单元测试 | P1 |
| `excel_utils.py` | `export_*()` | 单元测试 | P1 |
| `excel_utils.py` | `import_*()` | 单元测试 | P1 |
| `pagination.py` | `paginate()` | 单元测试 | P1 |

#### 优先级3: 辅助功能

| 文件 | 函数 | 测试类型 | 优先级 |
|------|------|---------|--------|
| `query_cache.py` | `get_cached_result()` | 单元测试 | P2 |
| `logistics_tracker.py` | `track()` | 单元测试 | P2 |
| `settings_manager.py` | `get_*()` | 单元测试 | P2 |

**UTILS模块补充目标**: +70项测试用例

---

## 三、实施计划

### 阶段1: 核心模块 (P0优先) - 预计3天

**目标**: 覆盖所有P0优先级测试用例

#### Day 1: CORE模块
- [ ] `db.py` - 连接管理测试 (10项)
- [ ] `event_bus.py` - 事件总线测试 (15项)
- [ ] `error_handler.py` - 错误处理测试 (10项)

#### Day 2: MODELS模块
- [ ] `order.py` - 订单DAO测试 (20项)
- [ ] `process.py` - 工序DAO测试 (15项)

#### Day 3: SERVICES + UTILS模块
- [ ] `order_service.py` - 订单服务测试 (15项)
- [ ] `process_service.py` - 工序服务测试 (15项)
- [ ] `validators.py` - 验证器测试 (20项)

**阶段1目标**: +105项测试用例

---

### 阶段2: 业务模块 - 预计5天

**目标**: 覆盖所有P1优先级测试用例

#### Day 4-5: MODELS模块扩展
- [ ] `quality.py` - 质检DAO测试 (15项)
- [ ] `production.py` - 生产DAO测试 (15项)
- [ ] `shipment.py` - 发货DAO测试 (15项)

#### Day 6-7: SERVICES模块扩展
- [ ] `schedule_dispatch_service.py` - 调度服务测试 (15项)
- [ ] `inventory_notifier.py` - 库存通知测试 (10项)
- [ ] `wechat_report_service.py` - 微信报表测试 (10项)

#### Day 8: UTILS模块扩展
- [ ] `helpers.py` - 辅助函数测试 (20项)
- [ ] `excel_utils.py` - Excel工具测试 (15项)

**阶段2目标**: +115项测试用例

---

### 阶段3: 边界和集成 - 预计3天

**目标**: 覆盖边界情况和集成测试

#### Day 9-10: 边界情况
- [ ] 所有模块的错误处理测试
- [ ] 所有模块的空值处理测试
- [ ] 所有模块的边界条件测试

#### Day 11: 集成测试
- [ ] 订单完整流程测试
- [ ] 报工完整流程测试
- [ ] 发货完整流程测试

**阶段3目标**: +80项测试用例

---

## 四、测试用例模板

### 4.1 单元测试模板

```python
# tests/unit/models/test_order.py
import pytest
from unittest.mock import patch, MagicMock

class TestOrderDAO:
    """OrderDAO 单元测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置mock环境"""
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        with patch('models.order.get_connection', return_value=self.mock_conn):
            from models.order import OrderDAO
            self.dao = OrderDAO()

    def test_create_order_success(self):
        """测试创建订单成功"""
        # Arrange
        self.mock_cursor.lastrowid = 1
        order_data = {
            'product_name': '测试产品',
            'quantity': 100
        }

        # Act
        result = self.dao.create(order_data)

        # Assert
        assert result == 1
        self.mock_conn.commit.assert_called_once()

    def test_create_order_with_invalid_data(self):
        """测试创建订单失败 - 无效数据"""
        # Arrange
        invalid_data = {'product_name': ''}

        # Act & Assert
        with pytest.raises(ValueError):
            self.dao.create(invalid_data)
```

### 4.2 边界测试模板

```python
def test_order_create_with_null_quantity(self):
    """测试创建订单 - 数量为null"""
    with patch('models.order.get_connection'):
        from models.order import OrderDAO
        dao = OrderDAO()
        with pytest.raises(ValueError, match="quantity不能为空"):
            dao.create({'product_name': 'test', 'quantity': None})

def test_order_create_with_zero_quantity(self):
    """测试创建订单 - 数量为0"""
    with patch('models.order.get_connection'):
        from models.order import OrderDAO
        dao = OrderDAO()
        with pytest.raises(ValueError, match="quantity必须大于0"):
            dao.create({'product_name': 'test', 'quantity': 0})

def test_order_create_with_negative_quantity(self):
    """测试创建订单 - 数量为负数"""
    with patch('models.order.get_connection'):
        from models.order import OrderDAO
        dao = OrderDAO()
        with pytest.raises(ValueError, match="quantity必须大于0"):
            dao.create({'product_name': 'test', 'quantity': -1})
```

---

## 五、质量标准

### 5.1 测试命名规范

```
test_{模块}_{功能}_{场景}
```

示例：
- `test_order_create_success`
- `test_order_create_with_null_quantity`
- `test_order_update_status_to_completed`

### 5.2 测试覆盖要求

| 测试类型 | 覆盖率要求 |
|---------|-----------|
| 正常流程 | 100% |
| 边界条件 | 90% |
| 异常处理 | 80% |
| 空值处理 | 90% |

### 5.3 测试质量检查清单

- [ ] 每个测试用例有清晰的docstring
- [ ] 使用有意义的断言消息
- [ ] 测试之间相互独立
- [ ] 测试覆盖正向和负向场景
- [ ] Mock外部依赖

---

## 六、验证方法

### 6.1 运行覆盖率测试

```bash
# 完整覆盖率测试
pytest tests/unit/ \
    --cov=core \
    --cov=models \
    --cov=services \
    --cov=utils \
    --cov-report=term-missing \
    --cov-report=html

# 单模块覆盖率
pytest tests/unit/core/ --cov=core --cov-report=term-missing
```

### 6.2 覆盖率目标检查

| 阶段 | 目标覆盖率 | 检查时间 |
|------|-----------|---------|
| 阶段1完成 | 20% | Day 3后 |
| 阶段2完成 | 40% | Day 8后 |
| 阶段3完成 | 55% | Day 11后 |
| 优化后 | 70% | Day 15后 |

---

## 七、风险和缓解

### 7.1 风险1: 测试执行时间过长

**缓解措施**:
- 使用pytest-xdist并行执行
- 按模块分组执行
- 标记慢速测试为@pytest.mark.slow

### 7.2 风险2: Mock过于复杂

**缓解措施**:
- 使用conftest.py共享fixture
- 创建mock辅助函数
- 必要时使用真实数据库

### 7.3 风险3: 依赖外部服务

**缓解措施**:
- Mock所有外部API调用
- 使用pytest-mock
- 标记外部依赖测试为@pytest.mark.integration

---

## 八、进度跟踪

### 当前进度

| 模块 | 目标 | 当前 | 进度 |
|------|------|------|------|
| core | 135 | 29 | 21.5% |
| models | 291 | 50 | 17.2% |
| services | 74 | 15 | 20.3% |
| utils | 248 | 39 | 15.7% |
| **总计** | **748** | **133** | **17.8%** |

---

## 九、下一步行动

1. **确认计划**: 请确认此计划是否符合预期
2. **优先级调整**: 如有需要调整优先级
3. **开始实施**: 确认后我将开始实施阶段1

请回复确认后，我将开始实施测试补充工作。
