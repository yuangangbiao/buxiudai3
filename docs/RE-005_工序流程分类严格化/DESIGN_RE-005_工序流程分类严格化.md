# RE-005 工序/流程/物料/质检/外协 分类严格化 — DESIGN

> **设计原则**: 一事一标签 · 物理工序 ≠ 流程步骤 · 字典唯一 · 模板显式枚举

---

## 一、概念边界(严格定义)

### 1.1 物理工序(Physical Process)
- **定义**: 工人在产线上执行的真实加工动作。
- **字典唯一来源**: `process_names` 表,共 20 个。
- **示例**: 焊接眼镜网 / 穿曲轴 / 整形校直 / 包装入库
- **data_type**: `process_report`(工序报工)
- **特征**: 有 `target_operator`(工人) / 有 `completed_qty`

### 1.2 流程步骤(Flow Step)
- **定义**: 工单生命周期的阶段,系统自动批量生成,无操作员。
- **模板来源**: `PROCESS_FLOW_TEMPLATES` 字典,4 个模板。
- **示例**: 工单发布 / 排产制定 / 排产确认 / 生产执行 / 报工完成 / 质检审核 / 完工入库 / 发货
- **data_type**: `flow_step`(流程步骤占位) + `flow_production`(排产发布特殊步骤)
- **特征**: 同工单同秒批量生成 / 无 `target_operator`

### 1.3 物料任务(Material Task)
- **定义**: 物料在工单生命周期内的流转记录。
- **data_type**: `material_request`(申请) / `material_pickup`(领料) / `material_buy`(采购)
- **特征**: `related_process` 是物料名 / 有 `planned_qty`

### 1.4 质检任务(Quality Task)
- **定义**: 质检员发起的检测单。
- **data_type**: `quality_task`
- **特征**: `related_process` 以"质检-"开头 或 content 含 `inspection_type`

### 1.5 维修任务(Equipment Repair)
- **定义**: 设备故障报修。
- **data_type**: `equipment_repair`

### 1.6 外协任务(Outsource Task)
- **定义**: 外协厂家加工单。
- **data_type**: `outsource_task`

---

## 二、数据流设计

### 2.1 创建端 → 数据库

```
工人扫码 ──> process_report  (process_names 白名单)
备料员 ──>  material_request
仓库 ──>    material_pickup
采购员 ──>  material_buy
质检员 ──>  quality_task
设备员 ──>  equipment_repair
外协员 ──>  outsource_task
工单发布 ──> flow_step(批量)
排产发布 ──> flow_production
```

### 2.2 数据库 → API 层

```
data_packages 表
  ↓ _core.py 加载
classify_pkg(pkg, process_set, flow_step_set)
  ↓ 6 张卡片
前端 6 tab
```

### 2.3 API 层 → 前端

```json
{
  "process_tasks":  [pkg...],   // 工序报工
  "flow_steps":     [pkg...],   // 流程步骤 + 排产
  "material_tasks": [pkg...],   // 物料申请+领料+采购
  "quality_tasks":  [pkg...],   // 质检
  "repair_tasks":   [pkg...],   // 维修
  "outsource_tasks":[pkg...],   // 外协
  "stats":          {...}
}
```

---

## 三、关键设计权衡

| 维度 | 选择 | 理由 |
|------|------|------|
| 新建 data_type 列 vs 复用旧值 | 新建 | 旧值语义过载,只能拆 |
| 是否双轨兼容 | 是 | 旧客户端不破坏,1-2 版本后再废弃 |
| content 字段兜底判定 | 是 | 4 条历史契约违反必须修复 |
| 物理工序字典放 DB | 是 | 业务侧要加新工序,不能改代码 |
| 流程步骤放代码字典 | 是 | 流程模板是核心业务,变更需走代码评审 |
| 渲染层 vs API 层 | API 层归类 | 前端只负责展示,不参与分类 |
| 单一枚举 vs 复合 tag | 单一 | 一事一标签,避免组合爆炸 |

---

## 四、判定算法(classify_pkg 伪代码)

```python
def classify_pkg(pkg, process_set, flow_step_set):
    dt = pkg.data_type
    rp = pkg.related_process
    c  = parse_content(pkg.content)

    # 1. 已是新契约值
    if dt in NEW_DATA_TYPES:
        return dt

    # 2. 旧值静态映射
    if dt in LEGACY_TO_NEW:
        target = LEGACY_TO_NEW[dt]
        if target != "__dynamic__":
            return target

    # 3. 旧值 'report' 动态拆分
    if dt == "report":
        # 3.1 content.flow_type 强信号
        if c.flow_type == "production":
            return "flow_production"
        # 3.2 质检信号
        if rp.startswith("质检-") or c.inspection_type:
            return "quality_task"
        # 3.3 物料信号 + quantity
        if ("备料-" in rp or "不锈钢" in rp) and c.quantity > 0:
            return "material_request"
        # 3.4 物理工序白名单
        if rp in process_set:
            return "process_report"
        # 3.5 流程步骤白名单
        if rp in flow_step_set:
            return "flow_step"
        # 3.6 契约违反
        return "__contract_violation__"

    return "__contract_violation__"
```

---

## 五、错误处理

| 场景 | 策略 |
|------|------|
| `data_type` 为空 | 视为 `config`(系统配置) |
| `data_type` 为新枚举值 | 直通 |
| `data_type` 为旧枚举值 | 走 LEGACY_TO_NEW |
| 旧值 `report` + 无法判定 | 返回 `__contract_violation__`,前端展示"未分类"+ 写 audit_log |
| `related_process` 为空 | 视为 `config` 占位 |
| 物理工序字典新增 | 走 DB 维护,5min 后缓存自动失效 |
| 流程模板新增 | 必须先注册 `PROCESS_FLOW_TEMPLATES` 常量,代码评审 |

---

## 六、扩展性预留

- **多租户**: `process_names` 表加 `tenant_id`,`PROCESS_FLOW_TEMPLATES` 加 tenant 维度
- **自定义流程**: 后续可加 `custom_flow_templates` 表,优先级高于内置模板
- **审计**: 所有 `__contract_violation__` 写 `audit_log` 表,后台可查
- **可视化分类**: 前端可加 "未分类" 卡片 + 红色警告,提示数据治理
