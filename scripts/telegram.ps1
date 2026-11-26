# Mở phiên Claude Code nhận lệnh qua Telegram. Chạy: powershell -ExecutionPolicy Bypass -File scripts\telegram.ps1
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:Path = "$PWD\.venv\Scripts;" + $env:Path
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
claude --channels plugin:telegram@claude-plugins-official --allowedTools "Bash(python -m vpak.giao_viec:*)"
