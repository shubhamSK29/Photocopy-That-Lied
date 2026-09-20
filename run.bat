@echo off
REM Photocopy That Lied - Windows Batch Launcher
REM This script launches the PowerShell startup script

cd /d "%~dp0"
call powershell.exe -ExecutionPolicy Bypass -NoProfile -File run.ps1
