#!/bin/bash
# 云端中继服务(cloud_relay)一键部署脚本
# 使用方法:
#   1. 上传 cloud_relay.py wechat_message_store.py wechat_app_bot.py logging_setup.py config.py .env 到同一目录
#   2. bash cloud_deploy_relay.sh

echo "========================================"
echo "  云端中继服务 - 一键部署"
echo "========================================"

# 1. 创建目录
echo "[1/5] 创建目录..."
mkdir -p logs
mkdir -p data

# 2. 安装依赖
echo "[2/5] 安装Python依赖..."
pip install flask requests python-dotenv waitress -q

# 3. 检查必要文件
echo "[3/5] 检查必要文件..."
MISSING=0
for f in cloud_relay.py wechat_message_store.py wechat_app_bot.py logging_setup.py config.py .env; do
    if [ ! -f "$f" ]; then
        echo "  -- 缺少: $f"
        MISSING=1
    else
        echo "  OK $f"
    fi
done
if [ "$MISSING" = "1" ]; then
    echo "错误: 存在缺失文件，请上传后重试"
    exit 1
fi

# 4. 停止旧服务
echo "[4/5] 停止旧服务..."
pkill -f "python.*cloud_relay.py" 2>/dev/null || true
pkill -f "python.*wechat_cloud.py" 2>/dev/null || true
sleep 1

# 5. 启动新服务
echo "[5/5] 启动服务..."
nohup python cloud_relay.py > logs/cloud_relay.log 2>&1 &
sleep 3

if ps aux | grep -v grep | grep "cloud_relay.py" > /dev/null; then
    PID=$(pgrep -f "cloud_relay.py")
    echo ""
    echo "========================================"
    echo "  部署成功! PID: $PID"
    echo "========================================"
    echo "  服务:    cloud_relay (端口 5005)"
    echo "  健康:    curl http://localhost:5005/api/health"
    echo "  日志:    tail -f logs/cloud_relay.log"
    echo "  停止:    pkill -f cloud_relay.py"
    echo "========================================"
else
    echo "启动失败，请检查日志:"
    cat logs/cloud_relay.log
    exit 1
fi
