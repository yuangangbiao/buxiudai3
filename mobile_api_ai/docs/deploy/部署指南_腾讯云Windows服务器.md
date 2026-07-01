# 企业微信应用机器人 - 腾讯云服务器部署指南
# 服务器IP: 124.223.57.82
# 域名: api.ningjinchenshengshusongshebeiyouxiangongsi.com

# ============================================
# 一、远程连接服务器
# ============================================

使用Windows远程桌面连接 (mstsc):
  计算机: 124.223.57.82
  用户名: Administrator

# ============================================
# 二、安装Python
# ============================================

在服务器上操作:

1. 打开Edge浏览器
2. 访问: https://www.python.org/downloads/
3. 点击 "Download Python 3.11.9" (或最新版本)
4. 运行下载的安装程序

重要: 安装时务必勾选选项:
  ☑ Add Python to PATH
  ☑ Install pip

5. 安装完成后，打开CMD验证:
   python --version
   # 应显示: Python 3.11.x

# ============================================
# 三、准备部署目录
# ============================================

在服务器上，文件放在 `C:\Users\Administrator\Desktop\云端部署包\` 目录下：

```
C:\Users\Administrator\Desktop\云端部署包\
├── wechat_server.py
├── 云端一键启动.bat
├── stop_all.bat
├── bots/
├── commands/
├── services/
└── .env
```

# ============================================
# 四、上传代码文件
# ============================================

需要上传以下文件（保持同一目录结构）:

【核心文件】
- wechat_server.py          (Flask服务器主程序)
- bots/                     (机器人模块目录)
- commands/                  (指令管理目录)
- services/                  (服务目录)
- .env                      (配置文件)

【配置文件】
- WW_verify_PWFveCpOUtSmyNnB.txt  (企业微信校验文件)

【可选/辅助服务】
- container_center_api.py   (容器中心，端口5002)
- wechat_cloud.py           (云端辅助服务，端口5006)
- 云端一键启动.bat           (一键启动所有服务)
- start_wechat_cloud.bat    (单独启动云端辅助服务)
- stop_all.bat              (停止所有服务)

上传方式:
  方式1: 远程桌面时共享本地磁盘，直接复制粘贴
  方式2: 使用WinSCP: https://winscp.net/eng/downloads.php
  方式3: 在服务器下载代码压缩包

# ============================================
# 五、安装Python依赖
# ============================================

在服务器CMD中，进入部署目录执行:

cd C:\Users\Administrator\Desktop\云端部署包
python -m pip install flask requests python-dotenv

如果安装慢，可以使用国内镜像:
pip install flask requests python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple

# ============================================
# 六、验证校验文件
# ============================================

确认文件存在于部署目录中:
  C:\Users\Administrator\Desktop\云端部署包\WW_verify_PWFveCpOUtSmyNnB.txt

文件内容应该是:
  PWFveCpOUtSmyNnB

# ============================================
# 七、启动服务
# ============================================

方式1：一键启动（推荐）

在服务器上双击 `云端一键启动.bat`，将自动按顺序启动：
  1. 容器中心（端口 5002）：python container_center_api.py
  2. 微信服务主站（端口 5003）：python wechat_server.py --port 5003
  3. 云端辅助服务（端口 5006）：python wechat_cloud.py

启动后会自动校验各端口是否监听成功，并显示状态。

方式2：单独启动

在服务器CMD中执行:

cd C:\Users\Administrator\Desktop\云端部署包
python wechat_server.py --port 5003

如果看到以下信息表示启动成功:
  [Server] 服务初始化完成
  [Server] 启动服务器: 0.0.0.0:5003
   * Running on http://0.0.0.0:5003

方式3：停止服务

双击 `stop_all.bat` 将自动停止所有运行中的服务（5002/5003/5006）。

# ============================================
# 八、本地测试
# ============================================

在本地电脑浏览器访问:

http://124.223.57.82:5003/health
预期返回: {"status":"healthy","timestamp":"..."}

http://124.223.57.82:5003/api/wechat/status
预期返回: JSON格式的服务状态

# ============================================
# 九、企业微信后台配置
# ============================================

登录企业微信管理后台:
  https://work.weixin.qq.com/wework_admin/frame

进入应用设置:
  应用管理 → 点击应用(1000002) → 接收消息 → 设置API接收

配置参数:
  URL: http://api.ningjinchenshengshusongshebeiyouxiangongsi.com/api/wechat/hook
  Token: GtbDrIBIv3yy496Pl6
  EncodingAESKey: NFSApPWqoOXX7828qd424kdrVn0BQqlHwMwmTWd52fb

点击"保存"完成配置

# ============================================
# 十、设置开机自启（可选）
# ============================================

方式0: 启动文件夹（推荐）
1. 按 Win + R → 输入 `shell:startup` → 回车
2. 将 `云端一键启动.bat` 的快捷方式粘贴进去
3. 以后开机就会自动启动所有服务（5002/5003/5006）

方式1: 任务计划程序
1. 打开"任务计划程序"
2. 创建基本任务
3. 任务名: WeChatBot
4. 触发器: 计算机启动时
5. 操作: 启动程序
6. 程序/脚本: cmd.exe
7. 参数: /c start "云端服务" python wechat_server.py --port 5003
8. 起始位置: C:\Users\Administrator\Desktop\云端部署包\

方式2: 使用Windows服务(NSSM)
1. 下载NSSM: https://nssm.cc/
2. 解压到D:\nssm
3. CMD运行: D:\nssm\nssm.exe install WeChatBot
4. 配置应用程序路径

# ============================================
# 十一、常见问题
# ============================================

Q1: 提示"连接超时"
A1: 检查腾讯云安全组是否开放5003端口

Q2: 提示"无法验证URL"
A2: 检查校验文件是否正确放在目录中

Q3: pip安装失败
A3: 使用管理员权限运行CMD，或换国内镜像源

Q4: Python不是内部命令
A1: 重新安装Python，确保勾选"Add Python to PATH"

# ============================================
# 十二、联系方式
# ============================================

如有问题，请联系技术支持。
