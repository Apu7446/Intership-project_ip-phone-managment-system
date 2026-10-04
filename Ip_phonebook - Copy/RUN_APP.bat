@echo off
title SBAC Bank PLC — IP Phone Management System
color 0A
cls
cd /d "%~dp0"

echo ====================================================================
echo    SBAC BANK PLC — IP Phone Management System (Auto Launcher)
echo ====================================================================
echo.

:: 1. Verify if system Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed on this PC or not added to PATH!
    echo.
    echo Please install Python 3.10+ and make sure to tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Verify if the copied venv actually works on this specific PC
set VENV_OK=0
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set VENV_OK=1
    ) else (
        echo [*] Detected copied virtual environment from another PC.
        echo [*] Cleaning and recreating fresh environment for this computer...
        rmdir /s /q venv >nul 2>&1
    )
)

:: 3. Create fresh venv if not working
if "%VENV_OK%"=="0" (
    echo [*] Setting up fresh Python environment on this PC - one-time setup...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create virtual environment. Running directly with system Python...
        goto RUN_SYSTEM_PYTHON
    )
    echo [*] Installing required libraries: customtkinter, mysql-connector, etc...
    venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [*] Retrying library installation with visible progress...
        venv\Scripts\python.exe -m pip install -r requirements.txt
    )
    echo [OK] Setup completed successfully!
    echo.
)

:: 4. Ensure Desktop Shortcut is updated with official SBAC Bank logo
cscript //nologo create_shortcut.vbs >nul 2>&1

:: 5. Launch the application with virtual environment
echo [*] Launching IP Phone System...
venv\Scripts\python.exe main.py
if not errorlevel 1 goto END

:RUN_SYSTEM_PYTHON
echo [*] Launching with system Python...
python main.py

:END
if errorlevel 1 (
    echo.
    echo ====================================================================
    echo [NOTICE] Application closed.
    echo If database connection failed, ensure Host Server MySQL is running.
    echo ====================================================================
    pause
)
