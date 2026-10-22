@echo off
:: Quick Launcher for Project Cleaner on Windows
chcp 65001 >nul
title Project Cleaner for Windows
cd /d "%~dp0"

python cleaner.py %*

:: Pause if executed via double-click without arguments
if "%~1"=="" (
    echo.
    pause
)
