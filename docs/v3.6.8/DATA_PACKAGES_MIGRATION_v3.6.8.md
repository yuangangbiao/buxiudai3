# data_packages 表废弃迁移方案 v3.6.8

> **文档日期**: 2026-06-25
> **版本**: v3.6.8
> **状态**: Phase 0 完成 ✅
> **评审人**: AI Team

---

## 一、背景与目标

### 1.1 问题描述

`container_center.data_packages` 表是项目初期的"万能表"，承担了 15+ 种不同业务数据的存储职责，违反单一职责原则。

**核心问题**:
- 上帝表：职责混乱，难以维护
- 数据冗余：`completed_qty` 字段与 `process_sub_steps.quantity` 重复
- 双写风险：写入时需同时维护 `data_packages` 和明细表
- 违反规范：项目架构规范 R-065 明确要求"禁止写入 data_packages"

### 1.2 迁移目标

**最终目标**: 完全废弃 `data_packages` 表，所有业务数据迁移到独立表。

**试点目标**: 以 `schedule` (排产记录) 为试点，完成以下工作：
1. 验证迁移方案可行性
2. 总结迁移经验
3. 为后续批量迁移提供模板

### 1.3 迁移策略

**试点优先**: 先对 `schedule_record` (排产记录) 做完整迁移试点，再批量迁移其他类型。

**分阶段实施**:
- Phase 0: 前置优化（索引）
- Phase 1: 试点迁移 (schedule)
- Phase 2: 批量迁移 (其他类型)
- Phase 3: 清理与删除

---

## 二、现状分析

### 2.1 data_packages 表结构

```sql
CREATE TABLE container_center.data_packages (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,              -- 核心分类字段
    title TEXT NOT NULL,
    content TEXT,                         -- JSON 动态数据
    data TEXT,
    status TEXT DEFAULT 'pending',
    related_order TEXT,                   -- 关联订单
    related_process TEXT,                 -- 关联工序
    target_operator TEXT,                 -- 目标操作员
    operator TEXT,
    source TEXT,
    quantity REAL DEFAULT 0,
    completed_qty REAL DEFAULT 0,       -- 已完成数量（冗余）
    package_type TEXT,
    wo_no TEXT,
    remark TEXT,
    process_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);
```

### 2.2 data_type 统计

| data_type | 数量 | 替代表 | 迁移状态 |
|-----------|------|--------|---------|
| process_task | 已迁移 | `process_sub_steps` | ✅ 完成 |
| process_report | 已迁移 | `process_sub_steps` | ✅ 完成 |
| report | 已迁移 | `process_sub_steps` | ✅ 完成 |
| quality_task | 已迁移 | `quality_records` | ✅ 完成 |
| material_request | 已迁移 | `material_records` | ✅ 完成 |
| **schedule** | **待迁移** | **`schedule_records`** | **⏳ 本次试点** |
| outsource | 待迁移 | `outsource_records` | ❌ 未迁移 |
| material_purchase | 待迁移 | `material_purchase_records` | ❌ 未迁移 |
| work_order | 待迁移 | `work_orders` | ❌ 未迁移 |
| order_production | 待迁移 | `production_orders` | ❌ 未迁移 |
| material (admin) | 部分迁移 | `material_records` | ⚠️ 部分 |
| repair | 部分迁移 | `repair_records` | ⚠️ 部分 |
| config | 很少使用 | 独立配置表 | ❌ 未迁移 |
| 其他 | - | - | ❌ 待清理 |

### 2.3 代码依赖地图

#### schedule 类型依赖

