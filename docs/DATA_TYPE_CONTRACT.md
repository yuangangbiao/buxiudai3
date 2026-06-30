# data_type 严格分类契约 v1.0

> **生效日期**: 2026-06-10
> **制定原因**: 历史版本中 `data_type='report'` 同时承载了"工序报工"和"流程步骤占位"两种语义,导致调度中心"工序任务"卡片统计失真。
> **适用范围**: `container_center.data_packages` 表 + `mobile_api_ai/dispatch_center/*` 加载/归类逻辑 + 前端展示文案

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| 1.1 一事一标签 | 一个 data_package 只对应一种业务实体,不允许"report" 这种大杂烩。 |
| 1.2 物理工序 ≠ 流程步骤 | 物理工序(production 产线上的加工动作)与流程步骤(工单生命周期阶段)是两个正交维度,严格区分。 |
| 1.3 工序字典唯一来源 | 物理工序名以 `process_names` 表为唯一来源,不允许硬编码字符串。 |
| 1.4 流程步骤显式枚举 | 流程步骤名必须落在已注册的 4 个流程模板的 step.name 集合内,不允许自由发挥。 |
| 1.5 不可空,不可未知 | data_type 必须是下面枚举值之一,空值或新值需要先在本契约登记。 |

---

## 2. 严格枚举(10 类)

| # | data_type | 中文 | 业务实体 | 创建方 | 字段特征 |
|---|-----------|------|---------|--------|----------|
| 1 | `process_report` | 工序报工 | **物理工序**的执行记录 | 工人扫码报工 | `related_process ∈ process_names.process_name` (白名单)<br>有 `target_operator` (工人) |
| 2 | `flow_step` | 流程步骤占位 | 流程生命周期中每 step 的状态占位 | 工单发布时**系统**自动批量创建 | `related_process ∈ 4 个流程模板的 step.name` 集合<br>无 `target_operator`<br>同工单同秒批量生成 |
| 3 | `flow_production` | 排产发布 | 排产计划已下达 | 主软件 schedule_publish | `data_type = flow_type` (production)<br>`related_process = 排产发布` |
| 4 | `material_request` | 物料申请 | 备料员发起的物料申请 | 主软件 (main_software) | `related_process` 物料名<br>`planned_qty` 有值<br>`status ∈ {pending, confirmed, material_confirmed}` |
| 5 | `material_pickup` | 领料/出库 | 仓库确认发料 | 仓库操作员 | 旧 `data_type='material'` |
| 6 | `material_buy` | 物料采购 | 物料短缺时采购 | 采购员 | 旧 `data_type='purchase'` |
| 7 | `quality_task` | 质检任务 | 质检员发起的检测单 | 质检员 | 旧 `data_type='quality'` + `quality_inspection` 合并 |
| 8 | `equipment_repair` | 设备报修 | 设备故障报修 | 设备管理员 | 旧 `data_type='repair'` |
| 9 | `outsource_task` | 外协任务 | 外协厂家加工单 | 外协员 | 旧 `data_type='outsource'` |
| 10 | `config` | 系统配置 | 流程模板/字典缓存 | 系统初始化 | 旧 `data_type='config'` 或 空 |

> 任何不在上表的 data_type 视为**契约违反**,需登记本契约后才能使用。

---

## 3. 物理工序字典 (`process_names`)

唯一可信的物理工序白名单:

| process_code | process_name | 业务归类 |
|--------------|--------------|----------|
| M01 | 备料/领料 | 物料 |
| P01 | 原材料准备 | 工序 |
| P02 | 焊接眼镜网 | 工序 |
| P03 | 激光切板 | 工序 |
| P04 | 链板冲压孔 | 工序 |
| P05 | 链板冲压成型 | 工序 |
| P06 | 编制左旋 | 工序 |
| P07 | 编制右旋 | 工序 |
| P08 | 穿曲轴 | 工序 |
| P09 | 输送带组装穿杆 | 工序 |
| P10 | 安装链条 | 工序 |
| P11 | 安装裙边 | 工序 |
| P12 | 整形校直 | 工序 |
| P13 | 焊接输送带 | 工序 |
| P14 | 表面处理 | 工序 |
| P15 | 质量检验 | 工序 |
| P16 | 包装入库 | 工序 |
| Q01 | 质检任务 | 质检 |
| X01 | 外协任务 | 外协 |
| P_CS | 工序测试 | 工序 |

> ⚠️ **新增/修改物理工序必须先改这张表**,不允许直接在 data_package 里写新工序名。

