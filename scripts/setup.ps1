# Storj Monitor Setup Script
# This script sets up the Python virtual environment and installs dependencies

Write-Host "Setting up Storj Monitor..." -ForegroundColor Green

# Check if Python 3.13 is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Blue
    
    if (-not ($pythonVersion -match "Python 3\.13")) {
        Write-Warning "Python 3.13 is recommended. Current version: $pythonVersion"
    }
} catch {
    Write-Error "Python not found! Please install Python 3.13 first."
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

Write-Host "Setup complete! To activate the virtual environment, run: venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "To initialize the database, run: python scripts\init_db.py" -ForegroundColor Cyan