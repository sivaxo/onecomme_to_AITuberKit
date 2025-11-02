@echo off
setlocal

chcp 65001 > nul
title OneComme x AITuberKit Bridge

echo ========================================
echo   OneComme x AITuberKit Bridge
echo ========================================
echo.

if exist venv\Scripts\activate.bat (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found.
    echo [INFO] Using system Python interpreter.
    echo.
)

if not exist logs (
    mkdir logs
)

if exist requirements.txt (
    echo [INFO] Verifying Python dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
)

echo [INFO] Starting bridge...
echo.
python -m src.main
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo ========================================
    echo   Bridge exited with errors
    echo ========================================
    echo Exit code: %EXITCODE%
    echo See logs\system.log for details.
    echo.
    pause
) else (
    echo ========================================
    echo   Bridge stopped normally
    echo ========================================
    echo.
    timeout /t 3 > nul
)

endlocal
