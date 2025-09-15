@echo off
echo =====================================================
echo Starting Storj Monitor with Satellite Tracking
echo =====================================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup first.
    pause
    exit /b 1
)

REM Activate virtual environment  
call venv\Scripts\activate.bat

echo.
echo [1/3] Starting Data Collector with Satellite Tracking...
start "Storj Monitor Collector" /min python -m collector.service

REM Wait a moment for collector to start
timeout /t 3 /nobreak > nul

echo [2/3] Starting Web Server...  
start "Storj Monitor Web Server" /min python -m webapp.server

REM Wait for web server to start
timeout /t 5 /nobreak > nul

echo [3/3] Opening Dashboard...
start "" "http://localhost:8000"

echo.
echo =====================================================
echo ✅ Storj Monitor is now running with satellite data!
echo =====================================================
echo.
echo 🌐 Dashboard:     http://localhost:8000
echo 🗄️  Database:      http://localhost:8000/db
echo 🛰️  Satellites:    Check /api/satellites endpoint
echo 📊 API Docs:      http://localhost:8000/api/docs
echo.
echo 📁 Logs are in the 'logs' directory
echo.
echo To stop: Close both command windows or press Ctrl+C in each
echo.
pause