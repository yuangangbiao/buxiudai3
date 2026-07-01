$ErrorActionPreference = 'Continue'
$tmp = "C:\temp_e2e"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$testBody = '{"order_no":"WO-TEST-001","work_order_no":"WO-TEST-001","product_name":"automation_test","quantity":10,"flow_type":"production"}'
$advBody = '{"operator":"test_op","notes":"e2e test"}'
$wxBody = '{"to_user":"@all","content":"E2E test OK","msg_type":"text"}'
[System.IO.File]::WriteAllText("$tmp\test_body.json", $testBody, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText("$tmp\adv_body.json", $advBody, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText("$tmp\wx_body.json", $wxBody, [System.Text.Encoding]::UTF8)

Write-Host "=== End-to-End Test ==="
Write-Host "[1] Health Check"
curl.exe -s --max-time 5 "http://localhost:5000/health" | Out-Null
Write-Host "  DC: $(if($LASTEXITCODE-eq0){'OK'}else{'FAIL'})"
curl.exe -s --max-time 5 "http://localhost:5002/health" | Out-Null
Write-Host "  CC: $(if($LASTEXITCODE-eq0){'OK'}else{'FAIL'})"
curl.exe -s --max-time 5 "http://localhost:5003/health" | Out-Null
Write-Host "  WX: $(if($LASTEXITCODE-eq0){'OK'}else{'FAIL'})"

Write-Host "[2] Create Process"
$r = curl.exe -s --max-time 5 -X POST -H "Content-Type: application/json" -d "@$tmp\test_body.json" "http://localhost:5002/api/processes"
$j = ConvertFrom-Json $r
$procId = $j.data.id
if ($j.code -eq 0) { Write-Host "  Created PID=$procId" } else { Write-Host "  FAIL: $($j.message)"; exit 1 }

Write-Host "[3] DC Query"
$r = curl.exe -s --max-time 5 "http://localhost:5000/api/dispatch-center/processes"
$j = ConvertFrom-Json $r
Write-Host "  Count: $($j.data.Count)"

Write-Host "[4] Advance Process"
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = curl.exe -s --max-time 15 -X POST -H "Content-Type: application/json" -d "@$tmp\adv_body.json" "http://localhost:5000/api/dispatch-center/processes/$procId/advance"
$sw.Stop()
$elapsed = $sw.ElapsedMilliseconds
$j = ConvertFrom-Json $r
if ($j.code -eq 0) { Write-Host "  Advance OK (${elapsed}ms)" } else { Write-Host "  Advance FAIL: $($j.message)" }

Start-Sleep 2

Write-Host "[5] Direct WeChat Send"
$sw2 = [Diagnostics.Stopwatch]::StartNew()
$r = curl.exe -s --max-time 15 -X POST -H "Content-Type: application/json" -d "@$tmp\wx_body.json" "http://localhost:5003/api/wechat/send"
$sw2.Stop()
$j2 = ConvertFrom-Json $r
$wxOK = if($j2.code -eq 0 -and $j2.success){"OK"}else{"FAIL"}
Write-Host "  WeChat: $wxOK ($($sw2.ElapsedMilliseconds)ms)"

if ($procId) {
    Write-Host "[6] Cleanup"
    curl.exe -s --max-time 5 -X DELETE "http://localhost:5002/api/processes/$procId" | Out-Null
    Write-Host "  Done"
}

Remove-Item "$tmp\*" -ErrorAction SilentlyContinue
Write-Host "=== All Done ==="