---

## 4. 流程步骤集合 (`PROCESS_FLOW_TEMPLATES`)

所有流程步骤名,落在以下 4 个流程模板的并集内:

### 4.1 material_purchase (物料采购流程, 5 步)
```
物料申请 → 任务确认 → 回复采购期限 → 入库通知 → 物料出库
```

### 4.2 production_6step (生产流程 6 步, 旧版)
```
工单发布 → 排产制定 → 生产执行 → 报工完成 → 质量检验 → 完工入库
```

### 4.3 production_7step (生产流程 7 步)
```
工单发布 → 排产制定 → 排产确认 → 生产执行 → 报工完成 → 质检审核 → 完工入库
```

### 4.4 production_8step (生产流程 8 步, 完整版)
```
工单发布 → 排产制定 → 排产确认 → 生产执行 → 质检审核 → 报工完成 → 完工入库 → 发货
```

> **新流程模板必须先注册到 `PROCESS_FLOW_TEMPLATES` 常量**,不允许运行时拼接。

---

## 5. 判定流程(给后端加载逻辑用)

```
对于 data_packages 的每一条记录 pkg:
  1. 读取 pkg.data_type
  2. 读取 pkg.related_process

  IF data_type 已经是新枚举值(1-10):
    直接使用,无需重判
    ↓
  ELIF data_type == 'report':
    IF related_process ∈ process_names.process_name 集合:
      归类 → process_report (工序报工)
      写入数据库 (新 data_type = 'process_report')
    ELIF related_process ∈ 流程步骤集合(4.1-4.4 步骤并集):
      归类 → flow_step (流程步骤占位)
      写入数据库 (新 data_type = 'flow_step')
    ELSE:
      ⚠️ 契约违反: 报警 + 写入 audit_log
  ELIF data_type == 'material':
    → material_pickup
  ELIF data_type == 'material_purchase':
    → material_request
  ELIF data_type == 'purchase':
    → material_buy
  ELIF data_type == 'quality' OR 'quality_inspection':
    → quality_task
  ELIF data_type == 'repair':
    → equipment_repair
  ELIF data_type == 'outsource':
    → outsource_task
  ELIF data_type == 'production':
    → flow_production
  ELSE:
    ⚠️ 契约违反: 报警
```

---

## 5.1 判定流程图(全貌 mermaid)

> **RE-008 修复后**的实际判定流程(已并入 `utils/data_type_contract.py:classify_pkg`):

