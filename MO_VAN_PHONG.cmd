@echo off
chcp 65001 >nul
title Van phong Agent
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\chay.ps1"
