@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 文献总结自动化 - 交互式入口
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_workflow.ps1"
echo.
pause
