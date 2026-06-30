"""运行 E2E 测试"""
import sys
import os
import datetime

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

# 重定向输出
log_file = open(r'd:\yuan\不锈钢网带跟单3.0\scripts\e2e_output.txt', 'w', encoding='utf-8')

import scripts.e2e_publish_test as e2e

log_file.write(f"E2E test completed at {datetime.datetime.now()}\n")
log_file.flush()
log_file.close()
