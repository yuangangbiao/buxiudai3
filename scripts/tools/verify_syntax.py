# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(base)

files = [
    'core/config.py',
    'mobile_api_ai/config.py',
    'mobile_api_ai/logging_setup.py',
    'mobile_api_ai/scripts/tools/logging_setup.py',
    'mobile_api_ai/app.py',
    'mobile_api_ai/wechat_work_bot_v2.py',
    'mobile_api_ai/container_api_server.py',
    'mobile_api_ai/container_config.py',
    'mobile_api_ai/container_center_api.py',
    'mobile_api_ai/dispatch_center.py',
    'mobile_api_ai/wecom_auth.py',
    'mobile_api_ai/bots/group_bot.py',
    'mobile_api_ai/services/session.py',
    'mobile_api_ai/modules/enhanced_backup.py',
    'mobile_api_ai/wechat_cloud.py',
    'mobile_api_ai/sync/sync_log.py',
    'mobile_api_ai/container_center_client.py',
    'mobile_api_ai/sync/handlers/worker_handler.py',
    'mobile_api_ai/sync/handlers/order_handler.py',
    'mobile_api_ai/sync/handlers/quality_handler.py',
    'mobile_api_ai/sync/handlers/attendance_handler.py',
    'mobile_api_ai/sync/handlers/sub_step_handler.py',
    'mobile_api_ai/api/decorators.py',
    'mobile_api_ai/api/swagger.py',
    'mobile_api_ai/tests/fixtures/wechat_cloud_debug.py',
]
all_ok = True
for f in files:
    full_path = os.path.join(base, f)
    try:
        compile(open(full_path, encoding='utf-8').read(), f, 'exec')
        print('OK:' + f)
    except SyntaxError as e:
        print('FAIL:' + f + ' -> ' + str(e))
        all_ok = False

if all_ok:
    print('\nAll ' + str(len(files)) + ' files passed syntax check')
else:
    print('\nSome files have syntax errors')
    sys.exit(1)
