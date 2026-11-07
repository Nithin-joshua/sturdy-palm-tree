@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo Multimodal Industrial Inspection Agent - Launcher
echo ========================================================

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.10 or higher from https://python.org
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [INFO] Creating Python virtual environment in .venv...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Initializing .env configuration from .env.example...
        copy .env.example .env >nul
    )
)

echo [INFO] Ensuring core lightweight dependencies are installed...
pip install -r backend\requirements.txt --quiet

echo ========================================================
echo Service starting at http://localhost:8000
echo Open http://localhost:8000 in your web browser.
echo Press Ctrl+C to terminate the server.
echo ========================================================

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
pause
