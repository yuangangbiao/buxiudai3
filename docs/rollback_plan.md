# data_packages 迁移 - 回滚方案

## 一、回滚触发条件

以下情况需回滚：
1. API 返回错误率 > 1%
2. 前端出现字段 undefined 报错
3. 数据写入丢失
4. 并发操作出现数据不一致

## 二、回滚步骤

### 2.1 代码回滚（立即）

```bash
# 1. 查看修改的文件
git status

# 2. 回滚 app.py 修改
git checkout HEAD -- mobile_api_ai/app.py

# 3. 回滚 report_record_admin.py 修改
git checkout HEAD -- mobile_api_ai/api/report_record_admin.py

# 4. 确认回滚
git diff --stat
```

### 2.2 数据回滚（如需要）

```sql
-- 如果有数据丢失，从备份表恢复（如果创建了备份表）
-- 注意：只有在新表有数据时才需要

-- 方案 A：从 data_packages 恢复（如果表存在）
INSERT INTO data_packages (id, type, related_order, title, ...)
SELECT id, type, order_no, product_name, ...
FROM schedule_records;

INSERT INTO data_packages (id, type, related_order, title, ...)
SELECT id, source, order_no, title, ...
FROM material_records;

-- 方案 B：保留新表，等待修复后重新部署
-- 不删除新表，标记为待用
```

## 三、预防措施

### 3.1 部署前备份

```sql
-- 备份现有数据
CREATE TABLE IF NOT EXISTS data_packages_backup_20260625 AS
SELECT * FROM data_packages WHERE 1=0;  -- 仅复制结构

INSERT INTO data_packages_backup_20260625
SELECT * FROM data_packages;

-- 如果 data_packages 不存在，创建空备份表
CREATE TABLE IF NOT EXISTS data_packages_backup_20260625 (
    id VARCHAR(64),
    data_type VARCHAR(50),
    related_order VARCHAR(64),
    title VARCHAR(255),
    content JSON,
    status VARCHAR(32),
    priority VARCHAR(32),
    target_operator VARCHAR(64),
    operator_id VARCHAR(64),
    quantity DECIMAL(12,2),
    created_at DATETIME,
    updated_at DATETIME
);
```

### 3.2 灰度验证

1. 部署前先在测试环境验证
2. 生产环境先切 10% 流量
3. 监控 30 分钟无异常后继续放量

## 四、快速回滚命令

```bash
# 单行命令回滚
git stash && git checkout HEAD~1 -- mobile_api_ai/app.py mobile_api_ai/api/report_record_admin.py
```
