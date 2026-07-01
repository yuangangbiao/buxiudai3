# 企业微信应用机器人 - Windows服务器部署指南
# 服务器IP: 124.223.57.82

# ============================================
# 第一步：连接服务器
# ============================================

# 使用远程桌面连接 (mstsc)
# 计算机: 124.223.57.82
# 用户名: Administrator

# ============================================
# 第二步：安装Python
# ============================================

# 1. 在服务器上下载Python:
#    访问: https://www.python.org/ftp/python/
#    下载: python-3.11.9-embed-amd64.exe (或最新版本)

# 2. 安装时务必勾选: "Add Python to PATH"

# 3. 验证安装:
#    打开CMD，输入:
#    python --version

# ============================================
# 第三步：创建目录
# ============================================

# 在服务器上打开CMD，执行:
mkdir D:\wechat_bot
mkdir D:\wechat_bot\mobile_api_ai

# ============================================
# 第四步：上传代码
# ============================================

# 使用以下方式上传代码到 D:\wechat_bot\mobile_api_ai\
# 方式1: 远程桌面共享本地磁盘
# 方式2: WinSCP (https://winscp.net/)
# 方式3: 直接复制粘贴文件

# 需要上传的文件:
# - wechat_server.py
# - bots\ 整个目录
# - commands\ 整个目录
# - services\ 整个目录
# - bots\__init__.py
# - commands\__init__.py
# - services\__init__.py
# - .env
# - container_center_v5.py (如果存在)

# ============================================
# 第五步：安装依赖
# ============================================

# 在CMD中执行:
cd D:\wechat_bot\mobile_api_ai
python -m pip install flask requests python-dotenv

# ============================================
# 第六步：创建校验文件
# ============================================

# 在 D:\wechat_bot\mobile_api_ai\ 目录创建文件:
# 文件名: WW_verify_PWFveCpOUtSmyNnB.txt
# 内容: PWFveCpOUtSmyNnB

# ============================================
# 第七步：启动服务
# ============================================

# 在CMD中执行:
cd D:\wechat_bot\mobile_api_ai
python wechat_server.py

# 如果需要后台运行，使用:
# pythonw wechat_server.py

# ============================================
# 第八步：测试
# ============================================

# 在本电脑浏览器访问:
# http://124.223.57.82:5003/health
# 应返回: {"status":"healthy"}

# ============================================
# 第九步：配置企业微信
# ============================================

# 在企业微信管理后台配置:
# URL: http://api.ningjinchenshengshusongshebeiyouxiangongsi.com/api/wechat/hook
# Token: GtbDrIBIv3yy496Pl6
# EncodingAESKey: NFSApPWqoOXX7828qd424kdrVn0BQqlHwMwmTWd52fb

# ============================================
# 第十步：设置开机自启（可选）
# ============================================

# 方式1: 使用任务计划程序
#    计算机管理 → 任务计划程序 → 创建基本任务
#    触发器: 计算机启动时
#    操作: 启动程序
#    程序: pythonw.exe
#    参数: D:\wechat_bot\mobile_api_ai\wechat_server.py

# 方式2: 使用Windows服务
#    使用 NSSM (https://nssm.cc/)
#    nssm install WeChatBot
#    设置应用程序路径和参数
