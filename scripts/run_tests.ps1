#!/usr/bin/env pwsh
# Run all tests for Storj Monitor

param(
    [switch]$Verbose,
    [switch]$Coverage,
    [string]$TestPattern = "",
    [switch]$Integration
)

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath
$PythonPath = Join-Path $ProjectRoot "venv\Scripts\python.exe"

# Check if Python virtual environment exists
if (-not (Test-Path $PythonPath)) {
    Write-Error "Python virtual environment not found. Run setup.ps1 first."
    exit 1
}

Write-Host "Running Storj Monitor Tests..." -ForegroundColor Green

# Set working directory to project root
Set-Location $ProjectRoot

# Build pytest command
$pytestArgs = @("-m", "pytest")

if ($TestPattern) {
    $pytestArgs += "-k", $TestPattern
    Write-Host "Running tests matching pattern: $TestPattern" -ForegroundColor Cyan
}

if ($Verbose) {
    $pytestArgs += "-v"
    Write-Host "Verbose output enabled" -ForegroundColor Cyan
}

if ($Coverage) {
    $pytestArgs += "--cov=storj_monitor", "--cov=collector", "--cov=webapp", "--cov-report=html", "--cov-report=term"
    Write-Host "Coverage analysis enabled" -ForegroundColor Cyan
}

if ($Integration) {
    $pytestArgs += "tests/test_integration.py"
    Write-Host "Running integration tests only" -ForegroundColor Cyan
} else {
    $pytestArgs += "tests/"
}

# Add additional pytest options
$pytestArgs += "--tb=short"  # Short traceback format
$pytestArgs += "--color=yes"  # Colored output

Write-Host "Command: $PythonPath $($pytestArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Run the tests
try {
    & $PythonPath $pytestArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "All tests passed!" -ForegroundColor Green
        
        if ($Coverage) {
            Write-Host "Coverage report generated in htmlcov/ directory" -ForegroundColor Cyan
        }
    } else {
        Write-Host ""
        Write-Host "Some tests failed. Exit code: $exitCode" -ForegroundColor Red
    }
    
    exit $exitCode
} catch {
    Write-Error "Failed to run tests: $_"
    exit 1
}