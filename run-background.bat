@echo off
REM Run Storj Monitor Dashboard in background
cd /d "C:\Users\lawre\py_projs\storj-monitor"

REM Log file for debugging
set LOGFILE=logs\service.log

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start the application in background
echo [%date% %time%] Starting Storj Monitor Dashboard... >> "%LOGFILE%"
python main.py >> "%LOGFILE%" 2>&1