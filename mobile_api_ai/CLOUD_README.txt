# 云端部署 - 最小文件集

## 只需上传这3个文件到云端:

| 文件 | 说明 |
|------|------|
| `wechat_cloud.py` | 云端服务主程序 |
| `wechat_app_bot.py` | 微信应用机器人 |
| `.env` | 配置文件 |

## 依赖安装（云端执行）:
```bash
pip install flask pycrypto werzeug
```

## 启动（云端执行）:
```bash
python wechat_cloud.py
```

---

## 可选：SSL配置
如有SSL证书，放置到:
- `ssl/cert.pem`
- `ssl/key.pem`

## 可选：一键脚本
上传 `cloud_deploy_mini.sh` 后执行:
```bash
bash cloud_deploy_mini.sh
```
