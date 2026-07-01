# 任务表结构规范 v3.6

## 概述

本规范定义了订单全流程中各类任务的数据库表结构。所有任务表遵循统一基础字段，并通过 `flow_type` 区分任务类型。

---

## 统一基础字段

所有任务表必须包含以下字段：

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | VARCHAR(64) | 主键 | PRIMARY KEY |
| order_no | VARCHAR(64) | 关联订单号 | 索引 |
| flow_type | VARCHAR(20) | 任务类型 | 必填 |
| title | VARCHAR(255) | 任务标题 | 必填 |
| status | VARCHAR(32) | 状态 | 索引 |
| priority | VARCHAR(20) | 优先级 | 默认 'normal' |
| quantity | DECIMAL(12,2) | 数量 | 默认 0 |
| completed_qty | DECIMAL(12,2) | 已完成数量 | 默认 0 |
| qualified_qty | DECIMAL(12,2) | 合格数量 | 默认 0 |
| unit | VARCHAR(20) | 单位 | 默认 '件' |
| target_operator | VARCHAR(64) | 负责人 | 索引 |
| operator_id | VARCHAR(64) | 负责人ID | |
| source | VARCHAR(64) | 数据来源 | |
| remark | TEXT | 备注 | |
| created_at | DATETIME | 创建时间 | 默认 CURRENT_TIMESTAMP |
| updated_at | DATETIME | 更新时间 | 自动更新 |
| completed_at | DATETIME | 完成时间 | |
| is_deleted | TINYINT(1) | 软删除 | 默认 0 |

---

## 工序代码规范

| 任务类型 | flow_type | 工序前缀 | 示例 | 说明 |
|---------|-----------|---------|------|------|
| 生产工序 | production | P | P06, P07... | 不锈钢网带生产工序 |
| 物料任务 | material_purchase | M | M01-M06 | 物料采购流程 |
| 质检任务 | quality | Q | Q01-Q06 | 质量检验流程 |
| 维修任务 | repair | R | R01-R07 | 设备维修流程 |
| 外协任务 | outsource | O | O01-O08 | 外协加工流程 |

---

## 各任务类型工序步骤

### 1. 生产工序 (production) - P06-P16

| 代码 | 工序名称 | 角色 |
|------|---------|------|
| P06 | 编制左旋 | 生产部 |
| P07 | 编制右旋 | 生产部 |
| P09 | 输送带组装穿杆 | 生产部 |
| P10 | 安装链条 | 生产部 |
| P12 | 整形校直 | 生产部 |
| P13 | 焊接输送带 | 生产部 |
| P14 | 表面处理 | 生产部 |
| P15 | 质量检验 | 质检部 |
| P16 | 包装入库 | 仓库 |

### 2. 物料任务 (material_purchase) - M01-M06

| 代码 | 工序名称 | 角色 |
|------|---------|------|
| M01 | 物料申请 | 采购部 |
| M02 | 供应商确认 | 采购部 |
| M03 | 物料采购 | 采购部 |
| M04 | 物料到货 | 仓库 |
| M05 | 质检入库 | 质检部 |
| M06 | 物料出库 | 生产部 |

### 3. 质检任务 (quality) - Q01-Q06

| 代码 | 工序名称 | 角色 |
|------|---------|------|
| Q01 | 接收质检 | 质检部 |
| Q02 | 外观检验 | 质检部 |
| Q03 | 尺寸检验 | 质检部 |
| Q04 | 性能检验 | 质检部 |
| Q05 | 判定结果 | 质检部 |
| Q06 | 质检放行 | 质检部 |

### 4. 维修任务 (repair) - R01-R07

| 代码 | 工序名称 | 角色 |
|------|---------|------|
| R01 | 故障报修 | 维修部 |
| R02 | 维修接单 | 维修部 |
| R03 | 故障诊断 | 维修部 |
| R04 | 维修执行 | 维修部 |
| R05 | 功能测试 | 维修部 |
| R06 | 验收确认 | 维修部 |
| R07 | 维修完成 | 维修部 |

### 5. 外协任务 (outsource) - O01-O08

| 代码 | 工序名称 | 角色 |
|------|---------|------|
| O01 | 外协发单 | 计划部 |
| O02 | 外协确认 | 外协厂 |
| O03 | 外协生产 | 外协厂 |
| O04 | 外协质检 | 质检部 |
| O05 | 外协回厂 | 仓库 |
| O06 | 质检审核 | 质检部 |
| O07 | 入库登记 | 仓库 |
| O08 | 发货 | 仓库 |

---

## 状态值规范

### 生产工序状态

| 状态 | 说明 |
|------|------|
| 待开始 | 工序未开始 |
| 生产中 | 正在生产 |
| 已完成 | 生产完成 |

### 物料任务状态

| 状态 | 说明 |
|------|------|
| pending | 待采购 |
| purchasing | 采购中 |
| arrived | 已到货 |
| qc_passed | 已质检 |
| delivered | 已出库 |

### 质检任务状态

| 状态 | 说明 |
|------|------|
| pending | 待检验 |
| inspecting | 检验中 |
| qualified | 合格 |
| unqualified | 不合格 |

### 维修任务状态

