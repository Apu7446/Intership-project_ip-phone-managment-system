@echo off
title SBAC Bank PLC — Automated Server PC Setup (1-Click)
color 0B
cls

:: 1. Elevate to Administrator if not already running as Admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ====================================================================
    echo    SBAC BANK PLC — IP Phone Management System
    echo ====================================================================
    echo [*] Requesting Administrator privileges to configure Windows Firewall...
    echo.
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:: Always ensure we are in the script's own directory
cd /d "%~dp0"

echo ====================================================================
echo    SBAC BANK PLC — Automated Server PC Setup Tool
echo ====================================================================
echo.

:: 2. Configure Windows Defender Firewall Inbound Rule for MySQL Port 3306
echo [*] Step 1/3: Configuring Windows Firewall for MySQL Port 3306...
netsh advfirewall firewall show rule name="SBAC_MySQL_Port_3306" >nul 2>&1
if %errorlevel% neq 0 (
    netsh advfirewall firewall add rule name="SBAC_MySQL_Port_3306" dir=in action=allow protocol=TCP localport=3306 profile=any >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Windows Firewall Inbound Rule for Port 3306 created successfully!
    ) else (
        echo [!] Warning: Could not automatically add firewall rule via netsh.
    )
) else (
    echo [OK] Windows Firewall Rule for Port 3306 is already enabled.
)
echo.

:: 3. Check Python and Virtual Environment
echo [*] Step 2/3: Checking Python Environment...
set PYTHON_CMD=
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=venv\Scripts\python.exe
    )
)

if "%PYTHON_CMD%"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.10+ and make sure "Add Python to PATH" is checked.
        echo.
        pause
        exit /b 1
    )
)

:: Ensure mysql-connector-python is installed
"%PYTHON_CMD%" -c "import mysql.connector" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required mysql-connector package...
    "%PYTHON_CMD%" -m pip install mysql-connector-python --quiet
)
echo [OK] Python environment ready (%PYTHON_CMD%).
echo.

:: 4. Run setup_server.py
echo [*] Step 3/3: Running Automated Database and Network Setup...
echo.
"%PYTHON_CMD%" setup_server.py
if errorlevel 1 (
    echo.
    echo [ERROR] Server setup encountered an error. Please review the messages above.
    pause
    exit /b 1
)

:: 5. Create Desktop Shortcut for RUN_APP if vbs exists
if exist "create_shortcut.vbs" (
    cscript //nologo create_shortcut.vbs >nul 2>&1
)

echo.
echo ====================================================================
echo  [SUCCESS] All setup operations completed!
echo  Check SERVER_INFO.txt in this folder for Client PC IP instructions.
echo ====================================================================
echo.
set /p LAUNCH="Would you like to start the IP Phone System application now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" RUN_APP.bat
)
exit /b 0
