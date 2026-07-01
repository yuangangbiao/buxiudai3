# v3.6.1 数据库迁移执行指南

## 任务：防止任务重复创建 - 数据库唯一约束

**优先级**：🟢 立即执行
**预计耗时**：1 小时（含验证）
**风险等级**：中（仅删除重复记录+添加索引）

---

## 📋 概述

为防止任务重复创建，添加 4 张任务表的唯一索引：

| 表 | 唯一字段 | 索引名 |
|----|---------|--------|
| `process_sub_steps` | (order_no, step_name, status) | uk_active_task |
| `quality_records` | (order_no, process_name, status) | uk_active_quality |
| `material_records` | (order_no, material_name, status) | uk_active_material |
| `outsource_records` | (order_no, title, status) | uk_active_outsource |

**重要**：因为 status 字段是 `'completed'` / `'withdrawn'` 等终态，索引对历史记录也生效；如果有历史重复记录，会添加失败。所以**必须先清理重复**。

---

## 🚀 执行步骤

### 第 1 步：备份（必做）

```bash
# 备份 4 张表
mysqldump -u root -p container_center \
  process_sub_steps quality_records material_records outsource_records \
  > migrations/backup_4tables_$(date +%Y%m%d_%H%M%S).sql
```

### 第 2 步：DRY-RUN 检查（必做）

```bash
cd D:\yuan\不锈钢网带跟单3.0\mobile_api_ai

# 方式 A：通过 run.py 父类工具
python migrations/run.py status
python migrations/run.py upgrade

# 方式 B：直接运行独立脚本（推荐）
python migrations/0620_prevent_task_duplicates.py --dry-run
```

**预期输出**：
```
[1] process_sub_steps 表去重约束
   [DRY-RUN] 将创建索引 uk_active_task
[2] quality_records 表去重约束
   [DRY-RUN] 将创建索引 uk_active_quality
[3] material_records 表去重约束
   [DRY-RUN] 将创建索引 uk_active_material
[4] outsource_records 表去重约束
   [DRY-RUN] 将创建索引 uk_active_outsource
[5] 验证迁移结果
   ⚠️  process_sub_steps.uk_active_task 缺失
   ⚠️  quality_records.uk_active_quality 缺失
   ⚠️  material_records.uk_active_material 缺失
   ⚠️  outsource_records.uk_active_outsource 缺失

[DRY-RUN] 预演完成，无数据修改
```

**重点检查**：
- ⚠️ 如果有"清理重复: X 条"输出，**记录 X 的数量**，删除后无法恢复（除非用第 1 步的备份）
- ⚠️ 如果 X 很大（>100），建议先人工 review 哪些数据被删

### 第 3 步：实际执行

```bash
python migrations/0620_prevent_task_duplicates.py
```

不加任何参数默认是 **execute** 模式。

**预期输出**：
```
[1] process_sub_steps 表去重约束
   清理重复: 0 条
   ✅ 索引 uk_active_task 创建成功
[2] quality_records 表去重约束
   清理重复: 0 条
   ✅ 索引 uk_active_quality 创建成功
[3] material_records 表去重约束
   清理重复: 0 条
   ✅ 索引 uk_active_material 创建成功
[4] outsource_records 表去重约束
   清理重复: 0 条
   ✅ 索引 uk_active_outsource 创建成功
[5] 验证迁移结果
   ✅ process_sub_steps.uk_active_task 已生效
   ✅ quality_records.uk_active_quality 已生效
   ✅ material_records.uk_active_material 已生效
   ✅ outsource_records.uk_active_outsource 已生效

✅ v3.6.1 防任务重复唯一约束已添加
```

### 第 4 步：迁移登记（必做）

```bash
python migrations/run.py upgrade
```

这会自动将迁移登记到 `schema_migrations` 表，下次执行 upgrade 时会跳过。

### 第 5 步：验证

