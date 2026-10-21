$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
$Version = if ($env:OMA_APP_VERSION) { $env:OMA_APP_VERSION } else { "0.1.2" }
$env:OMA_APP_VERSION = $Version

if (-not (Test-Path "models/inpainting_lama_2025jan.onnx")) {
    uv run oma-watermark-download-model
}

npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
npm run build:css
if ($LASTEXITCODE -ne 0) { throw "CSS build failed" }

Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
uv sync --extra desktop
uv run pyinstaller packaging/oma-watermark.spec --noconfirm --clean

$AppDir = "dist/Watermark Remover"
if (-not (Test-Path "$AppDir/Watermark Remover.exe")) {
    throw "Windows app was not created"
}

$Zip = "dist/Watermark-Remover-$Version-windows.zip"
Compress-Archive -Path "$AppDir/*" -DestinationPath $Zip -Force
Write-Output "Built $Zip"
