@echo off
title Claude Code Auto-Continue
cd /d "%~dp0"
echo ============================================================
echo   Starting Claude Code Auto-Continue Automation...
echo ============================================================
python auto_continue.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script ended with an error code: %ERRORLEVEL%
    pause
)
