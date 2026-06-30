$env:AGENT_BROWSER_HOME = "D:\yuan\agent-browser"
New-Item -ItemType Directory -Path "D:\yuan\agent-browser" -Force | Out-Null
& "C:\Users\lenovo\AppData\Roaming\npm\agent-browser.cmd" --headed open http://127.0.0.1:5009/mobile_unified.html
