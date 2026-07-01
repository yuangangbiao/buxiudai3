-- 对比数据库脚本
-- 请在 SQLite 命令行中运行

-- 连接根目录数据库
.connect D:\yuan\不锈钢网带跟单3.0\wechat_container.db

-- 查看根目录数据库
SELECT '根目录数据库' as DB, COUNT(*) as count FROM process_sub_steps;

-- 查看表列表
SELECT name, COUNT(*) as count FROM sqlite_master WHERE type='table' GROUP BY name;

-- 连接 mobile_api_ai 数据库
.connect D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db

SELECT 'mobile_api_ai数据库' as DB, COUNT(*) as count FROM process_sub_steps;

-- 连接 data 数据库
.connect D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\wechat_container.db

SELECT 'data数据库' as DB, COUNT(*) as count FROM process_sub_steps;
