@echo off
REM Start Storj Monitor Dashboard
REM Change to the project directory
cd /d "C:\Users\lawre\py_projs\storj-monitor"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

REM Start the application
echo Starting Storj Monitor Dashboard...
echo Access the dashboard at http://localhost:8080
python main.py

pause