```bash
# 登录 MySQL
mysql -u root -p container_center

# 查看迁移状态
SELECT * FROM schema_migrations WHERE version='20260620_prevent_task_duplicates';

# 查看索引
SHOW INDEX FROM process_sub_steps WHERE Key_name='uk_active_task';
SHOW INDEX FROM quality_records WHERE Key_name='uk_active_quality';
SHOW INDEX FROM material_records WHERE Key_name='uk_active_material';
SHOW INDEX FROM outsource_records WHERE Key_name='uk_active_outsource';
```

---

## 🔙 回滚（如需）

```bash
# 方式 A：使用 run.py 父类
python migrations/run.py downgrade -v 20260620_prevent_task_duplicates

# 方式 B：直接运行
python migrations/0620_prevent_task_duplicates.py --rollback
```

---

## ⚠️ 风险与限制

### 已知风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **删除数据** | 历史重复记录被永久删除 | 第 1 步先备份 |
| **索引冲突** | 如果有未发现的历史重复，ADD UNIQUE 会失败 | 第 2 步先 DRY-RUN |
| **性能影响** | 写操作多一步唯一检查（可忽略） | 无需缓解 |
| **应用兼容性** | 老代码未捕获 DuplicateKeyError 会 500 | 第 6 步同步更新应用层 |

### 限制

- 仅对 `container_center` 数据库生效
- 不影响 `steel_belt` 主库
- 不影响 `data_packages`（已废弃）
- 仅 `status IN ('pending', 'in_progress', 'distributed')` 时生效
- `status='completed'` / `'withdrawn'` 的历史记录仍允许重复

---

## 🔧 应用层配套修改（推荐）

数据库唯一约束生效后，应用层应捕获 `DuplicateKeyError`：

```python
# dispatch_center/_core.py 或新增任务时
try:
    conn.cursor().execute(
        "INSERT INTO process_sub_steps (...) VALUES (...)"
    )
    conn.commit()
except pymysql.err.IntegrityError as e:
    if e.args[0] == 1062:  # Duplicate entry
        logger.warning(f'任务重复（已由数据库拦截）: {e}')
        # 静默忽略或查询已存在记录
    else:
        raise
```

---

## 📊 业务效果

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 同时两次报工 | 2 条重复记录 | 1 条（数据库拦截） |
| 同一工序重复发布 | 2 条记录 | 1 条 |
| 同物料重复申请 | 2 条申请单 | 1 条 |
| 同外协任务重复派发 | 2 条派工记录 | 1 条 |

**重要**：此迁移不影响已完成或已撤回的记录（仅约束活跃状态）。

---

## 📞 故障排查

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| `OperationalError: 1062 Duplicate entry` | 已有重复数据 | 先执行 DELETE 清理 |
| `OperationalError: 1146 Table doesn't exist` | 表不存在 | 跳过该表（脚本已处理） |
| `Index uk_active_task already exists` | 索引已存在 | 脚本会自动跳过 |
| `Access denied for user` | 权限不足 | 用 root 用户或授予 INDEX 权限 |

---

## ✅ 完成检查清单

- [ ] 第 1 步：已备份 4 张表
- [ ] 第 2 步：DRY-RUN 通过，无大量重复
- [ ] 第 3 步：实际执行成功
- [ ] 第 4 步：迁移已登记到 schema_migrations
- [ ] 第 5 步：SHOW INDEX 确认索引存在
- [ ] 第 6 步：应用层代码已捕获 IntegrityError
- [ ] 重启 5008/5003 服务，应用正常启动
- [ ] 测试报工功能，不再产生重复记录

---

## 📅 执行记录

执行完成后，请在下方记录：

```
执行人：__________
执行时间：__________
DRY-RUN 输出（重复记录数）：
  - process_sub_steps: ___ 条
  - quality_records: ___ 条
  - material_records: ___ 条
  - outsource_records: ___ 条
实际执行输出：成功 / 失败
失败原因（如有）：__________
```

---

**最后更新**：2026-06-20
**版本**：v3.6.1
**作者**：Claude Code