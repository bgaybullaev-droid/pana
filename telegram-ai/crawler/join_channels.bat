@echo off
REM Auto-join all configured Telegram channels

cd /d "%~dp0"

echo ============================================================
echo Telegram Channel Auto-Join Script
echo ============================================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Run join script
python join_channels.py

pause
