# Mở dashboard Văn phòng Agent. Chạy: powershell -ExecutionPolicy Bypass -File scripts\chay.ps1
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:Path = "$PWD\.venv\Scripts;" + $env:Path
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
Start-Process "http://127.0.0.1:8765"
python -m vpak.server
