# Cài Văn phòng Agent Kế toán (chạy một lần): bấm đúp CAI_DAT.cmd ở thư mục gốc
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$root = (Get-Location).Path

Write-Host "1/4 Môi trường Python..."
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -e .

Write-Host "2/4 Claude Code dòng lệnh..."
$env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "   Đang tải Claude Code (vài phút, đừng bấm chuột vào cửa sổ)..."
    Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
}

Write-Host "3/4 File cấu hình .env..."
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "4/4 Biểu tượng trên màn hình..."
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Văn phòng Agent.lnk"))
$lnk.TargetPath = "$root\MO_VAN_PHONG.cmd"
$lnk.WorkingDirectory = $root
$lnk.IconLocation = "$env:SystemRoot\System32\imageres.dll,1"
$lnk.Save()

& .\.venv\Scripts\python.exe -m vpak.kiem_tra
Write-Host ""
Write-Host "Nếu mục Claude Code báo chưa đăng nhập: mở PowerShell, gõ claude, rồi gõ /login."
Write-Host "Từ nay đại ca chỉ cần bấm đúp biểu tượng 'Văn phòng Agent' trên màn hình."
Read-Host "Bấm Enter để đóng"
