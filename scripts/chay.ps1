# Mở dashboard Văn phòng Agent
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:Path = "$PWD\.venv\Scripts;$env:USERPROFILE\.local\bin;" + $env:Path
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
Start-Process "http://127.0.0.1:8765"
Write-Host "Văn phòng Agent đang chạy. Giữ cửa sổ này mở; đóng cửa sổ là tắt dashboard."
python -m vpak.server