| 状态 | 说明 |
|------|------|
| reported | 已报修 |
| assigned | 待派工 |
| in_progress | 维修中 |
| completed | 维修完成 |

### 外协任务状态

| 状态 | 说明 |
|------|------|
| pending | 待发单 |
| confirmed | 已发单 |
| in_production | 外协中 |
| returned | 已回厂 |
| qc_passed | 已质检 |

---

## 表结构详情

### process_sub_steps (生产工序明细)

```sql
CREATE TABLE process_sub_steps (
    id VARCHAR(64) PRIMARY KEY,
    order_no VARCHAR(64),
    process_code VARCHAR(10),      -- 工序代码 P06, P07...
    step_name VARCHAR(100),         -- 工序名称
    quantity DECIMAL(12,2) DEFAULT 0,
    completed_qty DECIMAL(12,2) DEFAULT 0,
    qualified_qty DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    operator VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_no (order_no),
    INDEX idx_process_code (process_code)
);
```

### material_records (物料任务)

```sql
CREATE TABLE material_records (
    id VARCHAR(64) PRIMARY KEY,
    order_no VARCHAR(64),
    flow_type VARCHAR(20) DEFAULT 'material_purchase',
    title VARCHAR(255),
    status VARCHAR(32),
    priority VARCHAR(20) DEFAULT 'normal',
    quantity DECIMAL(12,2) DEFAULT 0,
    completed_qty DECIMAL(12,2) DEFAULT 0,
    target_operator VARCHAR(64),
    source VARCHAR(64),
    remark TEXT,
    -- 物料专属字段
    material_name VARCHAR(200),
    material_spec VARCHAR(200),
    supplier VARCHAR(200),
    expected_date DATE,
    arrival_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    is_deleted TINYINT(1) DEFAULT 0,
    INDEX idx_order_no (order_no),
    INDEX idx_status (status),
    INDEX idx_target_operator (target_operator)
);
```

### quality_records (质检记录)

```sql
CREATE TABLE quality_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(64),
    production_id INT,
    inspection_type VARCHAR(20),    -- 检验类型
    inspection_items TEXT,          -- 检验项目
    result VARCHAR(20),            -- 检验结果
    defect_qty INT DEFAULT 0,
    defect_description TEXT,
    handling_method TEXT,
    inspector VARCHAR(50),
    judgment VARCHAR(20),           -- 判定
    status VARCHAR(30),
    record_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_no (order_no),
    INDEX idx_production_id (production_id)
);
```

### repair_records (维修任务)

```sql
CREATE TABLE repair_records (
    id VARCHAR(64) PRIMARY KEY,
    order_no VARCHAR(64),
    flow_type VARCHAR(20) DEFAULT 'repair',
    title VARCHAR(255),
    status VARCHAR(32) DEFAULT 'reported',
    priority VARCHAR(20) DEFAULT 'normal',
    quantity DECIMAL(12,2) DEFAULT 0,
    completed_qty DECIMAL(12,2) DEFAULT 0,
    target_operator VARCHAR(64),
    source VARCHAR(64),
    remark TEXT,
    -- 维修专属字段
    equipment_no VARCHAR(50),
    equipment_name VARCHAR(200),
    fault_type VARCHAR(50),
    fault_description TEXT,
    fault_date DATETIME,
    repair_type VARCHAR(20),
    estimated_hours DECIMAL(10,2) DEFAULT 0,
    actual_hours DECIMAL(10,2) DEFAULT 0,
    spare_parts TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    is_deleted TINYINT(1) DEFAULT 0,
    INDEX idx_order_no (order_no),
    INDEX idx_status (status),
    INDEX idx_equipment_no (equipment_no)
);
```

### outsource_records (外协任务)

```sql
CREATE TABLE outsource_records (
    id VARCHAR(64) PRIMARY KEY,
    order_no VARCHAR(64),
    flow_type VARCHAR(20) DEFAULT 'outsource',
    title VARCHAR(255),
    status VARCHAR(32) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'normal',
    quantity DECIMAL(12,2) DEFAULT 0,
    completed_qty DECIMAL(12,2) DEFAULT 0,
    target_operator VARCHAR(64),
    source VARCHAR(64),
    remark TEXT,
    -- 外协专属字段
    supplier_name VARCHAR(200),
    outsource_type VARCHAR(50),
    outsource_fee DECIMAL(12,2) DEFAULT 0,
    send_date DATE,
    return_date DATE,
    qc_result VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    is_deleted TINYINT(1) DEFAULT 0,
    INDEX idx_order_no (order_no),
    INDEX idx_status (status),
    INDEX idx_supplier (supplier_name)
);
```

---

## 迁移脚本

历史迁移脚本位于：`migrations/split_data_packages.sql`

### 已完成迁移

| 源表 | 目标表 | 迁移记录数 | 状态 |
|------|--------|----------|------|
| data_packages (material_request) | material_records | 4 | ✅ |
| data_packages (process_task/report) | process_packages | 82 | ✅ |
| data_packages (quality_task) | quality_packages | 13 | ✅ |

---

## 相关文档

- [ARCHITECTURE_v3.6.md](ARCHITECTURE_v3.6.md) - 系统架构文档