```mermaid
flowchart TD
    Start([classify_pkg pkg]) --> PreCheck{pkg 是 dict?}
    PreCheck -- "否" --> Violation1[/"__contract_violation__"/]
    PreCheck -- "是" --> ReadDT[读取 dt = pkg.data_type<br/>rp = pkg.related_process]

    ReadDT --> ZeroCheck{RE-008:<br/>rp ∈ flow_step_names_set?<br/>即 4 个流程模板 step.name 并集}

    %% ─── 0. 流程步骤白名单(RE-008 提前到最外层,异常 #9 防御)───
    ZeroCheck -- "✅ 是" --> FlowStep[/"flow_step<br/>(流程步骤)"/]
    ZeroCheck -- "❌ 否" --> NewEnumCheck

    %% ─── 1. 新契约枚举直接返回 ───
    NewEnumCheck{dt ∈ NEW_DATA_TYPES?}
    NewEnumCheck -- "✅ 是" --> DirectReturn[/dt 直接返回/]
    NewEnumCheck -- "❌ 否" --> LegacyCheck

    %% ─── 2. 旧值兼容 ───
    LegacyCheck{dt ∈ LEGACY_TO_NEW?}
    LegacyCheck -- "❌ 否" --> Violation2[/"__contract_violation__"/]

    LegacyCheck -- "✅ 是" --> TargetCheck{target =<br/>LEGACY_TO_NEW[dt]}

    TargetCheck -- "__dynamic__<br/>(旧 data_type='report')" --> LegacyReport[_classify_legacy_report]
    TargetCheck -- "新枚举值" --> MapReturn[/target 直接返回/]

    %% ─── 3. 旧 report 深度判定(0~5)───
    LegacyReport --> LR0{rp ∈ flow_step<br/>names_set?}
    LR0 -- "是" --> LR0Ret[/"flow_step"/]
    LR0 -- "否" --> LR1

    LR1{content.flow_type<br/>== 'production'?}
    LR1 -- "是" --> LR1Ret[/"flow_production<br/>(排产发布)"/]
    LR1 -- "否" --> LR2

    LR2{rp 开头 '质检-'<br/>或 content.inspection_type?}
    LR2 -- "是" --> LR2Ret[/"quality_task<br/>(质检任务)"/]
    LR2 -- "否" --> LR3

    LR3{rp 开头 '备料-'<br/>或 '物料'/'不锈钢' in rp<br/>且 quantity > 0?}
    LR3 -- "是" --> LR3Ret[/"material_request<br/>(物料申请)"/]
    LR3 -- "否" --> LR4

    LR4{rp ∈<br/>process_names_set?}
    LR4 -- "是" --> LR4Ret[/"process_report<br/>(工序报工)"/]
    LR4 -- "否" --> LR5Ret[/"__contract_violation__"/]

    %% ─── 4. 卡片分组 ───
    FlowStep --> GroupByCard
    DirectReturn --> GroupByCard
    MapReturn --> GroupByCard
    LR0Ret --> GroupByCard
    LR1Ret --> GroupByCard
    LR2Ret --> GroupByCard
    LR3Ret --> GroupByCard
    LR4Ret --> GroupByCard
    LR5Ret --> AuditLog[⚠️ audit_log<br/>审计告警]

    GroupByCard[group_by_card: 按 CARD_GROUPS<br/>分为 6 张卡片]
    AuditLog --> GroupByCard

    GroupByCard --> Out1[process_tasks]
    GroupByCard --> Out2[flow_steps]
    GroupByCard --> Out3[material_tasks]
    GroupByCard --> Out4[quality_tasks]
    GroupByCard --> Out5[repair_tasks]
    GroupByCard --> Out6[outsource_tasks]

    style FlowStep fill:#52c41a,color:#fff
    style DirectReturn fill:#52c41a,color:#fff
    style MapReturn fill:#52c41a,color:#fff
    style LR0Ret fill:#52c41a,color:#fff
    style LR1Ret fill:#52c41a,color:#fff
    style LR2Ret fill:#52c41a,color:#fff
    style LR3Ret fill:#52c41a,color:#fff
    style LR4Ret fill:#52c41a,color:#fff
    style Violation1 fill:#ff4d4f,color:#fff
    style Violation2 fill:#ff4d4f,color:#fff
    style LR5Ret fill:#ff4d4f,color:#fff
    style AuditLog fill:#faad14,color:#fff
```

### 5.2 关键严格化点(图上重点)

