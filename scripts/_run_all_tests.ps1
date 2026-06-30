param(
    $PYTHON = "C:\Users\lenovo\AppData\Local\Python\bin\python.exe",
    $ROOT = "d:\yuan\不锈钢网带跟单3.0"
)

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$results = @{}

function Run-Pytest {
    param(
        [string]$Label,
        [string[]]$Args,
        [string]$Cwd = $ROOT
    )
    $outputFile = Join-Path $ROOT "scripts\_test_output_${Label}_${TIMESTAMP}.txt"
    $reportFile = Join-Path $ROOT "scripts\_test_report_${Label}_${TIMESTAMP}.xml"

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "  $Label"
    $argsStr = $Args -join " "
    Write-Host "  Args: $PYTHON -m pytest $argsStr"
    Write-Host "============================================================"

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $PYTHON
    $psi.Arguments = "-m pytest $argsStr --tb=short --junitxml=$reportFile"
    $psi.WorkingDirectory = $Cwd
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()

    $exitCode = $proc.ExitCode

    $out = "STDOUT:`n$stdout`n`nSTDERR:`n$stderr`n`nEXIT: $exitCode"
    [System.IO.File]::WriteAllText($outputFile, $out, [System.Text.Encoding]::UTF8)

    $lines = $stdout -split "`n"
    $summary = ($lines | Where-Object { $_ -match "passed" -or $_ -match "failed" -or $_ -match "error" } | Select-Object -Last 1)
    if ($summary) {
        Write-Host "  Summary: $($summary.Trim())"
    } else {
        $preview = if ($stdout.Length -gt 0) { $stdout.Substring(0, [Math]::Min(300, $stdout.Length)) } else { "(empty)" }
        Write-Host "  Output: $preview"
    }
    if ($stderr -and $stderr.Length -gt 0) {
        $errPreview = $stderr.Substring(0, [Math]::Min(200, $stderr.Length))
        Write-Host "  Stderr: $errPreview"
    }

    $script:results[$Label] = @{
        Exit = $exitCode
        OutFile = $outputFile
        ReportFile = $reportFile
        Summary = if ($summary) { $summary.Trim() } else { "" }
    }

    return $exitCode -eq 0
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  Full Project Regression Tests"
Write-Host "  Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "============================================================"

Run-Pytest -Label "root_unit_tests" -Args @(
    "tests/unit",
    "-v",
    "-p", "no:cacheprovider",
    "--ignore=tests/unit/test_event_bus_factory.py"
)

$mobileRoot = Join-Path $ROOT "mobile_api_ai"
Run-Pytest -Label "mobile_api_unit_tests" -Args @(
    "tests/unit",
    "-v",
    "-p", "no:cacheprovider"
) -Cwd $mobileRoot

Run-Pytest -Label "integration_tests" -Args @(
    "tests/integration",
    "-v",
    "-p", "no:cacheprovider"
)

Run-Pytest -Label "all_tests_no_e2e" -Args @(
    "tests/",
    "-v",
    "-p", "no:cacheprovider",
    "--ignore=tests/e2e"
)

Write-Host ""
Write-Host "============================================================"
Write-Host "  Summary"
Write-Host "============================================================"

$allPass = $true
foreach ($label in $script:results.Keys) {
    $info = $script:results[$label]
    $status = if ($info.Exit -eq 0) { "PASS" } else { "FAIL" }
    $icon = if ($info.Exit -eq 0) { "[OK]" } else { "[!!]" }
    Write-Host "  $icon $status $label"
    Write-Host "       Report: $($info.ReportFile)"
    Write-Host "       Output: $($info.OutFile)"
    if ($info.Exit -ne 0) { $allPass = $false }
}
Write-Host "============================================================"

if ($allPass) {
    Write-Host "  All tests PASSED!"
} else {
    Write-Host "  Some tests FAILED. Check report files above."
}
Write-Host ""
