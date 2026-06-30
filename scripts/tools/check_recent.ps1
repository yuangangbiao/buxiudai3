# Quick check: only recent items and project-related items
Write-Host "=== Recycle Bin Quick Scan ==="
$shell = New-Object -ComObject Shell.Application
$recycle = $shell.NameSpace(0xa)
$items = $recycle.Items()
$total = $items.Count
Write-Host "Total items: $total"

$cutoff24h = (Get-Date).AddHours(-24)
$cutoff1h = (Get-Date).AddHours(-1)

Write-Host "`n--- Items deleted in last 24h ---"
$count24h = 0
$count1h = 0
$wal24h = 0
$proj24h = 0
for ($i = 0; $i -lt $total; $i++) {
    $item = $items.Item($i)
    $date = $item.ModifyDate
    $name = $item.Name
    if ($date -gt $cutoff24h) {
        $count24h++
        if ($date -gt $cutoff1h) { $count1h++ }
        if ($name -match '\.db-wal$|\.db-shm$|\.db-journal$') { $wal24h++ }
        if ($name -match 'wechat_|container_|dispatch_|steel_belt|face_check|checkin') { $proj24h++; Write-Host "[$date] $name" }
    }
}
Write-Host "Last 24h total: $count24h"
Write-Host "Last 1h total: $count1h"
Write-Host "DB files in 24h: $wal24h"
Write-Host "Project files in 24h: $proj24h"