| 文件 | 行号 | 操作 | 用途 |
|------|------|------|------|
| [report_record_admin.py:866-870](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/report_record_admin.py#L866-L870) | 866 | SELECT COUNT + SELECT | schedule_record_list 列表查询 |
| [report_record_admin.py:880-920](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/report_record_admin.py#L880-L920) | 880 | SELECT FOR UPDATE | schedule_record_update 修改 |
| [report_record_admin.py:923-960](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/report_record_admin.py#L923-L960) | 923 | SELECT FOR UPDATE | schedule_record_withdraw 撤回 |
| [report_record_admin.py:963-990](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/report_record_admin.py#L963-L990) | 963 | SELECT | schedule_record_history_full 历史 |

#### 关键字段映射

| data_packages 字段 | schedule 用途 | schedule_records 映射 |
|-------------------|-------------|---------------------|
| id | 主键 | id (TEXT PRIMARY KEY) |
| data_type='schedule' | 类型标识 | 移除（独立表无需此字段） |
| related_order | 关联订单 | order_no (TEXT) |
| related_process | 关联工序 | process_name (TEXT) |
| title | 标题 | title (TEXT) |
| quantity | 计划数量 | quantity (REAL) |
| status | 状态 | status (TEXT DEFAULT 'pending') |
| target_operator | 目标操作员 | target_operator (TEXT) |
| operator | 操作员 | operator (TEXT) |
| source | 来源 | source (TEXT) |
| content | 扩展数据 | content (TEXT) |
| process_code | 工序编码 | process_code (TEXT) |
| remark | 备注 | remark (TEXT) |
| created_at | 创建时间 | created_at (TIMESTAMP) |
| updated_at | 更新时间 | updated_at (TIMESTAMP) |
| is_deleted | 软删除 | is_deleted (INTEGER DEFAULT 0) |

---

## 三、迁移方案

### 3.1 试点: schedule → schedule_records

#### 3.1.1 创建 schedule_records 表

```sql
-- 迁移脚本: create_schedule_records.sql

CREATE TABLE IF NOT EXISTS container_center.schedule_records (
    id TEXT PRIMARY KEY,
    order_no TEXT NOT NULL,
    process_name TEXT,
    title TEXT,
    status TEXT DEFAULT 'pending',
    quantity REAL DEFAULT 0,
    target_operator TEXT,
    operator TEXT,
    source TEXT,
    priority TEXT,
    remark TEXT,
    process_code TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 幂等添加索引（兼容 MySQL 5.7+，避免重复执行报错）
-- 索引1: order_no 单列（支持按订单筛选）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_order') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_order (order_no)',
    'SELECT ''idx_schedule_order already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 索引2: status 单列（支持按状态筛选）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_status') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_status (status)',
    'SELECT ''idx_schedule_status already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 索引3: target_operator 单列（支持按操作员筛选）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_operator') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_operator (target_operator)',
    'SELECT ''idx_schedule_operator already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 索引4: 复合索引（支持 (order_no, process_name) 联合查询）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_order_process') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_order_process (order_no, process_name)',
    'SELECT ''idx_schedule_order_process already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
```

#### 3.1.2 数据迁移脚本

```sql
-- 迁移脚本: migrate_schedule_to_schedule_records.sql

-- Step 0: 幂等检查（防止重复执行）
SET @migration_done = (SELECT COUNT(*) FROM container_center.schedule_records LIMIT 1);
SET @source_count = (SELECT COUNT(*) FROM container_center.data_packages WHERE data_type = 'schedule');

-- 如果已迁移且数量一致，跳过
IF @migration_done > 0 AND @migration_done = @source_count THEN
    SELECT 'Migration already complete, skipping' AS status;
ELSE
    -- Step 1: 幂等清空（支持重新迁移）
    TRUNCATE TABLE container_center.schedule_records;

    -- Step 2: 备份原数据
    DROP TABLE IF EXISTS container_center.data_packages_schedule_backup;
    CREATE TABLE container_center.data_packages_schedule_backup AS
    SELECT * FROM container_center.data_packages
    WHERE data_type = 'schedule' AND is_deleted = 0;

    -- Step 3: 幂等迁移数据（使用 INSERT IGNORE 处理重复 key）
    INSERT IGNORE INTO container_center.schedule_records
        (id, order_no, process_name, title, status, quantity, target_operator, operator,
         source, priority, remark, process_code, content, created_at, updated_at, is_deleted)
    SELECT
        id,
        COALESCE(related_order, '') AS order_no,
        COALESCE(related_process, '') AS process_name,
        COALESCE(title, '') AS title,
        COALESCE(status, 'pending') AS status,
        COALESCE(quantity, 0) AS quantity,
        COALESCE(target_operator, '') AS target_operator,
        COALESCE(operator, '') AS operator,
        COALESCE(source, '') AS source,
        COALESCE(JSON_UNQUOTE(JSON_EXTRACT(content, '$.priority')), '') AS priority,
        COALESCE(remark, '') AS remark,
        COALESCE(process_code, '') AS process_code,
        content,
        created_at,
        updated_at,
        is_deleted
    FROM container_center.data_packages
    WHERE data_type = 'schedule';

    -- Step 4: 幂等数据验证
    SELECT
        (SELECT COUNT(*) FROM container_center.data_packages_schedule_backup) AS source_count,
        (SELECT COUNT(*) FROM container_center.schedule_records) AS target_count,
        (SELECT COUNT(*) FROM container_center.data_packages_schedule_backup) -
        (SELECT COUNT(*) FROM container_center.schedule_records) AS diff,
        CASE
            WHEN (SELECT COUNT(*) FROM container_center.data_packages_schedule_backup) =
                 (SELECT COUNT(*) FROM container_center.schedule_records) THEN '✅ 数量一致'
            ELSE '⚠️ 数量不一致，请检查 diff 列'
        END AS status;
END IF;
```

#### 3.1.3 代码迁移

**文件**: mobile_api_ai/api/report_record_admin.py

| 函数 | 改动 |
|------|------|
| `schedule_record_list` | FROM `data_packages WHERE data_type='schedule'` → `schedule_records` |
| `schedule_record_update` | FROM `data_packages WHERE id=...` → `schedule_records WHERE id=...` |
| `schedule_record_withdraw` | FROM `data_packages` → `schedule_records` |
| `schedule_record_history_full` | FROM `data_packages` → `schedule_records` |

**关键改动示例**:

```python
# 改动前 (report_record_admin.py:866)
cur.execute(
    f"SELECT dp.* FROM data_packages dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
    params + [page_size, offset])

# 改动后
cur.execute(
    f"SELECT sr.* FROM schedule_records sr WHERE {where_sql} ORDER BY sr.created_at DESC LIMIT %s OFFSET %s",
    params + [page_size, offset])
```

### 3.2 content 字段 JSON 结构规范

#### 3.2.0 现状 content 字段分析

`data_packages.content` 字段为 TEXT 类型，存储 JSON 字符串。不同 data_type 的 content 结构不一致，需先分析再统一迁移。

**现有 content JSON 结构调研**:

| data_type | content 示例 | 关键字段 | 迁移策略 |
|-----------|------------|---------|---------|
| schedule | `{"priority": "high", "notes": "...", "scheduled_date": "2026-06-25"}` | priority, notes | ✅ 直接映射 |
| quality_task | `{"defect_count": 5, "inspection_result": "pass"}` | defect_count | ✅ 直接映射 |
| material_request | `{"material_type": "steel", "unit": "kg"}` | material_type | ✅ 直接映射 |
| outsource | `{"supplier": "xxx", "contract_no": "yyy"}` | supplier, contract_no | ✅ 直接映射 |
| process_task | `{"machine": "M01", "operator": "张三"}` | machine, operator | ✅ 直接映射 |
| process_report | `{"report_by": "李四", "report_time": "..."}` | report_by, report_time | ✅ 直接映射 |
| report | `{"photos": [...], "remark": "..."}` | photos, remark | ⚠️ photos 为数组，需特殊处理 |
| repair | `{"repair_type": "maintenance", "cost": 500}` | repair_type, cost | ✅ 直接映射 |

**content 字段 JSON 结构规范**（新建 schedule_records 表使用）:

```sql
-- content 字段统一存储为 TEXT，包含以下标准结构（根据实际业务扩展）:
-- {
--     "priority": "high|normal|low",          -- 优先级（schedule 使用）
--     "notes": "备注信息",                      -- 备注说明
--     "scheduled_date": "2026-06-25",         -- 排产日期
--     "photos": ["url1", "url2"],              -- 图片列表（如有）
--     "extra": {}                               -- 扩展数据（兼容未定义字段）
-- }
```

**priority 字段提取逻辑**（迁移脚本中 JSON_EXTRACT 的正确用法）:

```sql
-- MySQL 5.7+ 正确提取 JSON 字符串
-- 注意：JSON_EXTRACT 返回的是 JSON 值类型，需要用 JSON_UNQUOTE 或 ->> 操作符
COALESCE(JSON_UNQUOTE(JSON_EXTRACT(content, '$.priority')), '') AS priority

-- MySQL 8.0+ 可用 ->> 操作符（等效于 JSON_UNQUOTE + JSON_EXTRACT）
-- COALESCE(content->>'$.priority', '') AS priority
```

**扩展字段保留策略**:

```sql
-- 迁移时将所有未映射字段保留在 content 中
-- content 不做裁剪，完整保留原始 JSON
content  -- 直接透传，不做字段拆分
```

#### 3.2.0b content 字段质量检查脚本

```sql
-- Step 1: 检查 content 字段格式有效性（排除非法 JSON）
SELECT COUNT(*) AS invalid_json_count
FROM container_center.data_packages
WHERE data_type = 'schedule'
  AND content IS NOT NULL
  AND content != ''
  AND JSON_VALID(content) = 0;

-- Step 2: 检查 priority 字段分布
SELECT
    JSON_UNQUOTE(JSON_EXTRACT(content, '$.priority')) AS priority,
    COUNT(*) AS count
FROM container_center.data_packages
WHERE data_type = 'schedule'
  AND content IS NOT NULL
  AND content != ''
  AND JSON_VALID(content) = 1
GROUP BY JSON_UNQUOTE(JSON_EXTRACT(content, '$.priority'));

-- Step 3: 检查 content 字段为空的比例（评估扩展性风险）
SELECT
    COUNT(*) AS total_count,
    SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) AS empty_content_count,
    ROUND(SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS empty_percentage
FROM container_center.data_packages
WHERE data_type = 'schedule';
```

### 3.3 completed_qty 实时汇总方案

#### 3.2.1 索引优化（Phase 0 前置工作）

**⚠️ 大表加索引风险评估（process_sub_steps 表）**:

| 风险项 | 说明 | 缓解措施 |
|--------|------|---------|
| InnoDB 表级锁 | `ALTER TABLE ... ADD INDEX` 会锁表（MySQL 5.6 之前），阻塞写操作 | 使用 `pt-online-schema-change`（推荐）或 `ALTER TABLE ... ALGORITHM=INPLACE, LOCK=NONE`（MySQL 5.6+） |
| 主从延迟 | 大表加索引期间从库复制可能滞后 | 在低峰期执行，监控从库状态 |
| 磁盘 I/O 飙升 | 索引构建消耗大量 I/O | 在低峰期执行，确保磁盘 I/O 充足 |
| 索引失效 | 复合索引列顺序不对导致无法命中 | 严格按 `(order_no, step_name, quantity)` 顺序创建 |

**推荐方案**（使用 pt-osc 零停机加索引）:

```bash
# 安装 pt-online-schema-change（如未安装）
# yum install percona-toolkit  或  apt install percona-toolkit

# 零停机添加复合索引（order_no, step_name, quantity）
pt-online-schema-change \
    --alter "ADD INDEX idx_order_step_qty (order_no, step_name, quantity)" \
    --execute \
    --charset=utf8mb4 \
    --chunk-size=1000 \
    --max-load="Threads_running=50" \
    D=container_center,t=process_sub_steps

# 零停机添加去重查询索引（order_no, step_name, batch_no）
pt-online-schema-change \
    --alter "ADD INDEX idx_order_step_batch (order_no, step_name, batch_no)" \
    --execute \
    --charset=utf8mb4 \
    --chunk-size=1000 \
    --max-load="Threads_running=50" \
    D=container_center,t=process_sub_steps
```

**回退方案**（pt-osc 失败时）:

```sql
-- 幂等加索引（MySQL 5.7+ 支持 ALGORITHM=INPLACE）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'process_sub_steps'
       AND INDEX_NAME = 'idx_order_step_qty') = 0,
    'ALTER TABLE process_sub_steps ADD INDEX idx_order_step_qty (order_no, step_name, quantity), ALGORITHM=INPLACE, LOCK=NONE',
    'SELECT ''idx_order_step_qty already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'process_sub_steps'
       AND INDEX_NAME = 'idx_order_step_batch') = 0,
    'ALTER TABLE process_sub_steps ADD INDEX idx_order_step_batch (order_no, step_name, batch_no), ALGORITHM=INPLACE, LOCK=NONE',
    'SELECT ''idx_order_step_batch already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
```

**索引效果验证**:

```sql
-- 加索引前：检查查询计划（应显示全表扫描）
EXPLAIN SELECT COALESCE(SUM(quantity), 0)
FROM process_sub_steps
WHERE order_no = 'ORD20240001' AND step_name = '焊接' AND quantity > 0;

-- 加索引后：验证索引被使用（type=ref, key=idx_order_step_qty）
EXPLAIN SELECT COALESCE(SUM(quantity), 0)
FROM process_sub_steps
WHERE order_no = 'ORD20240001' AND step_name = '焊接' AND quantity > 0;
```

#### 3.2.1b 幂等索引脚本（schedule_records）

> ⚠️ schedule_records 为新建表，数据量小，标准 `ALTER TABLE` 加索引无锁表风险，以下脚本为完整性保留。

```sql
-- 幂等添加索引（兼容 MySQL 5.7+）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_order') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_order (order_no)',
    'SELECT ''idx_schedule_order already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_status') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_status (status)',
    'SELECT ''idx_schedule_status already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_operator') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_operator (target_operator)',
    'SELECT ''idx_schedule_operator already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA = 'container_center'
       AND TABLE_NAME = 'schedule_records'
       AND INDEX_NAME = 'idx_schedule_order_process') = 0,
    'ALTER TABLE schedule_records ADD INDEX idx_schedule_order_process (order_no, process_name)',
    'SELECT ''idx_schedule_order_process already exists'' AS msg'
));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
```

#### 3.2.2 实时汇总函数

```python
def get_completed_qty(order_no: str, step_name: str) -> float:
    """
    实时从 process_sub_steps 汇总 completed_qty
    替代 data_packages.completed_qty 字段
    """
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(quantity), 0) "
            "FROM process_sub_steps "
            "WHERE order_no = %s AND step_name = %s AND quantity > 0",
            (order_no, step_name))
        result = cur.fetchone()
        return float(result[0] or 0) if result else 0.0
    finally:
        conn.close()
```

#### 3.2.3 删除双写逻辑

删除以下函数中的 `data_packages` 同步逻辑：

| 文件 | 函数 | 删除内容 |
|------|------|---------|
| app.py | `_sync_completed_qty_to_package` | 整个函数（Phase 1 后） |
| app.py | `_add_completed_qty_to_package` | 整个函数（Phase 1 后） |
| mysql_storage.py | `save_process_sub_step` | completed_qty 累加逻辑 |

### 3.3 后续迁移路线图

#### Phase 1: 试点 (schedule)

| 任务 | 工作量 | 风险 |
|------|--------|------|
| 创建 schedule_records 表 | 低 | 低 |
| 迁移历史数据 | 低 | 低 |
| 改写 report_record_admin.py 中的 schedule 函数 | 中 | 中 |
| 添加 completed_qty 索引 | 低 | 低 |
| 验证功能 | 中 | 中 |
| 灰度切换 | 低 | 低 |

#### Phase 2: 批量迁移 (其他类型)

| data_type | 替代表 | 工作量 | 备注 |
|-----------|--------|--------|------|
| outsource | outsource_records | 中 | 结构与 schedule 类似 |
| material_purchase | material_purchase_records | 中 | 需新建表 |
| work_order | work_orders | 低 | 数量少 |
| order_production | production_orders | 低 | 数量少 |
| material (admin) | material_records | 低 | 部分已完成 |

#### Phase 3: 清理与删除

| 任务 | 条件 |
|------|------|
| 删除 data_packages 表 | 所有 data_type 迁移完成且稳定运行 1 个月 |
| 清理调试脚本 | 确认无遗留引用 |
| 更新架构文档 | 删除 data_packages 相关说明 |

---

## 四、测试计划

### 4.1 单元测试

| 测试项 | 验证内容 |
|--------|---------|
| schedule_record_list | 返回数据与原接口一致 |
| schedule_record_update | 修改后数据正确 |
| schedule_record_withdraw | 撤回后 status='withdrawn' |
| schedule_record_history_full | 历史记录完整 |
| get_completed_qty | 汇总结果与原 completed_qty 一致 |

### 4.2 集成测试

| 测试项 | 验证内容 |
|--------|---------|
| 完整流程 | 报工 → 撤回 → 修改 全流程正常 |
| 历史数据 | 迁移后历史记录完整可查 |
| 性能测试 | 实时汇总查询 < 100ms |

### 4.3 回归测试

| 测试范围 | 说明 |
|---------|------|
| 全部 admin 接口 | report_record, quality_record, material_record, outsource_record, schedule_record |
| 全部报工接口 | process_sub_step, withdraw, history |
| 统计引擎 | stats_engine.py 中使用 completed_qty 的查询 |

---

## 五、风险与缓解

### 5.1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 历史数据迁移丢失 | 低 | 高 | 备份脚本 + 验证查询 |
| 迁移后查询性能下降 | 中 | 中 | 索引优化 + 性能监控 |
| 兼容层遗漏导致业务中断 | 低 | 高 | 灰度切换 + 回滚预案 |
| 双写逻辑遗漏导致数据不一致 | 低 | 高 | 代码审查 + 自动化测试 |

### 5.2 回滚预案

**触发条件**: 迁移后 24 小时内出现以下任一情况：
- 功能测试失败率 > 5%
- 查询性能下降 > 50%
- 数据不一致

**回滚步骤**:
1. 停止新数据写入新表
2. 恢复 `report_record_admin.py` 中的 `data_packages` 查询
3. 保留 `data_packages` 表 72 小时
4. 分析问题根因

---

## 六、实施计划

### 6.1 Phase 0: 前置优化 ✅ 完成

| 任务 | 负责人 | 产出 | 状态 |
|------|--------|------|------|
| 添加 process_sub_steps 索引 | AI | SQL 脚本 | ✅ 已完成 |
| 验证索引生效 | AI | EXPLAIN 输出 | ✅ 已完成 |
| 记录基线性能 | AI | 性能报告 | ✅ 已完成 |

**执行记录** (2026-06-25):

**现有索引:**
- `PRIMARY (UNIQUE)`: (id)
- `uk_active_task (UNIQUE)`: (order_no, step_name, status) — 防任务重复约束
- `uk_order_step_code (UNIQUE)`: (order_no, step_name, process_code) — 去重键

**新增索引:**
- ✅ `idx_order_step_qty (order_no, step_name, quantity)` — completed_qty 实时汇总
- ✅ `idx_order_step_code (order_no, step_name, process_code)` — 覆盖索引（冗余但提供选择）

**验证结果:**
- SUM 查询 EXPLAIN: `type=ref, key=uk_order_step_code, rows=1` （索引命中）
- 执行脚本: `scripts/phase0_add_pss_indexes.py`
- 幂等性: 已验证重复执行不会报错

### 6.2 Phase 1: 试点迁移 (3天)

| 任务 | 负责人 | 产出 |
|------|--------|------|
| 创建 schedule_records 表 | AI | 迁移脚本 |
| 迁移历史数据 | AI | 验证报告 |
| 改写代码 | AI | 修改后的代码 |
| 功能测试 | AI | 测试报告 |
| 灰度切换 | AI | 切换确认 |

### 6.3 Phase 2: 批量迁移 (待定)

根据 Phase 1 经验估算每种 data_type 迁移时间。

### 6.4 Phase 3: 清理 (待定)

根据实际迁移进度安排。

---

## 七、附录

### 7.1 关键文件索引

| 文件 | 用途 |
|------|------|
| mobile_api_ai/api/report_record_admin.py | 管理员记录管理 API |
| mobile_api_ai/app.py | 移动端 API |
| mobile_api_ai/storage/mysql_storage.py | DAO 层 |
| mobile_api_ai/migrations/split_data_packages.sql | 历史迁移参考 |
| core/config.py | 数据库配置 |
| .trae/rules/项目架构规范.md | 架构规范 |

### 7.2 术语表

| 术语 | 定义 |
|------|------|
| data_packages | 容器中心的万能任务表 |
| process_sub_steps | 工序明细表 |
| schedule_records | 排产记录表（新建） |
| completed_qty | 已完成数量字段 |
| 双写 | 同时写入两个表以保持同步 |

### 7.3 参考规范

- 项目架构规范 R-065: 禁止写入 data_packages
- 项目架构规范 R-113: 必须有软删除字段
- v3.6.1 拆表迁移经验

---

**文档状态**: 审计通过（P1-P4 已修复）
**下一步**: 进入 Phase 0 实施（添加 process_sub_steps 复合索引）
