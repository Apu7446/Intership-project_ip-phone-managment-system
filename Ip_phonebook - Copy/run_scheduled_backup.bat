@echo off
REM ==============================================================================
REM SBAC IP Phone Management System — Automated Scheduled Database Backup Runner
REM ==============================================================================
cd /d "%~dp0"

IF EXIST "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" "auto_backup.py" >> "backups\scheduler_log.txt" 2>&1
) ELSE (
    python "auto_backup.py" >> "backups\scheduler_log.txt" 2>&1
)
exit /b %ERRORLEVEL%
