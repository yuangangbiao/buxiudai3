# BACKUP.md（备份与恢复方案）

> 文档版本：v1.0（2026-06-13）

---

## 一、备份策略

### 1.1 镜像表备份

**全量备份**（每日 02:00）：

```bash
# /etc/cron.daily/mirror_backup.sh
mysqldump -h $MYSQL_HOST -u root \
  --single-transaction --routines --triggers \
  container_center \
  orders_local production_orders_local violations_local \
  process_records_local work_orders_local process_sub_steps_local \
  | gzip > /backup/mirror/daily/mirror_$(date +%Y%m%d).sql.gz
```

**增量备份**（每 6 小时）：

```bash
# 通过 binlog 增量备份
mysqlbinlog --read-from-remote-server --host=$MYSQL_HOST --user=root \
  --raw --stop-never --result-file=/backup/mirror/binlog/ \
  mysql-bin.000001
```

**保留策略**：
- 每日全量：保留 7 天
- 每周全量：保留 4 周
- 每月全量：保留 12 个月

### 1.2 源表备份（已存在）

复用现有 `mysqldump` 策略备份 `steel_belt.*` 表。

### 1.3 配置文件备份

```bash
# 每周备份 .env, 启动脚本, SQL DDL
tar czf /backup/config/config_$(date +%Y%m%d).tar.gz \
  /opt/yuan/.env \
  /opt/yuan/scripts/start_*.sh \
  /opt/yuan/mobile_api_ai/migrations/
```

---

## 二、恢复流程

### 2.1 镜像表损坏恢复

```bash
# 1. 停止 5002 服务
ps aux | grep container_center_api | awk '{print $2}' | xargs kill

# 2. 删除损坏表
mysql -e "DROP TABLE container_center.orders_local"

# 3. 恢复最新备份
zcat /backup/mirror/daily/mirror_20260613.sql.gz | mysql container_center

# 4. 重新运行 DDL 升级（兼容老表）
mysql container_center < /opt/yuan/mobile_api_ai/migrations/v1.1.0_module/002_local_mirror_tables.sql

# 5. 重置 ETL 状态（强制全量）
mysql -e "TRUNCATE TABLE container_center._sync_state"

# 6. 启动 5002
python container_center_api.py

# 7. 验证
mysql -e "SELECT COUNT(*) FROM container_center.orders_local"
```

### 2.2 业务层读镜像表失败恢复

```bash
# 1. 检查错误
tail -f /opt/yuan/logs/container_center_5002.log

# 2. 启用降级开关（业务层读源表）
mysql -e "UPDATE container_center.feature_flags SET enabled=0 WHERE name='use_local_mirror'"

# 3. 业务层将读 steel_belt.orders 等

# 4. 修复镜像表（见 2.1）

# 5. 关闭降级
mysql -e "UPDATE container_center.feature_flags SET enabled=1 WHERE name='use_local_mirror'"
```

### 2.3 outbox 死信清理

```sql
-- 查看死信
SELECT COUNT(*) FROM sync_outbox WHERE status='dead';

-- 批量重置
UPDATE sync_outbox 
SET status='pending', retry_count=0, last_error=NULL 
WHERE status='dead' AND created_at > DATE_SUB(NOW(), INTERVAL 1 DAY);

-- 长期死信（已确认无法处理）直接删除
DELETE FROM sync_outbox 
WHERE status='dead' AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

## 三、容量规划

| 表 | 当前预估 | 1 年后 | 备份大小 |
|----|----------|--------|----------|
| orders_local | 1 万行 | 5 万行 | 50 MB |
| production_orders_local | 5 千行 | 2 万行 | 20 MB |
| violations_local | 1 千行 | 1 万行 | 10 MB |
| process_records_local | 5 万行 | 50 万行 | 500 MB |
| work_orders_local | 1 万行 | 10 万行 | 100 MB |
| process_sub_steps_local | 50 万行 | 800 万行（90天保留 → 200万）| 2 GB |
| **总备份大小** | - | - | **~3 GB/日** |

---

## 四、参考

- [RUNBOOK.md](./RUNBOOK.md) - 运维操作手册
- [FALLBACK.md](./FALLBACK.md) - 降级方案
