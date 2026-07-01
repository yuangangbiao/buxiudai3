# INSIGHTFACE buffalo_l 模型下载脚本
$MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
$MODEL_DIR = "d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\models\buffalo_l"
$ZIP_FILE = "$MODEL_DIR\buffalo_l.zip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INSIGHTFACE buffalo_l 模型下载工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 创建目录
if (!(Test-Path $MODEL_DIR)) {
    New-Item -ItemType Directory -Path $MODEL_DIR -Force | Out-Null
}

# 检查是否已存在
if (Test-Path $ZIP_FILE) {
    Write-Host "`n发现已下载的压缩包: $ZIP_FILE" -ForegroundColor Yellow
    $response = Read-Host "是否重新下载？(y/N)"
    if ($response -ne "y") {
        Write-Host "跳过下载，直接解压..." -ForegroundColor Yellow
    } else {
        Remove-Item $ZIP_FILE -Force
    }
}

# 下载文件
if (!(Test-Path $ZIP_FILE)) {
    Write-Host "`n开始下载模型..." -ForegroundColor Green
    Write-Host "下载地址: $MODEL_URL" -ForegroundColor Gray
    Write-Host "保存位置: $ZIP_FILE" -ForegroundColor Gray

    try {
        # 使用 WebClient 下载，显示进度
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($MODEL_URL, $ZIP_FILE)
        $webClient.Dispose()

        Write-Host "`n模型下载完成！" -ForegroundColor Green
    } catch {
        Write-Host "`n下载失败: $_" -ForegroundColor Red
        exit 1
    }
}

# 解压
Write-Host "`n开始解压模型..." -ForegroundColor Green

try {
    Expand-Archive -Path $ZIP_FILE -DestinationPath $MODEL_DIR -Force

    Write-Host "模型解压完成！" -ForegroundColor Green
    Write-Host "`n模型文件位置: $MODEL_DIR" -ForegroundColor Cyan

    # 列出文件
    Write-Host "`n模型文件列表:" -ForegroundColor Yellow
    Get-ChildItem $MODEL_DIR -File | ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  - $($_.Name) ($sizeMB MB)" -ForegroundColor White
    }

    # 检查子目录
    $subDir = Join-Path $MODEL_DIR "2d106det"
    if (Test-Path $subDir) {
        Get-ChildItem $subDir -File | ForEach-Object {
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            Write-Host "  - 2d106det/$($_.Name) ($sizeMB MB)" -ForegroundColor White
        }
    }

} catch {
    Write-Host "`n解压失败: $_" -ForegroundColor Red
    exit 1
}

# 验证
Write-Host "`n验证模型文件..." -ForegroundColor Green

$requiredFiles = @("buffalo_l.json", "det_10g.onnx", "w600k_r50.onnx")
$allExist = $true

foreach ($file in $requiredFiles) {
    $filePath = Join-Path $MODEL_DIR $file
    if (Test-Path $filePath) {
        $sizeMB = [math]::Round((Get-Item $filePath).Length / 1MB, 2)
        Write-Host "  [OK] $file ($sizeMB MB)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $file" -ForegroundColor Red
        $allExist = $false
    }
}

# 检查2d106det
$subOnnx = Join-Path $MODEL_DIR "2d106det\2d106det.onnx"
if (Test-Path $subOnnx) {
    $sizeMB = [math]::Round((Get-Item $subOnnx).Length / 1MB, 2)
    Write-Host "  [OK] 2d106det/2d106det.onnx ($sizeMB MB)" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] 2d106det/2d106det.onnx" -ForegroundColor Red
    $allExist = $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allExist) {
    Write-Host "模型准备完成！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "下一步操作:" -ForegroundColor Yellow
    Write-Host "1. 安装依赖: pip install insightface onnxruntime-gpu" -ForegroundColor White
    Write-Host "2. 配置模型路径（见部署方案文档）" -ForegroundColor White
} else {
    Write-Host "模型验证失败，请检查网络后重试！" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
