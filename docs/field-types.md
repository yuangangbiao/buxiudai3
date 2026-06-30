# 字段类型系统

> 版本: v1.0
> 创建时间: 2026-06-15
> 适用范围: 不锈钢网带跟单3.0项目

---

## 概述

本项目使用**两套并行的类型字段**：
- `product_type`（业务侧，中文）
- `flow_type`（技术侧，英文）

两套字段**职责独立、正交共存**，通过分类器保持一致。

---

## 一、字段定义

### 1.1 product_type（产品类型）

**位置**：`process_records.product_type`

**含义**：工单的业务分类（产品/物料类型）

**值**：
| 值 | 含义 |
|----|------|
| `不锈钢网带` | 主生产产品 |
| `不锈钢丝` | 主生产产品 |
| `物料` | 物料采购 |
| `质检委托` | 质检 |
| `设备维修` | 设备报修 |

**使用方**：
- 前端订单列表筛选
- 业务报表
- 销售/客户对接

### 1.2 flow_type（流程类型）

**位置**：`process_records.flow_type`

**含义**：工单走哪个流程模板（流程引擎识别）

**值**：
| 值 | 含义 |
|----|------|
| `production` | 生产流程 |
| `material_purchase` | 物料采购流程 |
| `quality` | 质检流程 |
| `repair` | 设备维修流程 |

**使用方**：
- `match_flow_type()` 函数
- 流程模板加载
- 通知/消息推送分支
- 工序编排

---

## 二、两者的关系

| product_type | flow_type |
|--------------|-----------|
| 不锈钢网带 | production |
| 不锈钢丝 | production |
| 物料 | material_purchase |
| 质检委托 | quality |
| 设备维修 | repair |

**对照关系通过 `core.process_code_classifier.classify_process_codes()` 维护。**

---

## 三、process_code 编号体系

`process_sub_steps.process_code` 是工序的**编号**，由**桌面端主软件**在发布任务时根据业务路径自动添加，用于：
1. 推断该工序的 **product_type**（产品类型）
2. 推断该工序的 **flow_type**（流程类型）
3. 区分任务的**任务类型**（不是流程类型！）

> ⚠️ **重要说明**：process_code 的生成是**路径对应添加**，不是根据名称判断。桌面端发布任务时会根据工序的业务路径添加对应编号。

### 3.1 编号规则（分类推断）

| 规则 | 归类 | 任务类型 (data_type) |
|------|------|----------------------|
| `P` 开头 | 生产 | process_report（工序报工） |
| `M` 开头 | 物料 | material_request（物料请求） |
| `Q` 开头 | 质检 | quality_task（质检任务） |
| `X` / `OUTSOURCE` / `WX` / `OS-` 开头 | 外协 | outsource_task（外协任务） |
| `STOCK_IN` / `IN` | 入库 | warehousing（入库流程） |
| `PX*` / `P_CS` | 忽略 | 动态/测试工序 |
| `N/A` / `DBG` / `TEST*` | 忽略 | 测试/调试 |
| `None` / 空 | 忽略 | 未分类 |

### 3.2 当前已识别的编号

| 编号 | step_name | product_type | flow_type |
|------|-----------|--------------|-----------|
| P01 | 原材料准备 | 不锈钢网带 | production |
| P02 | 焊接眼镜网 | 不锈钢网带 | production |
| P03 | 激光切板 | 不锈钢网带 | production |
| P04 | 链板冲压孔 | 不锈钢网带 | production |
| P05 | 链板冲压成型 | 不锈钢网带 | production |
| P06 | 编制左旋 | 不锈钢网带 | production |
| P07 | 编制右旋 | 不锈钢网带 | production |
| P08 | 穿曲轴 | 不锈钢网带 | production |
| P09 | 输送带组装穿杆 | 不锈钢网带 | production |
| P10 | 安装链条 | 不锈钢网带 | production |
| P11 | 安装裙边 | 不锈钢网带 | production |
| P12 | 整形校直 | 不锈钢网带 | production |
| P13 | 焊接输送带 | 不锈钢网带 | production |
| P14 | 表面处理 | 不锈钢网带 | production |
| P15 | 质量检验 | 不锈钢网带 | production |
| P16 | 包装入库 | 不锈钢网带 | production |
| M01 | 备料 | 物料 | material_purchase |
| Q01 | 质检 | 质检委托 | quality |
| X01 | 外协 | 外协加工 | outsource |
| P_CS | 测试 | - | (忽略) |
| STOCK_IN | 入库 | 不锈钢网带 | warehousing |
| PX* | 动态工序 | - | (忽略) |
| N/A | 测试/调试 | - | (忽略) |

