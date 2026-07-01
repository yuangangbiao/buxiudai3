#!/bin/bash
# 云端一键部署脚本 - 最小化版本
# 使用方法:
#   1. 上传必需文件到当前目录:
#      wechat_cloud.py wechat_app_bot.py logging_setup.py config.py .env operators.json data/enterprise_structure.json
#   2. bash cloud_deploy_mini.sh

set -e

echo "========================================"
echo "  微信云端服务 - 一键部署 (精简版)"
echo "========================================"

# 1. 创建目录
echo "[1/5] 创建目录..."
mkdir -p logs ssl

# 2. 安装依赖
echo "[2/5] 安装依赖..."
pip install flask requests python-dotenv pyopenssl -q

# 3. 配置云端环境变量
echo "[3/5] 配置云端环境变量..."

# WECHAT_CLOUD_HOST 必须为空（云端直接调Webhook）
if grep -q "^WECHAT_CLOUD_HOST=" .env 2>/dev/null; then
    sed -i 's/^WECHAT_CLOUD_HOST=.*/WECHAT_CLOUD_HOST=/' .env
else
    echo "WECHAT_CLOUD_HOST=" >> .env
fi

# FLASK_PORT=5005
if grep -q "^FLASK_PORT=" .env 2>/dev/null; then
    sed -i 's/^FLASK_PORT=.*/FLASK_PORT=5005/' .env
else
    echo "FLASK_PORT=5005" >> .env
fi

echo "  ✅ 环境变量已配置 (WECHAT_CLOUD_HOST=, FLASK_PORT=5005)"

# 4. 停止旧服务
echo "[4/5] 停止旧服务..."
pkill -f "python.*wechat_cloud.py" 2>/dev/null || true
sleep 1

# 5. 启动新服务
echo "[5/5] 启动服务..."
nohup python wechat_cloud.py > logs/cloud.log 2>&1 &
sleep 3

# 检查
if ps aux | grep -v grep | grep "wechat_cloud.py" > /dev/null; then
    PID=$(pgrep -f "wechat_cloud.py")
    echo ""
    echo "========================================"
    echo "  ✅ 部署成功! PID: $PID"
    echo "========================================"
    echo "  日志: tail -f logs/cloud.log"
    echo "  停止: pkill -f wechat_cloud.py"
    echo "  测试: curl http://localhost:5005/health"
else
    echo "❌ 启动失败"
    cat logs/cloud.log
    exit 1
fi
