import os, shutil

WORK = r'd:\yuan\不锈钢网带跟单3.0'
deleted = []

old_dirs = [
    'docs/v3.7.0',
    'docs/v3.7.2', 'docs/v3.7.3', 'docs/v3.7.4', 'docs/v3.7.5',
    'docs/v3.7.6', 'docs/v3.7.7', 'docs/v3.7.8', 'docs/v3.7.9',
    'docs/v3.8.0', 'docs/v3.8.1',
    'docs/v3.8.2_test_full_run', 'docs/v3.8.2_xiaosheng_audit', 'docs/v3.8.4_e2e_chain',
    'docs/云端去除调度中心功能', 'docs/企业微信应用机器人', 'docs/企业微信扫码报工',
    'docs/修复日志爆炸', 'docs/全面测试', 'docs/全项目代码质量扫描',
    'docs/内联对话框重构', 'docs/分批入库发货', 'docs/前端页面',
    'docs/发布模式修正与任务撤回', 'docs/备料对话框提取', 'docs/容器池持久化',
    'docs/工单产品类型修复', 'docs/工单绑定', 'docs/工序追踪与发布切换',
    'docs/库存功能优化', 'docs/库存系统安全加固', 'docs/微信消息通知系统',
    'docs/批次改造方案', 'docs/数据库架构优化', 'docs/数据引用路径修复',
    'docs/架构文档审计', 'docs/架构重构', 'docs/模块化改造', 'docs/模块化重构',
    'docs/消除裸except', 'docs/缓存架构', 'docs/规则对话框提取重构',
    'docs/订单号与工序对应检查', 'docs/阶段四_excel导入导出',
]

for d in old_dirs:
    dp = os.path.join(WORK, d)
    if os.path.isdir(dp):
        shutil.rmtree(dp)
        deleted.append(d)
        print(f'  ✅ 删除 {d}')

# 保留: v3.6.9, v3.7.1, TODO_v3.7.1.md, acceptance/, learning/, dispatch_center/, playwright/
print(f'\n共删除 {len(deleted)} 个目录')
print('保留: v3.6.9/, v3.7.1/, acceptance/, learning/, dispatch_center/, playwright/')
