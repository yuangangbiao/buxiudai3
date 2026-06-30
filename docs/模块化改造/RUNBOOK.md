# RUNBOOK.md（运维操作手册）

> 文档版本：v1.0（2026-06-13）
> 适用：5002 容器中心 / 8008 sync_bridge / 镜像表运维
> 维护：运维团队

---

## 一、目录

1. [服务启动失败排查](#一服务启动失败排查)
2. [outbox 死信处理](#二outbox-死信处理)
3. [镜像表与源表数据不一致修复](#三镜像表与源表数据不一致修复)
4. [紧急回滚方案](#四紧急回滚方案)
5. [常见问题 FAQ](#五常见问题-faq)

---

## 二、服务启动失败排查

### 5002 启动失败

**症状**：`python container_center_api.py` 报 ImportError 或 ModuleNotFoundError

**排查步骤**：

```bash
# 1. 检查 Python 路径
cd D:\yuan\不锈钢网带跟单3.0\mobile_api_ai
python -c "from core.config import MYSQL_CFG; print('OK')"

# 2. 检查环境变量
echo %MYSQL_HOST%
echo %CONTAINER_MYSQL_DATABASE%

# 3. 检查数据库连接
python -c "import pymysql; from core.config import CONTAINER_MYSQL_CFG; c=pymysql.connect(**CONTAINER_MYSQL_CFG); print('DB OK')"

# 4. 检查镜像表 DDL
mysql -h $MYSQL_HOST -u root container_center < migrations/v1.1.0_module/002_local_mirror_tables.sql
```

### 5002 启动后立刻退出

**症状**：5002 启动 5 秒后无响应

**排查步骤**：

```bash
# 1. 查看日志
tail -f logs/container_center_5002.log

# 2. 常见错误：
# - DB Connection refused: 数据库没起来
# - 8008 不可达: 8008 没启动
# - 5003 不可达: 5003 没启动
```

---

## 二、outbox 死信处理

### 症状

`outbox_dead_letter_alert` 表新增告警，或 5003 微信收到死信告警。

### 死信定义

- 状态 `status='dead'` 表示 5 次重试全部失败
- 通常原因：5002 镜像表字段不匹配 / 鉴权失败 / 业务层拒绝

### 处理步骤

```sql
-- 1. 查看死信
SELECT id, trace_id, action, last_error, created_at 
FROM sync_outbox 
WHERE status = 'dead' 
ORDER BY created_at DESC 
LIMIT 20;

-- 2. 分析 last_error
-- 例 1: 'MIRROR 鉴权失败' → 检查 IP 白名单
-- 例 2: 'Unknown column uuid' → 镜像表 DDL 缺失
-- 例 3: 'CHECK constraint violated' → 数据值非法

-- 3. 修复问题后手动重试
UPDATE sync_outbox 
SET status='pending', retry_count=0, last_error=NULL 
WHERE id=? AND status='dead';

-- 4. 等待下次 outbox worker 处理（每 30s）
```

### 预防措施

- 死信出现后立即处理，否则数据永久丢失
- 每周一次死信清理（status='processed' and processed_at < NOW() - 7 DAY）
- 监控死信数 > 10 触发 1 级告警

---

## 三、镜像表与源表数据不一致修复

### 症状

业务层读镜像表数据与源表（steel_belt）不一致。

### 常见不一致场景

| 场景 | 原因 | 修复方法 |
|------|------|----------|
| 镜像表少数据 | ETL 同步延迟（60s）| 等待下轮同步 |
| 镜像表多数据 | 源表硬删后镜像表未删 | 等 G2 修复后自动清理 |
| 镜像表数据旧 | 业务层先写后 ETL 未追上 | 改用 mirror 直写 |
| 字段值不一致 | 业务层格式问题 | 查镜像表 _source 字段 |

### 修复脚本

```python
# scripts/fix_mirror_inconsistency.py
# 1. 比对镜像表与源表行数
SELECT COUNT(*) FROM orders_local;
SELECT COUNT(*) FROM steel_belt.orders WHERE is_deleted=0;

# 2. 找出镜像表有但源表无的
SELECT order_no FROM orders_local 
WHERE order_no NOT IN (SELECT order_no FROM steel_belt.orders);

# 3. 找出源表有但镜像表无的
SELECT order_no FROM steel_belt.orders 
WHERE is_deleted=0 AND order_no NOT IN (SELECT order_no FROM orders_local);

# 4. 修复：触发全量同步
UPDATE _sync_state SET last_sync_time='2000-01-01 00:00:00' WHERE table_name='orders_local';
```

---

## 四、紧急回滚方案

### 场景

5002 容器中心故障，业务层无法读镜像表。

### 步骤

#### 步骤 1：业务层降级到读源表

```python
# 在 _get_mysql_connection 中添加降级逻辑
def _get_mysql_connection(use_fallback=False):
    """读镜像表，失败时降级到读源表"""
    try:
        if use_fallback:
            return _get_source_db_connection()  # 读 steel_belt
        return _get_local_db_connection()  # 读 container_center
    except Exception as e:
        logger.warning(f'降级到源表: {e}')
        return _get_source_db_connection()
```

#### 步骤 2：关闭 5002，启老服务

```bash
# 1. 停止 5002
ps aux | grep container_center_api | awk '{print $2}' | xargs kill

# 2. 启动老服务（如果保留）
python legacy_container_server.py
```

#### 步骤 3：恢复 5002

```bash
# 1. 修复 5002 问题
# 2. 启动 5002
python container_center_api.py

# 3. 验证镜像表数据
mysql -e "SELECT COUNT(*) FROM container_center.orders_local"
```

### 回滚验证清单

- [ ] 镜像表行数 > 0
- [ ] ETL 同步正常（查看日志）
- [ ] 业务层读镜像表返回数据
- [ ] 写接口返回成功
- [ ] outbox 死信 < 10

---

## 五、常见问题 FAQ

### Q1: 5002 启动后端口被占用

**A**: 5002 端口冲突。`netstat -ano | findstr 5002`，杀掉占用进程。

### Q2: 镜像表同步延迟超过 60s

**A**: 
- 检查 ETL worker 是否在跑（5002 日志 `[ETL Worker]`）
- 检查 MySQL 连接：镜像表 + 源表都可达
- 检查源表是否有锁（`SHOW PROCESSLIST`）

### Q3: outbox 写入失败

**A**:
- 检查 `sync_outbox` 表是否存在
- 检查 `CONTAINER_MYSQL_CFG` 是否正确
- 失败时 mirror 数据会**丢失**！建议定期导出 8008 日志补偿

### Q4: 业务层读不到订单

**A**:
- 查 `SELECT 1 FROM orders_local WHERE order_no=?`
- 如果空：ETL 未同步，等下轮或手动触发
- 如果 is_deleted=1：订单已软删除，业务层应过滤

### Q5: 报工 sub_step 提交后未出现

**A**:
- 查 5002 业务层日志 `[MIRROR]`
- 查 5002 `_local` 表是否有数据
- 查 8008 sync_bridge 日志 `[8008->5002]`

### Q6: trace_id 在哪里

**A**: 每次 HTTP 请求自动生成（X-Trace-Id header），在 5002 业务层日志输出。

---

## 六、紧急联系方式

| 角色 | 姓名 | 电话 |
|------|------|------|
| 架构师 | - | - |
| DBA | - | - |
| 运维 | - | - |
| 业务负责人 | - | - |

---

## 七、参考

- [FALLBACK.md](./FALLBACK.md) - 降级方案
- [GRAYSCALE.md](./GRAYSCALE.md) - 灰度切换
- [SLO.md](../SLO.md) - 监控告警
