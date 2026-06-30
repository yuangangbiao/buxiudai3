# 检查 Windows 审计策略
Write-Host "=== 当前审计策略 (对象访问) ==="
auditpol /get /subcategory:"对象访问"

Write-Host "`n=== 尝试搜索安全日志中文件删除事件 ==="
try {
    $events = Get-WinEvent -FilterHashtable @{LogName='Security';Id=4656,4663} -MaxEvents 200 -ErrorAction SilentlyContinue
    foreach ($event in $events) {
        $xml = [xml]$event.ToXml()
        $file = ""
        $process = ""
        $access = ""
        foreach ($data in $xml.Event.EventData.Data) {
            if ($data.Name -eq "ObjectName") { $file = $data.'#text' }
            if ($data.Name -eq "ProcessName") { $process = $data.'#text' }
            if ($data.Name -eq "AccessMask") { $access = $data.'#text' }
        }
        if ($file -match '\.db-wal|\.db-shm') {
            Write-Host "[$($event.TimeCreated)] PID:$process 文件:$file 访问:$access"
        }
    }
    if (-not $events) { Write-Host "没有找到相关安全事件" }
} catch {
    Write-Host "读取安全日志失败: $_"
}

Write-Host "`n=== 检查文件 SACL 配置 ==="
$path = "D:\yuan\不锈钢网带跟单3.0\data"
try {
    $acl = Get-Acl -Path $path -Audit -ErrorAction SilentlyContinue
    if ($acl.GetAuditRules($true,$true,[System.Security.Principal.NTAccount])) {
        Write-Host "SACL 已配置"
    } else {
        Write-Host "SACL 未配置 - 需要配置才能审计文件删除"
    }
} catch {
    Write-Host "读取 SACL 失败: $_"
}
