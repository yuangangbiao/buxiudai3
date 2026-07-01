# Cloudflare Tunnel 部署指南

## 方案说明

使用 Cloudflare Tunnel 将本地 API 服务暴露到互联网，无需公网IP、无需配置路由器。

**优点：**
- 完全免费
- 不需要公网IP
- 不需要配置路由器
- 自动HTTPS加密
- 不暴露数据库端口

---

## 部署步骤

### 第一步：注册 Cloudflare 账号

1. 访问 https://dash.cloudflare.com/
2. 注册账号（可用GitHub登录）
3. 添加你的域名或使用 Cloudflare 分配的免费域名

### 第二步：下载 cloudflared

**Windows 下载：**
```powershell
# 使用 winget 安装
winget install Cloudflare.cloudflared

# 或手动下载
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
```

**验证安装：**
```powershell
cloudflared --version
```

### 第三步：创建 Tunnel

```powershell
# 登录 Cloudflare
cloudflared tunnel login

# 创建隧道
cloudflared tunnel create mobile-report-tunnel

# 记住返回的 Tunnel ID (UUID格式)
```

### 第四步：配置文件

创建配置文件 `config.yml`：

```yaml
# d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/config.yml

tunnel: <你的Tunnel-ID>
credentials-file: C:/Users/<你的用户名>/.cloudflared/<你的Tunnel-ID>.json

ingress:
  - hostname: mobile-report.your-domain.com
    service: http://localhost:5000
  - service: http_status:404
```

### 第五步：配置DNS

```powershell
# 添加DNS记录
cloudflared tunnel route dns mobile-report-tunnel mobile-report.your-domain.com
```

### 第六步：启动服务

```powershell
# 启动隧道
cloudflared tunnel run mobile-report-tunnel

# 或后台运行
cloudflared tunnel run mobile-report-tunnel --loglevel debug
```

### 第七步：测试访问

```
https://mobile-report.your-domain.com/health
```

---

## 使用脚本（推荐）

创建启动脚本 `start_tunnel.bat`：

```batch
@echo off
cd /d %~dp0
echo ==========================================
echo AI增强版移动报工系统 - Cloudflare Tunnel
echo ==========================================
echo.

echo [1/3] 启动API服务器...
start "API Server" python app.py

echo [2/3] 等待API服务器启动...
timeout /t 3

echo [3/3] 启动Cloudflare Tunnel...
cloudflared tunnel run mobile-report-tunnel

pause
```

---

## 域名方式（无域名也可以）

如果不想用域名，Cloudflare 会分配一个临时域名：

```powershell
cloudflared tunnel --url http://localhost:5000
```

会显示类似：
```
your-tunnel.trycloudflare.com
```

员工访问这个地址即可。

---

## 安全配置

### 1. 只暴露API端口

```yaml
ingress:
  - hostname: mobile-report.your-domain.com
    service: http://localhost:5000
  - service: http_status:404
```

### 2. 添加认证（可选）

```yaml
ingress:
  - hostname: mobile-report.your-domain.com
    service: http://localhost:5000
    originRequest:
      httpHostHeader: localhost
  - service: http_status:404
```

### 3. IP白名单（企业微信内）

可以在企业微信后台配置IP白名单。

---

## 故障排查

### 隧道无法连接

```powershell
# 检查日志
cloudflared tunnel log mobile-report-tunnel

# 重新认证
cloudflared tunnel login
```

### DNS解析问题

```powershell
# 检查DNS记录
nslookup mobile-report.your-domain.com

# 刷新DNS
ipconfig /flushdns
```

### API服务无响应

```powershell
# 检查API是否正常
curl http://localhost:5000/health
```

---

## 成本估算

| 项目 | 费用 |
|------|------|
| Cloudflare Tunnel | 免费 |
| 域名（可选） | ~50元/年 |
| 云服务器（可选） | 0元（不需要） |
| **总计** | **0-50元/年** |

---

## 注意事项

1. **保持电脑开机**：员工访问时，你的电脑需要开机并运行 cloudflared
2. **网络稳定性**：家庭宽带稳定性影响访问体验
3. **带宽限制**：Cloudflare 免费版有带宽限制，适合小规模使用
4. **重启后重连**：电脑重启后需要重新运行 cloudflared

---

## 下一步

部署完成后，更新企业微信小程序的 API 地址为你的域名即可。