---

## 四、使用场景速查

### 4.1 业务方使用 product_type

```python
# 前端筛选
if order.product_type === '不锈钢网带':
    # 显示生产相关按钮
    pass

# 报表统计
report = db.query(
    "SELECT product_type, COUNT(*) FROM process_records GROUP BY product_type"
)
```

### 4.2 技术方使用 flow_type

```python
# 流程引擎分支
if work_order.flow_type == 'production':
    template = load_template('production_v1')
elif work_order.flow_type == 'material_purchase':
    template = load_template('material_purchase_v1')

# 通知推送
send_wechat(notify_channel[work_order.flow_type], message)
```

### 4.3 工序任务窗口过滤

```python
from core.process_code_classifier import is_production_code

# 工序任务窗口只显示生产类工序
process_tasks = [t for t in sub_steps if is_production_code(t.process_code)]
```

---

## 五、如何新增 process_code

### 5.1 命名规则自动归类

新增 P17 / P18 / M02 / Q01 等编号时，**无需修改配置**：
- 分类器会根据命名规则自动归类
- 工单创建时会自动推断 product_type 和 flow_type

### 5.2 命名规则表

| 编号 | 自动归类 | 备注 |
|------|----------|------|
| `M01` | 物料 | M开头 |
| `M02` | 物料 | 新增自动归类 |
| `P17` | 生产 | P开头 |
| `P18` | 生产 | 新增自动归类 |
| `Q01` | 质检 | Q开头 |
| `STOCK_OUT` | 入库 | 包含STOCK |
| `IN` | 入库 | 等于IN |
| `PX...` | 忽略 | PX开头视为测试 |
| `TEST01` | 忽略 | TEST开头视为测试 |
| `None`/空 | 忽略 | 未分类 |

### 5.3 异常情况处理

如果新增的编号归类错误：
1. **不要修改分类器**（保持命名规则的简洁）
2. 在数据库中**手动**修改该工序的 process_code
3. 或在调用分类器前**手动指定**

---

## 六、核心模块

### 6.1 分类器位置

- 模块：[`mobile_api_ai/core/process_code_classifier.py`](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/core/process_code_classifier.py)
- 主要函数：
  - `infer_product_type_from_code(code: str) -> Optional[str]`
  - `infer_flow_type_from_code(code: str) -> Optional[str]`
  - `classify_process_codes(codes: List[str]) -> Dict[str, str]`
  - `is_production_code(code: str) -> bool`
  - `is_material_code(code: str) -> bool`
  - `is_quality_code(code: str) -> bool`
  - `is_warehousing_code(code: str) -> bool`

### 6.2 单元测试

- 测试位置：`tests/unit/core/test_process_code_classifier.py`
- 运行命令：`pytest tests/unit/core/test_process_code_classifier.py -v`

---

## 七、变更记录

| 日期 | 变更 | 作者 |
|------|------|------|
| 2026-06-15 | 初始化字段类型系统文档 | AI助手 |
| 2026-06-15 | 创建 process_code 分类器 | AI助手 |
| 2026-06-15 | 创建单元测试 | AI助手 |

---

**最后更新**: 2026-06-15
**维护人**: AI助手