| 节点 | 关键点 |
|------|--------|
| 🟢 **ZeroCheck 流程白名单** | **RE-008 修复** — 把"流程步骤判定"从 `_classify_legacy_report` 内部提到 `classify_pkg` 最外层,**保证无论 data_type 是什么,只要 rp 是流程步骤,必归 flow_step**。这是"质检审核"被强归 quality_task(异常 #9)的根因修复。 |
| 🟢 **NewEnumCheck 已是新枚举** | 1.1 一事一标签 — 不允许"report"这种大杂烩存在 |
| 🟢 **LR0 流程步骤再次兜底** | 即便走到了 `_classify_legacy_report` 内部,流程步骤判定依然第一优先(双保险) |
| 🟢 **LR4 物理工序白名单** | 1.3 工序字典唯一来源 — 物理工序必须落在 `process_names` 18 个白名单内 |
| 🔴 **LR5Ret / Violation 兜底** | 1.5 不可空不可未知 — 不在白名单的强制审计,不会静默"伪归类" |
| 🟡 **AuditLog** | 契约违反时,数据继续显示但记入审计日志,业务可定位 |

### 5.3 关键白名单

```
process_names_set   = {P01 原材料准备, P02 焊接眼镜网, P03 激光切板, P04 链板冲压孔,
                       P05 链板冲压成型, P06 编制左旋, P07 编制右旋, P08 穿曲轴,
                       P09 输送带组装穿杆, P10 安装链条, P11 安装裙边, P12 整形校直,
                       P13 焊接输送带, P14 表面处理, P15 质量检验,
                       P16 包装入库, M01 备料/领料, Q01 质检任务, X01 外协任务, P_CS 工序测试}
                      共 19 个

flow_step_names_set = material_purchase  ∪ production_6step  ∪ production_7step  ∪ production_8step
                     = {工单发布, 排产制定, 排产确认, 生产执行, 报工完成, 质量检验, 完工入库,
                        质检审核, 发货, 物料申请, 任务确认, 回复采购期限, 入库通知, 物料出库}
                      共 14 个(去重)
```

### 5.4 异常 #9 历史

> "质检审核" 应该归 `flow_steps` 还是 `quality_tasks`?

```
错误路径(RE-007 之前):
  pkg.data_type = 'quality'
  pkg.related_process = '质检审核'
    → LEGACY_TO_NEW['quality'] = 'quality_task' 直接映射
    → 即便 content.flow_type='production' 也被覆盖
    → 误归 quality_task ❌

正确路径(RE-008 之后):
  pkg.data_type = 'quality'
  pkg.related_process = '质检审核'
    → ZeroCheck: rp ∈ flow_step_names_set? ✅
    → 直接 return 'flow_step' ✅
    → 落入 flow_steps 卡片
```

---

## 6. 加载归类(API 层)

`_core.py` 加载逻辑按新契约归类:

```python
def _classify_pkg(pkg: dict, process_names_set: set) -> str:
    """根据新 data_type 契约,返回该 pkg 属于哪个分类标签"""
    dt = pkg.get('data_type', '')
    rp = pkg.get('related_process', '')

    if dt in NEW_DATA_TYPE_ENUM:
        return dt  # 已是新契约值,直接归类

    # 旧值兼容(契约生效后第一个版本保留,1-2 个版本后移除)
    LEGACY_MAP = {
        'report':          ('process_report' if rp in process_names_set else 'flow_step'),
        'material':        'material_pickup',
        'material_purchase': 'material_request',
        'purchase':        'material_buy',
        'quality':         'quality_task',
        'quality_inspection': 'quality_task',
        'repair':          'equipment_repair',
        'outsource':       'outsource_task',
        'production':      'flow_production',
    }
    if dt in LEGACY_MAP:
        return LEGACY_MAP[dt]
    return '__unknown__'  # 触发审计
```

---

## 7. 任务卡片对应(前端展示)

调度中心工单详情 6 张卡片:

| 卡片 | 卡片标题 | 取自 data_type | tab 标题 |
|------|----------|---------------|----------|
| 1 | 工序任务 (📋) | `process_report` | 工序报工 |
| 2 | 流程进度 (📊) | `flow_step` + `flow_production` | 流程步骤 |
| 3 | 物料任务 (📦) | `material_request` + `material_pickup` + `material_buy` | 物料任务 |
| 4 | 质检任务 (✓) | `quality_task` | 质检任务 |
| 5 | 维修任务 (🔧) | `equipment_repair` | 设备报修 |
| 6 | 外协任务 (🚚) | `outsource_task` | 外协任务 |

> ✅ **关键变化**:把原来的"工序任务"卡片拆成两张:
> - **工序报工**(物理加工,白名单工序字典)
> - **流程进度**(系统自动生成的 step 占位)

---

## 8. 历史数据迁移映射(执行清单)

| 旧 data_type | 新 data_type | 迁移条件 | 备注 |
|--------------|--------------|----------|------|
| `report` 且 related_process ∈ process_names | `process_report` | 物理工序 | 真实工人报工 |
| `report` 且 related_process ∈ 流程步骤 | `flow_step` | 流程步骤占位 | 2026-05-31 批量创建的 7 条 |
| `material` | `material_pickup` | 全部 | 领料 |
| `material_purchase` | `material_request` | 全部 | 物料申请 |
| `purchase` | `material_buy` | 全部 | 采购 |
| `quality` | `quality_task` | 全部 | 质检 |
| `quality_inspection` | `quality_task` | 全部 | 质检(合并) |
| `repair` | `equipment_repair` | 全部 | 设备报修 |
| `outsource` | `outsource_task` | 全部 | 外协 |
| `production` | `flow_production` | 全部 | 排产 |
| `config` / 空 | `config` | 保留 | 系统配置类 |

**脚本**:`scripts/migrations/migrate_data_type_to_v1.py`

---

## 9. 不允许/禁止

- ❌ 禁止给 `data_packages` 写 `data_type='report'` (必须用 `process_report` 或 `flow_step` 区分)
- ❌ 禁止用 `process_names` 字典外的物理工序名
- ❌ 禁止在 4 个流程模板外新增 step name
- ❌ 禁止在 API 归类逻辑里用 `if dt == 'report'` 这种粗粒度判断
- ❌ 禁止前端用"工序任务"同时展示物理工序和流程步骤(必须拆开)

---

## 10. 版本与变更

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-06-10 | 首次发布,严格区分物理工序与流程步骤 | Trae Agent |

