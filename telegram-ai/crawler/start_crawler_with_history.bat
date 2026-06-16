@echo off
REM Start Flexible Crawler with Historical Message Processing

cd /d "%~dp0"

echo ============================================================
echo Telegram Crawler - With Historical Processing
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

echo [INFO] Starting crawler with historical message processing...
echo [INFO] Edit .env to configure PROCESS_HISTORICAL_MESSAGES
echo.

REM Run crawler
python FlexibleCrawlerWithHistory.py

pause
