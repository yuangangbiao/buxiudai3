param(
    [Parameter(Mandatory)]
    [string]$QuantumId,
    [string[]]$InputFiles,
    [string]$VerifyCommand,
    [string]$ChangeDir
)

$PASS = 0
$FAIL = 0

Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  校验量子: $QuantumId" -ForegroundColor Cyan
Write-Host "  时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan

# Step 1: Input contract — 文件存在性检查
if ($InputFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "[步骤 1/3] 输入契约验证（文件存在性）" -ForegroundColor Yellow
    Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
    $allExist = $true
    foreach ($f in $InputFiles) {
        $resolved = if ($ChangeDir) { Join-Path $ChangeDir $f } else { $f }
        if (Test-Path $resolved) {
            Write-Host "  ✅ $f" -ForegroundColor Green
            $PASS++
        } else {
            Write-Host "  ❌ $f — 文件不存在！" -ForegroundColor Red
            $allExist = $false
            $FAIL++
        }
    }
    if (-not $allExist) {
        Write-Host "`n❌ 输入契约验证失败，中止校验" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 输入契约验证通过" -ForegroundColor Green
}

# Step 2: 执行验证命令
if ($VerifyCommand) {
    Write-Host ""
    Write-Host "[步骤 2/3] 执行验证命令" -ForegroundColor Yellow
    Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  \$ $VerifyCommand" -ForegroundColor Gray

    $cwd = if ($ChangeDir) { $ChangeDir } else { Get-Location }
    Push-Location $cwd
    try {
        $output = Invoke-Expression $VerifyCommand 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($exitCode -eq 0) {
        Write-Host "✅ 验证通过 (exit code: $exitCode)" -ForegroundColor Green
        if ($output) {
            Write-Host "── 输出 ──" -ForegroundColor DarkGray
            $output | ForEach-Object { Write-Host "  $_" }
            Write-Host "──────────" -ForegroundColor DarkGray
        }
        $PASS++
    } else {
        Write-Host "❌ 验证失败 (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "── 输出 ──" -ForegroundColor DarkGray
        $output | ForEach-Object { Write-Host "  $_" }
        Write-Host "──────────" -ForegroundColor DarkGray
        $FAIL++
        exit 1
    }
}

# Step 3: 输出契约 — 本次仅有文件存在性检查
Write-Host ""
Write-Host "[步骤 3/3] 输出契约摘要" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  通过: $PASS | 失败: $FAIL" -ForegroundColor $(if ($FAIL -eq 0) { "Green" } else { "Red" })
Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  量子 $QuantumId 校验结果: $(if ($FAIL -eq 0) { '✅ 通过' } else { '❌ 失败' })" -ForegroundColor $(if ($FAIL -eq 0) { "Green" } else { "Red" })
Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($FAIL -gt 0) { exit 1 }
