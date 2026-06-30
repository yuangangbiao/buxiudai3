# 工序计算引擎 — 独特设计解析

## 概述

本系统的工序计算引擎（`ProcessCalcEngine`）是整个桌面端最具独创性的模块之一。它实现了一套**可配置、产品类型感知、基于尺寸参数的工序自动生成与计划数量计算系统**，本质是一个**嵌入式领域特定语言（DSL）解析器 + 条件状态机**。

核心文件：[models/process_calc_rule.py](file:///d:/yuan/不锈钢网带跟单3.0/models/process_calc_rule.py)

---

## 一、设计三支柱

整个工序计算系统由三个独立又协作的子系统构成：

```
┌────────────────────────────────────────────────────────────┐
│                    ProcessCalcEngine                        │
│                                                           │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  条件匹配引擎      │  │  公式求值引擎  │  │  工序生成器   │ │
│  │  should_include   │  │  _calc_expr   │  │  generate_   │ │
│  │  _process()       │  │  evaluate_    │  │  processes_  │ │
│  │                   │  │  condition()  │  │  from_order()│ │
│  └──────────────────┘  └──────────────┘  └──────────────┘ │
│         │                      │                 │         │
│         ▼                      ▼                 ▼         │
│  产品类型筛选         数学表达式求值        批量工序创建     │
│  + 条件比较           + 占位符替换         + 序号分配      │
│  + AND/OR 组合        + 向上取整           + 缺失警告      │
└────────────────────────────────────────────────────────────┘
```

### 支柱 1：条件匹配引擎（决定"做不做"）

**独特设计：产品类型白名单 + 条件表达式双过滤**

```python
def should_include_process(process_name, order_data, rules):
    # 1. 从 process_calc_rules 表读取该工序的规则
    # 2. 检查 product_types_json（白名单），空=对所有类型生效
    # 3. 检查 condition_expr（尺寸条件表达式）
```

| 配置方式 | 示例 | 说明 |
|---------|------|------|
| **产品类型白名单** | `["编织网", "冲孔网"]` | 仅特定产品类型才创建该工序 |
| **条件表达式** | `宽度 > 1000` | 满足尺寸条件才创建（支持AND/OR） |
| **组合模式** | 白名单 + 条件 | 两个条件都过才创建 |

**关键差异点**：传统MES系统通常硬编码BOM路线，本系统采用**运行时规则匹配**——订单的"产品类型"和"尺寸参数"在录入时决定工序路线，而非预定义BOM结构。

### 支柱 2：公式求值引擎（决定"做多少"）

**独特设计：自研递归表达式解析器（零外部依赖）**

```python
@classmethod
def _calc_expr(cls, expr: str, data: dict) -> float:
    # 三步递归解析：
    # 1. 去括号：处理 (...) 括号
    # 2. 拆分二元运算符：优先处理 +/-, 然后 */ 
    # 3. 变量替换：{参数名} → data[参数名]。从 data 取值
```

**完整的运算符优先级**：
```
括号 → {变量} 替换 → + - → * /  → 数值/变量查值
                     (左结合)   (左结合)
```

这是不使用 `eval()`/`ast` 等Python内置执行函数的**纯手工递归下降解析器**，避免了安全风险，同时保持了对工业参数公式的完整支持。

### 支柱 3：工序生成器（决定"怎么排"）

**独特设计：订单驱动的动态工序清单生成**

```python
def generate_processes_from_order(order_data, all_processes):
    # 遍历全局工序列表 (PROCESSES)
    # 对每个工序调用 should_include_process() 判断
    # 符合条件的调用 calculate_planned_qty() 计算计划量
    # 收集结果 + 缺失参数警告 → 返回完整工序清单
```

---

## 二、物料相关计算的独特之处

### 2.1 物料种类数动态注入

```
{物料数量} 占位符引擎特殊处理
```

`_get_material_count(order_id)` 实时查询数据库 `order_materials` 表：

```python
SELECT COUNT(*) FROM order_materials WHERE order_id= %s AND required_qty > 0
```

**独特之处**：物料数量不是用户在界面填的，而是由公式引擎从数据库实时拉取。这意味着工序计划数量会随着物料配置的变更而动态变化。

### 2.2 用料差异计算（理论 vs 实际）

来源：[models/production_stats.py](file:///d:/yuan/不锈钢网带跟单3.0/models/production_stats.py)

```
用料差异 = 实际用量 - 理论用量
用料差异率(%) = (实际 - 理论) / 理论 × 100
```

- **理论用量** = 工序规则公式计算出的 `planned_qty`
- **实际用量** = 工人报工时录入的 `completed_qty`
- 差异 `> 0` 表示超用料，`< 0` 表示节约

**独特之处**：将"公式计算值"作为"理论基准"，与"实际报工值"对比，形成量化考核依据。

---

## 三、工序量计算的独特设计

### 3.1 公式模板化（脱离硬编码）

每条工序的公式保存在 `process_calc_rules` 表中而不是代码里。

| 工序 | 公式 | 含义 |
|------|------|------|
| 原材料准备 | `{物料数量}` | 多少种物料 → 准备多少次 |
| 激光切板 | `{总长度}*1000/{网带节距}` | 总长(米)→毫米，除以节距得片数 |
| 链板冲压孔 | `{总长度}*1000/{网带节距}` | 同上 |
| 链板冲压成型 | `{总长度}*1000/{网带节距}` | 同上 |
| 焊接眼镜网 | `{总长度}*1000/{网带节距}` | 同上 |
| 编织网/整卷类 | `1` | 固定值，按卷计 |

**独特之处**：公式在数据库层面管理，配合 `ProcessCalcRuleView` 提供图形化编辑界面，**业务人员可自行修改公式而无需改代码**。

### 3.2 向上取整（ceil）的工业语义

```python
final = math.ceil(result) if result > 0 else 0
```

**工业解释**：计算出 196.85 片时，你不能生产 0.85 片——必须向上取整到 197 片。这是离散制造（Discrete Manufacturing）的核心语义，和连续流程制造（Process Manufacturing）不同。

### 3.3 参数缺失的温和降级

```python
if result == 0 and resolved_formula not in ("0", "0.0"):
    missing_params = cls._find_missing_params(formula, calc_data)
    if missing_params:
        return 0.0   # 返回 0，但附带缺失参数列表
```

系统不会因为参数缺失而抛出异常，而是：
1. 计划数量设为 0（可人工修正）
2. 向上返回详细的缺失参数列表
3. UI 层展示这些警告（`alert()` 弹出提示）

### 3.4 条件表达式中的中文运算符

```python
COND_OPERATORS = {
    "等于":       lambda a, b: a == b,
    "大于":       lambda a, b: float(a) > float(b),
    "小于":       lambda a, b: float(a) < float(b),
    "包含":       lambda a, b: b in str(a),
    "不包含":     lambda a, b: b not in str(a),
}
```

**独特之处**：条件运算符使用**中文命名**（"大于"而非">"），降低业务人员配置门槛。同时保留英文运算符 `>`, `<`, `>=` 作为兼容备用。

---

## 四、整个流程的运行时全景

### 4.1 触发入口：_recalculate_processes()

当用户在工序追踪视图点击"🔧 计算"按钮时（[process_view.py](file:///d:/yuan/不锈钢网带跟单3.0/desktop/views/process_view.py) L1784）：

```
用户点击 "🔧 计算"
       │
       ▼
_recalculate_processes()
       │
       ├── 1. 从 OrderDAO 读取订单数据（含 extra_params 扩展参数）
       │
       ├── 2. 组装 order_data 字典（固定的基础参数 + 动态 extra_params）
       │     {
       │       "order_id": 123,
       │       "quantity": 50,
       │       "产品类型": "编织网",
       │       "总长度": 5.0,
       │       "总宽": 1.2,
       │       "钢丝直径": 2.5,
       │     }
       │
       ├── 3. 调用 ProcessCalcEngine.generate_processes_from_order()
       │     │
       │     │   ↓ 遍历 PROCESSES 全局工序列表
       │     │
       │     ├── should_include_process("激光切板", order_data, rules)?
       │     │      ├── 产品类型是否在白名单？ (product_types_json)
       │     │      └── 条件表达式是否满足？ (condition_expr)
       │     │
       │     ├── 否 → 跳过该工序
       │     │
       │     └── 是 → calculate_planned_qty("{总长度}*1000/{网带节距}", order_data)
       │                  │
       │                  ├── 解析 {总长度} → 5.0
       │                  ├── 解析 {网带节距} → 25.4
       │                  ├── 替换 → "5.0*1000/25.4"
       │                  ├── _calc_expr() 递归求值 → 196.85...
       │                  └── math.ceil() → 197
       │
       ├── 4. 对比现有工序记录：
       │     ├── 已有且仍在 → 更新 planned_qty（保留原有状态）
       │     ├── 已有但不再符合条件 → 保持不变（不删除）
       │     └── 新增工序 → 插入新记录（状态="待开始"）
       │
       └── 5. 去重清理：同工序名保留第一条，删除多余的重复
```

### 4.2 数据持久化与配置视图

```
process_calc_rules 表（MySQL）
       │
       ├── process_name             # 工序名
       ├── product_types_json       # 产品类型白名单 ["编织网","冲孔网"]
       ├── condition_expr           # 条件表达式 "总宽 > 1000"
       ├── planned_qty_formula      # 计划数量公式 "{总长度}*1000/{网带节距}"
       ├── priority                 # 优先级（大于=优先匹配）
       ├── enabled                  # 启用状态
       ├── default_worker           # 默认负责人
       └── unit                     # 单位（件/米/卷）
              │
              ▼
ProcessCalcRuleView（桌面配置界面）
       │
       ├── 工序下拉筛选
       ├── 规则列表树
       ├── 添加/编辑弹窗（ProcessRuleEditDialog）
       ├── 初始化全部工序默认规则
       ├── 保存/导出/导入模板（JSON文件）
       └── 在线使用说明面板
```

---

## 五、与同类系统的核心差异

| 维度 | 传统MES/ERP | 本系统 ProcessCalcEngine |
|------|-------------|-------------------------|
| **工序路线定义** | 预定义BOM/工艺路线 | 运行时规则匹配（产品类型+条件） |
| **计划数量** | 人工录入或简单复制订单量 | 表格驱动公式自动计算（基于尺寸参数） |
| **公式引擎** | 调用外部规则引擎（Drools等） | 自研递归下降解析器（零依赖） |
| **运算符支持** | 常规符号 | 中文运算符（"大于"）+ 英文运算符双支持 |
| **参数来源** | 固定字段 | 基础字段 + extra_params 扩展 + 物料数实时查询 |
| **降级策略** | 无法计算时抛异常 | 返回 0 + 缺失参数列表（温和降级） |
| **产品类型适配** | 不同产品建不同BOM | 同一套规则引擎通过白名单 + 条件动态适配 |
| **可配置性** | 需二次开发 | 业务人员通过UI配置公式和条件 |
| **复核场景** | 工序单独建 | `quality_rule.py` 复用同一 `_calc_expr()` 计算质检标准值 |

---

## 六、质检规则复用（延伸设计）

质量检验的判定公式也复用了 `ProcessCalcEngine._calc_expr()` 解析器：

```python
# quality_rule.py L367
calc_result = ProcessCalcEngine._calc_expr(formula.strip(), order_data)
standard_value = calc_result   # 计算出的标准值

# 判定：|实测 - 标准| ≤ 公差？
is_passed = abs(measured - standard_value) <= tol_val
```

**独特之处**：同一套公式解析器被**两个完全不同业务场景**复用：
- **工序量计算**：`ProcessCalcEngine.calculate_planned_qty()` — 决定生产多少
- **质检标准值**：`QualityRuleDAO.evaluate_quality_rules()` — 决定是否合格

共享的是 `_calc_expr()` 这个纯函数——它只负责"给定字符串表达式 + 参数表 → 数值"，不关心业务含义。

---

## 七、小结

本系统的工序计算引擎是**面向离散制造行业定制的一套可配置规则引擎**，核心创新点：

1. **产品类型动态路由**：不依赖预定义BOM，通过白名单+条件表达式在运行时决定工序清单
2. **自研递归下降表达式解析器**：纯手工实现，安全无 `eval()`，支持括号优先级和中文运算符
3. **表格驱动公式**：公式存在数据库，UI可配置，业务人员可自助修改
4. **跨场景复用**：同一解析器给工序量计算和质检标准值计算两个场景共用
5. **工业语义内置**：`math.ceil` 向上取整、参数缺失温和降级、物料数量动态注入
