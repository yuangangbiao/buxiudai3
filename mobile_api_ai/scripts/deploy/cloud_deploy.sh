#!/bin/bash
# 云端一键部署脚本
# 使用方法:
#   1. 将以下文件上传到云服务器同一目录:
#      wechat_cloud.py wechat_app_bot.py logging_setup.py config.py .env requirements.txt
#   2. bash cloud_deploy.sh

echo "========================================"
echo "  微信云端服务 - 一键部署"
echo "========================================"

# 1. 创建目录
echo "[1/6] 创建目录..."
mkdir -p logs
mkdir -p ssl

# 2. 安装依赖
echo "[2/6] 安装Python依赖..."
pip install flask requests python-dotenv pyopenssl -q

# 3. 检查必要文件
echo "[3/6] 检查必要文件..."
MISSING=0
for f in wechat_cloud.py wechat_app_bot.py logging_setup.py config.py .env operators.json data/enterprise_structure.json; do
    if [ ! -f "$f" ]; then
        echo "  ❌ 缺少: $f"
        MISSING=1
    else
        echo "  ✅ $f"
    fi
done
if [ "$MISSING" = "1" ]; then
    echo "错误: 存在缺失文件，请上传后重试"
    exit 1
fi

# 4. 配置云端环境变量（关键步骤）
echo "[4/6] 配置云端环境变量..."

# 4a. WECHAT_CLOUD_HOST 必须为空（云端直接调Webhook，无需转发）
if grep -q "^WECHAT_CLOUD_HOST=" .env; then
    sed -i 's/^WECHAT_CLOUD_HOST=.*/WECHAT_CLOUD_HOST=/' .env
else
    echo "WECHAT_CLOUD_HOST=" >> .env
fi
echo "  ✅ WECHAT_CLOUD_HOST= (已置空，云端将直接调用Webhook)"

# 4b. 确保 FLASK_PORT=5005
if grep -q "^FLASK_PORT=" .env; then
    sed -i 's/^FLASK_PORT=.*/FLASK_PORT=5005/' .env
else
    echo "FLASK_PORT=5005" >> .env
fi
echo "  ✅ FLASK_PORT=5005"

# 5. 停止旧服务
echo "[5/6] 停止旧服务..."
pkill -f "python.*wechat_cloud.py" 2>/dev/null || true
sleep 1

# 6. 启动新服务
echo "[6/6] 启动服务..."
nohup python wechat_cloud.py > logs/cloud.log 2>&1 &
sleep 3

# 检查是否启动成功
if ps aux | grep -v grep | grep "wechat_cloud.py" > /dev/null; then
    PID=$(pgrep -f "wechat_cloud.py")
    echo ""
    echo "========================================"
    echo "  ✅ 部署成功! PID: $PID"
    echo "========================================"
    echo "  服务地址: http://公网IP:5005"
    echo "  健康检查: curl http://localhost:5005/health"
    echo "  查看日志: tail -f logs/cloud.log"
    echo "  停止服务: pkill -f wechat_cloud.py"
    echo "========================================"
else
    echo "❌ 启动失败，请检查日志:"
    cat logs/cloud.log
    exit 1
fi
