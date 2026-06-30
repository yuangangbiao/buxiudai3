"""R13 修复打包 stage"""
import subprocess, sys

REPO = r'D:\yuan'
PROJ = r'D:\yuan\不锈钢网带跟单3.0'

files = [
    f'{PROJ}/core/_config_domain.py',
    f'{PROJ}/services/inventory_sync.py',
    f'{PROJ}/mobile_api_ai/template_engine.py',
    f'{PROJ}/tests/unit/utils/test_auto_schema_push.py',
    f'{PROJ}/tests/test_v354_error_recovery.py',
    f'{PROJ}/tests/test_v354_perf.py',
    f'{PROJ}/tests/unit/test_template_engine.py',
    f'{PROJ}/tests/unit/core/test_process_code_custom.py',
    f'{PROJ}/tests/unit/core/test_process_code_order.py',
    f'{PROJ}/tests/unit/services/test_inventory_sync_complete.py',
    f'{PROJ}/tests/unit/services/test_order_service.py',
    f'{PROJ}/tests/unit/utils/test_final_batch2.py',
    f'{PROJ}/scripts/migrate_templates_to_db.py',
    f'{PROJ}/scripts/sync_s1_deploy.py',
    f'{PROJ}/scripts/e2e_b0_register.py',
    f'{PROJ}/scripts/skip_legacy_tests.py',
    # S1 deploy output (新版本 + 备份)
    f'{PROJ}/mobile_api_ai/deploy_output/wechat_app_bot.py',
    f'{PROJ}/mobile_api_ai/deploy_output/cloud_backup.py',
    f'{PROJ}/mobile_api_ai/deploy_output/logging_setup.py',
    f'{PROJ}/mobile_api_ai/deploy_output/wechat_cloud.py',
    f'{PROJ}/mobile_api_ai/deploy_output/requirements.txt',
    f'{PROJ}/mobile_api_ai/deploy_output/templates/config_center.html',
    f'{PROJ}/mobile_api_ai/deploy_output/templates/container_dashboard.html',
    f'{PROJ}/mobile_api_ai/deploy_output/wechat_app_bot.py.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/cloud_backup.py.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/logging_setup.py.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/wechat_cloud.py.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/requirements.txt.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/templates/config_center.html.bak_pre_s1_sync',
    f'{PROJ}/mobile_api_ai/deploy_output/templates/container_dashboard.html.bak_pre_s1_sync',
]

result = subprocess.run(
    ['git', '-C', REPO, 'add', '--'] + files,
    capture_output=True, text=True
)
print('STDOUT:', result.stdout)
print('STDERR:', result.stderr[:500] if result.stderr else '')
print('RC:', result.returncode)

# Check staged
r2 = subprocess.run(
    ['git', '-C', REPO, 'diff', '--staged', '--name-only'],
    capture_output=True, text=True
)
staged = [l for l in r2.stdout.split('\n') if '不锈钢网带跟单3.0' in l]
print(f'\nSTAGED ({len(staged)} files):')
for f in staged:
    print(f'  {f}')
