-- ============================================================
-- 完整回滚 SQL - 从 MySQL 镜像表方案回退到 SQLite 原始方案
-- [K9 修复 2026-06-14] 真实可执行的回滚步骤
-- ============================================================
-- 警告：执行此脚本将**完全回退**模块化改造
-- 适用场景：
--   1. 镜像表方案不可用
--   2. 5002 完全无法启动
--   3. 业务层无法读镜像表
-- ============================================================

-- 前提：先关闭 5002 进程
-- ps aux | grep container_center_api | awk '{print $2}' | xargs kill

-- ============================================================
-- 步骤 1：备份当前状态（防止回退后无法恢复）
-- ============================================================
-- 1.1 备份 MySQL 容器中心数据
mysqldump -h $MYSQL_HOST -u root --single-transaction --routines --triggers \
    container_center \
    | gzip > /backup/container_center_pre_rollback_$(date +%Y%m%d_%H%M%S).sql.gz

-- 1.2 备份源表（防止误操作）
mysqldump -h $MYSQL_HOST -u root --single-transaction \
    steel_belt orders production_orders process_records work_orders \
    violation_log process_sub_steps \
    | gzip > /backup/steel_belt_pre_rollback_$(date +%Y%m%d_%H%M%S).sql.gz


-- ============================================================
-- 步骤 2：关闭所有镜像表相关功能
-- ============================================================
-- 2.1 关闭 feature_flags（最关键）
UPDATE container_center.feature_flags SET enabled=0
WHERE name IN ('use_local_mirror', 'use_outbox_fallback',
               'enable_etl_sync', 'enable_hard_delete_sync',
               'enable_outbox_worker', 'enable_auto_cleanup');

-- 2.2 关闭 sync_outbox 调度（如果有）
UPDATE container_center.sync_outbox
SET status='processed', last_error='disabled by rollback'
WHERE status='pending';


-- ============================================================
-- 步骤 3：恢复 DB_PATHS 注释（回退到 SQLite）
-- ============================================================
-- 编辑 mobile_api_ai/core/config.py：
-- 1) 取消注释以下行（取消迁移时的删除注释）：
--    'wechat_container': 'data/wechat_container.db',
--    'container_center': 'data/container_center.db',
-- 2) 注释掉 CONTAINER_MYSQL_CFG（保留定义不删除）
--    # CONTAINER_MYSQL_CFG = { ... }  # 已禁用，回退到 SQLite


-- ============================================================
-- 步骤 4：回退到原始代码（可选）
-- ============================================================
-- 4.1 如果 5002 代码有大量镜像表读取改动，回退到 git 旧版本：
--    git checkout main~10 -- mobile_api_ai/container_center_api.py
--    git checkout main~10 -- mobile_api_ai/sync_bridge.py

-- 4.2 如果只回退 feature_flags，保留新代码：
--    业务层用 try/except 包装：try 读镜像表 except 读源表


-- ============================================================
-- 步骤 5：验证回退
-- ============================================================
-- 5.1 确认镜像表关闭
SELECT name, enabled FROM container_center.feature_flags
WHERE name LIKE 'use_%' OR name LIKE 'enable_%';
-- 预期：所有 enabled=0

-- 5.2 确认 outbox 关闭
SELECT COUNT(*) AS pending_count FROM container_center.sync_outbox
WHERE status='pending';
-- 预期：0

-- 5.3 启动 5002
-- python mobile_api_ai/container_center_api.py
-- 预期：5002 启动成功，但用 SQLite 读数据


-- ============================================================
-- 步骤 6：清理镜像表（可选，需要再次确认）
-- ============================================================
-- 警告：以下操作会**永久删除**镜像表数据
-- 仅在完全确认回退成功后才执行
-- DROP TABLE IF EXISTS container_center.orders_local;
-- DROP TABLE IF EXISTS container_center.production_orders_local;
-- DROP TABLE IF EXISTS container_center.process_records_local;
-- DROP TABLE IF EXISTS container_center.process_sub_steps_local;
-- DROP TABLE IF EXISTS container_center.work_orders_local;
-- DROP TABLE IF EXISTS container_center.violations_local;
-- DROP TABLE IF EXISTS container_center.sync_outbox;
-- DROP TABLE IF EXISTS container_center.etl_dead_letter;
-- DROP TABLE IF EXISTS container_center.feature_flags;


-- ============================================================
-- 步骤 7：恢复镜像表（如果步骤 6 执行后想恢复）
-- ============================================================
-- 7.1 恢复备份
-- zcat /backup/container_center_pre_rollback_*.sql.gz | mysql container_center

-- 7.2 重新跑 DDL
-- mysql container_center < mobile_api_ai/migrations/v1.1.0_module/002_local_mirror_tables.sql

-- 7.3 重新启用 feature_flags
-- UPDATE container_center.feature_flags SET enabled=1
-- WHERE name IN ('use_local_mirror', 'use_outbox_fallback',
--                'enable_etl_sync', 'enable_hard_delete_sync',
--                'enable_outbox_worker', 'enable_auto_cleanup');

-- 7.4 重启 5002
-- python mobile_api_ai/container_center_api.py
