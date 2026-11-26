# Cài Văn phòng Agent Kế toán lần đầu. Chạy: powershell -ExecutionPolicy Bypass -File scripts\cai_dat.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv")) {
    Write-Host "Đang tạo môi trường Python riêng (.venv)..."
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e .
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Đã tạo file .env. Đại ca mở file này bằng Notepad và điền các khóa còn trống."
}
& .\.venv\Scripts\python.exe -m vpak.kiem_tra
