@echo off
REM Simple startup script for Storj Monitor Dashboard
REM Place this in your Windows Startup folder for automatic boot startup

cd /d "C:\Users\lawre\py_projs\storj-monitor"

REM Check if already running
tasklist /FI "IMAGENAME eq python.exe" | find "python.exe" > nul
if %errorlevel% == 0 (
    echo Storj Monitor may already be running. Check http://localhost:8080
    timeout /t 5 /nobreak > nul
    exit /b
)

REM Create logs directory if needed
if not exist logs mkdir logs

REM Start the service in background
echo Starting Storj Monitor Dashboard...
start /B "" python main.py > logs\startup.log 2>&1

REM Give it time to start
timeout /t 10 /nobreak > nul

REM Check if it started successfully
tasklist /FI "IMAGENAME eq python.exe" | find "python.exe" > nul
if %errorlevel% == 0 (
    echo Storj Monitor Dashboard started successfully!
    echo Access it at: http://localhost:8080
) else (
    echo Failed to start Storj Monitor Dashboard
    echo Check logs\startup.log for details
)

timeout /t 5 /nobreak > nul