@echo off
setlocal
title Game Collection
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python or add it to PATH.
    pause
    exit /b 1
)

python run_demo.py
if errorlevel 1 (
    echo.
    echo The app could not start. Keep this window open and check the error above.
    pause
)
