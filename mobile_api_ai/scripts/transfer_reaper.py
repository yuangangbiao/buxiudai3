#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调拨死信清理 - 扫描 in_transit 超时自动取消

TASK-T6: DESIGN v2.0 缺陷 1.2 调拨"在途库存"数据一致性防护
建议添加到 crontab: 每小时执行一次
  0 * * * * cd /path/to/mobile_api_ai && python scripts/transfer_reaper.py

修复 M-4：超时小时数可通过环境变量 INVENTORY_TRANSFER_STALE_HOURS 调整（默认 24）
修复 M-4：失败时退出码非 0，cron 可识别
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inventory_web.services.transfer_service import TransferService


def main():
    print('[transfer_reaper] 开始扫描超时调拨...')
    count = TransferService.reap_stale_transfers()
    if count < 0:
        # 修复 M-4：失败用退出码 2 标识
        print('[transfer_reaper] 失败（退出码 2）', file=sys.stderr)
        sys.exit(2)
    print(f'[transfer_reaper] 已自动取消 {count} 个超时调拨')
    sys.exit(0)


if __name__ == '__main__':
    main()
