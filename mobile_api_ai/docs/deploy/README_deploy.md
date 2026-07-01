# 部署指南

## 如何生成部署包

`deploy_prepared/` 目录已删除，不再维护独立副本。

部署时直接从主目录复制所需文件即可：

```powershell
# 创建部署目录
mkdir deploy_package

# 复制入口文件
copy wechat_server.py deploy_package\
copy container_center_v5.py deploy_package\

# 复制模块目录
copy -Recurse api\ deploy_package\api\
copy -Recurse bots\ deploy_package\bots\
copy -Recurse commands\ deploy_package\commands\
copy -Recurse services\ deploy_package\services\
copy -Recurse models\ deploy_package\models\

# 复制配置文件
copy requirements.txt deploy_package\
copy .env deploy_package\
copy WW_verify_PWFveCpOUtSmyNnB.txt deploy_package\
```

## 部署前检查清单

- [ ] `.env` 配置是否正确（企业微信凭证等）
- [ ] `requirements.txt` 依赖是否安装：`pip install -r requirements.txt`
- [ ] 端口配置是否与服务器环境一致（详见 `config.py`）

## 注意

- 所有代码以 `mobile_api_ai/` 主目录为准
- 部署时直接使用主目录文件，无需额外同步
- 配置项统一在 `config.py` 中管理，支持环境变量覆盖
