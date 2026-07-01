# TASK-T2: service 层抽象

## 输入契约

**前置依赖**：T1
**输入数据**：DESIGN v2.0 缺陷 2 中的接口签名
**环境依赖**：`inventory_web/db_utils.py` 已实现 `execute()`

## 输出契约

**输出数据**：6 个 service 文件
- `inventory_web/services/__init__.py`
- `inventory_web/services/product_service.py`
- `inventory_web/services/inventory_service.py`
- `inventory_web/services/stocktake_service.py`
- `inventory_web/services/transfer_service.py`
- `inventory_web/services/report_service.py`
- `inventory_web/services/notification_service.py`

**验收标准**：
- [ ] 每个 service 的方法签名与 DESIGN v2.0 完全一致
- [ ] 所有方法返回 `(http_code, payload)` 元组
- [ ] 不直接调用 `pymysql.connect()`，全部走 `execute()`
- [ ] 异常用 `logger.exception()` 记录，返回 5xx

## 实现约束

- **技术栈**：纯 Python（不引入新依赖）
- **接口规范**：见 DESIGN v2.0 缺陷 2
- **质量要求**：
  - 业务规则校验全部在 service 层
  - 不在 service 层做 HTTP 响应格式化
  - 不在 service 层做权限检查（保持单一职责）

## 依赖关系

**后置任务**：T3/T4/T5/T6/T7/T8
**并行任务**：无
