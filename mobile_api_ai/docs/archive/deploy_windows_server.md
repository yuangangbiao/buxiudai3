# 企业微信应用机器人 - Windows服务器部署脚本
# 用于在Windows腾讯云服务器上部署

# ============================================
# 部署步骤
# ============================================

# 步骤1: 配置腾讯云安全组（需要在腾讯云控制台操作）
# ----------------------------------------
# 位置: 云服务器 → 安全组 → 添加入站规则
#
# 规则1: 开放5003端口
#   协议: TCP
#   端口: 5003
#   来源: 0.0.0.0/0
#
# 规则2: 开放3389端口（远程桌面）
#   协议: TCP
#   端口: 3389
#   来源: 0.0.0.0/0

# 步骤2: 修改域名解析
# ----------------------------------------
# 位置: DNSPod域名解析
#
# 记录类型: A
# 主机记录: api
# 记录值: 124.223.57.82
# TTL: 600

# 步骤3: 远程连接到Windows服务器
# ----------------------------------------
# 使用远程桌面连接 (mstsc)
# 计算机: 124.223.57.82
# 用户名: Administrator

# 步骤4: 在服务器上安装Python
# ----------------------------------------
# 下载Python: https://www.python.org/downloads/
# 安装时勾选: Add Python to PATH
# 安装版本: Python 3.9 或更高

# 步骤5: 在服务器上创建目录
# ----------------------------------------
# 创建目录: D:\wechat_bot

# 步骤6: 上传代码
# ----------------------------------------
# 使用以下方式之一上传代码：
# 1. 远程桌面共享本地磁盘，上传文件
# 2. 使用WinSCP上传
# 3. 使用PowerShell的Invoke-WebRequest

# 步骤7: 配置.env文件
# ----------------------------------------
# 编辑 D:\wechat_bot\mobile_api_ai\.env
# 更新以下配置:
#   WECHAT_CORP_ID=ww2a8dcc32f0c57889
#   WECHAT_AGENT_ID=1000002
#   WECHAT_SECRET=aM4kGTZiqfswfk4CEv5bmAo7EpMOujoDsjMZyhPWPPA
#   WECHAT_TOKEN=GtbDrIBIv3yy496Pl6
#   WECHAT_AES_KEY=NFSApPWqoOXX7828qd424kdrVn0BQqlHwMwmTWd52fb

# 步骤8: 安装依赖
# ----------------------------------------
# 打开CMD或PowerShell，运行:
# cd D:\wechat_bot\mobile_api_ai
# pip install flask requests python-dotenv

# 步骤9: 创建校验文件
# ----------------------------------------
# 将校验文件 WW_verify_PWFveCpOUtSmyNnB.txt
# 放入 D:\wechat_bot\mobile_api_ai\ 目录

# 步骤10: 启动服务
# ----------------------------------------
# cd D:\wechat_bot\mobile_api_ai
# python wechat_server.py

# 步骤11: 测试访问
# ----------------------------------------
# 访问: http://124.223.57.82:5003/health
# 访问: http://api.ningjinchenshengshusongshebeiyouxiangongsi.com/api/wechat/status

# ============================================
# 企业微信后台配置
# ============================================
#
# URL: http://api.ningjinchenshengshusongshebeiyouxiangongsi.com/api/wechat/hook
# Token: GtbDrIBIv3yy496Pl6
# EncodingAESKey: NFSApPWqoOXX7828qd424kdrVn0BQqlHwMwmTWd52fb
