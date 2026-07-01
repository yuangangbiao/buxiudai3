# -*- coding: utf-8 -*-
$mobileUrl = if ($env:MOBILE_SERVER_URL) { $env:MOBILE_SERVER_URL } else { "http://192.168.1.32:5003" }
$content = @"
**<big>[新任务] 张三 请查收！</big>**

---

**📋 订单：**`ORD2026050801`
**🏭 客户：**上海机械厂
**📦 产品：**100米 乙字形网带
**🔧 工序：**编织
**🎯 数量：**100
**⏰ 时间：**2026-05-10 10:30

---
👉 **<a href="$mobileUrl/task/A1B2C3D4">点击手机端快速处理任务</a>**

---
💡 回复 **"确认A1B2C3"** 来接收任务
"@

$pythonScript = @"
import os, sys, requests, json
from datetime import datetime

def load_env_config():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

    env_file2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DAT', '.env')
    if os.path.exists(env_file2):
        with open(env_file2, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

def send_broadcast(content):
    base_url = os.getenv('DISPATCH_CENTER_URL', 'http://localhost:5003')
    url = f"{base_url}/messages/send"
    payload = {"content": content, "channels": ["wechat_group"]}
    try:
        $timeout = if ($env:REQUEST_TIMEOUT_NORMAL) { [int]$env:REQUEST_TIMEOUT_NORMAL } else { 10 }
        resp = requests.post(url, json=payload, timeout=$timeout)
        return resp.json()
    except Exception as e:
        return {'code': 500, 'message': str(e)}

load_env_config()
result = send_broadcast(`"$content`")
print(json.dumps(result, ensure_ascii=False, indent=2))
"@

$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
Set-Content -Path $tempFile -Value $pythonScript -Encoding UTF8

$env:PYTHONIOENCODING = "utf-8"
python $tempFile
Remove-Item $tempFile -Force