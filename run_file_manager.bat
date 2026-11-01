@echo off
title Inercorp Disk Usage & File Manager
cd /d "%~dp0"
python file_manager.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Terjadi kendala saat menjalankan aplikasi.
    pause
)

