#!/bin/bash
# -*- coding: utf-8 -*-
"""调拨死信清理 - crontab 安装脚本

TASK-T6 / TODO-T4
用法：
  bash scripts/install_transfer_reaper_cron.sh
或：
  ./scripts/install_transfer_reaper_cron.sh

Windows 用户请用：
  任务计划程序 → 创建基本任务 → 触发器：每天每小时 → 操作：启动程序
  程序：python  参数：scripts/transfer_reaper.py
"""
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REAPER="$PROJECT_DIR/scripts/transfer_reaper.py"

# 修复 L-6：日志路径可通过环境变量配置，避免 /var/log 写权限问题
DEFAULT_LOG_DIR="$PROJECT_DIR/logs"
LOG_DIR="${INVENTORY_LOG_DIR:-$DEFAULT_LOG_DIR}"
LOG="$LOG_DIR/transfer_reaper.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR" 2>/dev/null || {
  echo "[WARN] 无法创建日志目录 $LOG_DIR，使用 /tmp 兜底"
  LOG="/tmp/transfer_reaper.log"
}

echo "=== 调拨死信清理 - crontab 安装 ==="
echo "项目目录: $PROJECT_DIR"
echo "清理脚本: $REAPER"
echo "日志文件: $LOG"

# 检查脚本存在
if [ ! -f "$REAPER" ]; then
    echo "[FAIL] 清理脚本不存在: $REAPER"
    exit 1
fi

# 检查 python
PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
if [ -z "$PYTHON" ]; then
    echo "[FAIL] python 未找到"
    exit 1
fi
echo "Python: $PYTHON"

# 准备 crontab 行
CRON_LINE="0 * * * * cd $PROJECT_DIR && $PYTHON $REAPER >> $LOG 2>&1"

# 备份当前 crontab
crontab -l > /tmp/crontab.backup 2>/dev/null || true

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "transfer_reaper.py"; then
    echo "[SKIP] crontab 已存在 transfer_reaper 任务"
    crontab -l | grep "transfer_reaper"
    exit 0
fi

# 添加新行
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

# 验证
echo "[OK] 已添加 crontab 任务："
crontab -l | grep "transfer_reaper"

echo ""
echo "测试运行："
$PYTHON $REAPER
echo ""
echo "日志位置: $LOG"
echo "如需移除：crontab -e 删除对应行"
